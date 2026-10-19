"""Testing: one "test me" button with every kind of question, and essay answers graded by Claude."""
import asyncio
import random
from html import escape

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest

import botkit
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
        polls += [(q["question"], q["options"], q["answer_index"], q.get("explanation", ""), q.get("time", ""))
                  for q in lec.get("mcq", [])]
    if kind in ("tf", "all"):
        polls += [(f"صح أم خطأ؟ {t['statement']}", ["صح", "خطأ"], 0 if t["answer"] else 1, t.get("explanation", ""),
                   t.get("time", "")) for t in lec.get("true_false", [])]
    if kind == "all":
        random.shuffle(polls)
    for i, (question, options, correct, explanation, at) in enumerate(polls, 1):
        await botkit.send_quiz(context, chat, f"{i}. {question}", options, correct, explanation, at, track)
    if kind in ("essay", "all") and lec.get("essay"):
        await _send_essay(context, chat, lid, lec, 0)


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
    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    try:
        g = await asyncio.to_thread(study.grade_essay, q, msg.text)
    except AnalysisError as e:
        log.warning("essay grading failed: %s", e)
        botkit.expect(ud, "essay_answer", payload)
        await msg.reply_text("⚠️ تعذّر تصحيح إجابتك الآن. أرسلها مرة أخرى بعد قليل.")
        return
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
    lectures = [(lid, store.get(uid, ud, lid)) for lid in library.course_lectures(ud, cid)]
    lectures = [(lid, lec) for lid, lec in lectures if lec]
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
    stats = ud.get("stats", {})
    pool = []
    for lid, lec in lectures:
        w = _weight(stats, lid)
        if kind in ("mcq", "all"):
            pool += [(w, lid, q["question"], q["options"], q["answer_index"], q.get("explanation", ""))
                     for q in lec.get("mcq", [])]
        if kind in ("tf", "all"):
            pool += [(w, lid, f"صح أم خطأ؟ {t['statement']}", ["صح", "خطأ"], 0 if t["answer"] else 1,
                      t.get("explanation", "")) for t in lec.get("true_false", [])]
    # Weighted sampling without replacement: a higher weight makes a question likelier to be picked.
    pool.sort(key=lambda item: -(random.random() ** (1 / item[0])))
    seen, picked = set(), []
    for item in pool:
        if item[2] not in seen:  # the same question can come from a lecture shared twice
            seen.add(item[2])
            picked.append(item)
    for i, (_, lid, question, options, correct, explanation) in enumerate(picked[:COURSE_QUIZ_SIZE], 1):
        await botkit.send_quiz(context, chat, f"{i}. {question}", options, correct, explanation, "",
                               {"kind": "lecture", "uid": uid, "lid": lid})


def register(app) -> None:
    pass


botkit.LECTURE_BUTTONS.update({"quiz": on_quiz, "qz": on_kind})
botkit.BUTTONS.update({"es": on_essay_button, "cq": on_course_quiz})
botkit.TEXT_INPUTS.update({"essay_answer": input_essay_answer})
