"""Telegram bot: students send a lecture recording (or a YouTube / Google Drive link) and get back study material."""
import asyncio
import logging
import shutil
import tempfile
import time
import uuid
from html import escape
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, NetworkError, TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler,
                          PicklePersistence, PollAnswerHandler, filters)

import bot_growth
import bot_library
import bot_quiz
import bot_share
import bot_wallet
import botkit
from botkit import count as _count, hour_name as _hour_name, minutes as _minutes
from botkit import send_long as _send_long, work_root as _work_root
from lecturebot import cache, config, library, materials, pipeline, store, study
from lecturebot.analyze import AnalysisError
from lecturebot import media
from lecturebot.media import Source, download_url, find_media_url

logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)  # WeasyPrint's font subsetting is chatty
logging.getLogger("weasyprint").setLevel(logging.ERROR)
log = logging.getLogger("lecturebot")

CLOUD_DOWNLOAD_LIMIT = 20 * 1024 * 1024  # Telegram's cloud Bot API refuses bigger downloads
KEEP_LECTURES = config.KEEP_LECTURES     # lectures kept per student (in the library, on disk)
JOBS = asyncio.Semaphore(config.MAX_PARALLEL_JOBS)
# A local Bot API server answers getFile only after it has fetched the whole file from Telegram,
# which takes minutes for a long recording; the library's default is a few seconds.
BIG_FILE_TIMEOUTS = {"read_timeout": 1800, "write_timeout": 60, "connect_timeout": 30, "pool_timeout": 30}
_waiting = 0

WELCOME = (
    "أهلاً بك في <b>فَهيم</b> 👋\n"
    "حوّل تسجيل محاضرتك إلى مذكرة مذاكرة كاملة.\n\n"
    "📝 <b>ألخّص لك المحاضرة</b>\n"
    "أربعة ملفات: الملخص مع النص الكامل، والأسئلة، والمصطلحات، والرسوم التوضيحية.\n\n"
    "🧪 <b>أختبرك فيها</b>\n"
    "أسئلة اختيار من متعدد، وصح أو خطأ، ومقالية أصححها لك، وبطاقات مراجعة يومية.\n\n"
    "📚 <b>أنظّم مذاكرتك</b>\n"
    "مكتبة بموادك، وموعد كل اختبار، وخطة مذاكرة حتى يومه.\n\n"
    "<b>كيف تبدأ؟</b>\n"
    "١. أرسل تسجيل المحاضرة (صوت أو فيديو) أو رابطه.\n"
    "   ليس لها تسجيل؟ أرسل شرائحها أو صور صفحات الكتاب وحدها.\n"
    "٢. أرفق شرائح المحاضرة إن وُجدت، ليكون الملخص أدق.\n"
    "٣. استلم ملخصك خلال دقائق.\n\n"
    "بقية الأوامر في زر القائمة ☰ أسفل الشاشة."
)

COMMANDS = [
    ("start", "البداية وطريقة الاستخدام"),
    ("library", "مكتبتي: موادي ومحاضراتي"),
    ("review", "مراجعة بطاقات اليوم"),
    ("exam", "ملخص ليلة الاختبار"),
    ("search", "البحث في محاضراتي"),
    ("wallet", "محفظتي والأسعار"),
    ("stats", "إحصاءاتي"),
    ("reminder", "وقت التذكير اليومي"),
    ("privacy", "الخصوصية"),
    ("delete", "حذف بياناتي"),
    ("paysupport", "الدعم ومشكلات الدفع"),
]

PRIVACY = (
    "🔒 <b>خصوصيتك</b>\n\n"
    "• التسجيل والملفات والصور تُحذف من الخادم فور انتهاء المعالجة.\n"
    "• تُعالج المحاضرة عبر خدمات ذكاء اصطناعي (لتحويل الكلام إلى نص وكتابة الملخص)، "
    "ولا تُشارك مع أحد، ولا تُستخدم لأي غرض آخر.\n"
    "• أحتفظ بنص محاضراتك وملخصاتها وأسئلتها، لتعمل مكتبتك وأزرار المذاكرة. "
    "يمكنك حذفها كلها في أي وقت بالأمر /delete."
)


# ---------- helpers ----------

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
    lines.append("\nالملفات في الأسفل 👇")
    text = "\n".join(lines)
    return text if len(text) < 4000 else text[:3990] + "…"


def _fresh(items: list, minutes: int = config.PENDING_IMAGES_TTL_MINUTES) -> list:
    return [p for p in items if isinstance(p, dict) and time.time() - p["ts"] < minutes * 60]


class Progress:
    """Edits one status message as the job moves on, without flooding Telegram."""

    STAGES = {"transcribe": "🎧 أحوّل الكلام إلى نص", "analyze": "🧠 أكتب الملخص والأسئلة",
              "render": "📄 أجهّز الملفات"}

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
    new = not context.user_data.get("seen")
    context.user_data["seen"] = True
    if context.args:  # t.me/<bot>?start=<prefix>_<value>: shared lecture
        prefix, _, value = context.args[0].partition("_")
        handler = botkit.START_LINKS.get(prefix)
        if handler and await handler(update, context, value, new):
            return
    if new:
        bot_growth.welcome_credits(context.user_data)
    await update.effective_message.reply_text(WELCOME, parse_mode=ParseMode.HTML)


async def privacy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(PRIVACY, parse_mode=ParseMode.HTML)


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in ("lectures", "pending_images", "pending_docs", "parts", "deck", "exam_sel",
                "courses", "await", "stats"):
        context.user_data.pop(key, None)
    store.delete_user(update.effective_user.id)
    await update.effective_message.reply_text("🗑 حذفت كل محاضراتك وموادك وبطاقاتك وملفاتك المحفوظة.")


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
    context.user_data["name"] = botkit.first_name(update)
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
    await _add_part(update, context, {"file_id": media.file_id, "uid": media.file_unique_id,
                                      "title": Path(title).stem if title else "", "ts": time.time()})


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = find_media_url(update.effective_message.text)
    pending = context.user_data.get("await")
    if not url and pending and time.time() - pending.get("ts", 0) < 3600:
        context.user_data.pop("await", None)
        handler = botkit.TEXT_INPUTS.get(pending["kind"])
        if handler:
            await handler(update, context, pending.get("payload", ""))
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
    if await bot_growth.on_cookies_file(update, context):
        return
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
        await update.effective_message.reply_text(
            note + "\n\nعندك تسجيل لهذه المحاضرة؟ أرسله الآن وأضمّ هذا إليه.\n"
                   "أو، إن لم يكن لها تسجيل، أرسل بقية الملفات أو الصفحات ثم اضغط:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 لخّص الملفات وحدها", callback_data="files:")]]))


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


def _full_from(result) -> dict:
    """What is stored for a lecture: its notes, questions and transcript."""
    a = result.analysis
    full = {key: a.get(key, []) for key in ("mcq", "true_false", "essay", "flashcards", "sections", "glossary",
                                            "divisions", "processes", "comparisons")}
    full.update(title=a.get("title", ""), subject=a.get("subject", ""), overview=a.get("overview", ""),
                transcript=result.transcript_text, ndiv=len(a.get("divisions", [])),
                duration=result.extra.get("duration", 0), source_url=result.source.url or "")
    return full


async def _save_and_send(context, chat_id: int, user_id: int, full: dict, paths: dict | None = None,
                         note: str = "") -> str:
    """Put a finished lecture in the student's library, add its cards, send its files; returns its id."""
    ud = context.user_data
    lid = uuid.uuid4().hex[:8]
    full = dict(full, time=time.time())
    store.put(user_id, ud, lid, full)
    lectures = ud["lectures"]
    for old in sorted(lectures, key=lambda k: lectures[k]["time"])[:-KEEP_LECTURES]:
        store.remove(user_id, ud, old)
    cid = library.assign_course(ud, lid, full["subject"])
    added = study.add_cards(ud.setdefault("deck", []), full.get("flashcards", []), full.get("title", ""))
    ud.setdefault("reminder_hour", config.DEFAULT_REMINDER_HOUR)
    bot_growth.lecture_done(ud, full)
    n_questions = len(full["mcq"]) + len(full["true_false"]) + len(full.get("essay", []))
    caption = ([note] if note else []) + [
        f"✅ {full.get('title') or 'ملخص المحاضرة'}",
        f"📁 حُفظت في مادة «{library.courses(ud)[cid]['name']}»",
        "🧪 " + _count(n_questions, "سؤال واحد", "سؤالان", "أسئلة", "سؤالاً") + " للاختبار"
        + (" · 🃏 " + _count(added, "بطاقة واحدة", "بطاقتان", "بطاقات", "بطاقة") + " للمراجعة اليومية" if added else "")]
    markup = botkit.lecture_keyboard(lid, lectures[lid])
    ids = await botkit.send_files(context, chat_id, paths or botkit.lecture_files(full), "\n".join(caption), markup)
    if ids:
        lectures[lid]["files"] = full["files"] = ids
        lectures[lid]["pdf_file_id"] = full["pdf_file_id"] = ids.get("summary")
    return lid


async def _download_extras(context, chat_id: int, images_meta: list, docs_meta: list) -> tuple[list, list]:
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
    return images, mats


async def _clear_collector(context, chat_id: int, user_id: int) -> None:
    for job in context.job_queue.get_jobs_by_name(f"start:{user_id}"):
        job.schedule_removal()
    collector = context.user_data.pop("collector_msg", None)
    if collector:
        try:
            await context.bot.delete_message(chat_id, collector)
        except TelegramError:
            pass


async def _run_job(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> None:
    global _waiting
    ud = context.user_data
    parts = ud.pop("parts", [])
    if not parts:
        return
    await _clear_collector(context, chat_id, user_id)
    compare = ud.pop("compare_next", False) and botkit.is_owner(context, user_id)

    # The same recording was processed before (for anyone): reuse it.
    key = cache.key_for(parts)
    cached = None if compare else cache.get(key)
    if cached and cached.get("pdf_file_id"):
        if not await bot_wallet.require(context, chat_id, ud, bot_wallet.RECEIVE, "هذه المحاضرة (سبق تلخيصها)"):
            ud["parts"] = parts  # kept, so "▶️ أكمل" after topping up carries on
            return
        ud.pop("pending_images", None)
        ud.pop("pending_docs", None)
        try:
            await _save_and_send(context, chat_id, user_id, cached, note="⚡ وصلتك فوراً: سبق تلخيص هذه المحاضرة.")
            bot_wallet.charge(context, ud, bot_wallet.RECEIVE, "محاضرة سبق تلخيصها")
            return
        except TelegramError as e:
            log.warning("cached delivery failed, processing again: %s", e)

    if not compare and not await bot_wallet.can_start(context, chat_id, ud):
        ud["parts"] = parts
        return
    images_meta = _fresh(ud.pop("pending_images", []))
    docs_meta = _fresh(ud.pop("pending_docs", []))
    major = None

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
                except Exception as e:
                    log.exception("download failed (part %d, %s)", i, "link" if p.get("url") else "telegram file")
                    await bot_growth.tell_owner(context, f"⚠️ تعذّر تنزيل {'رابط' if p.get('url') else 'ملف'} "
                                                         f"لطالب ({user_id}):\n{p.get('url', '')}\n{str(e)[:600]}")
                    await status.edit_text(
                        "⚠️ تعذّر تنزيل فيديو يوتيوب الآن. أعد المحاولة بعد قليل، أو أرسل صوت المحاضرة ملفاً."
                        if media.is_youtube(p.get("url", "")) else
                        "⚠️ تعذّر تنزيل الرابط. تأكد أنه عام (في Google Drive: مشاركة ← أي شخص لديه الرابط)."
                        if p.get("url") else "⚠️ تعذّر تنزيل الملف من تيليجرام. أعد إرساله بعد قليل.")
                    return
            images, mats = await _download_extras(context, chat_id, images_meta, docs_meta)
            if compare:
                await bot_growth.run_compare(context, chat_id, status, sources, work, major, images, mats)
                return

            duration = sum(s.duration or pipeline.probe_duration(s.path) for s in sources)
            price, _ = bot_wallet.upload_cost(ud, duration)
            if not await bot_wallet.require(context, chat_id, ud, price, f"محاضرة {_minutes(duration)}"):
                ud.update(parts=parts, pending_images=images_meta, pending_docs=docs_meta)
                await status.delete()
                return
            eta = pipeline.estimate_seconds(duration)
            await status.edit_text(f"🎧 بدأت العمل على المحاضرة ({_minutes(duration)}).\n"
                                   f"⏱ الوقت المتوقع: {_minutes(eta)}")
            loop = asyncio.get_running_loop()
            progress = Progress(status, loop, eta)
            sender = SectionSender(context.bot, chat_id, loop)
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            result = await asyncio.to_thread(pipeline.run, sources, work, major, images, progress.update,
                                             None, mats, sender)
            await asyncio.sleep(1)  # let the last streamed section go out first
            async with sender.lock:
                pass

        await status.delete()
        if not sender.count:  # the sections were not streamed: send the outline first
            await context.bot.send_message(chat_id, _quick_summary(result.analysis, False), parse_mode=ParseMode.HTML)
        full = _full_from(result)
        lid = await _save_and_send(context, chat_id, user_id, full, result.extra["files"])
        bot_wallet.charge_upload(context, ud, duration)
        meta = ud["lectures"][lid]
        cache.put(key, dict(full, pdf_file_id=meta.get("pdf_file_id"), files=meta.get("files")))
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


async def _run_files_job(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> None:
    """A lecture without a recording: summarise its slides, files or photos of book pages."""
    ud = context.user_data
    images_meta = _fresh(ud.pop("pending_images", []))
    docs_meta = _fresh(ud.pop("pending_docs", []))
    if not images_meta and not docs_meta:
        return
    await _clear_collector(context, chat_id, user_id)
    if not await bot_wallet.require(context, chat_id, ud, bot_wallet.FILES, "ملخص الملفات"):
        ud.update(pending_images=images_meta, pending_docs=docs_meta)
        return
    status = await context.bot.send_message(chat_id, "📄 أقرأ الملفات وأكتب الملخص والأسئلة… (دقيقتان تقريباً)")
    work = Path(tempfile.mkdtemp(prefix="files_", dir=_work_root()))
    try:
        images, mats = await _download_extras(context, chat_id, images_meta, docs_meta)
        if not images and not mats:
            await status.edit_text("⚠️ لم أستطع قراءة الملفات. أرسلها بصيغة PDF أو PowerPoint أو صور.")
            return
        title = Path(docs_meta[0]["name"]).stem if docs_meta else ""
        loop = asyncio.get_running_loop()
        sender = SectionSender(context.bot, chat_id, loop)
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        result = await asyncio.to_thread(pipeline.run_files, work, title, None, images, mats, None, sender)
        await asyncio.sleep(1)
        async with sender.lock:
            pass
        await status.delete()
        await _save_and_send(context, chat_id, user_id, _full_from(result), result.extra["files"])
        bot_wallet.charge(context, ud, bot_wallet.FILES, "ملخص من الملفات")
    except AnalysisError as e:
        log.warning("files analysis failed: %s", e)
        await status.edit_text("⚠️ تعذّر كتابة الملخص هذه المرة. أعد المحاولة بعد قليل.")
    except Exception:
        log.exception("files job failed")
        await status.edit_text("⚠️ حدث خطأ أثناء قراءة الملفات. أعد المحاولة.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- buttons ----------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    action, _, arg = (q.data or "").partition(":")
    chat_id = q.message.chat_id

    if action == "go":
        await _run_job(context, chat_id, update.effective_user.id)
        return
    if action == "files":
        try:
            await q.edit_message_reply_markup(None)
        except BadRequest:
            pass
        await _run_files_job(context, chat_id, update.effective_user.id)
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

    if action in botkit.BUTTONS:
        await botkit.BUTTONS[action](update, context, arg)
        return

    lid, _, extra = arg.partition(":")
    lec = store.get(update.effective_user.id, context.user_data, lid)
    if not lec:
        await context.bot.send_message(chat_id, "لم أعد أحتفظ بهذه المحاضرة. أرسلها من جديد.")
        return
    arg = lid
    if action in botkit.LECTURE_BUTTONS:
        await botkit.LECTURE_BUTTONS[action](update, context, lid, lec, extra)
        return
    if action == "cards":
        cards = lec["flashcards"]
        for start_i in range(0, len(cards), 5):
            chunk = cards[start_i:start_i + 5]
            text = "\n\n".join(f"❓ <b>{escape(c['front'])}</b>\n<tg-spoiler>{escape(c['back'])}</tg-spoiler>"
                               for c in chunk)
            await context.bot.send_message(chat_id, ("🃏 اضغط على الجواب المخفي لكشفه\n\n" if start_i == 0 else "")
                                           + text, parse_mode=ParseMode.HTML)
    elif action == "simp":
        sections = lec.get("sections", [])
        if extra:
            i = int(extra)
            if i < len(sections):
                if not await bot_wallet.require(context, chat_id, context.user_data, bot_wallet.EXPLAIN, "الشرح المبسط"):
                    return
                await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
                try:
                    text = await asyncio.to_thread(study.explain, lec, sections[i])
                    bot_wallet.charge(context, context.user_data, bot_wallet.EXPLAIN, "شرح مبسط")
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
    elif action == "more":
        await context.bot.send_message(chat_id, f"⋯ <b>{escape(lec['title'])}</b>", parse_mode=ParseMode.HTML,
                                       reply_markup=botkit.more_keyboard(lid, context.user_data))
    elif action == "del":
        store.remove(update.effective_user.id, context.user_data, lid)
        await context.bot.send_message(chat_id, "🗑 حذفت هذه المحاضرة من مكتبتك.")


# ---------- study tools ----------

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
    bot_growth.reviewed(ud)
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
    await q.edit_message_reply_markup(None)
    ud["exam_sel"] = []
    await bot_library.generate_exam(update, context, sel)


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


def setup(app: Application) -> None:
    """Register every handler (also used by the tests)."""
    app.add_handler(CommandHandler(["start", "help"], start))
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
    for module in (bot_library, bot_share, bot_growth, bot_quiz, bot_wallet):
        module.register(app)
    app.add_handler(PollAnswerHandler(bot_growth.on_poll_answer))
    app.add_error_handler(on_error)


async def _set_menu(app: Application) -> None:
    """The ☰ menu of commands, so students never need to remember them."""
    await app.bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (see .env.example)")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    builder = (Application.builder().token(config.TELEGRAM_BOT_TOKEN)
               .persistence(PicklePersistence(filepath=config.DATA_DIR / "state.pickle"))
               .concurrent_updates(True).post_init(_set_menu))
    if config.TELEGRAM_LOCAL_API_URL:
        _leave_cloud_api()
        builder = (builder.base_url(f"{config.TELEGRAM_LOCAL_API_URL}/bot")
                   .base_file_url(f"{config.TELEGRAM_LOCAL_API_URL}/file/bot").local_mode(True))
    app = builder.build()
    setup(app)
    log.info("bot starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
