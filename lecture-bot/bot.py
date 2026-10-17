"""Telegram bot: students send a lecture recording (or a YouTube link) and get back study material."""
import asyncio
import logging
import shutil
import tempfile
import time
import uuid
from html import escape
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Poll, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import NetworkError, TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler,
                          PicklePersistence, filters)

from lecturebot import config, pipeline
from lecturebot.analyze import MAJOR_NAMES, AnalysisError
from lecturebot.media import Source, download_youtube, find_youtube_url, probe_duration

logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("lecturebot")

CLOUD_DOWNLOAD_LIMIT = 20 * 1024 * 1024  # Telegram's cloud Bot API refuses bigger downloads
KEEP_LECTURES = 5                        # results kept per student for the quiz/cards buttons
JOBS = asyncio.Semaphore(1)              # one heavy transcription at a time
_waiting = 0

WELCOME = (
    "أهلاً بك 👋\n\n"
    "أرسل لي <b>تسجيل المحاضرة</b> (صوت أو فيديو أو رسالة صوتية) أو <b>رابط يوتيوب</b>، "
    "وأرجع لك:\n"
    "• ملخصاً مرتباً بالعناوين، وبجانب كل نقطة وقتها في التسجيل\n"
    "• المصطلحات الإنجليزية مع معناها\n"
    "• أسئلة اختيار من متعدد، وبطاقات مراجعة\n"
    "• النص الكامل للمحاضرة\n"
    "• كل ذلك في ملف PDF جاهز للمذاكرة\n\n"
    "📸 عندك صور للسبورة أو الشرائح؟ أرسلها <b>قبل</b> المحاضرة، وأضمّها للملخص.\n"
    "🎓 اختر تخصصك بالأمر /major لتكون المصطلحات أدق.\n"
    "🔒 لا أحتفظ بتسجيلاتك: أحذفها فور الانتهاء. /privacy للتفاصيل."
)

PRIVACY = (
    "🔒 <b>خصوصيتك</b>\n\n"
    "• التسجيل والصور تُحذف من الخادم فور انتهاء المعالجة.\n"
    "• لا تُشارك محاضراتك مع أحد، ولا تُستخدم لأي غرض آخر.\n"
    "• أحتفظ فقط بنص آخر محاضراتك والأسئلة، لتعمل أزرار الاختبار والبطاقات. "
    "يمكنك حذفها كلها في أي وقت بالأمر /delete."
)


# ---------- helpers ----------

def _majors_keyboard() -> InlineKeyboardMarkup:
    rows, row = [], []
    for key, name in MAJOR_NAMES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"major:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    row.append(InlineKeyboardButton("أخرى / عام", callback_data="major:none"))
    rows.append(row)
    return InlineKeyboardMarkup(rows)


def _result_keyboard(lid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 اختبرني", callback_data=f"quiz:{lid}"),
         InlineKeyboardButton("🃏 بطاقات المراجعة", callback_data=f"cards:{lid}")],
        [InlineKeyboardButton("📄 النص الكامل", callback_data=f"txt:{lid}"),
         InlineKeyboardButton("🗑 حذف", callback_data=f"del:{lid}")],
    ])


def _minutes(seconds: float) -> str:
    m = max(1, round(seconds / 60))
    return "دقيقة واحدة" if m == 1 else ("دقيقتين" if m == 2 else f"{m} دقائق" if m <= 10 else f"{m} دقيقة")


def _quick_summary(analysis: dict) -> str:
    lines = [f"✅ <b>{escape(analysis.get('title', 'ملخص المحاضرة'))}</b>"]
    if analysis.get("overview"):
        lines.append(escape(analysis["overview"]))
    heads = [s.get("heading", "") for s in analysis.get("sections", []) if s.get("heading")]
    if heads:
        lines.append("\n<b>محاور المحاضرة:</b>")
        lines += [f"• {escape(h)} <code>{escape(s.get('time', ''))}</code>"
                  for h, s in zip(heads, analysis["sections"])]
    lines.append(f"\n🧪 {len(analysis.get('mcq', []))} سؤالاً · 🃏 {len(analysis.get('flashcards', []))} بطاقة"
                 " · الملف الكامل في الأسفل 👇")
    text = "\n".join(lines)
    return text if len(text) < 4000 else text[:3990] + "…"


class Progress:
    """Edits one status message as the job moves on, without flooding Telegram."""

    STAGES = {"transcribe": "🎧 أحوّل الكلام إلى نص", "analyze": "🧠 أكتب الملخص والأسئلة",
              "render": "📄 أجهّز ملف PDF"}

    def __init__(self, msg: Message, loop: asyncio.AbstractEventLoop, eta_seconds: int):
        self.msg, self.loop, self.deadline = msg, loop, time.time() + eta_seconds
        self.last_text, self.last_edit = "", 0.0

    def update(self, stage: str, fraction: float) -> None:  # called from the worker thread
        now = time.time()
        if stage == "transcribe" and now - self.last_edit < 15 and fraction < 1:
            return
        self.last_edit = now
        bar = f" {int(fraction * 100)}%" if stage == "transcribe" else ""
        left = self.deadline - now
        eta = f"\n⏱ متبقٍّ تقريباً: {_minutes(left)}" if left > 30 else ""
        text = f"{self.STAGES.get(stage, '⏳ أعمل على المحاضرة')}{bar}…{eta}"
        if text != self.last_text:
            self.last_text = text
            asyncio.run_coroutine_threadsafe(self._edit(text), self.loop)

    async def _edit(self, text: str) -> None:
        try:
            await self.msg.edit_text(text)
        except TelegramError:
            pass


# ---------- commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(WELCOME, parse_mode=ParseMode.HTML)
    if "major" not in context.user_data:
        await update.effective_message.reply_text("ما تخصصك؟", reply_markup=_majors_keyboard())


async def major_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("اختر تخصصك:", reply_markup=_majors_keyboard())


async def privacy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(PRIVACY, parse_mode=ParseMode.HTML)


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("lectures", None)
    context.user_data.pop("pending_images", None)
    await update.effective_message.reply_text("🗑 حذفت كل محاضراتك وصورك المحفوظة.")


# ---------- photos of the board / slides ----------

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg.photo:
        file_id, mime = msg.photo[-1].file_id, "image/jpeg"
    else:
        file_id, mime = msg.document.file_id, msg.document.mime_type or "image/jpeg"
    if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        await msg.reply_text("أرسل الصورة بصيغة JPG أو PNG.")
        return
    pending = [p for p in context.user_data.get("pending_images", [])
               if time.time() - p[1] < config.PENDING_IMAGES_TTL_MINUTES * 60]
    if len(pending) >= config.MAX_IMAGES_PER_LECTURE:
        await msg.reply_text(f"وصلت للحد الأعلى ({config.MAX_IMAGES_PER_LECTURE} صورة). أرسل المحاضرة الآن.")
        return
    pending.append((file_id, time.time(), mime))
    context.user_data["pending_images"] = pending
    await msg.reply_text(f"📸 حفظت الصورة ({len(pending)}). أرسل صوراً أخرى، أو أرسل تسجيل المحاضرة.")


# ---------- the lecture job ----------

async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    media = msg.audio or msg.voice or msg.video or msg.video_note or msg.document
    if media.file_size and media.file_size > CLOUD_DOWNLOAD_LIMIT and not config.TELEGRAM_LOCAL_API_URL:
        await msg.reply_text(
            "⚠️ الملف أكبر من 20 ميغابايت، وهذا أكبر حجم يستطيع البوت تنزيله حالياً.\n"
            "الحلول: أرسل التسجيل <b>صوتاً فقط</b> (m4a أو mp3 بجودة منخفضة)، أو قسّمه جزأين، "
            "أو ارفعه على يوتيوب (غير مدرج) وأرسل الرابط.", parse_mode=ParseMode.HTML)
        return
    title = getattr(media, "title", None) or getattr(media, "file_name", None) or ""
    await _run_job(update, context, title=Path(title).stem if title else "", tg_file=media)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = find_youtube_url(update.effective_message.text)
    if url:
        await _run_job(update, context, url=url)
    else:
        await update.effective_message.reply_text(
            "أرسل تسجيل المحاضرة (ملف صوت أو فيديو) أو رابط يوتيوب، وأجهّز لك الملخص والأسئلة.")


async def _run_job(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str = "", tg_file=None,
                   url: str | None = None) -> None:
    global _waiting
    msg = update.effective_message
    major = context.user_data.get("major")
    images_meta = [p for p in context.user_data.pop("pending_images", [])
                   if time.time() - p[1] < config.PENDING_IMAGES_TTL_MINUTES * 60]
    status = await msg.reply_text("⏳ استلمت المحاضرة…" + (f"\n📸 مع {len(images_meta)} صورة" if images_meta else ""))

    work = Path(tempfile.mkdtemp(prefix="lec_", dir=_work_root()))
    queued = JOBS.locked()
    if queued:
        _waiting += 1
        await status.edit_text(f"⏳ في الطابور: قبلك {_waiting} محاضرة. أبدأ بمحاضرتك فور انتهائها.")
    try:
        async with JOBS:
            if queued:
                _waiting -= 1
                queued = False
            await status.edit_text("⬇️ أنزّل المحاضرة…")
            if url:
                source = await asyncio.to_thread(download_youtube, url, work)
            else:
                f = await tg_file.get_file()
                path = work / ("input" + (Path(f.file_path).suffix if f.file_path else ""))
                await f.download_to_drive(path)
                source = Source(path=path, title=title)
            images = []
            for file_id, _, mime in images_meta:
                f = await context.bot.get_file(file_id)
                images.append((bytes(await f.download_as_bytearray()), mime))

            source.duration = source.duration or probe_duration(source.path)
            eta = pipeline.estimate_seconds(source.duration)
            await status.edit_text(f"🎧 بدأت العمل على المحاضرة ({_minutes(source.duration)}).\n"
                                   f"⏱ الوقت المتوقع: {_minutes(eta)}")
            progress = Progress(status, asyncio.get_running_loop(), eta)
            await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
            result = await asyncio.to_thread(pipeline.run, source, work, major, images, progress.update)

        lid = uuid.uuid4().hex[:8]
        lectures = context.user_data.setdefault("lectures", {})
        lectures[lid] = {"title": result.analysis.get("title", ""), "mcq": result.analysis.get("mcq", []),
                         "flashcards": result.analysis.get("flashcards", []),
                         "transcript": result.transcript_text, "time": time.time()}
        for old in sorted(lectures, key=lambda k: lectures[k]["time"])[:-KEEP_LECTURES]:
            del lectures[old]

        await status.delete()
        await msg.reply_text(_quick_summary(result.analysis), parse_mode=ParseMode.HTML)
        with open(result.pdf_path, "rb") as fh:
            await msg.reply_document(fh, filename=result.pdf_path.name, reply_markup=_result_keyboard(lid),
                                     caption="📄 الملخص الكامل: المحاور، والمصطلحات، والأسئلة مع الإجابات، "
                                             "والبطاقات، والنص الكامل.")
    except pipeline.LectureTooLong:
        await status.edit_text(f"⚠️ المحاضرة أطول من {config.MAX_LECTURE_MINUTES} دقيقة. قسّمها وأرسلها على أجزاء.")
    except AnalysisError as e:
        log.warning("analysis failed: %s", e)
        await status.edit_text("⚠️ تعذّر كتابة الملخص هذه المرة. أعد إرسال المحاضرة بعد قليل.")
    except Exception:
        log.exception("job failed")
        await status.edit_text("⚠️ حدث خطأ أثناء المعالجة. تأكد أن الملف تسجيل صوتي أو فيديو، ثم أعد المحاولة.")
    finally:
        if queued:  # cancelled while still waiting in the queue
            _waiting -= 1
        shutil.rmtree(work, ignore_errors=True)  # the recording never stays on the server


def _work_root() -> str:
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    return str(config.WORK_DIR)


# ---------- buttons ----------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    action, _, arg = (q.data or "").partition(":")
    chat_id = q.message.chat_id

    if action == "major":
        if arg == "none":
            context.user_data.pop("major", None)
            await q.edit_message_text("تم. سأتعامل مع محاضراتك كتخصص عام.")
        else:
            context.user_data["major"] = arg
            await q.edit_message_text(f"🎓 تم اختيار: {MAJOR_NAMES.get(arg, arg)}. أرسل تسجيل المحاضرة الآن.")
        return

    lec = context.user_data.get("lectures", {}).get(arg)
    if not lec:
        await context.bot.send_message(chat_id, "لم أعد أحتفظ بهذه المحاضرة. أرسلها من جديد.")
        return

    if action == "quiz":
        for i, item in enumerate(lec["mcq"], 1):
            try:
                await context.bot.send_poll(
                    chat_id, f"{i}. {item['question']}"[:300], [o[:100] for o in item["options"]],
                    type=Poll.QUIZ, correct_option_id=item["answer_index"],
                    explanation=(item.get("explanation", "") + (f" ⏱ {item['time']}" if item.get("time") else ""))[:200],
                    is_anonymous=False,
                )
            except TelegramError as e:
                log.warning("poll failed: %s", e)
            await asyncio.sleep(0.4)
    elif action == "cards":
        cards = lec["flashcards"]
        for start_i in range(0, len(cards), 5):
            chunk = cards[start_i:start_i + 5]
            text = "\n\n".join(f"❓ <b>{escape(c['front'])}</b>\n<tg-spoiler>{escape(c['back'])}</tg-spoiler>"
                               for c in chunk)
            await context.bot.send_message(chat_id, ("🃏 اضغط على الجواب المخفي لكشفه\n\n" if start_i == 0 else "")
                                           + text, parse_mode=ParseMode.HTML)
    elif action == "txt":
        name = pipeline.safe_name(lec["title"]) + ".txt"
        await context.bot.send_document(chat_id, lec["transcript"].encode("utf-8"), filename=name,
                                        caption="📄 النص الكامل للمحاضرة، مع وقت كل فقرة.")
    elif action == "del":
        del context.user_data["lectures"][arg]
        await context.bot.send_message(chat_id, "🗑 حذفت بيانات هذه المحاضرة.")


# ---------- startup ----------

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, NetworkError):  # brief connection drops; polling retries on its own
        log.warning("network error: %s", context.error)
        return
    log.error("unhandled error", exc_info=context.error)


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (see .env.example)")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    builder = (Application.builder().token(config.TELEGRAM_BOT_TOKEN)
               .persistence(PicklePersistence(filepath=config.DATA_DIR / "state.pickle"))
               .concurrent_updates(True))
    if config.TELEGRAM_LOCAL_API_URL:
        builder = (builder.base_url(f"{config.TELEGRAM_LOCAL_API_URL}/bot")
                   .base_file_url(f"{config.TELEGRAM_LOCAL_API_URL}/file/bot").local_mode(True))
    app = builder.build()

    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("major", major_cmd))
    app.add_handler(CommandHandler("privacy", privacy_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(
        filters.AUDIO | filters.VOICE | filters.VIDEO | filters.VIDEO_NOTE
        | filters.Document.AUDIO | filters.Document.VIDEO, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_error_handler(on_error)
    log.info("bot starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
