"""Testing: one "test me" button with every kind of question, and essay answers graded by Claude."""
import asyncio
import random
import time
import uuid
from html import escape

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

import botkit
import bot_wallet
from botkit import button, log
from lecturebot import library, store, study
from lecturebot.analyze import AnalysisError


def _questions(n: int) -> str:
    return botkit.count(n, "سؤال واحد", "سؤالان", "أسئلة", "سؤالاً")


async def on_quiz(update: Update, context, lid: str, lec: dict, extra: str) -> None:
    mcq, tf, essay = lec.get("mcq", []), lec.get("true_false", []), lec.get("essay", [])
    rows = []
    if mcq:
        rows.append([button(f"🔘 اختيار من متعدد ({len(mcq)})", f"qz:{lid}:mcq")])
    if tf:
        rows.append([button(f"✅❌ صح أو خطأ ({len(tf)})", f"qz:{lid}:tf")])
    if essay:
        rows.append([button(f"✍️ أسئلة مقالية ({len(essay)})", f"qz:{lid}:essay")])
    if len(rows) > 1:
        rows.append([button("🎲 الكل", f"qz:{lid}:all")])
    if not rows:
        await context.bot.send_message(update.effective_chat.id, "لا توجد أسئلة لهذه المحاضرة.")
        return
    await context.bot.send_message(update.effective_chat.id, f"🧪 <b>اختبرني في «{escape(lec['title'])}»</b>\n"
                                                             "اختر نوع الأسئلة:",
                                   parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))


async def on_kind(update: Update, context, lid: str, lec: dict, kind: str) -> None:
    chat = update.effective_chat.id
    track = {"kind": "lecture", "uid": update.effective_user.id, "lid": lid}
    polls = []
    if kind in ("mcq", "all"):
        polls += [(q["question"], q["options"], q["answer_index"], q.get("explanation", ""), q.get("time", ""), "m", j)
                  for j, q in enumerate(lec.get("mcq", []))]
    if kind in ("tf", "all"):
        polls += [(_tf(t), ["صح", "خطأ"], 0 if t["answer"] else 1, t.get("explanation", ""), t.get("time", ""), "t", j)
                  for j, t in enumerate(lec.get("true_false", []))]
    if kind == "all":
        random.shuffle(polls)
    for i, (question, options, correct, explanation, at, k, j) in enumerate(polls, 1):
        await botkit.send_quiz(context, chat, f"{i}. {question}", options, correct, explanation, at, track,
                               buttons=[botkit.evidence_button(lid, k, j)])
    if kind in ("essay", "all") and lec.get("essay"):
        await _send_essay(context, chat, lid, lec, 0)


def _tf(t: dict) -> str:
    english = sum(c.isascii() and c.isalpha() for c in t["statement"]) > len(t["statement"]) / 2
    return ("True or false? " if english else "صح أم خطأ؟ ") + t["statement"]


# ---------- the proof: the lecturer's own words behind an answer ----------

def _context_line(transcript: str, at: str) -> str:
    """The transcript paragraph that contains the moment `at` (transcript lines start with [mm:ss])."""
    def secs(t: str) -> int:
        n = 0
        for x in t.split(":"):
            n = n * 60 + int(x) if x.isdigit() else n
        return n
    best = ""
    for para in (transcript or "").split("\n\n"):
        if para.startswith("[") and "]" in para:
            if secs(para[1:para.index("]")]) <= secs(at):
                best = para[para.index("]") + 1:].strip()
            else:
                break
    return best


async def on_evidence(update: Update, context, arg: str) -> None:
    lid, kind, i = (arg.split(":") + ["", "", ""])[:3]
    lec = store.get(update.effective_user.id, context.user_data, lid)
    items = (lec or {}).get({"m": "mcq", "t": "true_false"}.get(kind, ""), [])
    if not i.isdigit() or int(i) >= len(items):
        return
    item = items[int(i)]
    quote, at = item.get("evidence", ""), item.get("time", "")
    if not quote:
        await context.bot.send_message(update.effective_chat.id, "لا يوجد اقتباس محفوظ لهذا السؤال.")
        return
    lines = ["📍 <b>الدليل من كلام المحاضر</b>" + (f" ⏱ {escape(at)}" if at else ""), f"«{escape(quote)}»"]
    around = _context_line(lec.get("transcript", ""), at) if at else ""
    if around and quote[:20] not in around[:20]:
        lines += ["", f"<b>السياق:</b> {escape(around[:700])}"]
    await context.bot.send_message(update.effective_chat.id, "\n".join(lines), parse_mode=ParseMode.HTML)


# ---------- essay questions ----------

def _essay_buttons(lid: str, i: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[button("👁 نموذج الإجابة", f"es:{lid}:{i}:show"),
                                  button("⏭ السؤال التالي", f"es:{lid}:{i + 1}:go")]])


async def _send_essay(context, chat: int, lid: str, lec: dict, i: int) -> None:
    essays = lec.get("essay", [])
    if i >= len(essays):
        context.user_data.pop("await", None)
        await context.bot.send_message(chat, "🎉 انتهت الأسئلة المقالية. أحسنت!")
        return
    q = essays[i]
    botkit.expect(context.user_data, "essay_answer", f"{lid}:{i}")
    await context.bot.send_message(
        chat, f"✍️ <b>سؤال مقالي {i + 1} من {len(essays)}</b>\n\n{escape(q['question'])}\n\n"
              "اكتب إجابتك في رسالة، وأصححها لك وأعطيك درجتك.",
        parse_mode=ParseMode.HTML, reply_markup=_essay_buttons(lid, i))


def _model_answer(q: dict) -> str:
    points = "\n".join(f"• {escape(p)}" for p in q.get("key_points", []))
    return (f"📖 <b>نموذج الإجابة</b>\n<tg-spoiler>{escape(q.get('model_answer', ''))}</tg-spoiler>"
            + (f"\n\n<b>النقاط الأساسية:</b>\n{points}" if points else ""))


async def on_essay_button(update: Update, context, arg: str) -> None:
    lid, _, rest = arg.partition(":")
    i, _, step = rest.partition(":")
    lec = store.get(update.effective_user.id, context.user_data, lid)
    if not lec or not i.isdigit():
        return
    i, chat = int(i), update.effective_chat.id
    if step == "show" and i < len(lec.get("essay", [])):
        await context.bot.send_message(chat, _model_answer(lec["essay"][i]), parse_mode=ParseMode.HTML,
                                       reply_markup=InlineKeyboardMarkup([[button("⏭ السؤال التالي",
                                                                                  f"es:{lid}:{i + 1}:go")]]))
    elif step == "go":
        try:
            await update.callback_query.edit_message_reply_markup(None)
        except BadRequest:
            pass
        await _send_essay(context, chat, lid, lec, i)


def _bar(score: int) -> str:
    return "▰" * score + "▱" * (10 - score)


async def input_essay_answer(update: Update, context, payload: str) -> None:
    lid, _, i = payload.partition(":")
    ud, msg = context.user_data, update.effective_message
    lec = store.get(update.effective_user.id, ud, lid)
    if not lec or not i.isdigit() or int(i) >= len(lec.get("essay", [])):
        return
    i = int(i)
    q = lec["essay"][i]
    graded = ud.setdefault("essays_graded", {})
    price = bot_wallet.ESSAY if graded.get(lid, 0) >= bot_wallet.ESSAY_FREE else 0
    if not await bot_wallet.require(context, msg.chat_id, ud, price, "تصحيح إجابة مقالية"):
        botkit.expect(ud, "essay_answer", payload)
        return
    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    try:
        g = await asyncio.to_thread(study.grade_essay, q, msg.text)
    except AnalysisError as e:
        log.warning("essay grading failed: %s", e)
        botkit.expect(ud, "essay_answer", payload)
        await msg.reply_text("⚠️ تعذّر تصحيح إجابتك الآن. أرسلها مرة أخرى بعد قليل.")
        return
    graded[lid] = graded.get(lid, 0) + 1
    bot_wallet.charge(context, ud, price, "تصحيح إجابة مقالية")
    stats = ud.setdefault("stats", {})
    stats["essays"] = stats.get("essays", 0) + 1
    stats["essay_points"] = stats.get("essay_points", 0) + g["score"]
    lines = [f"📝 <b>درجتك: {g['score']} من 10</b>\n{_bar(g['score'])}", ""]
    if g.get("good"):
        lines.append(f"✅ {escape(g['good'])}")
    if g.get("missing"):
        lines.append("\n<b>ما ينقص إجابتك:</b>")
        lines += [f"• {escape(m)}" for m in g["missing"]]
    if g.get("advice"):
        lines.append(f"\n💡 {escape(g['advice'])}")
    lines += ["", _model_answer(q)]
    await botkit.send_long(context, msg.chat_id, "\n".join(lines), parse_mode=ParseMode.HTML,
                           reply_markup=InlineKeyboardMarkup([[button("✍️ أعد المحاولة", f"es:{lid}:{i}:go"),
                                                               button("⏭ السؤال التالي", f"es:{lid}:{i + 1}:go")]]))


# ---------- the course quiz: questions from every lecture of a course ----------

COURSE_QUIZ_SIZE = 20


def _weight(stats: dict, lid: str) -> float:
    """Lectures the student answers badly come up more often (up to three times)."""
    c, t = stats.get("by_lecture", {}).get(lid, (0, 0))
    return 1.0 + (2.0 * (1 - c / t) if t >= 2 else 1.0)


async def on_course_quiz(update: Update, context, arg: str) -> None:
    cid, _, kind = arg.partition(":")
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    course = library.courses(ud).get(cid)
    if not course:
        return
    lectures = _course_lectures(context, uid, cid)
    if not kind:
        n_mcq = sum(len(lec.get("mcq", [])) for _, lec in lectures)
        n_tf = sum(len(lec.get("true_false", [])) for _, lec in lectures)
        if not n_mcq + n_tf:
            await context.bot.send_message(chat, "لا توجد أسئلة في محاضرات هذه المادة بعد.")
            return
        rows = [[button("🎲 اختيار من متعدد وصح أو خطأ", f"cq:{cid}:all")]]
        if n_mcq:
            rows.append([button("🔘 اختيار من متعدد فقط", f"cq:{cid}:mcq")])
        if n_tf:
            rows.append([button("✅❌ صح أو خطأ فقط", f"cq:{cid}:tf")])
        await context.bot.send_message(
            chat, f"🧪 <b>اختبار شامل: {escape(course['name'])}</b>\n{_questions(COURSE_QUIZ_SIZE)} من "
                  f"{botkit.count(len(lectures), 'محاضرة واحدة', 'محاضرتين', 'محاضرات', 'محاضرة')}، "
                  "وتتكرر أكثر أسئلة المحاضرات التي تحتاج مراجعة.",
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))
        return
    for i, (lid, question, options, correct, explanation, k, j) in enumerate(_pick(ud, lectures, kind), 1):
        await botkit.send_quiz(context, chat, f"{i}. {question}", options, correct, explanation, "",
                               {"kind": "lecture", "uid": uid, "lid": lid},
                               buttons=[botkit.evidence_button(lid, k, j)])


def _pick(ud: dict, lectures: list, kind: str, size: int = COURSE_QUIZ_SIZE) -> list:
    """Questions from a course's lectures; weak lectures come up more often, no question twice."""
    stats = ud.get("stats", {})
    pool = []
    for lid, lec in lectures:
        w = _weight(stats, lid)
        if kind in ("mcq", "all"):
            pool += [(w, lid, q["question"], q["options"], q["answer_index"], q.get("explanation", ""), "m", j)
                     for j, q in enumerate(lec.get("mcq", []))]
        if kind in ("tf", "all"):
            pool += [(w, lid, _tf(t), ["صح", "خطأ"], 0 if t["answer"] else 1, t.get("explanation", ""), "t", j)
                     for j, t in enumerate(lec.get("true_false", []))]
    # Weighted sampling without replacement: a higher weight makes a question likelier to be picked.
    pool.sort(key=lambda item: -(random.random() ** (1 / item[0])))
    seen, picked = set(), []
    for item in pool:
        if item[2] not in seen:  # the same question can come from a lecture shared twice
            seen.add(item[2])
            picked.append(item[1:])
    return picked[:size]


# ---------- exam simulation: one question at a time, against the clock ----------

SIM_SIZE = 20
SIM_SECONDS = {"m": 60, "t": 30}


def _course_lectures(context, uid: int, cid: str) -> list:
    ud = context.user_data
    lectures = [(lid, store.get(uid, ud, lid)) for lid in library.course_lectures(ud, cid)]
    return [(lid, lec) for lid, lec in lectures if lec]


async def on_sim(update: Update, context, arg: str) -> None:
    cid, _, step = arg.partition(":")
    ud, uid, chat = context.user_data, update.effective_user.id, update.effective_chat.id
    course = library.courses(ud).get(cid)
    if not course:
        return
    if step == "stop":
        if ud.get("sim", {}).get("cid") == cid:
            await _sim_finish(context, chat, uid, stopped=True)
        return
    lectures = _course_lectures(context, uid, cid)
    if step != "go":
        n = len(_pick(ud, lectures, "all", SIM_SIZE))
        if not n:
            await context.bot.send_message(chat, "لا توجد أسئلة في محاضرات هذه المادة بعد.")
            return
        await context.bot.send_message(
            chat, f"⏱ <b>محاكاة اختبار: {escape(course['name'])}</b>\n\n"
                  f"{_questions(n)} من كل محاضرات المادة، سؤال بعد سؤال، كقاعة الاختبار:\n"
                  f"• دقيقة لسؤال الاختيار من متعدد، ونصف دقيقة لصح أو خطأ.\n"
                  "• إذا انتهى الوقت ينتقل السؤال التالي تلقائياً.\n"
                  "• في النهاية: درجتك، ونسبة جاهزيتك، والمحاضرات التي تحتاج مراجعة.\n\nجاهز؟",
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[button("▶️ ابدأ المحاكاة", f"sim:{cid}:go")]]))
        return
    items = _pick(ud, lectures, "all", SIM_SIZE)
    if not items:
        return
    random.shuffle(items)
    ud["sim"] = {"cid": cid, "items": items, "i": 0, "right": 0, "per": {}, "started": time.time(),
                 "token": uuid.uuid4().hex[:8]}
    await _sim_next(context, chat, uid)


async def _sim_next(context, chat: int, uid: int) -> None:
    sim = context.user_data.get("sim")
    if not sim:
        return
    for job in context.job_queue.get_jobs_by_name(f"sim:{uid}"):
        job.schedule_removal()
    if sim["i"] >= len(sim["items"]):
        await _sim_finish(context, chat, uid)
        return
    lid, question, options, correct, explanation, k, j = sim["items"][sim["i"]]
    seconds = SIM_SECONDS[k]
    await botkit.send_quiz(context, chat, f"{sim['i'] + 1}/{len(sim['items'])}. {question}", options, correct,
                           explanation, "", {"kind": "sim", "uid": uid, "lid": lid, "token": sim["token"], "i": sim["i"]},
                           buttons=[button("⏹ إنهاء المحاكاة", f"sim:{sim['cid']}:stop")], open_period=seconds)
    context.job_queue.run_once(_sim_timeout, seconds + 3, chat_id=chat, user_id=uid, name=f"sim:{uid}",
                               data={"token": sim["token"], "i": sim["i"]})


def _record(sim: dict, right: bool) -> None:
    lid = sim["items"][sim["i"]][0]
    c, t = sim["per"].get(lid, (0, 0))
    sim["per"][lid] = (c + int(right), t + 1)
    sim["right"] += int(right)
    sim["i"] += 1


async def _sim_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    sim = context.user_data.get("sim")
    data = context.job.data
    if sim and sim["token"] == data["token"] and sim["i"] == data["i"]:
        _record(sim, False)
        await _sim_next(context, context.job.chat_id, context.job.user_id)


async def sim_answer(context, info: dict, right: bool) -> None:
    sim = context.user_data.get("sim")
    if sim and sim["token"] == info.get("token") and sim["i"] == info.get("i"):
        _record(sim, right)
        await _sim_next(context, info["uid"], info["uid"])


def _readiness(pct: int) -> str:
    if pct >= 85:
        return "💪 جاهز للاختبار"
    if pct >= 70:
        return "👍 قريب من الجاهزية: راجع المحاضرات أدناه"
    return "📚 تحتاج مراجعة قبل الاختبار"


async def _sim_finish(context, chat: int, uid: int, stopped: bool = False) -> None:
    ud = context.user_data
    sim = ud.pop("sim", None)
    for job in context.job_queue.get_jobs_by_name(f"sim:{uid}"):
        job.schedule_removal()
    if not sim or not sim["i"]:
        await context.bot.send_message(chat, "⏹ أُنهيت المحاكاة.")
        return
    done, right = sim["i"], sim["right"]
    pct = round(100 * right / done)
    course = library.courses(ud).get(sim["cid"])
    if course is not None and not stopped:
        course["readiness"] = {"pct": pct, "date": study.today().isoformat()}
    lines = ["⏱ <b>نتيجة المحاكاة</b>" + (" (أُنهيت مبكراً)" if stopped else ""),
             f"✅ {right} من {done} · {pct}%\n{_bar(round(pct / 10))}",
             f"⌛ الوقت: {botkit.minutes(time.time() - sim['started'])}", "", f"<b>جاهزيتك: {pct}%</b> · {_readiness(pct)}"]
    weak = sorted(((c / t, lid) for lid, (c, t) in sim["per"].items() if t and c / t < 0.7))
    rows = []
    if weak:
        lines += ["", "<b>راجع هذه المحاضرات:</b>"]
        for frac, lid in weak[:5]:
            title = ud.get("lectures", {}).get(lid, {}).get("title") or "محاضرة"
            c, t = sim["per"][lid]
            lines.append(f"• {escape(title)}: {c} من {t}")
            rows.append([button(f"🧪 {title[:40]}", f"quiz:{lid}")])
    rows.append([button("🔁 محاكاة جديدة", f"sim:{sim['cid']}:go")])
    await context.bot.send_message(chat, "\n".join(lines), parse_mode=ParseMode.HTML,
                                   reply_markup=InlineKeyboardMarkup(rows))


def register(app) -> None:
    pass


botkit.LECTURE_BUTTONS.update({"quiz": on_quiz, "qz": on_kind})
botkit.BUTTONS.update({"es": on_essay_button, "cq": on_course_quiz, "sim": on_sim, "ev": on_evidence})
botkit.POLL_HOOKS.update({"sim": sim_answer})
botkit.TEXT_INPUTS.update({"essay_answer": input_essay_answer})
