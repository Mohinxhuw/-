"""The student's wallet, in Telegram Stars (Telegram requires Stars for digital services in bots).

A student tops up once (with a bonus on bigger packs) and the bot deducts small amounts as they use it,
with no payment window each time. Charging is off until the owner turns it on with /billing on;
until then everything is free and only the free minutes and referral rewards are counted.
"""
import math
import time
from html import escape

from telegram import InlineKeyboardMarkup, LabeledPrice, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, PreCheckoutQueryHandler, filters

import botkit
from botkit import button, log
from lecturebot import config

# Prices in Stars (a student pays about 2 US cents per Star; about 1.3 cents reaches the owner).
UPLOAD_PER_MINUTE = 1.5     # processing a new recording
RECEIVE = 5                 # a lecture from a classmate, or a recording processed before
FILES = 60                  # a lecture made of slides / book pages only
EXPLAIN = 10                # "explain it more simply", per part
ESSAY = 5                   # grading an essay answer, after ESSAY_FREE free ones per lecture
ESSAY_FREE = 2
ENGLISH = 30                # the English PDF
EXAM = 50                   # the exam-night summary
CASHBACK = 1                # to the student whose lecture a classmate receives
FREE_MINUTES = 60           # every new student's first hour of recordings
FREE_RECEIVES = 3           # and their first lectures from classmates
PACKS = [(100, 0), (250, 25), (500, 75), (1000, 200)]  # (Stars paid, bonus Stars)


def enabled(context) -> bool:
    return context.bot_data.get("billing", config.BILLING_ENABLED)


def balance(ud: dict) -> int:
    return int(ud.get("stars", 0))


def welcome(ud: dict) -> None:
    """Every new student starts with an hour of free recordings."""
    if "free_minutes" not in ud:
        ud["free_minutes"] = FREE_MINUTES
        ud["free_receives"] = FREE_RECEIVES


def _log(ud: dict, delta: int, reason: str) -> None:
    ud.setdefault("ledger", []).append({"t": time.time(), "d": delta, "r": reason})
    del ud["ledger"][:-50]


def credit(ud: dict, stars: int, reason: str) -> None:
    ud["stars"] = balance(ud) + stars
    _log(ud, stars, reason)


def charge(context, ud: dict, stars: int, reason: str) -> None:
    if enabled(context) and stars > 0:
        ud["stars"] = balance(ud) - stars
        _log(ud, -stars, reason)


def upload_cost(ud: dict, seconds: float) -> tuple[int, int]:
    """(Stars, free minutes used) for processing a recording of this length."""
    minutes = max(1, math.ceil(seconds / 60))
    free = min(int(ud.get("free_minutes", 0)), minutes)
    return math.ceil((minutes - free) * UPLOAD_PER_MINUTE), free


def charge_upload(context, ud: dict, seconds: float) -> None:
    stars, free = upload_cost(ud, seconds)
    if enabled(context):
        ud["free_minutes"] = int(ud.get("free_minutes", 0)) - free
    charge(context, ud, stars, f"محاضرة {max(1, math.ceil(seconds / 60))} دقيقة")


def _packs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[button(f"⭐ {stars}" + (f" + {bonus} هدية" if bonus else ""), f"wal:buy:{stars}")]
                                 for stars, bonus in PACKS])


async def require(context, chat_id: int, ud: dict, stars: int, what: str) -> bool:
    """True when the student can pay `stars` (or charging is off); otherwise offers a top-up."""
    if not enabled(context) or stars <= 0 or balance(ud) >= stars:
        return True
    await context.bot.send_message(
        chat_id, f"👛 {escape(what)}: ⭐ {stars}\nرصيدك: ⭐ {balance(ud)}\n\nاشحن رصيدك مرة واحدة، "
                 "وأخصم منه تلقائياً مع كل استخدام:", parse_mode=ParseMode.HTML, reply_markup=_packs_keyboard())
    return False


async def can_start(context, chat_id: int, ud: dict) -> bool:
    """Before downloading a recording: is there anything to pay with at all?"""
    welcome(ud)
    if not enabled(context) or balance(ud) > 0 or ud.get("free_minutes", 0) > 0:
        return True
    return await require(context, chat_id, ud, 1, "معالجة محاضرة جديدة")


# ---------- the wallet ----------

def price_list() -> str:
    return (f"• محاضرة جديدة: ⭐ {UPLOAD_PER_MINUTE:g} للدقيقة (⭐ {math.ceil(60 * UPLOAD_PER_MINUTE)} للساعة)\n"
            f"• محاضرة من زميل: ⭐ {RECEIVE}\n"
            f"• ملخص من الشرائح أو الكتاب: ⭐ {FILES}\n"
            f"• اشرح لي أبسط: ⭐ {EXPLAIN}\n"
            f"• تصحيح سؤال مقالي: أول {ESSAY_FREE} لكل محاضرة مجاناً، ثم ⭐ {ESSAY}\n"
            f"• النسخة الإنجليزية: ⭐ {ENGLISH}\n"
            f"• ملخص ليلة الاختبار: ⭐ {EXAM}\n"
            "• المكتبة والاختبارات والبطاقات والمراجعة والخطة: مجاناً دائماً")


async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = context.user_data
    welcome(ud)
    lines = [f"👛 <b>محفظتك</b>: ⭐ {balance(ud)}"]
    if ud.get("free_minutes", 0) > 0:
        lines.append(f"🎁 دقائق مجانية: {ud['free_minutes']}")
    if ud.get("free_receives", 0) > 0:
        lines.append(f"🎁 محاضرات مجانية من زملائك: {ud['free_receives']}")
    if not enabled(context):
        lines.append("\n(فَهيم مجاني حالياً، ولا يُخصم شيء من رصيدك.)")
    lines += ["", "<b>الأسعار</b>", price_list(), "",
              f"🎁 كل زميل يستلم محاضرة شاركتها معه يضيف ⭐ {CASHBACK} لرصيدك.", "", "<b>اشحن رصيدك</b>:"]
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=_packs_keyboard())


async def on_wallet_button(update: Update, context, arg: str) -> None:
    step, _, value = arg.partition(":")
    if step != "buy" or not value.isdigit():
        return
    stars = int(value)
    bonus = dict(PACKS).get(stars)
    if bonus is None:
        return
    await context.bot.send_invoice(
        update.effective_chat.id, title=f"رصيد فَهيم: ⭐ {stars + bonus}",
        description=f"شحن محفظة فَهيم بـ {stars} نجمة" + (f" ومعها {bonus} نجمة هدية" if bonus else "")
                    + ". يُخصم منها مع كل استخدام.",
        payload=f"pack:{stars}", currency="XTR", prices=[LabeledPrice("رصيد فَهيم", stars)])


async def on_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.pre_checkout_query
    stars = q.invoice_payload.partition(":")[2]
    ok = q.invoice_payload.startswith("pack:") and stars.isdigit() and int(stars) in dict(PACKS)
    await q.answer(ok=ok, error_message=None if ok else "هذه الباقة لم تعد متاحة.")


async def on_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pay = update.effective_message.successful_payment
    stars = int(pay.invoice_payload.partition(":")[2])
    bonus = dict(PACKS).get(stars, 0)
    ud = context.user_data
    credit(ud, stars + bonus, "شحن")
    ud.setdefault("payments", []).append({"t": time.time(), "stars": stars, "charge": pay.telegram_payment_charge_id})
    rows = []
    if ud.get("parts"):
        rows.append([button("▶️ أكمل معالجة محاضرتك", "go:")])
    elif ud.get("pending_images") or ud.get("pending_docs"):
        rows.append([button("📄 أكمل تلخيص الملفات", "files:")])
    rows += [[button("🔓 افتح: " + item["name"][:40], f"unl:{token}")] for token, item in ud.get("locked", {}).items()]
    await update.effective_message.reply_text(f"✅ شُحن رصيدك: ⭐ {stars + bonus}. رصيدك الآن ⭐ {balance(ud)}. شكراً لك!",
                                              reply_markup=InlineKeyboardMarkup(rows[:10]) if rows else None)


async def paysupport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram asks every bot that takes payments to answer /paysupport."""
    await update.effective_message.reply_text(
        "💬 <b>الدعم والدفع</b>\nإن واجهتك مشكلة في الشحن أو خُصم منك رصيد بالخطأ، اكتب رسالتك هنا بعد الأمر، "
        "مثل:\n/paysupport خُصم رصيدي ولم تصلني المحاضرة\nويصل طلبك للإدارة وتُرد مستحقاتك.",
        parse_mode=ParseMode.HTML)
    owner = context.bot_data.get("owner")
    if context.args and owner:
        ud = context.user_data
        recent = "، ".join(f"{p['stars']}⭐" for p in ud.get("payments", [])[-3:]) or "لا يوجد"
        try:
            await context.bot.send_message(owner, f"💬 طلب دعم من {update.effective_user.full_name} "
                                                  f"(<code>{update.effective_user.id}</code>):\n{escape(' '.join(context.args))}\n"
                                                  f"الرصيد: ⭐ {balance(ud)} · آخر الشحنات: {recent}",
                                           parse_mode=ParseMode.HTML)
        except TelegramError:
            pass


# ---------- owner: turning charging on and off, refunds ----------

async def billing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not botkit.is_owner(context, update.effective_user.id):
        return
    arg = (context.args or [""])[0]
    if arg in ("on", "off"):
        context.bot_data["billing"] = arg == "on"
    state = "مفعّل ✅" if enabled(context) else "متوقف (كل شيء مجاني)"
    await update.effective_message.reply_text(f"💳 الدفع: {state}\n/billing on لتفعيله · /billing off لإيقافه")


async def refund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/refund <user id>: refund that student's last Stars payment."""
    if not botkit.is_owner(context, update.effective_user.id) or not context.args or not context.args[0].isdigit():
        return
    uid = int(context.args[0])
    ud = context.application.user_data.get(uid, {})
    payments = ud.get("payments", [])
    if not payments:
        await update.effective_message.reply_text("لا توجد مدفوعات لهذا المستخدم.")
        return
    p = payments[-1]
    try:
        await context.bot.refund_star_payment(uid, p["charge"])
    except TelegramError as e:
        await update.effective_message.reply_text(f"تعذّر الاسترداد: {e}")
        return
    payments.pop()
    ud["stars"] = balance(ud) - p["stars"] - dict(PACKS).get(p["stars"], 0)
    _log(ud, -p["stars"], "استرداد")
    context.application.mark_data_for_update_persistence(user_ids=[uid])
    await update.effective_message.reply_text(f"↩️ استُرد ⭐ {p['stars']} للمستخدم {uid}.")
    log.info("refunded %s stars to %s", p["stars"], uid)


def register(app) -> None:
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("paysupport", paysupport_cmd))
    app.add_handler(CommandHandler("billing", billing_cmd))
    app.add_handler(CommandHandler("refund", refund_cmd))
    app.add_handler(PreCheckoutQueryHandler(on_precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_paid))


botkit.BUTTONS.update({"wal": on_wallet_button})
