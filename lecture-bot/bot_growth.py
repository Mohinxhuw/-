"""Growth: statistics, invite links and credits, the free trial, and the teacher version.

Credits are tracked from day one but only enforced when BILLING_ENABLED is on (when paid plans start):
every new student gets FREE_LECTURES, and every REFERRALS_PER_CREDIT friends they bring earn one more.
"""
import asyncio
import datetime as dt
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

import botkit
from botkit import button
from lecturebot import config, exports, library, pipeline, render, study


def _questions(n: int) -> str:
    return botkit.count(n, "سؤال واحد", "سؤالان", "أسئلة", "سؤالاً")


def _friends(n: int) -> str:
    return botkit.count(n, "صديق واحد", "صديقين", "أصدقاء", "صديقاً")


def _stats(ud: dict) -> dict:
    return ud.setdefault("stats", {"lectures": 0, "seconds": 0, "answered": 0, "correct": 0, "by_lecture": {},
                                   "review_days": []})


# ---------- credits and referrals ----------

def welcome_credits(ud: dict) -> None:
    if "credits" not in ud:
        ud["credits"] = config.FREE_LECTURES


async def referred(context, referrer: int, new_user: int) -> None:
    if referrer == new_user or context.user_data.get("referred_by"):
        return
    context.user_data["referred_by"] = referrer
    ref_ud = context.application.user_data[referrer]
    refs = ref_ud.setdefault("refs", [])
    if new_user in refs:
        return
    refs.append(new_user)
    earned = len(refs) % config.REFERRALS_PER_CREDIT == 0
    if earned:
        ref_ud["credits"] = ref_ud.get("credits", 0) + 1
    context.application.mark_data_for_update_persistence(user_ids=[referrer])
    try:
        text = "🎉 انضم صديق جديد إلى فَهيم من رابطك!"
        if earned:
            text += " وحصلت على محاضرة مجانية 🎁"
        else:
            text += " صديق واحد آخر وتحصل على محاضرة مجانية 🎁"
        await context.bot.send_message(referrer, text)
    except TelegramError:
        pass


async def can_process(context, chat_id: int, ud: dict) -> bool:
    """With billing on, a lecture needs a credit. Without it, everyone can use the bot freely."""
    if not config.BILLING_ENABLED or ud.get("credits", 0) > 0:
        return True
    link = f"https://t.me/{context.bot.username}?start=r_{chat_id}"
    await context.bot.send_message(
        chat_id, "🎁 انتهى رصيدك من المحاضرات المجانية.\nادعُ صديقين بهذا الرابط، وتحصل على محاضرة مجانية لكل صديقين:\n"
                 f"{link}", disable_web_page_preview=True)
    return False


def lecture_done(ud: dict, full: dict) -> None:
    s = _stats(ud)
    s["lectures"] += 1
    s["seconds"] += int(full.get("duration") or 0)
    if config.BILLING_ENABLED:
        ud["credits"] = max(0, ud.get("credits", 0) - 1)


def reviewed(ud: dict) -> None:
    days = _stats(ud)["review_days"]
    t = study.today().isoformat()
    if t not in days:
        days.append(t)
        del days[:-60]


async def start_referral(update: Update, context, referrer: str, new: bool) -> bool:
    if new and referrer.isdigit():
        welcome_credits(context.user_data)
        await referred(context, int(referrer), update.effective_user.id)
    return False  # carry on with the normal welcome


async def invite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = context.user_data
    welcome_credits(ud)
    link = f"https://t.me/{context.bot.username}?start=r_{update.effective_user.id}"
    refs = len(ud.get("refs", []))
    to_next = config.REFERRALS_PER_CREDIT - refs % config.REFERRALS_PER_CREDIT
    note = "" if config.BILLING_ENABLED else "\n(فَهيم مجاني حالياً؛ يُستخدم رصيدك عند إطلاق الاشتراكات)"
    await update.effective_message.reply_text(
        f"🎁 <b>ادعُ أصدقاءك</b>\nكل {_friends(config.REFERRALS_PER_CREDIT)} ينضمون من رابطك = محاضرة مجانية.\n\n{link}\n\n"
        f"👥 انضم من رابطك: {refs}\n🎟 رصيدك: {ud.get('credits', 0)} محاضرة\n"
        f"⏭ باقي {_friends(to_next)} للمحاضرة المجانية التالية{note}",
        parse_mode=ParseMode.HTML, disable_web_page_preview=True)


# ---------- statistics ----------

def _bar(frac: float, width: int = 10) -> str:
    n = round(max(0.0, min(1.0, frac)) * width)
    return "▰" * n + "▱" * (width - n)


def _streak(days: list[str], today: dt.date) -> int:
    have, n, d = set(days), 0, today
    if d.isoformat() not in have:
        d -= dt.timedelta(days=1)  # today's review may not be done yet
    while d.isoformat() in have:
        n += 1
        d -= dt.timedelta(days=1)
    return n


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud, today = context.user_data, study.today()
    s = _stats(ud)
    lectures = ud.get("lectures", {})
    deck = ud.get("deck", [])
    mastered = sum(1 for c in deck if c["box"] >= 3)
    lines = ["📊 <b>إحصاءاتك</b>", "",
             f"📚 المحاضرات: {len(lectures)} · ⏱ {round(s['seconds'] / 3600, 1)} ساعة تسجيل",
             f"📁 المواد: {len([c for c in library.courses(ud) if library.course_lectures(ud, c)])}"]
    if s["answered"]:
        acc = s["correct"] / s["answered"]
        lines.append(f"🧪 الأسئلة: {s['correct']} صحيحة من {s['answered']}\n{_bar(acc)} {round(acc * 100)}%")
    if deck:
        lines.append(f"🃏 البطاقات: {len(deck)} · أتقنت {mastered}\n{_bar(mastered / len(deck))} {round(mastered / len(deck) * 100)}%")
    streak = _streak(s["review_days"], today)
    if streak:
        lines.append(f"🔥 أيام المراجعة المتتالية: {streak}")
    exams = [(library.days_left(c, today), c["name"]) for c in library.courses(ud).values()]
    exams = sorted((d, n) for d, n in exams if d is not None and d >= 0)
    if exams:
        lines += ["", "📅 <b>اختباراتك القادمة</b>"] + [f"• {escape(n)}: {library.countdown_text(d)}" for d, n in exams[:5]]
    weak = [(c / t, lid) for lid, (c, t) in s["by_lecture"].items() if t >= 3 and c / t < 0.6 and lid in lectures]
    rows = []
    if weak:
        lines += ["", "⚠️ <b>محاضرات تحتاج مراجعة</b> (أقل من 60% في أسئلتها):"]
        for acc, lid in sorted(weak)[:5]:
            lines.append(f"• {escape(lectures[lid]['title'])} ({round(acc * 100)}%)")
            rows.append([button("📖 " + lectures[lid]["title"][:50], f"lib:l:{lid}")])
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML,
                                              reply_markup=InlineKeyboardMarkup(rows) if rows else None)


async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ans = update.poll_answer
    info = context.bot_data.get("polls", {}).get(ans.poll_id)
    if not info or not ans.user:
        return
    right = info["correct"] in ans.option_ids
    if info["kind"] == "lecture":
        s = _stats(context.user_data)
        s["answered"] += 1
        s["correct"] += int(right)
        c, t = s["by_lecture"].get(info["lid"], (0, 0))
        s["by_lecture"][info["lid"]] = (c + int(right), t + 1)
    elif info["kind"] == "tq":
        quiz = context.bot_data.get("tquiz", {}).get(info["token"])
        if quiz:
            r = quiz["answers"].setdefault(str(ans.user.id), {"name": ans.user.full_name, "correct": 0, "answered": 0})
            r["answered"] += 1
            r["correct"] += int(right)
            q = quiz.setdefault("per_question", {}).setdefault(str(info["q"]), [0, 0])
            q[0] += int(right)
            q[1] += 1


def prune_polls(context) -> None:
    polls = context.bot_data.get("polls", {})
    old = time.time() - 30 * 86400
    for pid in [p for p, v in polls.items() if v.get("ts", 0) < old]:
        del polls[pid]


async def _prune_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    prune_polls(context)


# ---------- teacher version ----------

async def teacher_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = context.user_data
    ud["teacher"] = not ud.get("teacher")
    if ud["teacher"]:
        await update.effective_message.reply_text(
            "👨‍🏫 <b>تم تفعيل نسخة المعلم</b>\nأرسل تسجيل شرحك، ثم من «⋯ المزيد» تحت الملف تجد:\n"
            "• 📝 ورقة اختبار جاهزة للطباعة (وملف Word للتعديل)\n• 🔑 نموذج الإجابة\n"
            "• 🔗 اختبار لطلابك برابط: يحلّونه هنا، وتصلك نتائجهم بالأمر /results\n\nلإيقافها أرسل /teacher مرة أخرى.",
            parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text("تم إيقاف نسخة المعلم.")


async def on_paper(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    chat, name = update.effective_chat.id, pipeline.safe_name(lec["title"])
    work = Path(tempfile.mkdtemp(prefix="paper_", dir=botkit.work_root()))
    try:
        pdf = await asyncio.to_thread(render.write_pdf, exports.exam_paper_html(lec, False), work / f"{name}-exam.pdf")
        with open(pdf, "rb") as fh:
            await context.bot.send_document(chat, fh, filename=pdf.name, caption="📝 ورقة الاختبار جاهزة للطباعة.")
        data = await asyncio.to_thread(exports.exam_paper_docx, lec)
        await context.bot.send_document(chat, data, filename=f"{name}-exam.docx", caption="📤 نسخة Word للتعديل.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def on_key(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    name = pipeline.safe_name(lec["title"])
    work = Path(tempfile.mkdtemp(prefix="key_", dir=botkit.work_root()))
    try:
        pdf = await asyncio.to_thread(render.write_pdf, exports.exam_paper_html(lec, True), work / f"{name}-answers.pdf")
        with open(pdf, "rb") as fh:
            await context.bot.send_document(update.effective_chat.id, fh, filename=pdf.name, caption="🔑 نموذج الإجابة.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def on_teacher_quiz(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    token = uuid.uuid4().hex[:10]
    context.bot_data.setdefault("tquiz", {})[token] = {
        "owner": update.effective_user.id, "title": lec["title"], "mcq": lec.get("mcq", []),
        "tf": lec.get("true_false", []), "answers": {}, "ts": time.time()}
    link = f"https://t.me/{context.bot.username}?start=t_{token}"
    n = len(lec.get("mcq", [])) + len(lec.get("true_false", []))
    await context.bot.send_message(update.effective_chat.id,
                                   f"🔗 اختبار «{escape(lec['title'])}» ({_questions(n)}). أرسل هذا الرابط لطلابك:\n\n{link}\n\n"
                                   "يحلّونه داخل تيليجرام، وترى نتائجهم بالأمر /results", parse_mode=ParseMode.HTML,
                                   disable_web_page_preview=True)


async def start_teacher_quiz(update: Update, context, token: str, new: bool) -> bool:
    quiz = context.bot_data.get("tquiz", {}).get(token)
    chat = update.effective_chat.id
    if not quiz:
        await update.effective_message.reply_text("رابط الاختبار لم يعد صالحاً.")
        return True
    if new:
        welcome_credits(context.user_data)
    n = len(quiz["mcq"]) + len(quiz["tf"])
    await update.effective_message.reply_text(f"📝 اختبار «{quiz['title']}» من معلمك: {_questions(n)}. بالتوفيق!")
    i = 0
    for q in quiz["mcq"]:
        i += 1
        await botkit.send_quiz(context, chat, f"{i}. {q['question']}", q["options"], q["answer_index"],
                               q.get("explanation", ""), "", {"kind": "tq", "token": token, "q": i})
    for t in quiz["tf"]:
        i += 1
        await botkit.send_quiz(context, chat, f"{i}. صح أم خطأ؟ {t['statement']}", ["صح", "خطأ"], 0 if t["answer"] else 1,
                               t.get("explanation", ""), "", {"kind": "tq", "token": token, "q": i})
    return True


async def results_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    mine = [(k, q) for k, q in context.bot_data.get("tquiz", {}).items() if q["owner"] == uid]
    if not mine:
        await update.effective_message.reply_text("لا توجد اختبارات بعد. فعّل /teacher وأرسل شرحك، ثم أنشئ اختباراً لطلابك.")
        return
    rows = [[button(f"📝 {q['title'][:40]} ({len(q['answers'])})", f"tres:{k}")]
            for k, q in sorted(mine, key=lambda kq: -kq[1]["ts"])[:15]]
    await update.effective_message.reply_text("📊 اختر الاختبار لترى نتائج طلابك:", reply_markup=InlineKeyboardMarkup(rows))


async def on_results(update: Update, context, token: str) -> None:
    quiz = context.bot_data.get("tquiz", {}).get(token)
    if not quiz or quiz["owner"] != update.effective_user.id:
        return
    total = len(quiz["mcq"]) + len(quiz["tf"])
    people = sorted(quiz["answers"].values(), key=lambda r: -r["correct"])
    lines = [f"📊 <b>{escape(quiz['title'])}</b> · {_questions(total)} · "
             + botkit.count(len(people), "طالب واحد", "طالبان", "طلاب", "طالباً")]
    if people:
        avg = sum(r["correct"] for r in people) / len(people)
        lines.append(f"المتوسط: {round(avg, 1)} من {total}\n")
        lines += [f"• {escape(r['name'])}: {r['correct']}/{total}" + ("" if r["answered"] >= total else
                                                                       f" (أجاب {r['answered']})") for r in people[:50]]
        hard = sorted(((c / t, int(q)) for q, (c, t) in quiz.get("per_question", {}).items() if t >= 3))[:3]
        if hard and hard[0][0] < 0.5:
            lines.append("\n⚠️ أصعب الأسئلة: " + "، ".join(f"السؤال {q} ({round(a * 100)}%)" for a, q in hard if a < 0.5))
    else:
        lines.append("لم يحل أحد الاختبار بعد.")
    await botkit.send_long(context, update.effective_chat.id, "\n".join(lines), parse_mode=ParseMode.HTML)


def register(app) -> None:
    for name, fn in (("stats", stats_cmd), ("invite", invite_cmd), ("teacher", teacher_cmd), ("results", results_cmd)):
        app.add_handler(CommandHandler(name, fn))
    app.job_queue.run_repeating(_prune_job, interval=86400, first=3600)


botkit.LECTURE_BUTTONS.update({"tpaper": on_paper, "tkey": on_key, "tquiz": on_teacher_quiz})
botkit.BUTTONS.update({"tres": on_results})
botkit.START_LINKS.update({"r": start_referral, "t": start_teacher_quiz})
