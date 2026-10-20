"""Statistics, the free hour for new students, and the owner's tools."""
import asyncio
import datetime as dt
import time
from html import escape

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes

import botkit
import bot_wallet
from botkit import button, log
from lecturebot import analyze, config, library, media, pipeline, study


def _questions(n: int) -> str:
    return botkit.count(n, "سؤال واحد", "سؤالان", "أسئلة", "سؤالاً")


def _friends(n: int) -> str:
    return botkit.count(n, "صديق واحد", "صديقين", "أصدقاء", "صديقاً")


def _stats(ud: dict) -> dict:
    return ud.setdefault("stats", {"lectures": 0, "seconds": 0, "answered": 0, "correct": 0, "by_lecture": {},
                                   "review_days": []})


# ---------- the free hour ----------

def welcome_credits(ud: dict) -> None:
    bot_wallet.welcome(ud)


def lecture_done(ud: dict, full: dict) -> None:
    s = _stats(ud)
    s["lectures"] += 1
    s["seconds"] += int(full.get("duration") or 0)


def reviewed(ud: dict) -> None:
    days = _stats(ud)["review_days"]
    t = study.today().isoformat()
    if t not in days:
        days.append(t)
        del days[:-60]


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
    if info["kind"] in ("lecture", "sim"):
        s = _stats(context.user_data)
        s["answered"] += 1
        s["correct"] += int(right)
        c, t = s["by_lecture"].get(info["lid"], (0, 0))
        s["by_lecture"][info["lid"]] = (c + int(right), t + 1)
    hook = botkit.POLL_HOOKS.get(info["kind"])
    if hook:
        await hook(context, info, right)


def prune_polls(context) -> None:
    polls = context.bot_data.get("polls", {})
    old = time.time() - 30 * 86400
    for pid in [p for p, v in polls.items() if v.get("ts", 0) < old]:
        del polls[pid]


async def _prune_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    prune_polls(context)


# ---------- owner tools: claiming the bot, comparing models ----------

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = (context.args or [""])[0]
    if not config.OWNER_CODE or code != config.OWNER_CODE:
        await update.effective_message.reply_text("الرمز غير صحيح.")
        return
    context.bot_data["owner"] = update.effective_user.id
    await update.effective_message.reply_text("👑 أنت مالك البوت الآن. لديك أمر /compare لمقارنة نماذج Claude.")


async def tell_owner(context, text: str) -> None:
    """Technical problems go to the owner (the student only sees a short message)."""
    owner = context.bot_data.get("owner")
    if owner:
        try:
            await context.bot.send_message(owner, text[:4000], disable_web_page_preview=True)
        except TelegramError:
            pass


async def cookies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cookies: the owner sends a YouTube account's cookies.txt, for servers YouTube asks to sign in."""
    if not botkit.is_owner(context, update.effective_user.id):
        return
    path = media.youtube_cookies()
    if context.args and context.args[0] == "off":
        path.unlink(missing_ok=True)
        await update.effective_message.reply_text("🍪 حُذف ملف الكوكيز.")
        return
    botkit.expect(context.user_data, "cookies")
    state = "موجود ✅" if path.exists() else "غير موجود"
    await update.effective_message.reply_text(
        f"🍪 ملف كوكيز يوتيوب: {state}\nأرسل الآن ملف cookies.txt (من حساب يوتيوب مخصص للبوت، لا حسابك الشخصي).\n"
        "/cookies off لحذفه.")


async def on_cookies_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Called for a document while the owner is expected to send cookies.txt; True if handled."""
    pending = context.user_data.get("await") or {}
    doc = update.effective_message.document
    if pending.get("kind") != "cookies" or not doc or not botkit.is_owner(context, update.effective_user.id):
        return False
    context.user_data.pop("await", None)
    f = await context.bot.get_file(doc.file_id)
    data = bytes(await f.download_as_bytearray())
    cookies, problem = media.parse_cookies(data)
    if not cookies:
        why = {"empty": "الملف لا يحوي أي كوكيز. غالباً الإضافة غير مسموح لها في النوافذ الخاصة: ⋮ ← الامتدادات ← "
                        "cookies.txt ← فعّل «السماح في النوافذ الخاصة»، ثم صدّر الملف من جديد.",
               "other_site": "الملف لموقع آخر غير يوتيوب. صدّره وأنت في صفحة youtube.com نفسها.",
               "signed_out": "الملف من يوتيوب لكن بلا تسجيل دخول. ادخل بالحساب في النافذة نفسها ثم صدّره."}[problem]
        await update.effective_message.reply_text(f"⚠️ {why}\nثم أرسل /cookies والملف مرة أخرى.")
        return True
    path = media.youtube_cookies()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cookies)
    path.chmod(0o600)
    try:
        await update.effective_message.delete()  # the cookies are a login: do not leave them in the chat
    except TelegramError:
        pass
    await context.bot.send_message(update.effective_chat.id, "✅ حُفظ ملف الكوكيز، وحذفت رسالته من المحادثة. "
                                                             "جرّب رابط يوتيوب الآن.")
    return True


async def compare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not botkit.is_owner(context, update.effective_user.id):
        return
    context.user_data["compare_next"] = True
    await update.effective_message.reply_text(
        "🔬 أرسل الآن تسجيل محاضرة (مع شرائحها إن أردت). سأحوّلها إلى نص مرة واحدة، ثم أكتب ملخصها وأسئلتها "
        "مرتين: بـ Opus كاملاً، وبالطريقة المختلطة (Opus للملخص، وSonnet للأسئلة ثم يراجعها Opus)، "
        "وأرسل لك الملفين مع تكلفة كل واحد لتقارن.\n"
        "💡 محاضرة من 20 إلى 30 دقيقة تكفي للمقارنة وتوفّر التكلفة.")


# (label, notes model, questions model): everything by Opus, or the mixed setup the bot uses.
COMPARE_MODELS = (("Opus", "claude-opus-5-5", "claude-opus-5-5"),
                  ("مختلط", "claude-opus-5-5", "claude-sonnet-5-5"))
GROQ_DOLLARS_PER_HOUR = 0.111


async def run_compare(context, chat_id: int, status, sources, work, major, images, mats) -> None:
    """Transcribe once, write the notes and questions with each model, send both PDFs with their costs."""
    await status.edit_text("🔬 مقارنة: أحوّل الكلام إلى نص…")
    segments, duration, parts = await asyncio.to_thread(pipeline.transcribe_sources, sources, major, mats)
    await status.edit_text("🔬 مقارنة: يكتب النموذجان الملخص والأسئلة في الوقت نفسه… (دقائق)")

    async def one(label, model, questions_model):
        started = time.time()
        result = await asyncio.to_thread(analyze.analyze, segments, major=major, images=images, duration=duration,
                                         materials=mats, parts=parts, model=model, questions_model=questions_model)
        res = await asyncio.to_thread(pipeline.finish, result, segments, work, sources[0], duration, f"-{label}")
        return label, res, time.time() - started

    outcomes = await asyncio.gather(*(one(*m) for m in COMPARE_MODELS), return_exceptions=True)
    await status.delete()
    hours = max(duration / 3600, 0.01)
    lines = [f"🔬 <b>نتيجة المقارنة</b> · محاضرة {botkit.minutes(duration)}", ""]
    for outcome in outcomes:
        if isinstance(outcome, Exception):
            log.warning("compare model failed: %s", outcome)
            lines.append(f"⚠️ فشل أحد النموذجين: {escape(str(outcome))[:200]}")
            continue
        label, res, seconds = outcome
        a, u = res.analysis, res.analysis.get("_usage", {})
        dropped = f" · حذفت المراجعة {a['_dropped_by_review']} سؤالاً" if a.get("_dropped_by_review") else ""
        counts = (f"{len(a.get('sections', []))} قسماً · {len(a.get('mcq', []))} اختيار · {len(a.get('true_false', []))} "
                  f"صح/خطأ · {len(a.get('essay', []))} مقالي · {len(a.get('flashcards', []))} بطاقة · "
                  f"{len(a.get('divisions', []))} تقسيم{dropped}")
        await botkit.send_files(context, chat_id, res.extra["files"],
                                f"🔬 {label}: ${u.get('cost', 0):.2f} لهذه المحاضرة\n{counts}")
        per_hour = u.get("cost", 0) / hours + GROQ_DOLLARS_PER_HOUR
        lines.append(f"<b>{label}</b>: ${u.get('cost', 0):.2f} (Claude) · وقت الكتابة {botkit.minutes(seconds)}\n"
                     f"   تكلفة ساعة المحاضرة كاملة تقريباً: <b>${per_hour:.2f}</b> (مع تحويل الصوت)\n"
                     f"   {u.get('input', 0):,} رمز داخل · {u.get('output', 0):,} رمز خارج")
    lines += ["", "قارن الملفين: دقة الملخص، ووضوح الأسئلة، وصحة المصطلحات. ثم أخبرني أيهما نعتمد."]
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.HTML)


def register(app) -> None:
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("compare", compare_cmd))
    app.add_handler(CommandHandler("cookies", cookies_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.job_queue.run_repeating(_prune_job, interval=86400, first=3600)


