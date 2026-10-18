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

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Poll, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from lecturebot import config, store

log = logging.getLogger("lecturebot")

BUTTONS: dict = {}
LECTURE_BUTTONS: dict = {}
TEXT_INPUTS: dict = {}
START_LINKS: dict = {}


def keyboard(options: dict[str, str], prefix: str, other: str | None = None, per_row: int = 2) -> InlineKeyboardMarkup:
    rows, row = [], []
    for key, name in options.items():
        row.append(InlineKeyboardButton(name, callback_data=f"{prefix}:{key}"))
        if len(row) == per_row:
            rows.append(row)
            row = []
    if other:
        row.append(InlineKeyboardButton(other, callback_data=f"{prefix}:none"))
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data[:64])


def lecture_keyboard(lid: str, meta: dict | None = None) -> InlineKeyboardMarkup:
    """The buttons under a lecture's PDF. meta: the lecture's details (to know if it has divisions)."""
    second = [button("💡 اشرح لي أبسط", f"simp:{lid}")]
    if (meta or {}).get("ndiv"):
        second.append(button("🌳 التقسيمات", f"div:{lid}"))
    return InlineKeyboardMarkup([
        [button("🧪 اختبرني", f"quiz:{lid}"), button("🃏 البطاقات", f"cards:{lid}")],
        second,
        [button("🌐 English", f"en:{lid}"), button("⋯ المزيد", f"more:{lid}")],
    ])


def more_keyboard(lid: str, ud: dict) -> InlineKeyboardMarkup:
    rows = [
        [button("📤 Word", f"docx:{lid}"), button("📝 Notion", f"md:{lid}")],
        [button("📄 النص الكامل", f"txt:{lid}"), button("📁 نقل لمادة أخرى", f"mv:{lid}")],
        [button("🔗 شاركها مع زميل", f"share:{lid}")],
    ]
    if ud.get("groups"):
        rows[-1].append(button("👥 أرسلها لمجموعة", f"tog:{lid}"))
    if ud.get("teacher"):
        rows.append([button("📝 ورقة اختبار", f"tpaper:{lid}"), button("🔑 نموذج الإجابة", f"tkey:{lid}")])
        rows.append([button("🔗 اختبار لطلابي", f"tquiz:{lid}")])
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
                    at: str, track: dict | None = None) -> None:
    """A Telegram quiz poll. track (e.g. {"kind": "lecture", "lid": ...}) records answers for statistics."""
    try:
        msg = await context.bot.send_poll(
            chat_id, question[:300], [o[:100] for o in options], type=Poll.QUIZ, correct_option_ids=[correct],
            explanation=(explanation + (f" ⏱ {at}" if at else ""))[:200], is_anonymous=False,
        )
        if track is not None and msg.poll:
            polls = context.bot_data.setdefault("polls", {})
            polls[msg.poll.id] = dict(track, correct=correct, ts=time.time())
    except TelegramError as e:
        log.warning("poll failed: %s", e)
    await asyncio.sleep(0.4)


async def send_lecture_pdf(context, chat_id: int, user_id: int, ud: dict, lid: str, caption: str) -> bool:
    """Send a stored lecture's PDF again (Telegram keeps it; we keep its file id)."""
    meta = ud.get("lectures", {}).get(lid, {})
    if not meta.get("pdf_file_id"):
        return False
    try:
        await context.bot.send_document(chat_id, meta["pdf_file_id"], caption=caption,
                                        reply_markup=lecture_keyboard(lid, meta))
        return True
    except TelegramError as e:
        log.warning("resend pdf failed: %s", e)
        return False


def first_name(update: Update) -> str:
    u = update.effective_user
    return (u.first_name or u.username or "زميلك") if u else "زميلك"


def safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
