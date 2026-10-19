"""Translating, exporting and sharing: English PDF, Word / Notion files, share links for classmates
and study groups."""
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
from telegram.ext import CommandHandler, ContextTypes

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
        f"مكتبته:\n\n{link}\n\n🎁 وكل زميل يستلمها يضيف ⭐ لرصيدك، وكل صديقين جديدين يضيفان ⭐ {bot_wallet.REFERRAL}.",
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
        await bot_growth.referred(context, share["uid"], uid)
    title = context.application.user_data.get(share["uid"], {}).get("lectures", {}).get(share["lid"], {}).get("title")
    if not await receive(context, share["uid"], share["lid"], uid, share["name"],
                         f"📚 شاركك {share['name']} ملخص «{title}». حفظته في مكتبتك /library"):
        await update.effective_message.reply_text("حذف صاحب المحاضرة هذه المحاضرة، فلم تعد متاحة.")
        return True
    if new:
        await update.effective_message.reply_text("أهلاً بك في فَهيم 👋 أرسل تسجيل أي محاضرة، وأجهّز لك ملخصها "
                                                  "وأسئلتها. /start لطريقة الاستخدام.")
    return True


# ---------- study groups ----------

def _members(n: int) -> str:
    return botkit.count(n, "عضو واحد", "عضوان", "أعضاء", "عضواً")


def my_groups(context, ud: dict) -> list[tuple[str, dict]]:
    groups = context.bot_data.get("groups", {})
    return [(gid, groups[gid]) for gid in ud.get("groups", []) if gid in groups]


async def groups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _groups_home(update, context)


async def _groups_home(update: Update, context) -> None:
    ud = context.user_data
    rows = [[button(f"👥 {g['name'][:40]} ({len(g['members'])})", f"grp:v:{gid}")] for gid, g in my_groups(context, ud)]
    rows.append([button("➕ مجموعة جديدة", "grp:new:")])
    text = ("👥 <b>مجموعات الدراسة</b>\nادعُ زملاء دفعتك، وأي محاضرة يرسلها أحدكم للمجموعة تصل للجميع بملخصها "
            "وأسئلتها، فلا يحتاج كل واحد أن يرفعها.")
    await context.bot.send_message(update.effective_chat.id, text, parse_mode=ParseMode.HTML,
                                   reply_markup=InlineKeyboardMarkup(rows))


async def on_group(update: Update, context, arg: str) -> None:
    step, _, gid = arg.partition(":")
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    groups = context.bot_data.setdefault("groups", {})
    if step == "new":
        botkit.expect(ud, "group_name")
        await context.bot.send_message(chat, "👥 اكتب اسم المجموعة (مثلاً: فسيولوجي - دفعة 2026):")
        return
    g = groups.get(gid)
    if not g or uid not in g["members"]:
        await context.bot.send_message(chat, "لم تعد هذه المجموعة موجودة.")
        return
    if step == "v":
        link = f"https://t.me/{context.bot.username}?start=g_{gid}"
        course = ud.get("group_course", {}).get(gid)
        cname = library.courses(ud).get(course, {}).get("name") if course else None
        rows = [[button("🚪 مغادرة المجموعة", f"grp:leave:{gid}")]]
        if cname:
            rows.insert(0, [button("⏸ إيقاف الإرسال التلقائي", f"grp:unlink:{gid}")])
        auto = (f"🔄 محاضرات «{escape(cname)}» التي ترفعها تصل للمجموعة تلقائياً." if cname else
                "بعد أول محاضرة ترفعها أسألك: هل أرسل محاضرات مادتها للمجموعة تلقائياً؟")
        await context.bot.send_message(
            chat, f"👥 <b>{escape(g['name'])}</b> · {_members(len(g['members']))}\n\n{auto}\n\n"
                  f"رابط الدعوة (أرسله لزملائك):\n{link}",
            parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(rows))
    elif step == "unlink":
        ud.get("group_course", {}).pop(gid, None)
        ud.setdefault("group_declined", {}).pop(gid, None)
        await context.bot.send_message(chat, f"⏸ أوقفت الإرسال التلقائي لمجموعة «{g['name']}». "
                                             "تستطيع إرسال أي محاضرة يدوياً من «⋯ المزيد».")
    elif step == "leave":
        g["members"].remove(uid)
        ud["groups"] = [x for x in ud.get("groups", []) if x != gid]
        if not g["members"]:
            groups.pop(gid, None)
        await context.bot.send_message(chat, f"🚪 غادرت مجموعة «{g['name']}».")


async def input_group_name(update: Update, context, _payload: str) -> None:
    ud, uid = context.user_data, update.effective_user.id
    gid = uuid.uuid4().hex[:8]
    name = update.effective_message.text.strip()[:60]
    context.bot_data.setdefault("groups", {})[gid] = {"name": name, "owner": uid, "members": [uid], "ts": time.time()}
    ud.setdefault("groups", []).append(gid)
    link = f"https://t.me/{context.bot.username}?start=g_{gid}"
    await update.effective_message.reply_text(f"👥 أنشأت مجموعة «{name}». أرسل هذا الرابط لزملائك لينضموا:\n{link}",
                                              disable_web_page_preview=True)


async def start_group(update: Update, context, gid: str, new: bool) -> bool:
    g = context.bot_data.get("groups", {}).get(gid)
    uid = update.effective_user.id
    if not g:
        await update.effective_message.reply_text("رابط المجموعة لم يعد صالحاً.")
        return True
    if new:
        bot_growth.welcome_credits(context.user_data)
        await bot_growth.referred(context, g["owner"], uid)
    if uid not in g["members"]:
        g["members"].append(uid)
        context.user_data.setdefault("groups", []).append(gid)
        for member in g["members"]:
            if member != uid:
                try:
                    await context.bot.send_message(member, f"👥 انضم {botkit.first_name(update)} إلى مجموعة «{g['name']}».")
                except TelegramError:
                    pass
    await update.effective_message.reply_text(
        f"👥 أنت الآن في مجموعة «{g['name']}» ({_members(len(g['members']))}). ستصلك محاضرات زملائك هنا.\n"
        "وأرسل أنت أي تسجيل محاضرة، ثم شاركه مع المجموعة.")
    return True


async def send_to_group(context, uid: int, lid: str, gid: str) -> int:
    """Copy a lecture into every other member's library and send it to them; returns how many got it."""
    g = context.bot_data.get("groups", {}).get(gid)
    ud = context.application.user_data[uid]
    meta = ud.get("lectures", {}).get(lid)
    if not g or not meta:
        return 0
    name, n = ud.get("name") or "زميلك", 0
    for member in g["members"]:
        if member == uid:
            continue
        link = context.application.user_data[member].get("group_course", {}).get(gid)
        try:
            if await receive(context, uid, lid, member, name,
                             f"👥 {name} شارك في «{g['name']}»: ملخص «{meta['title']}». حفظته في مكتبتك /library",
                             course=link):
                n += 1
        except TelegramError as e:
            log.info("group delivery to %s failed: %s", member, e)
    return n


async def on_to_group(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    groups = my_groups(context, ud)
    if not extra:
        if not groups:
            await context.bot.send_message(chat, "لست في أي مجموعة بعد. /groups لإنشاء مجموعة.")
            return
        rows = [[button("👥 " + g["name"][:50], f"tog:{lid}:{gid}")] for gid, g in groups]
        await context.bot.send_message(chat, "👥 لأي مجموعة أرسلها؟", reply_markup=InlineKeyboardMarkup(rows))
        return
    g = dict(groups).get(extra)
    if not g:
        return
    ud["name"] = botkit.first_name(update)
    n = await send_to_group(context, uid, lid, extra)
    await context.bot.send_message(chat, f"👥 أرسلتها إلى أعضاء «{g['name']}» ({_members(n)}). شكراً لأنك تساعد زملاءك!")


# ---------- automatic sharing ----------
# Each member links a group to one of their courses. A lecture filed in that course goes to the group
# by itself. The first time, the bot asks; after that it never asks again for that group and course.

async def auto_share(context, uid: int, lid: str) -> None:
    ud = context.application.user_data[uid]
    course = ud.get("lectures", {}).get(lid, {}).get("course")
    links, declined = ud.setdefault("group_course", {}), ud.setdefault("group_declined", {})
    for gid, g in my_groups(context, ud):
        link = links.get(gid)
        if link == course:
            n = await send_to_group(context, uid, lid, gid)
            if n:
                await context.bot.send_message(uid, f"👥 أرسلتها تلقائياً لمجموعة «{g['name']}» ({_members(n)}).")
        elif link is None and course not in declined.get(gid, []):
            asked = ud.setdefault("group_asked", [])
            if f"{gid}:{course}" in asked:  # already asked; waiting for the answer
                continue
            asked.append(f"{gid}:{course}")
            cname = library.courses(ud).get(course, {}).get("name", "هذه المادة")
            await context.bot.send_message(
                uid, f"👥 هل أرسل محاضرات «{cname}» لمجموعة «{g['name']}» تلقائياً من الآن؟\n"
                     "(تصل لزملائك بملخصها وأسئلتها فور انتهائها)",
                reply_markup=InlineKeyboardMarkup([[button("✅ نعم، دائماً", f"gl:{gid}:{lid}:y"),
                                                    button("❌ لا", f"gl:{gid}:{lid}:n")]]))


async def on_group_link(update: Update, context, arg: str) -> None:
    gid, lid, answer = (arg.split(":") + ["", "", ""])[:3]
    ud, uid = context.user_data, update.effective_user.id
    course = ud.get("lectures", {}).get(lid, {}).get("course")
    g = context.bot_data.get("groups", {}).get(gid)
    if not g or not course:
        return
    ud["name"] = botkit.first_name(update)
    if answer == "y":
        ud.setdefault("group_course", {})[gid] = course
        n = await send_to_group(context, uid, lid, gid)
        await update.callback_query.edit_message_text(
            f"✅ تم: محاضرات «{library.courses(ud)[course]['name']}» تصل لمجموعة «{g['name']}» تلقائياً. "
            f"وأرسلت هذه الآن ({_members(n)}).")
    else:
        ud.setdefault("group_declined", {}).setdefault(gid, []).append(course)
        await update.callback_query.edit_message_text("👍 حسناً، لن أرسل محاضرات هذه المادة للمجموعة.")


def register(app) -> None:
    app.add_handler(CommandHandler("groups", groups_cmd))


botkit.LECTURE_BUTTONS.update({"en": on_english, "docx": on_docx, "md": on_markdown,
                               "share": on_share, "tog": on_to_group})
botkit.BUTTONS.update({"grp": on_group, "gl": on_group_link, "unl": on_unlock})
botkit.TEXT_INPUTS.update({"group_name": input_group_name})
botkit.START_LINKS.update({"s": start_shared, "g": start_group})
