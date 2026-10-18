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
                  PARTS_WAIT_SECONDS="1")

from telegram import Update  # noqa: E402
from telegram.ext import Application  # noqa: E402
from telegram.request import BaseRequest  # noqa: E402

import bot  # noqa: E402
from lecturebot import pipeline, study, tts  # noqa: E402
from lecturebot.pipeline import LectureResult  # noqa: E402

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
        if "/file/bot" in url:
            return 200, b"\0" * 2000
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
        elif name in ("sendMessage", "editMessageText"):
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
    "true_false": [{"statement": "التحلل في النواة", "answer": False, "explanation": "", "time": "00:05"}],
    "flashcards": [{"front": "ناتج التحلل؟", "back": "2 ATP"}], "comparisons": [],
    "mindmap": {"center": "التنفس", "branches": [{"label": "التحلل", "children": ["2 ATP"]}]},
}


def fake_run(sources, work, *a):
    pdf = work / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    r = LectureResult(dict(ANALYSIS), [], pdf, "[00:00] نتحدث اليوم عن الميتوكوندريا\n\n[00:30] التحلل السكري", sources[0])
    r.extra["duration"] = 3600
    return r


pipeline.run = fake_run
study.ask = lambda lec, q, h=None: f"جواب: {q}"
study.audio_script = lambda lec: "نص صوتي"
study.translate = lambda lec: dict(ANALYSIS, title="Cellular respiration")
study.exam_summary = lambda lecs: {"title": "ملخص", "overview": "", "topics": [], "must_memorize": [], "pitfalls": [],
                                   "self_test": []}


def fake_speak(text, out):
    out.write_bytes(b"\0" * 5000)
    return out


tts.speak = fake_speak
tts.duration = lambda p: 60

A, B, T = 7, 8, 9  # two students and a teacher


def user(uid):
    return {"id": uid, "is_bot": False, "first_name": {A: "سارة", B: "خالد", T: "د. أحمد"}[uid]}


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
        last(A, "حفظتها في مكتبتك")

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

        # phase 4 buttons
        for action in ("audio", "audio", "en", "docx", "md", "more"):
            await send(press(A, f"{action}:{lid}"))
        assert ud["lectures"][lid]["audio_file_id"].startswith("aud"), "audio cached"
        assert ud["lectures"][lid]["en_file_id"].startswith("doc"), "English cached"

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
        await send(press(A, f"quiz:{lid}"))
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
        assert len(POLLS) == 2
        await send(answer(B, POLLS[0], 1))
        await send(answer(B, POLLS[1], 0))
        await send(cmd(T, "/results"))
        await send(press(T, f"tres:{qtoken}"))
        assert "خالد: 1/2" in last(T, "طالب واحد")["text"], last(T, "طالب واحد")["text"]

        # old-format lecture (kept in memory by an earlier version) moves to disk when opened
        app.user_data[A]["lectures"]["old1"] = dict(ANALYSIS, transcript="[00:00] قديم", time=1.0)
        await send(press(A, "map:old1"))
        assert "transcript" not in app.user_data[A]["lectures"]["old1"]
        assert (TMP / "data" / "lectures" / str(A) / "old1.json").exists()

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
