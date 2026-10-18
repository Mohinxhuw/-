"""Telegram bot: students send a lecture recording (or a YouTube / Google Drive link) and get back study material."""
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
from telegram.error import BadRequest, NetworkError, TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler,
                          PicklePersistence, filters)

from lecturebot import config, materials, mindmap, pipeline, render, study
from lecturebot.analyze import MAJOR_NAMES, AnalysisError
from lecturebot.media import Source, download_url, find_media_url
from lecturebot.transcribe import DIALECTS

logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)  # WeasyPrint's font subsetting is chatty
log = logging.getLogger("lecturebot")

CLOUD_DOWNLOAD_LIMIT = 20 * 1024 * 1024  # Telegram's cloud Bot API refuses bigger downloads
KEEP_LECTURES = config.KEEP_LECTURES     # lectures kept per student for the study buttons and /exam
ASK_HISTORY = 6                          # earlier question/answer turns sent with a new question
JOBS = asyncio.Semaphore(config.MAX_PARALLEL_JOBS)
# A local Bot API server answers getFile only after it has fetched the whole file from Telegram,
# which takes minutes for a long recording; the library's default is a few seconds.
BIG_FILE_TIMEOUTS = {"read_timeout": 1800, "write_timeout": 60, "connect_timeout": 30, "pool_timeout": 30}
_waiting = 0

WELCOME = (
    "أهلاً بك في <b>فَهيم</b> 👋\n\n"
    "أرسل لي <b>تسجيل المحاضرة</b> (صوت أو فيديو أو رسالة صوتية)، أو <b>رابط يوتيوب</b> "
    "أو <b>Google Drive</b>، وأرجع لك:\n"
    "• ملخصاً مرتباً بالعناوين، يصلك جزءاً جزءاً، وبجانب كل نقطة وقتها في التسجيل\n"
    "• المصطلحات الإنجليزية مع معناها\n"
    "• أسئلة اختيار من متعدد، وأسئلة صح أو خطأ، وبطاقات مراجعة\n"
    "• النص الكامل للمحاضرة\n"
    "• كل ذلك في ملف PDF جاهز للمذاكرة\n\n"
    "🧩 المحاضرة على عدة أجزاء أو رسائل صوتية؟ أرسلها كلها متتالية، وأجمعها في ملخص واحد.\n"
    "📎 عندك شرائح المحاضرة (PDF أو PowerPoint) أو صور السبورة؟ أرسلها مع التسجيل لملخص أدق.\n"
    "🧠 بعد كل محاضرة: خريطة ذهنية، وجداول مقارنة، واسألني عن أي شيء فيها، أو اطلب شرحاً أبسط.\n"
    "🔁 /review مراجعة يومية للبطاقات بتذكير · 🌙 /exam ملخص ليلة الاختبار لعدة محاضرات\n"
    "🎓 /major لاختيار تخصصك · 🗣 /dialect للهجة المحاضر\n"
    "🔒 لا أحتفظ بتسجيلاتك: أحذفها فور الانتهاء. /privacy للتفاصيل."
)

PRIVACY = (
    "🔒 <b>خصوصيتك</b>\n\n"
    "• التسجيل والملفات والصور تُحذف من الخادم فور انتهاء المعالجة.\n"
    "• تُعالج المحاضرة عبر خدمات ذكاء اصطناعي (لتحويل الكلام إلى نص وكتابة الملخص)، "
    "ولا تُشارك مع أحد، ولا تُستخدم لأي غرض آخر.\n"
    "• أحتفظ فقط بنص آخر محاضراتك والأسئلة، لتعمل أزرار الاختبار والبطاقات. "
    "يمكنك حذفها كلها في أي وقت بالأمر /delete."
)


# ---------- helpers ----------

def _keyboard(options: dict[str, str], prefix: str, other: str | None = None) -> InlineKeyboardMarkup:
    rows, row = [], []
    for key, name in options.items():
        row.append(InlineKeyboardButton(name, callback_data=f"{prefix}:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if other:
        row.append(InlineKeyboardButton(other, callback_data=f"{prefix}:none"))
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _result_keyboard(lid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 اختبرني", callback_data=f"quiz:{lid}"),
         InlineKeyboardButton("✅❌ صح أو خطأ", callback_data=f"tf:{lid}")],
        [InlineKeyboardButton("🃏 بطاقات المراجعة", callback_data=f"cards:{lid}"),
         InlineKeyboardButton("🧠 الخريطة الذهنية", callback_data=f"map:{lid}")],
        [InlineKeyboardButton("❓ اسألني عن المحاضرة", callback_data=f"ask:{lid}"),
         InlineKeyboardButton("💡 اشرح لي أبسط", callback_data=f"simp:{lid}")],
        [InlineKeyboardButton("📄 النص الكامل", callback_data=f"txt:{lid}"),
         InlineKeyboardButton("🗑 حذف", callback_data=f"del:{lid}")],
    ])


def _minutes(seconds: float) -> str:
    m = max(1, round(seconds / 60))
    return "دقيقة واحدة" if m == 1 else ("دقيقتين" if m == 2 else f"{m} دقائق" if m <= 10 else f"{m} دقيقة")


def _section_text(section: dict, n: int) -> str:
    lines = [f"📌 <b>{n}. {escape(section.get('heading', ''))}</b> <code>{escape(section.get('time', ''))}</code>"]
    for p in section.get("points", []):
        t = f" <code>{escape(p['time'])}</code>" if p.get("time") else ""
        lines.append(f"• {escape(p.get('text', ''))}{t}")
    text = "\n".join(lines)
    return text if len(text) < 4000 else text[:3990] + "…"


def _quick_summary(analysis: dict, streamed: bool) -> str:
    lines = [f"✅ <b>{escape(analysis.get('title', 'ملخص المحاضرة'))}</b>"]
    if analysis.get("overview"):
        lines.append(escape(analysis["overview"]))
    if not streamed:  # the sections were not already sent one by one
        heads = [(s.get("heading", ""), s.get("time", "")) for s in analysis.get("sections", []) if s.get("heading")]
        if heads:
            lines.append("\n<b>محاور المحاضرة:</b>")
            lines += [f"• {escape(h)} <code>{escape(t)}</code>" for h, t in heads]
    lines.append(f"\n🧪 {len(analysis.get('mcq', []))} سؤال اختيار · ✅❌ {len(analysis.get('true_false', []))} صح أو خطأ"
                 f" · 🃏 {len(analysis.get('flashcards', []))} بطاقة\nالملف الكامل في الأسفل 👇")
    text = "\n".join(lines)
    return text if len(text) < 4000 else text[:3990] + "…"


def _count(n: int, one: str, two: str, few: str, many: str) -> str:
    """Arabic counted noun: 1 تسجيل, 2 تسجيلان, 3-10 تسجيلات, 11+ تسجيلاً."""
    return one if n == 1 else two if n == 2 else f"{n} {few}" if n <= 10 else f"{n} {many}"


def _fresh(items: list, minutes: int = config.PENDING_IMAGES_TTL_MINUTES) -> list:
    return [p for p in items if isinstance(p, dict) and time.time() - p["ts"] < minutes * 60]


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
        note = "\n📝 سأرسل لك الملخص جزءاً جزءاً فور كتابته." if stage == "analyze" else ""
        text = f"{self.STAGES.get(stage, '⏳ أعمل على المحاضرة')}{bar}…{eta}{note}"
        if text != self.last_text:
            self.last_text = text
            asyncio.run_coroutine_threadsafe(self._edit(text), self.loop)

    async def _edit(self, text: str) -> None:
        try:
            await self.msg.edit_text(text)
        except TelegramError:
            pass


class SectionSender:
    """Sends summary sections to the student, in order, as Claude writes them (from the worker thread)."""

    def __init__(self, bot, chat_id: int, loop: asyncio.AbstractEventLoop):
        self.bot, self.chat_id, self.loop = bot, chat_id, loop
        self.count, self.lock = 0, asyncio.Lock()

    def __call__(self, section: dict) -> None:
        self.count += 1
        asyncio.run_coroutine_threadsafe(self._send(section, self.count), self.loop)

    async def _send(self, section: dict, n: int) -> None:
        async with self.lock:  # asyncio.Lock is first-come first-served, so sections keep their order
            try:
                if n == 1:
                    await self.bot.send_message(self.chat_id, "📝 <b>الملخص</b> (يصلك جزءاً جزءاً، والملف الكامل في النهاية)",
                                                parse_mode=ParseMode.HTML)
                await self.bot.send_message(self.chat_id, _section_text(section, n), parse_mode=ParseMode.HTML)
            except TelegramError as e:
                log.warning("section send failed: %s", e)


# ---------- commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(WELCOME, parse_mode=ParseMode.HTML)
    if "major" not in context.user_data:
        await update.effective_message.reply_text("ما تخصصك؟", reply_markup=_keyboard(MAJOR_NAMES, "major", "أخرى / عام"))


async def major_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("اختر تخصصك:", reply_markup=_keyboard(MAJOR_NAMES, "major", "أخرى / عام"))


async def dialect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    names = {k: v[0] for k, v in DIALECTS.items()}
    await update.effective_message.reply_text(
        "بأي لهجة يشرح المحاضر غالباً؟ يساعدني هذا على فهم كلامه بدقة، والملخص يبقى بالفصحى.",
        reply_markup=_keyboard(names, "dialect"))


async def privacy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(PRIVACY, parse_mode=ParseMode.HTML)


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in ("lectures", "pending_images", "pending_docs", "parts", "deck", "ask", "ask_history", "exam_sel"):
        context.user_data.pop(key, None)
    await update.effective_message.reply_text("🗑 حذفت كل محاضراتك وملفاتك المحفوظة.")


# ---------- collecting a lecture: recordings, slides, photos ----------
# A lecture can come in several pieces (parts of one recording, a run of voice notes, two lectures
# of the same course) plus its slides and photos. Pieces are collected for PARTS_WAIT_SECONDS after
# the last one arrives, or until the student taps "start now", then processed as one lecture.

def _collector_text(ud: dict) -> str:
    parts, docs, imgs = ud.get("parts", []), _fresh(ud.get("pending_docs", [])), _fresh(ud.get("pending_images", []))
    lines = ["📥 استلمت " + _count(len(parts), "التسجيل", "تسجيلين", "تسجيلات", "تسجيلاً")]
    if docs:
        lines.append("📎 " + _count(len(docs), "ملف واحد", "ملفان", "ملفات", "ملفاً") + " للمحاضرة")
    if imgs:
        lines.append("📸 " + _count(len(imgs), "صورة واحدة", "صورتان", "صور", "صورة"))
    lines.append(f"\nعندك أجزاء أخرى أو شرائح المحاضرة؟ أرسلها الآن. "
                 f"سأبدأ تلقائياً بعد {config.PARTS_WAIT_SECONDS} ثانية من آخر ملف.")
    return "\n".join(lines)


_COLLECT_KB = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ ابدأ الآن", callback_data="go:"),
                                     InlineKeyboardButton("✖️ إلغاء", callback_data="cancel:")]])


async def _refresh_collector(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> None:
    """Show (at the bottom of the chat) what has been collected and restart the countdown."""
    ud = context.user_data
    old = ud.pop("collector_msg", None)
    if old:
        try:
            await context.bot.delete_message(chat_id, old)
        except TelegramError:
            pass
    msg = await context.bot.send_message(chat_id, _collector_text(ud), reply_markup=_COLLECT_KB)
    ud["collector_msg"] = msg.message_id
    for job in context.job_queue.get_jobs_by_name(f"start:{user_id}"):
        job.schedule_removal()
    context.job_queue.run_once(_start_job, config.PARTS_WAIT_SECONDS, chat_id=chat_id, user_id=user_id,
                               name=f"start:{user_id}")


async def _start_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_job(context, context.job.chat_id, context.job.user_id)


async def _add_part(update: Update, context: ContextTypes.DEFAULT_TYPE, part: dict) -> None:
    # Parts left over from before a restart (their countdown is gone) must not join a new lecture.
    parts = context.user_data["parts"] = _fresh(context.user_data.get("parts", []), 30)
    if len(parts) >= config.MAX_PARTS:
        await update.effective_message.reply_text(f"⚠️ الحد الأعلى {config.MAX_PARTS} أجزاء للمحاضرة الواحدة.")
        return
    parts.append(part)
    await _refresh_collector(context, update.effective_chat.id, update.effective_user.id)


async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    media = msg.audio or msg.voice or msg.video or msg.video_note or msg.document
    if media.file_size and media.file_size > CLOUD_DOWNLOAD_LIMIT and not config.TELEGRAM_LOCAL_API_URL:
        await msg.reply_text(
            "⚠️ الملف أكبر من 20 ميغابايت، وهذا أكبر حجم يستطيع البوت تنزيله حالياً.\n"
            "الحلول: أرسل التسجيل <b>صوتاً فقط</b> (m4a أو mp3)، أو قسّمه أجزاء، "
            "أو ارفعه على Google Drive أو يوتيوب وأرسل الرابط.", parse_mode=ParseMode.HTML)
        return
    title = getattr(media, "title", None) or getattr(media, "file_name", None) or ""
    await _add_part(update, context, {"file_id": media.file_id, "title": Path(title).stem if title else "",
                                      "ts": time.time()})


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = find_media_url(update.effective_message.text)
    if not url and context.user_data.get("ask"):
        await _answer_question(update, context)
        return
    if url:
        await _add_part(update, context, {"url": url, "title": "", "ts": time.time()})
    else:
        await update.effective_message.reply_text(
            "أرسل تسجيل المحاضرة (ملف صوت أو فيديو) أو رابط يوتيوب أو Google Drive، وأجهّز لك الملخص والأسئلة.")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg.photo:
        file_id, mime = msg.photo[-1].file_id, "image/jpeg"
    else:
        file_id, mime = msg.document.file_id, msg.document.mime_type or "image/jpeg"
    if mime not in materials.IMAGE_TYPES:
        await msg.reply_text("أرسل الصورة بصيغة JPG أو PNG.")
        return
    pending = _fresh(context.user_data.get("pending_images", []))
    if len(pending) >= config.MAX_IMAGES_PER_LECTURE:
        await msg.reply_text(f"وصلت للحد الأعلى ({config.MAX_IMAGES_PER_LECTURE} صورة).")
        return
    pending.append({"file_id": file_id, "ts": time.time(), "mime": mime})
    context.user_data["pending_images"] = pending
    await _after_extra(update, context, f"📸 حفظت الصورة ({len(pending)}).")


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """PDF and PowerPoint files of the lecture."""
    msg, doc = update.effective_message, update.effective_message.document
    if not materials.kind_of(doc.file_name, doc.mime_type):
        await msg.reply_text("أرسل التسجيل صوتاً أو فيديو، وملفات المحاضرة بصيغة PDF أو PowerPoint (pptx).")
        return
    limit = min(config.MAX_DOCUMENT_MB * 1024 * 1024,
                CLOUD_DOWNLOAD_LIMIT if not config.TELEGRAM_LOCAL_API_URL else 1 << 40)
    if doc.file_size and doc.file_size > limit:
        await msg.reply_text(f"⚠️ الملف أكبر من {limit // (1024 * 1024)} ميغابايت. أرسل نسخة أصغر.")
        return
    pending = _fresh(context.user_data.get("pending_docs", []))
    if len(pending) >= config.MAX_DOCUMENTS_PER_LECTURE:
        await msg.reply_text(f"وصلت للحد الأعلى ({config.MAX_DOCUMENTS_PER_LECTURE} ملفات للمحاضرة).")
        return
    pending.append({"file_id": doc.file_id, "name": doc.file_name or "slides", "mime": doc.mime_type, "ts": time.time()})
    context.user_data["pending_docs"] = pending
    await _after_extra(update, context, f"📎 حفظت الملف: {doc.file_name}")


async def _after_extra(update: Update, context: ContextTypes.DEFAULT_TYPE, note: str) -> None:
    if context.user_data.get("parts"):
        await _refresh_collector(context, update.effective_chat.id, update.effective_user.id)
    else:
        await update.effective_message.reply_text(note + "\nأرسل تسجيل المحاضرة، وأضمّ هذا إليها.")


# ---------- the lecture job ----------

async def _download_part(context: ContextTypes.DEFAULT_TYPE, part: dict, work: Path, i: int) -> Source:
    if part.get("url"):
        source = await asyncio.to_thread(download_url, part["url"], work, f"part{i}")
        return source
    f = await context.bot.get_file(part["file_id"], **BIG_FILE_TIMEOUTS)
    path = work / (f"part{i}" + (Path(f.file_path).suffix if f.file_path else ""))
    await f.download_to_drive(path, read_timeout=BIG_FILE_TIMEOUTS["read_timeout"])
    _drop_local_copy(f.file_path)
    return Source(path=path, title=part.get("title", ""))


async def _run_job(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> None:
    global _waiting
    ud = context.user_data
    parts = ud.pop("parts", [])
    if not parts:
        return
    for job in context.job_queue.get_jobs_by_name(f"start:{user_id}"):
        job.schedule_removal()
    collector = ud.pop("collector_msg", None)
    if collector:
        try:
            await context.bot.delete_message(chat_id, collector)
        except TelegramError:
            pass
    images_meta = _fresh(ud.pop("pending_images", []))
    docs_meta = _fresh(ud.pop("pending_docs", []))
    major, dialect = ud.get("major"), ud.get("dialect")

    extras = ["🧩 " + _count(len(parts), "", "جزآن", "أجزاء", "جزءاً") if len(parts) > 1 else "",
              "📎 " + _count(len(docs_meta), "ملف واحد", "ملفان", "ملفات", "ملفاً") if docs_meta else "",
              "📸 " + _count(len(images_meta), "صورة واحدة", "صورتان", "صور", "صورة") if images_meta else ""]
    extra = " · ".join(e for e in extras if e)
    status = await context.bot.send_message(chat_id, "⏳ استلمت المحاضرة…" + (f"\n{extra}" if extra else ""))

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
            sources = []
            for i, p in enumerate(parts, 1):
                try:
                    sources.append(await _download_part(context, p, work, i))
                except Exception:
                    log.exception("download failed (part %d, %s)", i, "link" if p.get("url") else "telegram file")
                    await status.edit_text(
                        "⚠️ تعذّر تنزيل الرابط. تأكد أنه عام (في Google Drive: مشاركة ← أي شخص لديه الرابط)."
                        if p.get("url") else "⚠️ تعذّر تنزيل الملف من تيليجرام. أعد إرساله بعد قليل.")
                    return
            images = []
            for m in images_meta:
                f = await context.bot.get_file(m["file_id"], **BIG_FILE_TIMEOUTS)
                images.append((bytes(await f.download_as_bytearray()), m["mime"]))
            mats = []
            for d in docs_meta:
                f = await context.bot.get_file(d["file_id"], **BIG_FILE_TIMEOUTS)
                data = bytes(await f.download_as_bytearray())
                _drop_local_copy(f.file_path)
                try:
                    mats.append(await asyncio.to_thread(materials.load, data, d["name"], d["mime"]))
                except Exception:
                    log.exception("could not read %s", d["name"])
                    await context.bot.send_message(chat_id, f"⚠️ لم أستطع قراءة الملف {d['name']}، سأكمل بدونه.")

            duration = sum(s.duration or pipeline.probe_duration(s.path) for s in sources)
            eta = pipeline.estimate_seconds(duration)
            await status.edit_text(f"🎧 بدأت العمل على المحاضرة ({_minutes(duration)}).\n"
                                   f"⏱ الوقت المتوقع: {_minutes(eta)}")
            loop = asyncio.get_running_loop()
            progress = Progress(status, loop, eta)
            sender = SectionSender(context.bot, chat_id, loop)
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            result = await asyncio.to_thread(pipeline.run, sources, work, major, images, progress.update,
                                             None, mats, dialect, sender)
            await asyncio.sleep(1)  # let the last streamed section go out first
            async with sender.lock:
                pass

        lid = uuid.uuid4().hex[:8]
        lectures = ud.setdefault("lectures", {})
        a = result.analysis
        lectures[lid] = {key: a.get(key, []) for key in ("mcq", "true_false", "flashcards", "sections", "glossary",
                                                         "comparisons")}
        lectures[lid].update(title=a.get("title", ""), subject=a.get("subject", ""), overview=a.get("overview", ""),
                             mindmap=a.get("mindmap", {}), transcript=result.transcript_text, time=time.time())
        for old in sorted(lectures, key=lambda k: lectures[k]["time"])[:-KEEP_LECTURES]:
            del lectures[old]
        added = study.add_cards(ud.setdefault("deck", []), a.get("flashcards", []), a.get("title", ""))
        ud.setdefault("reminder_hour", config.DEFAULT_REMINDER_HOUR)

        await status.delete()
        await context.bot.send_message(chat_id, _quick_summary(result.analysis, sender.count > 0),
                                       parse_mode=ParseMode.HTML)
        with open(result.pdf_path, "rb") as fh:
            await context.bot.send_document(chat_id, fh, filename=result.pdf_path.name,
                                            reply_markup=_result_keyboard(lid),
                                            caption="📄 الملخص الكامل: المحاور، والخريطة الذهنية، والمقارنات، "
                                                    "والمصطلحات، والأسئلة مع الإجابات، والبطاقات، والنص الكامل.")
        if added:
            hour = ud.get("reminder_hour")
            when = f"كل يوم الساعة {_hour_name(hour)}" if hour is not None else "متى أرسلت /review"
            await context.bot.send_message(chat_id, f"🔁 أضفت بطاقات هذه المحاضرة ({added}) لمراجعتك اليومية، وأذكّرك بها {when}. "
                                                    "/reminder لتغيير الوقت.")
    except pipeline.LectureTooLong:
        await status.edit_text(f"⚠️ المحاضرة أطول من {config.MAX_LECTURE_MINUTES} دقيقة. قسّمها وأرسلها على دفعات.")
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
    if action == "dialect":
        context.user_data["dialect"] = arg
        await q.edit_message_text(f"🗣 تم: لهجة {DIALECTS.get(arg, ('',))[0]}. الملخص يبقى بالفصحى.")
        return
    if action == "go":
        await _run_job(context, chat_id, update.effective_user.id)
        return
    if action == "cancel":
        context.user_data.pop("parts", None)
        context.user_data.pop("collector_msg", None)
        for job in context.job_queue.get_jobs_by_name(f"start:{update.effective_user.id}"):
            job.schedule_removal()
        try:
            await q.edit_message_text("✖️ ألغيت. أرسل المحاضرة متى شئت.")
        except BadRequest:
            pass
        return

    if action == "rev":
        await _review_button(update, context, arg)
        return
    if action == "rem":
        context.user_data["reminder_hour"] = None if arg == "off" else int(arg)
        await q.edit_message_text("🔕 أوقفت التذكير اليومي. /review للمراجعة متى شئت." if arg == "off"
                                  else f"⏰ سأذكّرك بالمراجعة كل يوم الساعة {_hour_name(int(arg))}.")
        return
    if action == "ex":
        await _exam_button(update, context, arg)
        return
    if action == "askend":
        context.user_data.pop("ask", None)
        context.user_data.pop("ask_history", None)
        await q.edit_message_reply_markup(None)
        await context.bot.send_message(chat_id, "👍 انتهت الأسئلة. أرسل محاضرة جديدة متى شئت.")
        return

    lid, _, extra = arg.partition(":")
    lec = context.user_data.get("lectures", {}).get(lid)
    if not lec:
        await context.bot.send_message(chat_id, "لم أعد أحتفظ بهذه المحاضرة. أرسلها من جديد.")
        return
    arg = lid

    if action == "quiz":
        for i, item in enumerate(lec["mcq"], 1):
            await _send_quiz(context, chat_id, f"{i}. {item['question']}", item["options"], item["answer_index"],
                             item.get("explanation", ""), item.get("time", ""))
    elif action == "tf":
        items = lec.get("true_false", [])
        if not items:
            await context.bot.send_message(chat_id, "لا توجد أسئلة صح أو خطأ لهذه المحاضرة. أعد إرسالها لتحصل عليها.")
        for i, item in enumerate(items, 1):
            await _send_quiz(context, chat_id, f"{i}. صح أم خطأ؟ {item['statement']}", ["صح", "خطأ"],
                             0 if item["answer"] else 1, item.get("explanation", ""), item.get("time", ""))
    elif action == "cards":
        cards = lec["flashcards"]
        for start_i in range(0, len(cards), 5):
            chunk = cards[start_i:start_i + 5]
            text = "\n\n".join(f"❓ <b>{escape(c['front'])}</b>\n<tg-spoiler>{escape(c['back'])}</tg-spoiler>"
                               for c in chunk)
            await context.bot.send_message(chat_id, ("🃏 اضغط على الجواب المخفي لكشفه\n\n" if start_i == 0 else "")
                                           + text, parse_mode=ParseMode.HTML)
    elif action == "map":
        png = await asyncio.to_thread(mindmap.render_png, lec.get("mindmap") or {})
        if png:
            await context.bot.send_document(chat_id, png, filename=pipeline.safe_name(lec["title"]) + "-mindmap.png",
                                            caption="🧠 الخريطة الذهنية للمحاضرة")
        else:
            await context.bot.send_message(chat_id, "لا توجد خريطة ذهنية لهذه المحاضرة. أعد إرسالها لتحصل عليها.")
    elif action == "ask":
        context.user_data["ask"], context.user_data["ask_history"] = lid, []
        await context.bot.send_message(
            chat_id, f"❓ اكتب سؤالك عن محاضرة «{lec['title']}»، وأجيبك من كلام المحاضر مع وقت الشرح.\n"
                     "يمكنك أن تسأل أكثر من سؤال. للخروج اضغط «إنهاء».",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✔️ إنهاء الأسئلة", callback_data="askend:")]]))
    elif action == "simp":
        sections = lec.get("sections", [])
        if extra:
            i = int(extra)
            if i < len(sections):
                await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
                try:
                    text = await asyncio.to_thread(study.explain, lec, sections[i])
                except AnalysisError as e:
                    log.warning("explain failed: %s", e)
                    text = "⚠️ تعذّر الشرح الآن. حاول بعد قليل."
                await _send_long(context, chat_id, f"💡 {sections[i].get('heading', '')}\n\n{text}")
        elif sections:
            rows = [[InlineKeyboardButton(s.get("heading", "")[:60], callback_data=f"simp:{lid}:{i}")]
                    for i, s in enumerate(sections[:20])]
            await context.bot.send_message(chat_id, "💡 أي جزء تريد أن أشرحه لك بأسلوب أبسط؟",
                                           reply_markup=InlineKeyboardMarkup(rows))
        else:
            await context.bot.send_message(chat_id, "أعد إرسال المحاضرة لتستخدم هذه الميزة.")
    elif action == "txt":
        name = pipeline.safe_name(lec["title"]) + ".txt"
        await context.bot.send_document(chat_id, lec["transcript"].encode("utf-8"), filename=name,
                                        caption="📄 النص الكامل للمحاضرة، مع وقت كل فقرة.")
    elif action == "del":
        del context.user_data["lectures"][arg]
        await context.bot.send_message(chat_id, "🗑 حذفت بيانات هذه المحاضرة.")


async def _send_quiz(context, chat_id: int, question: str, options: list[str], correct: int,
                     explanation: str, at: str) -> None:
    try:
        await context.bot.send_poll(
            chat_id, question[:300], [o[:100] for o in options], type=Poll.QUIZ, correct_option_id=correct,
            explanation=(explanation + (f" ⏱ {at}" if at else ""))[:200], is_anonymous=False,
        )
    except TelegramError as e:
        log.warning("poll failed: %s", e)
    await asyncio.sleep(0.4)


# ---------- study tools ----------

def _hour_name(h: int) -> str:
    if h == 0:
        return "12 منتصف الليل"
    if h < 12:
        return f"{h} صباحاً"
    if h == 12:
        return "12 ظهراً"
    return f"{h - 12} " + ("عصراً" if h < 17 else "مساءً")


async def _send_long(context, chat_id: int, text: str, **kw) -> None:
    for i in range(0, len(text), 4000):
        await context.bot.send_message(chat_id, text[i:i + 4000], **kw)


async def _answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud, msg = context.user_data, update.effective_message
    lec = ud.get("lectures", {}).get(ud["ask"])
    if not lec:
        ud.pop("ask", None)
        await msg.reply_text("لم أعد أحتفظ بهذه المحاضرة. أرسلها من جديد.")
        return
    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    history = ud.setdefault("ask_history", [])
    try:
        answer = await asyncio.to_thread(study.ask, lec, msg.text, history[-2 * ASK_HISTORY:])
    except AnalysisError as e:
        log.warning("question failed: %s", e)
        await msg.reply_text("⚠️ تعذّر الإجابة الآن. أعد السؤال بعد قليل.")
        return
    history += [{"role": "user", "content": msg.text}, {"role": "assistant", "content": answer}]
    end = InlineKeyboardMarkup([[InlineKeyboardButton("✔️ إنهاء الأسئلة", callback_data="askend:")]])
    for i in range(0, len(answer), 4000):
        last = i + 4000 >= len(answer)
        await msg.reply_text(answer[i:i + 4000], reply_markup=end if last else None)


# spaced review: one card at a time; "show answer", then "knew it" / "didn't"

def _card_text(card: dict, reveal: bool) -> str:
    text = f"🃏 <b>{escape(card['front'])}</b>"
    if reveal:
        text += f"\n\n{escape(card['back'])}"
    return text + f"\n\n<i>{escape(card.get('title', ''))}</i>"


async def _next_card(context, chat_id: int) -> None:
    ud = context.user_data
    done = ud.get("reviewed_today", {})
    t = study.today().isoformat()
    count = done.get("n", 0) if done.get("date") == t else 0
    due = study.due_cards(ud.get("deck", []))
    if not due or count >= config.REVIEW_CARDS_PER_DAY:
        left = f"\nالمتبقي للغد: {len(due)}" if due else ""
        await context.bot.send_message(chat_id, f"🎉 أحسنت! أنهيت مراجعة اليوم.\nراجعت: {count}{left}")
        return
    card = due[0]
    await context.bot.send_message(
        chat_id, f"🔁 المتبقي اليوم: {min(len(due), config.REVIEW_CARDS_PER_DAY - count)}\n\n" + _card_text(card, False),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👁 اكشف الجواب", callback_data=f"rev:show:{card['id']}")]]))


async def review_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("deck"):
        await update.effective_message.reply_text("لا توجد بطاقات بعد. أرسل محاضرة، وتُضاف بطاقاتها لمراجعتك اليومية.")
        return
    await _next_card(context, update.effective_chat.id)


async def _review_button(update: Update, context: ContextTypes.DEFAULT_TYPE, arg: str) -> None:
    q, ud = update.callback_query, context.user_data
    step, _, cid = arg.partition(":")
    if step == "start":
        await _next_card(context, q.message.chat_id)
        return
    card = next((c for c in ud.get("deck", []) if c["id"] == cid), None)
    if not card:
        return
    if step == "show":
        await q.edit_message_text(_card_text(card, True), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ عرفتها", callback_data=f"rev:ok:{cid}"),
              InlineKeyboardButton("❌ لم أعرفها", callback_data=f"rev:no:{cid}")]]))
        return
    study.grade(card, step == "ok")
    t = study.today().isoformat()
    done = ud.get("reviewed_today", {})
    ud["reviewed_today"] = {"date": t, "n": (done.get("n", 0) if done.get("date") == t else 0) + 1}
    mark = "✅" if step == "ok" else "❌ سأعيدها لك غداً"
    await q.edit_message_text(_card_text(card, True) + f"\n{mark}", parse_mode=ParseMode.HTML)
    await _next_card(context, q.message.chat_id)


async def reminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    hours = [6, 8, 12, 16, 18, 20, 21, 22]
    rows = [[InlineKeyboardButton(_hour_name(h), callback_data=f"rem:{h}") for h in hours[i:i + 2]]
            for i in range(0, len(hours), 2)]
    rows.append([InlineKeyboardButton("🔕 إيقاف التذكير", callback_data="rem:off")])
    await update.effective_message.reply_text("⏰ متى أذكّرك بمراجعة البطاقات كل يوم؟",
                                              reply_markup=InlineKeyboardMarkup(rows))


async def _daily_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Every 10 minutes: remind students whose hour has come and who have cards due."""
    import datetime as dt
    from zoneinfo import ZoneInfo

    now = dt.datetime.now(ZoneInfo(config.REMINDER_TZ))
    today = now.date().isoformat()
    for user_id, ud in list(context.application.user_data.items()):
        hour = ud.get("reminder_hour")
        if hour is None or now.hour != hour or ud.get("reminded_on") == today:
            continue
        due = study.due_cards(ud.get("deck", []))
        if not due:
            continue
        ud["reminded_on"] = today
        try:
            await context.bot.send_message(
                user_id, f"🔁 حان وقت المراجعة! بطاقات اليوم: {min(len(due), config.REVIEW_CARDS_PER_DAY)}\n"
                         "دقائق قليلة تثبّت المعلومة في ذاكرتك.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ ابدأ المراجعة", callback_data="rev:start")]]))
        except TelegramError as e:
            log.info("reminder to %s failed: %s", user_id, e)


# exam-night summary: pick lectures, then one PDF

def _exam_keyboard(ud: dict) -> InlineKeyboardMarkup:
    lectures = ud.get("lectures", {})
    sel = set(ud.get("exam_sel", []))
    order = sorted(lectures, key=lambda k: lectures[k]["time"], reverse=True)[:20]
    rows = [[InlineKeyboardButton(("✅ " if k in sel else "▫️ ") + (lectures[k]["title"] or "محاضرة")[:50],
                                  callback_data=f"ex:t:{k}")] for k in order]
    rows.append([InlineKeyboardButton("☑️ الكل", callback_data="ex:all:"),
                 InlineKeyboardButton(f"🌙 جهّز الملخص ({len(sel)})", callback_data="ex:go:")])
    return InlineKeyboardMarkup(rows)


async def exam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("lectures"):
        await update.effective_message.reply_text("لا توجد محاضرات محفوظة بعد. أرسل محاضراتك أولاً.")
        return
    context.user_data["exam_sel"] = []
    await update.effective_message.reply_text("🌙 <b>ملخص ليلة الاختبار</b>\nاختر محاضرات المادة، ثم اضغط «جهّز الملخص».",
                                              parse_mode=ParseMode.HTML, reply_markup=_exam_keyboard(context.user_data))


async def _exam_button(update: Update, context: ContextTypes.DEFAULT_TYPE, arg: str) -> None:
    q, ud = update.callback_query, context.user_data
    step, _, lid = arg.partition(":")
    lectures = ud.get("lectures", {})
    sel = [k for k in ud.get("exam_sel", []) if k in lectures]
    if step == "t":
        sel = [k for k in sel if k != lid] if lid in sel else sel + [lid]
    elif step == "all":
        sel = sorted(lectures, key=lambda k: lectures[k]["time"], reverse=True)[:20]
    if step in ("t", "all"):
        ud["exam_sel"] = sel
        try:
            await q.edit_message_reply_markup(_exam_keyboard(ud))
        except BadRequest:
            pass
        return
    if not sel:
        await context.bot.send_message(q.message.chat_id, "اختر محاضرة واحدة على الأقل.")
        return
    chosen = sorted((lectures[k] for k in sel), key=lambda l: l["time"])
    if any(not l.get("sections") for l in chosen):
        await context.bot.send_message(q.message.chat_id, "⚠️ بعض المحاضرات المختارة قديمة ولا تحتوي على الملخص "
                                                          "اللازم. أعد إرسالها أو اخترها بدونها.")
        return
    await q.edit_message_reply_markup(None)
    status = await context.bot.send_message(q.message.chat_id, f"🌙 أجهّز ملخص ليلة الاختبار من {len(chosen)} محاضرة…")
    work = Path(tempfile.mkdtemp(prefix="exam_", dir=_work_root()))
    try:
        summary = await asyncio.to_thread(study.exam_summary, chosen)
        html = render.build_exam_html(summary, [l["title"] for l in chosen])
        pdf = await asyncio.to_thread(render.write_pdf, html,
                                      work / (pipeline.safe_name(summary.get("title") or "exam") + ".pdf"))
        await status.delete()
        with open(pdf, "rb") as fh:
            await context.bot.send_document(q.message.chat_id, fh, filename=pdf.name,
                                            caption="🌙 ملخص ليلة الاختبار: أهم الأفكار، وما يجب حفظه، "
                                                    "ونقاط يخلط فيها الطلاب، واختبر نفسك. بالتوفيق!")
        ud["exam_sel"] = []
    except AnalysisError as e:
        log.warning("exam summary failed: %s", e)
        await status.edit_text("⚠️ تعذّر تجهيز الملخص الآن. حاول بعد قليل.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- startup ----------

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, NetworkError):  # brief connection drops; polling retries on its own
        log.warning("network error: %s", context.error)
        return
    log.error("unhandled error", exc_info=context.error)


def _drop_local_copy(file_path: str | None) -> None:
    """A local Bot API server keeps every downloaded file; remove ours once copied."""
    if config.TELEGRAM_LOCAL_API_URL and file_path and Path(file_path).is_absolute():
        Path(file_path).unlink(missing_ok=True)


def _leave_cloud_api() -> None:
    """Telegram requires logOut from its cloud servers once before a bot uses a local Bot API server."""
    marker = config.DATA_DIR / ".cloud_logged_out"
    if marker.exists():
        return
    import httpx

    r = httpx.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/logOut", timeout=30)
    # 400 "Logged out" means it was already done.
    log.info("cloud logOut: %s %s", r.status_code, r.text[:200])
    if r.status_code in (200, 400):
        marker.touch()


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (see .env.example)")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    builder = (Application.builder().token(config.TELEGRAM_BOT_TOKEN)
               .persistence(PicklePersistence(filepath=config.DATA_DIR / "state.pickle"))
               .concurrent_updates(True))
    if config.TELEGRAM_LOCAL_API_URL:
        _leave_cloud_api()
        builder = (builder.base_url(f"{config.TELEGRAM_LOCAL_API_URL}/bot")
                   .base_file_url(f"{config.TELEGRAM_LOCAL_API_URL}/file/bot").local_mode(True))
    app = builder.build()

    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("major", major_cmd))
    app.add_handler(CommandHandler("dialect", dialect_cmd))
    app.add_handler(CommandHandler("privacy", privacy_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(CommandHandler("review", review_cmd))
    app.add_handler(CommandHandler("reminder", reminder_cmd))
    app.add_handler(CommandHandler("exam", exam_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(
        filters.AUDIO | filters.VOICE | filters.VIDEO | filters.VIDEO_NOTE
        | filters.Document.AUDIO | filters.Document.VIDEO, on_media))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_error_handler(on_error)
    app.job_queue.run_repeating(_daily_reminders, interval=600, first=60)
    log.info("bot starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
