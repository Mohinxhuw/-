"""Listening, translating, exporting and sharing: audio summary, English PDF, Word / Notion files,
share links for classmates and study groups."""
import asyncio
import shutil
import tempfile
import time
import uuid
from html import escape
from pathlib import Path

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes

import bot_growth
import botkit
from botkit import button, log
from lecturebot import config, exports, library, pipeline, render, store, study, tts
from lecturebot.analyze import AnalysisError


def _meta(context, lid: str) -> dict:
    return context.user_data.get("lectures", {}).get(lid, {})


async def _resend(context, chat_id: int, file_id: str | None, kind: str, caption: str) -> bool:
    if not file_id:
        return False
    try:
        if kind == "audio":
            await context.bot.send_audio(chat_id, file_id, caption=caption)
        else:
            await context.bot.send_document(chat_id, file_id, caption=caption)
        return True
    except TelegramError:
        return False


# ---------- audio summary ----------

async def on_audio(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    chat, meta = update.effective_chat.id, _meta(context, lid)
    caption = f"🎧 ملخص صوتي: {lec['title']}"
    if await _resend(context, chat, meta.get("audio_file_id"), "audio", caption):
        return
    status = await context.bot.send_message(chat, "🎧 أجهّز الملخص الصوتي… (دقيقة تقريباً)")
    work = Path(tempfile.mkdtemp(prefix="tts_", dir=botkit.work_root()))
    try:
        script = await asyncio.to_thread(study.audio_script, lec)
        await context.bot.send_chat_action(chat, ChatAction.UPLOAD_VOICE)
        mp3 = await asyncio.to_thread(tts.speak, script, work / "summary.mp3")
        with open(mp3, "rb") as fh:
            sent = await context.bot.send_audio(chat, fh, title=lec["title"][:60], performer="فَهيم",
                                                duration=tts.duration(mp3), caption=caption,
                                                filename=pipeline.safe_name(lec["title"]) + ".mp3")
        if sent.audio:
            meta["audio_file_id"] = sent.audio.file_id
        await status.delete()
    except (AnalysisError, tts.TTSError) as e:
        log.warning("audio summary failed: %s", e)
        await status.edit_text("⚠️ تعذّر تجهيز الملخص الصوتي الآن. حاول بعد قليل.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- English version ----------

async def on_english(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    chat, meta = update.effective_chat.id, _meta(context, lid)
    caption = f"🌐 English version: {lec['title']}"
    if await _resend(context, chat, meta.get("en_file_id"), "doc", caption):
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

def copy_lecture(context, from_uid: int, lid: str, to_uid: int, sender_name: str) -> str | None:
    """Put a copy of a lecture in another student's library; returns its new id there."""
    owner_ud = context.application.user_data.get(from_uid, {})
    full = store.get(from_uid, owner_ud, lid)
    if not full:
        return None
    to_ud = context.application.user_data[to_uid]
    new_lid = uuid.uuid4().hex[:8]
    full = dict(full, time=time.time(), shared_from=sender_name, course=None)
    for k in ("audio_file_id", "en_file_id"):
        full.pop(k, None)
    store.put(to_uid, to_ud, new_lid, full)
    library.assign_course(to_ud, new_lid, full.get("subject", ""))
    study.add_cards(to_ud.setdefault("deck", []), full.get("flashcards", []), full.get("title", ""))
    to_ud.setdefault("reminder_hour", config.DEFAULT_REMINDER_HOUR)
    context.application.mark_data_for_update_persistence(user_ids=[to_uid])
    return new_lid


async def _deliver(context, to_uid: int, new_lid: str, note: str) -> None:
    ud = context.application.user_data[to_uid]
    meta = ud["lectures"][new_lid]
    sent = False
    if meta.get("pdf_file_id"):
        try:
            await context.bot.send_document(to_uid, meta["pdf_file_id"], caption=note,
                                            reply_markup=botkit.lecture_keyboard(new_lid))
            sent = True
        except TelegramError as e:
            log.info("deliver pdf to %s failed: %s", to_uid, e)
    if not sent:
        await context.bot.send_message(to_uid, note, reply_markup=botkit.lecture_keyboard(new_lid))


# ---------- share link ----------

async def on_share(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    token = uuid.uuid4().hex[:10]
    context.bot_data.setdefault("shares", {})[token] = {"uid": update.effective_user.id, "lid": lid,
                                                        "name": botkit.first_name(update), "ts": time.time()}
    link = f"https://t.me/{context.bot.username}?start=s_{token}"
    await context.bot.send_message(
        update.effective_chat.id,
        f"🔗 أرسل هذا الرابط لزملائك، فيحصل كل من يفتحه على ملخص «{escape(lec['title'])}» وأسئلته وبطاقاته في "
        f"مكتبته:\n\n{link}\n\n🎁 وكل صديقين جديدين يدخلان من روابطك يمنحانك محاضرة مجانية.",
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
    new_lid = copy_lecture(context, share["uid"], share["lid"], uid, share["name"])
    if not new_lid:
        await update.effective_message.reply_text("حذف صاحب المحاضرة هذه المحاضرة، فلم تعد متاحة.")
        return True
    title = context.user_data["lectures"][new_lid]["title"]
    await _deliver(context, uid, new_lid, f"📚 شاركك {share['name']} ملخص «{title}». حفظته في مكتبتك /library")
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
        rows = [[button("🚪 مغادرة المجموعة", f"grp:leave:{gid}")]]
        await context.bot.send_message(
            chat, f"👥 <b>{escape(g['name'])}</b> · {_members(len(g['members']))}\n\nرابط الدعوة (أرسله لزملائك):\n{link}\n\n"
                  "لإرسال محاضرة للمجموعة: افتحها واضغط «⋯ المزيد» ← «👥 أرسلها لمجموعة».",
            parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(rows))
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
    name, n = botkit.first_name(update), 0
    for member in g["members"]:
        if member == uid:
            continue
        new_lid = copy_lecture(context, uid, lid, member, name)
        if new_lid:
            try:
                await _deliver(context, member, new_lid,
                               f"👥 {name} شارك في «{g['name']}»: ملخص «{lec['title']}». حفظته في مكتبتك /library")
                n += 1
            except TelegramError as e:
                log.info("group delivery to %s failed: %s", member, e)
    await context.bot.send_message(chat, f"👥 أرسلتها إلى أعضاء «{g['name']}» ({_members(n)}). شكراً لأنك تساعد زملاءك!")


def register(app) -> None:
    app.add_handler(CommandHandler("groups", groups_cmd))


botkit.LECTURE_BUTTONS.update({"audio": on_audio, "en": on_english, "docx": on_docx, "md": on_markdown,
                               "share": on_share, "tog": on_to_group})
botkit.BUTTONS.update({"grp": on_group})
botkit.TEXT_INPUTS.update({"group_name": input_group_name})
botkit.START_LINKS.update({"s": start_shared, "g": start_group})
