"""Organisation: the student's library by course, search, and the daily reminder."""
import asyncio
import datetime as dt
import shutil
import tempfile
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CommandHandler, ContextTypes

import botkit
import bot_wallet
from botkit import button, log
from lecturebot import config, library, pipeline, render, store, study
from lecturebot.analyze import AnalysisError


def _lectures(n: int) -> str:
    return botkit.count(n, "محاضرة واحدة", "محاضرتين", "محاضرات", "محاضرة")


def _today() -> dt.date:
    return study.today()


def _course_label(c: dict, n: int) -> str:
    return f"📁 {c['name']} ({n})"


async def _show(update: Update, context, text: str, rows: list) -> None:
    """Edit the message the button was on, or send a new one for a command."""
    markup = InlineKeyboardMarkup(rows)
    q = update.callback_query
    if q:
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except BadRequest:
            pass
    await context.bot.send_message(update.effective_chat.id, text, parse_mode=ParseMode.HTML, reply_markup=markup)


# ---------- library ----------

async def library_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _home(update, context)


async def _home(update: Update, context) -> None:
    ud = context.user_data
    if not ud.get("lectures"):
        await _show(update, context, "📚 مكتبتك فارغة. أرسل تسجيل محاضرة، وأحفظها لك هنا مرتبة بالمواد.", [])
        return
    rows = [[button(_course_label(c, len(library.course_lectures(ud, cid))), f"lib:c:{cid}")]
            for cid, c in library.courses(ud).items() if library.course_lectures(ud, cid)]
    loose = library.unfiled(ud)
    if loose:
        rows.append([button(f"🗂 بلا مادة ({len(loose)})", "lib:u:")])
    rows.append([button("🔍 بحث في محاضراتي", "lib:find:")])
    n_courses = len(rows) - 1 - (1 if loose else 0)
    await _show(update, context, f"📚 <b>مكتبتك</b>: {_lectures(len(ud['lectures']))} في "
                                 f"{botkit.count(n_courses, 'مادة واحدة', 'مادتين', 'مواد', 'مادة')}.\n"
                                 "اختر مادة:", rows)


async def _course(update: Update, context, cid: str) -> None:
    ud, today = context.user_data, _today()
    c = library.courses(ud).get(cid)
    if not c:
        await _home(update, context)
        return
    lids = library.course_lectures(ud, cid)
    lectures = ud["lectures"]
    lines = [f"📁 <b>{escape(c['name'])}</b> · {_lectures(len(lids))}"]
    if c.get("readiness"):
        r = c["readiness"]
        lines.append(f"📈 جاهزيتك: {r['pct']}% (آخر محاكاة {library.day_name(dt.date.fromisoformat(r['date']), today)})")
    rows = [[button("📄 " + (lectures[l].get("title") or "محاضرة")[:55], f"lib:l:{l}")] for l in lids[-25:]]
    rows.append([button("🧪 اختبار شامل للمادة", f"cq:{cid}"), button("🌙 ملخص ليلة الاختبار", f"lib:exam:{cid}")])
    rows.append([button("⏱ محاكاة الاختبار", f"sim:{cid}"), button("📖 مصطلحات المادة", f"glos:{cid}")])
    rows.append([button("✏️ إعادة التسمية", f"lib:ren:{cid}")])
    rows.append([button("↩️ المكتبة", "lib:home:")])
    await _show(update, context, "\n".join(lines), rows)


async def _unfiled(update: Update, context) -> None:
    ud = context.user_data
    rows = [[button("📄 " + (ud["lectures"][l].get("title") or "محاضرة")[:55], f"lib:l:{l}")]
            for l in library.unfiled(ud)[-25:]]
    rows.append([button("↩️ المكتبة", "lib:home:")])
    await _show(update, context, "🗂 محاضرات بلا مادة. افتح محاضرة وانقلها لمادتها من «⋯ المزيد».", rows)


async def _lecture(update: Update, context, lid: str) -> None:
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    meta = ud.get("lectures", {}).get(lid)
    if not meta:
        await context.bot.send_message(chat, "لم أعد أحتفظ بهذه المحاضرة.")
        return
    when = dt.datetime.fromtimestamp(meta["time"], ZoneInfo(config.REMINDER_TZ)).strftime("%Y-%m-%d")
    course = library.courses(ud).get(meta.get("course"), {}).get("name", "بلا مادة")
    dur = f" · {botkit.minutes(meta['duration'])}" if meta.get("duration") else ""
    caption = f"📄 {meta.get('title', '')}\n📁 {course} · {when}{dur}"
    if "questions" in botkit.lecture_files(meta) and await botkit.send_lecture(context, chat, ud, lid, caption):
        return
    # Saved before the lecture's files were split, or its files are gone: make them again from what is stored.
    lec = store.get(uid, ud, lid)
    if not lec:
        await context.bot.send_message(chat, caption, reply_markup=botkit.lecture_keyboard(lid, meta))
        return
    await context.bot.send_chat_action(chat, ChatAction.UPLOAD_DOCUMENT)
    work = Path(tempfile.mkdtemp(prefix="files_", dir=botkit.work_root()))
    try:
        paths = await asyncio.to_thread(pipeline.write_files, lec, pipeline.paragraphs_of(lec.get("transcript", "")),
                                        work, "", lec.get("source_url", ""), lec.get("duration") or 0)
        ids = await botkit.send_files(context, chat, paths, caption, botkit.lecture_keyboard(lid, meta))
        if ids:
            meta["files"], meta["pdf_file_id"] = ids, ids.get("summary")
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def on_lib(update: Update, context: ContextTypes.DEFAULT_TYPE, arg: str) -> None:
    step, _, value = arg.partition(":")
    ud = context.user_data
    if step == "home":
        await _home(update, context)
    elif step == "c":
        await _course(update, context, value)
    elif step == "u":
        await _unfiled(update, context)
    elif step == "l":
        await _lecture(update, context, value)
    elif step == "find":
        botkit.expect(ud, "search")
        await context.bot.send_message(update.effective_chat.id, "🔍 اكتب الكلمة أو العبارة التي تبحث عنها:")
    elif step == "ren":
        botkit.expect(ud, "rename_course", value)
        await context.bot.send_message(update.effective_chat.id, "✏️ اكتب الاسم الجديد للمادة:")
    elif step == "exam":
        lids = library.course_lectures(ud, value)
        await generate_exam(update, context, lids)


# ---------- moving a lecture to another course ----------

async def on_move(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    ud = context.user_data
    rows = [[button("📁 " + c["name"][:50], f"mvto:{lid}:{cid}")] for cid, c in library.courses(ud).items()]
    rows.append([button("➕ مادة جديدة", f"mvnew:{lid}")])
    await context.bot.send_message(update.effective_chat.id, f"📁 إلى أي مادة أنقل «{escape(lec['title'])}»؟",
                                   parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))


async def on_move_to(update: Update, context, arg: str) -> None:
    lid, _, cid = arg.partition(":")
    ud = context.user_data
    if lid in ud.get("lectures", {}) and cid in library.courses(ud):
        ud["lectures"][lid]["course"] = cid
        await update.callback_query.edit_message_text(f"📁 نقلتها إلى «{library.courses(ud)[cid]['name']}».")


async def on_move_new(update: Update, context, arg: str) -> None:
    botkit.expect(context.user_data, "new_course", arg)
    await context.bot.send_message(update.effective_chat.id, "➕ اكتب اسم المادة الجديدة:")


async def input_new_course(update: Update, context, lid: str) -> None:
    ud = context.user_data
    cid = library.new_course(ud, update.effective_message.text)
    if lid in ud.get("lectures", {}):
        ud["lectures"][lid]["course"] = cid
    await update.effective_message.reply_text(f"📁 أنشأت مادة «{library.courses(ud)[cid]['name']}» ونقلت المحاضرة إليها.",
                                              reply_markup=InlineKeyboardMarkup([[button("📂 افتح المادة", f"lib:c:{cid}")]]))


async def input_rename(update: Update, context, cid: str) -> None:
    c = library.courses(context.user_data).get(cid)
    if c:
        c["name"] = update.effective_message.text.strip()[:60]
        await update.effective_message.reply_text(f"✏️ صار اسم المادة «{c['name']}».",
                                                  reply_markup=InlineKeyboardMarkup([[button("📂 افتح المادة", f"lib:c:{cid}")]]))


# ---------- exam-night summary ----------

async def generate_exam(update: Update, context, lids: list[str]) -> None:
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    chosen = [store.get(uid, ud, k) for k in lids]
    chosen = sorted((l for l in chosen if l and l.get("sections")), key=lambda l: l["time"])
    if not chosen:
        await context.bot.send_message(chat, "لا توجد محاضرات جاهزة لهذا الملخص. أرسل محاضرات المادة أولاً.")
        return
    if not await bot_wallet.require(context, chat, ud, bot_wallet.EXAM, "ملخص ليلة الاختبار"):
        return
    status = await context.bot.send_message(chat, f"🌙 أجهّز ملخص ليلة الاختبار من {_lectures(len(chosen))}…")
    work = Path(tempfile.mkdtemp(prefix="exam_", dir=botkit.work_root()))
    try:
        summary = await asyncio.to_thread(study.exam_summary, chosen)
        html = render.build_exam_html(summary, [l["title"] for l in chosen])
        pdf = await asyncio.to_thread(render.write_pdf, html,
                                      work / (pipeline.safe_name(summary.get("title") or "exam") + ".pdf"))
        await status.delete()
        with open(pdf, "rb") as fh:
            await context.bot.send_document(chat, fh, filename=pdf.name,
                                            caption="🌙 ملخص ليلة الاختبار: أهم الأفكار، وما يجب حفظه، "
                                                    "ونقاط يخلط فيها الطلاب، واختبر نفسك. بالتوفيق!")
        bot_wallet.charge(context, ud, bot_wallet.EXAM, "ملخص ليلة الاختبار")
    except AnalysisError as e:
        log.warning("exam summary failed: %s", e)
        await status.edit_text("⚠️ تعذّر تجهيز الملخص الآن. حاول بعد قليل.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- glossaries: of one lecture, or of a whole course, each in one file ----------

async def on_terms(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    chat, meta = update.effective_chat.id, context.user_data.get("lectures", {}).get(lid, {})
    if not lec.get("glossary"):
        await context.bot.send_message(chat, "لا توجد مصطلحات في هذه المحاضرة.")
        return
    caption = f"📖 مصطلحات «{lec.get('title', '')}»"
    file_id = botkit.lecture_files(meta).get("glossary")
    if file_id:
        try:
            await context.bot.send_document(chat, file_id, caption=caption)
            return
        except TelegramError:
            pass
    work = Path(tempfile.mkdtemp(prefix="terms_", dir=botkit.work_root()))
    try:
        html = render.build_files(lec, [], duration=lec.get("duration") or 0)["glossary"]
        pdf = await asyncio.to_thread(render.write_pdf, html, work / f"المصطلحات - {pipeline.safe_name(lec.get('title', ''))}.pdf")
        with open(pdf, "rb") as fh:
            sent = await context.bot.send_document(chat, fh, filename=pdf.name, caption=caption)
        if sent.document and meta.get("files"):
            meta["files"]["glossary"] = sent.document.file_id
    finally:
        shutil.rmtree(work, ignore_errors=True)




async def on_course_terms(update: Update, context, cid: str) -> None:
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    course = library.courses(ud).get(cid)
    if not course:
        return
    lectures = sorted((lec for lec in (store.get(uid, ud, l) for l in library.course_lectures(ud, cid)) if lec),
                      key=lambda l: l["time"])
    seen, terms = set(), []
    for lec in lectures:
        for g in lec.get("glossary", []):
            key = (g.get("term") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                terms.append(g)
    if not terms:
        await context.bot.send_message(chat, "لا توجد مصطلحات في محاضرات هذه المادة بعد.")
        return
    work = Path(tempfile.mkdtemp(prefix="terms_", dir=botkit.work_root()))
    try:
        html = render.build_files({"title": course["name"], "glossary": terms}, [])["glossary"]
        pdf = await asyncio.to_thread(render.write_pdf, html, work / f"مصطلحات المادة - {pipeline.safe_name(course['name'])}.pdf")
        with open(pdf, "rb") as fh:
            await context.bot.send_document(
                chat, fh, filename=pdf.name,
                caption=f"📖 مصطلحات مادة «{course['name']}»: "
                        + botkit.count(len(terms), "مصطلح واحد", "مصطلحان", "مصطلحات", "مصطلحاً")
                        + " من " + _lectures(len(lectures)) + ".")
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------- search ----------

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        await _search(update, context, " ".join(context.args))
    else:
        botkit.expect(context.user_data, "search")
        await update.effective_message.reply_text("🔍 اكتب الكلمة أو العبارة التي تبحث عنها في محاضراتك:")


async def input_search(update: Update, context, _payload: str) -> None:
    await _search(update, context, update.effective_message.text)


async def _search(update: Update, context, query: str) -> None:
    hits = await asyncio.to_thread(library.search, update.effective_user.id, context.user_data, query)
    if not hits:
        await update.effective_message.reply_text(f"🔍 لم أجد «{query}» في محاضراتك. جرّب كلمة أخرى.")
        return
    lines = [f"🔍 نتائج «{escape(query)}»:"]
    rows, seen = [], set()
    for h in hits:
        t = f" ⏱ {h['time']}" if h["time"] else ""
        lines.append(f"\n📄 <b>{escape(h['title'])}</b>{t}\n{escape(h['snippet'])}")
        if h["lid"] not in seen:
            seen.add(h["lid"])
            rows.append([button("📂 " + h["title"][:50], f"lib:l:{h['lid']}")])
    await botkit.send_long(context, update.effective_chat.id, "\n".join(lines), parse_mode=ParseMode.HTML,
                           reply_markup=InlineKeyboardMarkup(rows))


# ---------- the daily reminder: the cards due today ----------

def reminder_text(ud: dict, today: dt.date) -> tuple[str, list]:
    lines, rows = [], []
    due = study.due_cards(ud.get("deck", []))
    if due:
        lines.append(f"\n🔁 بطاقات المراجعة اليوم: {min(len(due), config.REVIEW_CARDS_PER_DAY)}")
        rows.append([button("▶️ ابدأ مراجعة البطاقات", "rev:start")])
    return "\n".join(lines).strip(), rows


async def daily_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Every 10 minutes: at each student's chosen hour, once a day, send what is due today."""
    now = dt.datetime.now(ZoneInfo(config.REMINDER_TZ))
    today = now.date()
    for user_id, ud in list(context.application.user_data.items()):
        hour = ud.get("reminder_hour")
        if hour is None or now.hour != hour or ud.get("reminded_on") == today.isoformat():
            continue
        text, rows = reminder_text(ud, today)
        if not text:
            continue
        ud["reminded_on"] = today.isoformat()
        try:
            await context.bot.send_message(user_id, "☀️ <b>يومك مع فَهيم</b>\n\n" + text, parse_mode=ParseMode.HTML,
                                           reply_markup=InlineKeyboardMarkup(rows))
        except TelegramError as e:
            log.info("reminder to %s failed: %s", user_id, e)
    context.application.mark_data_for_update_persistence(user_ids=list(context.application.user_data))


def register(app) -> None:
    app.add_handler(CommandHandler("library", library_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.job_queue.run_repeating(daily_reminders, interval=600, first=60)


botkit.BUTTONS.update({"lib": on_lib, "mvto": on_move_to, "mvnew": on_move_new, "glos": on_course_terms})
botkit.LECTURE_BUTTONS.update({"mv": on_move, "terms": on_terms})
botkit.TEXT_INPUTS.update({"search": input_search, "rename_course": input_rename, "new_course": input_new_course})
