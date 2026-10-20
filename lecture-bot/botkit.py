"""Helpers shared by the bot's modules (bot.py and the bot_*.py feature modules).

Feature modules register their buttons here instead of growing one big handler:
- BUTTONS[action] = handler(update, context, arg) for callback data "action:arg"
- LECTURE_BUTTONS[action] = handler(update, context, lid, lecture, extra) for "action:lid[:extra]"
- TEXT_INPUTS[kind] = handler(update, context, payload) for a reply the bot asked for with expect()
- START_LINKS[prefix] = handler(update, context, value, is_new_user) -> handled, for t.me/<bot>?start=prefix_value
"""
import asyncio
import logging
import time
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, Poll, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from lecturebot import config, store

log = logging.getLogger("lecturebot")

BUTTONS: dict = {}
LECTURE_BUTTONS: dict = {}
TEXT_INPUTS: dict = {}
START_LINKS: dict = {}
POLL_HOOKS: dict = {}  # poll kind -> fn(context, info, right), after an answer is recorded


def button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data[:64])


def lecture_keyboard(lid: str, meta: dict | None = None) -> InlineKeyboardMarkup:
    """The buttons under a lecture's files."""
    return InlineKeyboardMarkup([
        [button("🧪 اختبرني", f"quiz:{lid}"), button("🃏 البطاقات", f"cards:{lid}")],
        [button("💡 اشرح لي أبسط", f"simp:{lid}")],
        [button("🌐 English", f"en:{lid}"), button("⋯ المزيد", f"more:{lid}")],
    ])


def more_keyboard(lid: str, ud: dict) -> InlineKeyboardMarkup:
    rows = [
        [button("📤 Word", f"docx:{lid}"), button("📝 Notion", f"md:{lid}")],
        [button("📁 نقل لمادة أخرى", f"mv:{lid}"), button("🔗 شاركها مع زميل", f"share:{lid}")],
    ]
    rows.append([button("🗑 حذف", f"del:{lid}")])
    return InlineKeyboardMarkup(rows)


def count(n: int, one: str, two: str, few: str, many: str) -> str:
    """Arabic counted noun: 1 تسجيل, 2 تسجيلان, 3-10 تسجيلات, 11+ تسجيلاً."""
    return one if n == 1 else two if n == 2 else f"{n} {few}" if n <= 10 else f"{n} {many}"


def minutes(seconds: float) -> str:
    m = max(1, round(seconds / 60))
    return "دقيقة واحدة" if m == 1 else ("دقيقتين" if m == 2 else f"{m} دقائق" if m <= 10 else f"{m} دقيقة")


def hour_name(h: int) -> str:
    if h == 0:
        return "12 منتصف الليل"
    if h < 12:
        return f"{h} صباحاً"
    if h == 12:
        return "12 ظهراً"
    return f"{h - 12} " + ("عصراً" if h < 17 else "مساءً")


async def send_long(context, chat_id: int, text: str, **kw) -> None:
    for i in range(0, len(text), 4000):
        await context.bot.send_message(chat_id, text[i:i + 4000], **kw)


def work_root() -> str:
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    return str(config.WORK_DIR)


def expect(ud: dict, kind: str, payload: str = "") -> None:
    """The student's next text message answers a question the bot asked (handled by TEXT_INPUTS[kind])."""
    ud["await"] = {"kind": kind, "payload": payload, "ts": time.time()}


def lecture(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: str) -> dict | None:
    return store.get(update.effective_user.id, context.user_data, lid)


async def send_quiz(context, chat_id: int, question: str, options: list[str], correct: int, explanation: str,
                    at: str, track: dict | None = None, buttons: list | None = None,
                    open_period: int | None = None) -> str | None:
    """A Telegram quiz poll; returns its id. track (e.g. {"kind": "lecture", "lid": ...}) records answers
    for statistics. buttons: one row of buttons under the poll. open_period: seconds to answer."""
    pid = None
    try:
        msg = await context.bot.send_poll(
            chat_id, question[:300], [o[:100] for o in options], type=Poll.QUIZ, correct_option_ids=[correct],
            explanation=(explanation + (f" ⏱ {at}" if at else ""))[:200], is_anonymous=False,
            open_period=open_period, reply_markup=InlineKeyboardMarkup([buttons]) if buttons else None,
        )
        if msg.poll:
            pid = msg.poll.id
            if track is not None:
                polls = context.bot_data.setdefault("polls", {})
                polls[pid] = dict(track, correct=correct, ts=time.time())
    except TelegramError as e:
        log.warning("poll failed: %s", e)
    await asyncio.sleep(0.4)
    return pid


def evidence_button(lid: str, kind: str, i: int):
    """"📍 The proof": the lecturer's own words behind a question's answer."""
    return button("📍 الدليل", f"ev:{lid}:{kind}:{i}")


FILE_KINDS = ("summary", "questions", "glossary", "visuals")  # the order of a lecture's files


def lecture_files(meta: dict) -> dict:
    """kind -> Telegram file id of a stored lecture's files (older lectures have a single PDF)."""
    return dict(meta.get("files") or ({"summary": meta["pdf_file_id"]} if meta.get("pdf_file_id") else {}))


async def send_files(context, chat_id: int, files: dict, caption: str, markup=None) -> dict:
    """Send a lecture's files together (paths of new files, or file ids), then the caption with its buttons.
    Returns kind -> file id of what was sent."""
    items = [(k, files[k]) for k in FILE_KINDS if files.get(k)]
    handles, media = [], []
    try:
        for _, f in items:
            if isinstance(f, Path):
                fh = open(f, "rb")
                handles.append(fh)
                media.append(InputMediaDocument(fh, filename=f.name))
            else:
                media.append(InputMediaDocument(f))
        if len(media) == 1:
            f = items[0][1]
            sent = [await context.bot.send_document(chat_id, handles[0] if isinstance(f, Path) else f,
                                                    filename=f.name if isinstance(f, Path) else None,
                                                    read_timeout=120, write_timeout=120)]
        elif media:
            sent = await context.bot.send_media_group(chat_id, media, read_timeout=120, write_timeout=120)
        else:
            sent = []
    finally:
        for fh in handles:
            fh.close()
    await context.bot.send_message(chat_id, caption, reply_markup=markup)
    return {k: m.document.file_id for (k, _), m in zip(items, sent) if m.document}


async def send_lecture(context, chat_id: int, ud: dict, lid: str, caption: str) -> bool:
    """Send a stored lecture's files again (Telegram keeps them; we keep their file ids)."""
    meta = ud.get("lectures", {}).get(lid, {})
    files = lecture_files(meta)
    if not files:
        return False
    try:
        await send_files(context, chat_id, files, caption, lecture_keyboard(lid, meta))
        return True
    except TelegramError as e:
        log.warning("resend files failed: %s", e)
        return False


def is_owner(context, user_id: int) -> bool:
    """The bot's owner, who claimed it with /owner and the code printed by install.sh."""
    return context.bot_data.get("owner") == user_id


def first_name(update: Update) -> str:
    u = update.effective_user
    return (u.first_name or u.username or "زميلك") if u else "زميلك"


def safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
