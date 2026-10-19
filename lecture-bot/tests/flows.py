"""End-to-end check of the bot's conversations against a simulated Telegram server.

Claude, text-to-speech and transcription are replaced by stubs, so this needs no keys or network:
    python tests/flows.py
It prints every message the bot sends and fails loudly if a step raises or a check does not hold.
"""
import asyncio
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp(prefix="flows_"))
os.environ.update(TELEGRAM_BOT_TOKEN="123:abc", DATA_DIR=str(TMP / "data"), WORK_DIR=str(TMP / "work"),
                  PARTS_WAIT_SECONDS="1", OWNER_CODE="424242")

from telegram import Update  # noqa: E402
from telegram.ext import Application  # noqa: E402
from telegram.request import BaseRequest  # noqa: E402

import bot  # noqa: E402
from lecturebot import analyze, pipeline, study  # noqa: E402
from lecturebot.pipeline import LectureResult  # noqa: E402

def _sample_pdf() -> bytes:
    from weasyprint import HTML
    return HTML(string="<p>Mitochondria الخلية وحدة بناء الكائن الحي</p>").write_pdf()


SAMPLE_PDF = _sample_pdf()
SENT: list[tuple[int, str, dict]] = []
POLLS: list[str] = []
_mid = [100]


class FakeTelegram(BaseRequest):
    async def initialize(self): pass
    async def shutdown(self): pass

    @property
    def read_timeout(self):
        return 5

    async def do_request(self, url, method, request_data=None, **kw):
        name = url.rsplit("/", 1)[-1]
        if "/file/bot" in url:  # every download is a small real PDF (fine for audio too: the pipeline is stubbed)
            return 200, SAMPLE_PDF
        params = request_data.parameters if request_data else {}
        chat = int(params.get("chat_id", 0) or 0)
        keep = {k: str(v)[:2000] for k, v in params.items() if k in ("text", "caption", "question")}
        if "reply_markup" in params:
            keep["buttons"] = [b["callback_data"] for row in params["reply_markup"].get("inline_keyboard", [])
                               for b in row if "callback_data" in b]
        SENT.append((chat, name, keep))
        _mid[0] += 1
        msg = {"message_id": _mid[0], "date": 0, "chat": {"id": chat, "type": "private"}, "text": "x"}
        if name == "getMe":
            r = {"id": 1, "is_bot": True, "first_name": "Faheem", "username": "FaheemSyBot"}
        elif name == "sendDocument":
            r = dict(msg, document={"file_id": f"doc{_mid[0]}", "file_unique_id": "u"})
        elif name == "sendAudio":
            r = dict(msg, audio={"file_id": f"aud{_mid[0]}", "file_unique_id": "u", "duration": 60})
        elif name == "sendPoll":
            pid = f"poll{_mid[0]}"
            POLLS.append(pid)
            r = dict(msg, poll={"id": pid, "question": "q", "options": [], "total_voter_count": 0, "is_closed": False,
                                "is_anonymous": False, "type": "quiz", "allows_multiple_answers": False,
                                "allows_revoting": False, "members_only": False})
        elif name in ("sendMessage", "editMessageText", "sendInvoice"):
            r = msg
        elif name == "getFile":
            r = {"file_id": "f", "file_unique_id": "u", "file_path": "voice/f.ogg"}
        else:
            r = True
        return 200, json.dumps({"ok": True, "result": r}).encode()


ANALYSIS = {
    "title": "التنفس الخلوي", "subject": "أحياء", "overview": "نبذة",
    "sections": [{"heading": "التحلل السكري", "time": "00:05", "points": [{"text": "في Cytoplasm", "time": "00:06"}]}],
    "glossary": [{"term": "ATP", "arabic": "أدينوسين", "explanation": "طاقة"}],
    "mcq": [{"question": "أين يحدث كربس؟", "options": ["النواة", "الميتوكوندريا"], "answer_index": 1,
             "explanation": "", "time": "01:00"}],
    "true_false": [{"statement": "التحلل في النواة", "answer": False, "explanation": "", "time": "00:30",
                    "evidence": "التحلل السكري"}],
    "essay": [{"question": "اشرح مراحل التنفس الخلوي", "model_answer": "التحلل ثم كربس ثم نقل الإلكترونات.",
               "key_points": ["التحلل", "كربس", "نقل الإلكترونات"], "time": "00:05", "evidence": ""}],
    "flashcards": [{"front": "ناتج التحلل؟", "back": "2 ATP"}], "comparisons": [],
    "divisions": [{"title": "مراحل التنفس", "center": "التنفس الخلوي", "time": "00:05",
                   "branches": [{"label": "التحلل", "children": []}, {"label": "كربس", "children": []}]}],
}


RUNS = []


LANGS = []


def fake_run(sources, work, *a, lang="ar", **kw):
    RUNS.append(len(sources))
    LANGS.append(lang)
    pdf = work / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    r = LectureResult(dict(ANALYSIS), [], pdf, "[00:00] نتحدث اليوم عن الميتوكوندريا\n\n[00:30] التحلل السكري", sources[0])
    r.extra["duration"] = 3600
    return r


pipeline.run = fake_run


def fake_run_files(work, title, *a, **kw):
    RUNS.append("files")
    pdf = work / "f.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    from lecturebot.media import Source
    return LectureResult(dict(ANALYSIS, title="فصل الخلية"), [], pdf, "الخلية وحدة بناء الكائن الحي",
                         Source(path=Path("f"), title=title))


pipeline.run_files = fake_run_files
DURATION = [3600.0]
pipeline.probe_duration = lambda path: DURATION[0]
pipeline.transcribe_sources = lambda sources, major, mats, stage=None, lang="ar": ([], 1200.0, [(0, "")])
analyze.analyze = lambda segs, **kw: dict(ANALYSIS, _usage={"cost": 0.3 if "opus" in kw["model"] else 0.15,
                                                            "input": 1000, "output": 500})
study.ask = lambda lec, q, h=None: f"جواب: {q}"
study.grade_essay = lambda q, a: {"score": 7, "good": "ذكرت مرحلتين", "missing": ["نقل الإلكترونات"], "advice": "اذكر الثالثة"}
study.translate = lambda lec: dict(ANALYSIS, title="Cellular respiration")
study.exam_summary = lambda lecs: {"title": "ملخص", "overview": "", "topics": [], "must_memorize": [], "pitfalls": [],
                                   "self_test": []}

A, B, T, C = 7, 8, 9, 10  # three students and a teacher


def user(uid):
    return {"id": uid, "is_bot": False, "first_name": {A: "سارة", B: "خالد", T: "د. أحمد", C: "نورة"}[uid]}


_uid = [0]


def msg(uid, **kw):
    _uid[0] += 1
    m = {"message_id": _uid[0], "date": int(dt.datetime.now().timestamp()), "chat": {"id": uid, "type": "private"},
         "from": user(uid)}
    m.update(kw)
    return {"update_id": _uid[0], "message": m}


def cmd(uid, text):
    word = text.split()[0]
    return msg(uid, text=text, entities=[{"type": "bot_command", "offset": 0, "length": len(word)}])


def press(uid, data):
    _uid[0] += 1
    return {"update_id": _uid[0], "callback_query": {
        "id": str(_uid[0]), "from": user(uid), "chat_instance": "x", "data": data,
        "message": {"message_id": 5, "date": 0, "chat": {"id": uid, "type": "private"}, "text": "x"}}}


def answer(uid, poll_id, option):
    _uid[0] += 1
    return {"update_id": _uid[0], "poll_answer": {"poll_id": poll_id, "user": user(uid), "option_ids": [option],
                                            "option_persistent_ids": [str(option)]}}


def last(uid, contains=""):
    for chat, name, p in reversed(SENT):
        if chat == uid and contains in (p.get("text", "") + p.get("caption", "") + p.get("question", "")):
            return p
    raise AssertionError(f"no message to {uid} containing {contains!r}")


def find_button(uid, prefix):
    for chat, name, p in reversed(SENT):
        for b in p.get("buttons", []) if chat == uid else []:
            if b.startswith(prefix):
                return b
    raise AssertionError(f"no button {prefix!r} for {uid}")


async def main():
    app = Application.builder().token("123:abc").request(FakeTelegram()).get_updates_request(FakeTelegram()).build()
    bot.setup(app)
    async with app:
        await app.start()
        send = lambda u: app.process_update(Update.de_json(u, app.bot))  # noqa: E731

        # student A: a lecture, filed into a course
        await send(cmd(A, "/start"))
        await send(msg(A, voice={"file_id": "v1", "file_unique_id": "a", "duration": 5}))
        await send(press(A, "go:"))
        await asyncio.sleep(0.5)
        ud = app.user_data[A]
        lid = next(iter(ud["lectures"]))
        assert ud["lectures"][lid]["pdf_file_id"].startswith("doc"), "PDF file id saved"
        assert (TMP / "data" / "lectures" / str(A) / f"{lid}.json").exists(), "lecture saved on disk"
        cid = ud["lectures"][lid]["course"]
        assert ud["courses"][cid]["name"] == "أحياء"
        last(A, "حُفظت في مادة")

        # library, search, exam date, plan
        await send(cmd(A, "/library"))
        await send(press(A, f"lib:c:{cid}"))
        await send(press(A, f"lib:l:{lid}"))
        await send(cmd(A, "/search الميتوكوندريا"))
        assert "الميتوكوندريا" in last(A, "نتائج")["text"]
        await send(press(A, f"lib:date:{cid}"))
        await send(msg(A, text="بعد 5 أيام"))
        assert ud["courses"][cid]["exam"], "exam date set"
        last(A, "خطة مذاكرة")
        text, rows = bot.bot_library.reminder_text(ud, study.today())
        assert "خطة اليوم" in text and "باقي 5 أيام" in text, text
        await send(press(A, f"plan:done:{cid}:0"))
        assert ud["courses"][cid]["plan"][0]["done"]
        await send(press(A, f"mv:{lid}"))
        await send(press(A, f"mvnew:{lid}"))
        await send(msg(A, text="فسيولوجي"))
        assert ud["courses"][ud["lectures"][lid]["course"]]["name"] == "فسيولوجي"

        # buttons under the PDF: divisions only when the lecture has them
        kb = [b for chat, name, p in SENT if chat == A and name == "sendDocument" for b in p.get("buttons", [])]
        assert f"div:{lid}" in kb and not any(b.startswith(("audio:", "ask:", "tf:", "map:")) for b in kb), kb
        for action in ("div", "en", "en", "docx", "md", "more", "simp"):
            await send(press(A, f"{action}:{lid}"))
        assert ud["lectures"][lid]["en_file_id"].startswith("doc"), "English cached"

        # test me: the menu, each kind, and an essay graded
        await send(press(A, f"quiz:{lid}"))
        assert last(A, "اختر نوع الأسئلة")["buttons"] == [f"qz:{lid}:mcq", f"qz:{lid}:tf", f"qz:{lid}:essay", f"qz:{lid}:all"]
        POLLS.clear()
        await send(press(A, f"qz:{lid}:tf"))
        assert len(POLLS) == 1
        await send(press(A, f"qz:{lid}:essay"))
        last(A, "سؤال مقالي 1 من 1")
        await send(msg(A, text="التحلل السكري ثم دورة كربس"))
        assert "درجتك: 7 من 10" in last(A, "درجتك")["text"]
        await send(press(A, f"es:{lid}:0:show"))
        await send(press(A, f"es:{lid}:1:go"))
        last(A, "انتهت الأسئلة المقالية")

        # share link: B opens it and gets a copy
        await send(press(A, f"share:{lid}"))
        token = last(A, "?start=s_")["text"].split("start=s_")[1].split()[0]
        await send(cmd(B, f"/start s_{token}"))
        assert len(app.user_data[B]["lectures"]) == 1, "B got the lecture"
        assert app.user_data[A]["refs"] == [B], "referral counted"
        last(B, "شاركك سارة")

        # groups: A creates, B joins, A sends a lecture to the group
        await send(cmd(A, "/groups"))
        await send(press(A, "grp:new:"))
        await send(msg(A, text="أحياء - دفعة 2026"))
        gid = app.user_data[A]["groups"][0]
        await send(cmd(B, f"/start g_{gid}"))
        assert B in app.bot_data["groups"][gid]["members"]
        await send(press(A, f"tog:{lid}:{gid}"))
        assert len(app.user_data[B]["lectures"]) == 2, "group delivery"
        last(A, "عضو واحد")

        # quiz answers feed the statistics
        POLLS.clear()
        await send(press(A, f"qz:{lid}:mcq"))
        await send(answer(A, POLLS[-1], 1))
        await send(cmd(A, "/stats"))
        assert "1 صحيحة من 1" in last(A, "إحصاءاتك")["text"]
        await send(cmd(A, "/invite"))
        last(A, "ادعُ أصدقاءك")

        # teacher: paper, key, quiz link, a student solves it, results
        await send(cmd(T, "/teacher"))
        await send(msg(T, voice={"file_id": "v2", "file_unique_id": "b", "duration": 5}))
        await send(press(T, "go:"))
        await asyncio.sleep(0.5)
        tlid = next(iter(app.user_data[T]["lectures"]))
        await send(press(T, f"more:{tlid}"))
        assert any(b.startswith("tpaper:") for b in last(T, "⋯")["buttons"])
        for action in ("tpaper", "tkey", "tquiz"):
            await send(press(T, f"{action}:{tlid}"))
        qtoken = last(T, "?start=t_")["text"].split("start=t_")[1].split()[0]
        POLLS.clear()
        await send(cmd(B, f"/start t_{qtoken}"))
        assert len(POLLS) == 2, POLLS
        await send(answer(B, POLLS[0], 1))
        await send(answer(B, POLLS[1], 0))
        await send(cmd(T, "/results"))
        await send(press(T, f"tres:{qtoken}"))
        assert "خالد: 1/2" in last(T, "طالب واحد")["text"], last(T, "طالب واحد")["text"]

        # old-format lecture (kept in memory by an earlier version) moves to disk when opened
        app.user_data[A]["lectures"]["old1"] = dict(ANALYSIS, transcript="[00:00] قديم", time=1.0)
        await send(press(A, "cards:old1"))
        assert "transcript" not in app.user_data[A]["lectures"]["old1"]
        assert (TMP / "data" / "lectures" / str(A) / "old1.json").exists()

        # the same recording again (another student forwards it): no processing, delivered at once
        before = len(RUNS)
        await send(msg(B, voice={"file_id": "v1-again", "file_unique_id": "a", "duration": 5}))
        await send(press(B, "go:"))
        await asyncio.sleep(0.3)
        assert len(RUNS) == before, "served from the cache"
        last(B, "سبق تلخيص هذه المحاضرة")

        # slides only, no recording
        await send(msg(A, document={"file_id": "d1", "file_unique_id": "d", "file_name": "ch1.pdf",
                                    "mime_type": "application/pdf", "file_size": 1000}))
        assert "files:" in last(A, "حفظت الملف")["buttons"]
        await send(press(A, "files:"))
        await asyncio.sleep(0.3)
        assert RUNS[-1] == "files"
        last(A, "فصل الخلية")

        # automatic group sharing: asked once, then automatic
        n_b = len(app.user_data[B]["lectures"])
        await send(msg(A, voice={"file_id": "v3", "file_unique_id": "c3", "duration": 5}))
        await send(press(A, "go:"))
        await asyncio.sleep(0.5)
        yes = find_button(A, f"gl:{gid}:")
        assert yes.endswith(":y") or yes.endswith(":n")
        await send(press(A, yes.rsplit(":", 1)[0] + ":y"))
        assert len(app.user_data[B]["lectures"]) == n_b + 1, "sent after saying yes"
        await send(msg(A, voice={"file_id": "v4", "file_unique_id": "c4", "duration": 5}))
        await send(press(A, "go:"))
        await asyncio.sleep(0.5)
        assert len(app.user_data[B]["lectures"]) == n_b + 2, "sent automatically"
        last(A, "أرسلتها تلقائياً")

        # course quiz
        acid = app.user_data[A]["lectures"][max(app.user_data[A]["lectures"],
                                                key=lambda k: app.user_data[A]["lectures"][k]["time"])]["course"]
        await send(press(A, f"cq:{acid}"))
        last(A, "اختبار شامل")
        POLLS.clear()
        await send(press(A, f"cq:{acid}:all"))
        assert len(POLLS) >= 2, POLLS

        # owner and model comparison
        await send(cmd(T, "/owner 111"))
        last(T, "الرمز غير صحيح")
        await send(cmd(T, "/owner 424242"))
        assert app.bot_data["owner"] == T
        await send(cmd(T, "/compare"))
        await send(msg(T, voice={"file_id": "v5", "file_unique_id": "c5", "duration": 5}))
        await send(press(T, "go:"))
        await asyncio.sleep(1.5)
        assert "Opus" in last(T, "نتيجة المقارنة")["text"] and "مختلط" in last(T, "نتيجة المقارنة")["text"]
        last(T, "🔬 Opus: $0.30")

        # owner: YouTube cookies (a file that is not cookies.txt is refused)
        await send(cmd(T, "/cookies"))
        last(T, "ملف كوكيز يوتيوب")
        await send(msg(T, document={"file_id": "ck", "file_unique_id": "ck", "file_name": "cookies.txt",
                                    "mime_type": "text/plain", "file_size": 100}))
        last(T, "لا يحوي أي كوكيز")

        # the wallet: charging on, the free hour, a top-up with Stars, and per-use charges
        await send(cmd(T, "/billing on"))
        assert app.bot_data["billing"] is True
        await send(cmd(C, "/start"))
        cu = app.user_data[C]
        assert cu["free_minutes"] == 60 and cu["free_receives"] == 3
        await send(msg(C, voice={"file_id": "v6", "file_unique_id": "c6", "duration": 5}))
        await send(press(C, "go:"))
        await asyncio.sleep(0.5)
        assert cu["free_minutes"] == 0 and cu.get("stars", 0) == 0, "the first hour is free"
        DURATION[0] = 600.0
        await send(msg(C, voice={"file_id": "v7", "file_unique_id": "c7", "duration": 5}))
        await send(press(C, "go:"))
        await asyncio.sleep(0.5)
        assert "wal:buy:100" in last(C, "اشحن رصيدك")["buttons"] and cu["parts"], "short: offered packs, kept parts"
        await send(press(C, "wal:buy:250"))
        assert any(n == "sendInvoice" and ch == C for ch, n, _ in SENT)
        _uid[0] += 1
        await send({"update_id": _uid[0], "pre_checkout_query": {
            "id": "pq1", "from": user(C), "currency": "XTR", "total_amount": 250, "invoice_payload": "pack:250"}})
        await send(msg(C, successful_payment={"currency": "XTR", "total_amount": 250, "invoice_payload": "pack:250",
                                              "telegram_payment_charge_id": "ch1", "provider_payment_charge_id": "p1"}))
        assert cu["stars"] == 275, cu.get("stars")
        assert "go:" in last(C, "شُحن رصيدك")["buttons"]
        await send(press(C, "go:"))
        await asyncio.sleep(0.5)
        assert cu["stars"] == 275 - 15, cu["stars"]
        clid = max(cu["lectures"], key=lambda k: cu["lectures"][k]["time"])
        await send(press(C, f"simp:{clid}:0"))
        assert cu["stars"] == 260 - 10
        await send(press(C, f"en:{clid}"))
        await send(press(C, f"en:{clid}"))
        assert cu["stars"] == 250 - 30, "English charged once"
        for _ in range(3):
            await send(press(C, f"es:{clid}:0:go"))
            await send(msg(C, text="التحلل ثم كربس"))
        assert cu["stars"] == 220 - 5, "two free essays, then a paid one"
        await send(cmd(C, "/exam"))
        await send(press(C, f"ex:t:{clid}"))
        await send(press(C, "ex:go:"))
        assert cu["stars"] == 215 - 50, "exam-night summary"

        # receiving from a classmate: free at first, then 5 Stars with 1 back to the sender, locked when short
        await send(press(A, f"share:{lid}"))
        token = last(A, "?start=s_")["text"].split("start=s_")[1].split()[0]
        n_c = len(cu["lectures"])
        await send(cmd(C, f"/start s_{token}"))
        assert len(cu["lectures"]) == n_c + 1 and cu["free_receives"] == 2 and cu["stars"] == 165
        cu["free_receives"], cu["stars"], a_stars = 0, 3, app.user_data[A].get("stars", 0)
        await send(cmd(C, f"/start s_{token}"))
        assert len(cu["lectures"]) == n_c + 1, "locked, not delivered"
        unl = find_button(C, "unl:")
        await send(press(C, unl))
        last(C, "فتح هذه المحاضرة: ⭐ 5")
        cu["stars"] = 10
        await send(press(C, unl))
        assert len(cu["lectures"]) == n_c + 2 and cu["stars"] == 5 and not cu["locked"]
        assert app.user_data[A]["stars"] == a_stars + 1, "cashback"
        await send(cmd(C, "/wallet"))
        last(C, "محفظتك")
        await send(cmd(C, "/paysupport لم يصلني الرصيد"))
        last(T, "طلب دعم من نورة")
        await send(cmd(T, f"/refund {C}"))
        assert cu["stars"] == 5 - 275 and not cu["payments"]
        await send(cmd(T, "/billing off"))

        # a lecture taught in English: the language button, then the glossary instead of the English PDF
        await send(msg(A, voice={"file_id": "v8", "file_unique_id": "c8", "duration": 5}))
        assert "lang:" in last(A, "استلمت")["buttons"]
        await send(press(A, "lang:"))
        assert app.user_data[A]["lecture_lang"] == "en"
        await send(press(A, "go:"))
        await asyncio.sleep(0.5)
        assert LANGS[-1] == "en"
        elid = max(app.user_data[A]["lectures"], key=lambda k: app.user_data[A]["lectures"][k]["time"])
        assert app.user_data[A]["lectures"][elid]["lang"] == "en"
        assert f"terms:{elid}" in find_button(A, f"terms:{elid}")
        await send(press(A, f"terms:{elid}"))
        assert "ATP" in last(A, "مصطلحات «")["text"]
        await send(press(A, "lang:"))  # (no collector open: just switches back)
        assert app.user_data[A]["lecture_lang"] == "ar"
        ecid = app.user_data[A]["lectures"][elid]["course"]
        await send(press(A, f"glos:{ecid}"))
        last(A, "قاموس مادة")

        # the proof behind an answer
        POLLS.clear()
        await send(press(A, f"qz:{elid}:tf"))
        assert f"ev:{elid}:t:0" in find_button(A, "ev:")
        await send(press(A, f"ev:{elid}:t:0"))
        assert "«التحلل السكري»" in last(A, "الدليل من كلام المحاضر")["text"]

        # exam simulation: one question at a time, readiness at the end
        await send(press(A, f"sim:{ecid}"))
        last(A, "محاكاة اختبار")
        POLLS.clear()
        await send(press(A, f"sim:{ecid}:go"))
        sim = app.user_data[A]["sim"]
        n = len(sim["items"])
        assert len(POLLS) == 1 and n >= 1
        for k in range(n):
            info = app.bot_data["polls"][POLLS[-1]]
            await send(answer(A, POLLS[-1], info["correct"] if k else 1 - info["correct"]))
        assert "sim" not in app.user_data[A] and len(POLLS) == n
        result = last(A, "نتيجة المحاكاة")["text"]
        pct = round(100 * (n - 1) / n)
        assert f"جاهزيتك: {pct}%" in result, result
        assert app.user_data[A]["courses"][ecid]["readiness"]["pct"] == pct
        await send(press(A, f"lib:c:{ecid}"))
        assert f"جاهزيتك: {pct}%" in last(A, "📈")["text"]

        # delete everything
        await send(cmd(B, "/delete"))
        assert not (TMP / "data" / "lectures" / str(B)).exists()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
    for chat, name, p in SENT:
        if name not in ("getMe", "sendChatAction", "answerCallbackQuery", "deleteMessage", "getFile"):
            print(chat, name, {k: v[:120] for k, v in p.items() if k != "buttons"})
    print("\nALL FLOWS PASSED")
