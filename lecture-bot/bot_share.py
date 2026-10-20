"""Translating, exporting and sharing: English PDF, Word / Notion files, and share links for classmates."""
import asyncio
import shutil
import tempfile
import time
import uuid
from html import escape
from pathlib import Path

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError

import bot_growth
import bot_wallet
import botkit
from botkit import button, log
from lecturebot import config, exports, library, pipeline, render, store, study
from lecturebot.analyze import AnalysisError


def _meta(context, lid: str) -> dict:
    return context.user_data.get("lectures", {}).get(lid, {})


async def _resend(context, chat_id: int, file_id: str | None, kind: str, caption: str) -> bool:
    if not file_id:
        return False
    try:
        await context.bot.send_document(chat_id, file_id, caption=caption)
        return True
    except TelegramError:
        return False


# ---------- English version ----------

async def on_english(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    chat, meta = update.effective_chat.id, _meta(context, lid)
    caption = f"🌐 English version: {lec['title']}"
    if await _resend(context, chat, meta.get("en_file_id"), "doc", caption):
        return
    if not await bot_wallet.require(context, chat, context.user_data, bot_wallet.ENGLISH, "النسخة الإنجليزية"):
        return
    status = await context.bot.send_message(chat, "🌐 أترجم الملخص والأسئلة إلى الإنجليزية… (دقيقة أو دقيقتان)")
    work = Path(tempfile.mkdtemp(prefix="en_", dir=botkit.work_root()))
    try:
        en = await asyncio.to_thread(study.translate, lec)
        html = render.build_html(en, [], duration=lec.get("duration") or 0, lang="en")
        pdf = await asyncio.to_thread(render.write_pdf, html, work / (pipeline.safe_name(en.get("title") or "lecture")
                                                                       + "-EN.pdf"))
        with open(pdf, "rb") as fh:
            sent = await context.bot.send_document(chat, fh, filename=pdf.name,
                                                   caption=f"🌐 English version: {en.get('title') or lec['title']}\n"
                                                           "(the full transcript stays in the Arabic PDF)")
        if sent.document:
            meta["en_file_id"] = sent.document.file_id
        bot_wallet.charge(context, context.user_data, bot_wallet.ENGLISH, "النسخة الإنجليزية")
        await status.delete()
    except AnalysisError as e:
        log.warning("translation failed: %s", e)
        await status.edit_text("⚠️ تعذّرت الترجمة الآن. حاول بعد قليل.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- Word and Notion ----------

async def on_docx(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    data = await asyncio.to_thread(exports.lecture_docx, lec)
    await context.bot.send_document(update.effective_chat.id, data, filename=pipeline.safe_name(lec["title"]) + ".docx",
                                    caption="📤 نسخة Word قابلة للتعديل: أضف ملاحظاتك عليها.")


async def on_markdown(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    data = exports.lecture_markdown(lec).encode("utf-8")
    await context.bot.send_document(update.effective_chat.id, data, filename=pipeline.safe_name(lec["title"]) + ".md",
                                    caption="📝 ملف Markdown لـ Notion: في Notion اختر Import ← Markdown، ثم هذا الملف.")


# ---------- copying a lecture to another student ----------

def copy_lecture(context, from_uid: int, lid: str, to_uid: int, sender_name: str,
                 course: str | None = None) -> str | None:
    """Put a copy of a lecture in another student's library (in `course` if given, else filed by its
    subject); returns its new id there."""
    owner_ud = context.application.user_data.get(from_uid, {})
    full = store.get(from_uid, owner_ud, lid)
    if not full:
        return None
    to_ud = context.application.user_data[to_uid]
    new_lid = uuid.uuid4().hex[:8]
    full = dict(full, time=time.time(), shared_from=sender_name, course=None)
    full.pop("en_file_id", None)
    store.put(to_uid, to_ud, new_lid, full)
    if course and course in library.courses(to_ud):
        to_ud["lectures"][new_lid]["course"] = course
    else:
        library.assign_course(to_ud, new_lid, full.get("subject", ""))
    study.add_cards(to_ud.setdefault("deck", []), full.get("flashcards", []), full.get("title", ""))
    to_ud.setdefault("reminder_hour", config.DEFAULT_REMINDER_HOUR)
    context.application.mark_data_for_update_persistence(user_ids=[to_uid])
    return new_lid


async def _deliver(context, to_uid: int, new_lid: str, note: str) -> None:
    ud = context.application.user_data[to_uid]
    meta = ud["lectures"][new_lid]
    if not await botkit.send_lecture(context, to_uid, ud, new_lid, note):
        await context.bot.send_message(to_uid, note, reply_markup=botkit.lecture_keyboard(new_lid, meta))


async def receive(context, from_uid: int, lid: str, to_uid: int, sender_name: str, note: str,
                  course: str | None = None) -> bool:
    """Give a classmate's lecture to `to_uid`: free while charging is off or for their first few,
    otherwise for bot_wallet.RECEIVE Stars (the sender gets bot_wallet.CASHBACK). When their balance is
    short, they get a notice with an unlock button instead. Returns whether anything reached them."""
    to_ud = context.application.user_data[to_uid]
    meta = context.application.user_data.get(from_uid, {}).get("lectures", {}).get(lid)
    if not meta:
        return False
    bot_wallet.welcome(to_ud)
    free = not bot_wallet.enabled(context) or to_ud.get("free_receives", 0) > 0
    if not free and bot_wallet.balance(to_ud) < bot_wallet.RECEIVE:
        token = uuid.uuid4().hex[:8]
        to_ud.setdefault("locked", {})[token] = {"from": from_uid, "lid": lid, "name": sender_name,
                                                 "note": note, "course": course, "ts": time.time()}
        context.application.mark_data_for_update_persistence(user_ids=[to_uid])
        await context.bot.send_message(
            to_uid, f"📥 وصلتك محاضرة «{meta['title']}» من {sender_name}.\n"
                    f"افتحها بـ ⭐ {bot_wallet.RECEIVE} (رصيدك ⭐ {bot_wallet.balance(to_ud)}).",
            reply_markup=InlineKeyboardMarkup([[button(f"🔓 افتحها (⭐ {bot_wallet.RECEIVE})", f"unl:{token}")]]))
        return True
    new_lid = copy_lecture(context, from_uid, lid, to_uid, sender_name, course=course)
    if not new_lid:
        return False
    if bot_wallet.enabled(context):
        if to_ud.get("free_receives", 0) > 0:
            to_ud["free_receives"] -= 1
        else:
            bot_wallet.charge(context, to_ud, bot_wallet.RECEIVE, f"محاضرة من {sender_name}")
            bot_wallet.credit(context.application.user_data[from_uid], bot_wallet.CASHBACK, "زميل استلم محاضرتك")
            context.application.mark_data_for_update_persistence(user_ids=[from_uid])
    await _deliver(context, to_uid, new_lid, note)
    return True


async def on_unlock(update: Update, context, token: str) -> None:
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    item = ud.get("locked", {}).get(token)
    if not item:
        await context.bot.send_message(chat, "فتحت هذه المحاضرة من قبل، أو لم تعد متاحة. /library")
        return
    if not await bot_wallet.require(context, chat, ud, bot_wallet.RECEIVE, "فتح هذه المحاضرة"):
        return
    ud["locked"].pop(token)
    if not await receive(context, item["from"], item["lid"], uid, item["name"], item["note"], item["course"]):
        await context.bot.send_message(chat, "حذف صاحب المحاضرة هذه المحاضرة، فلم تعد متاحة.")
        return
    try:
        await update.callback_query.edit_message_reply_markup(None)
    except TelegramError:
        pass


# ---------- share link ----------

async def on_share(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    token = uuid.uuid4().hex[:10]
    context.bot_data.setdefault("shares", {})[token] = {"uid": update.effective_user.id, "lid": lid,
                                                        "name": botkit.first_name(update), "ts": time.time()}
    link = f"https://t.me/{context.bot.username}?start=s_{token}"
    await context.bot.send_message(
        update.effective_chat.id,
        f"🔗 أرسل هذا الرابط لزملائك، فيحصل كل من يفتحه على ملخص «{escape(lec['title'])}» وأسئلته وبطاقاته في "
        f"مكتبته:\n\n{link}\n\n🎁 وكل زميل يستلمها يضيف ⭐ لرصيدك.",
        parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def start_shared(update: Update, context, token: str, new: bool) -> bool:
    share = context.bot_data.get("shares", {}).get(token)
    uid = update.effective_user.id
    if not share:
        await update.effective_message.reply_text("هذا الرابط لم يعد صالحاً. اطلب من زميلك رابطاً جديداً.")
        return True
    if share["uid"] == uid:
        await update.effective_message.reply_text("هذا رابط مشاركة لمحاضرتك. أرسله لزملائك 🙂")
        return True
    if new:
        bot_growth.welcome_credits(context.user_data)
    title = context.application.user_data.get(share["uid"], {}).get("lectures", {}).get(share["lid"], {}).get("title")
    if not await receive(context, share["uid"], share["lid"], uid, share["name"],
                         f"📚 شاركك {share['name']} ملخص «{title}». حفظته في مكتبتك /library"):
        await update.effective_message.reply_text("حذف صاحب المحاضرة هذه المحاضرة، فلم تعد متاحة.")
        return True
    if new:
        await update.effective_message.reply_text("أهلاً بك في فَهيم 👋 أرسل تسجيل أي محاضرة، وأجهّز لك ملخصها "
                                                  "وأسئلتها. /start لطريقة الاستخدام.")
    return True


def register(app) -> None:
    pass


botkit.LECTURE_BUTTONS.update({"en": on_english, "docx": on_docx, "md": on_markdown, "share": on_share})
botkit.BUTTONS.update({"unl": on_unlock})
botkit.START_LINKS.update({"s": start_shared})
