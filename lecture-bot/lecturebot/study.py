"""Study tools on top of a processed lecture: questions about it, simpler explanations,
the exam-night summary across lectures, and the spaced-repetition review deck."""
import datetime as dt
import json
import uuid

import anthropic

from . import config
from .analyze import AnalysisError

FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

TUTOR = """You are Faheem, a patient tutor helping a university student study one recorded Arabic \
lecture. The lecture transcript (with [mm:ss] timestamps) and its summary are below.

Answer in clear Modern Standard Arabic, keeping English technical terms in Latin letters. Base every \
answer on the lecture. When you use something the lecturer said, cite the time like (12:34) so the \
student can listen again. If the lecture does not cover the question, say so in one sentence, then give \
a short general answer clearly marked as from outside the lecture. Keep answers focused: usually under \
200 words, using short paragraphs or a few bullet points. Telegram shows plain text, so do not use \
Markdown headings, tables or bold markers."""


def _lecture_context(lec: dict) -> str:
    sections = "\n".join(f"- {s.get('heading', '')} ({s.get('time', '')})" for s in lec.get("sections", []))
    return (f"<lecture title=\"{lec.get('title', '')}\">\n<outline>\n{sections}\n</outline>\n"
            f"<transcript>\n{lec.get('transcript', '')}\n</transcript>\n</lecture>")


def _text(message) -> str:
    if message.stop_reason == "refusal":
        raise AnalysisError("refused")
    return "".join(b.text for b in message.content if b.type == "text").strip()


def ask(lec: dict, question: str, history: list[dict] | None = None) -> str:
    """Answer a request about one lecture (used for the simpler explanations)."""
    client = anthropic.Anthropic()
    messages = list(history or []) + [{"role": "user", "content": question}]
    try:
        message = client.beta.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4000,
            # The transcript is the same for every question on this lecture: cache it.
            system=[{"type": "text", "text": TUTOR},
                    {"type": "text", "text": _lecture_context(lec), "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            output_config={"effort": "low"},
            **FALLBACK,
        )
    except anthropic.APIStatusError as e:
        raise AnalysisError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AnalysisError("Could not reach the Claude API") from e
    return _text(message)


def explain(lec: dict, section: dict) -> str:
    points = "\n".join(f"- {p.get('text', '')}" for p in section.get("points", []))
    return ask(lec, f"اشرح لي هذا الجزء من المحاضرة بأسلوب أبسط، كأنك تشرحه لطالب يسمعه أول مرة، "
                    f"مع مثال من الحياة اليومية، ثم لخّص الفكرة في جملة واحدة.\n\n"
                    f"الجزء: {section.get('heading', '')} ({section.get('time', '')})\n{points}")


# ---------- exam-night summary ----------

EXAM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "overview": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"heading": {"type": "string"}, "lecture": {"type": "string"},
                               "points": {"type": "array", "items": {"type": "string"}}},
                "required": ["heading", "lecture", "points"],
                "additionalProperties": False,
            },
        },
        "must_memorize": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"item": {"type": "string"}, "detail": {"type": "string"}},
                "required": ["item", "detail"],
                "additionalProperties": False,
            },
        },
        "pitfalls": {"type": "array", "items": {"type": "string"}},
        "self_test": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"question": {"type": "string"}, "answer": {"type": "string"}},
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "overview", "topics", "must_memorize", "pitfalls", "self_test"],
    "additionalProperties": False,
}

EXAM_SYSTEM = """You write the night-before-the-exam summary for a university student, from the study \
notes of several recorded Arabic lectures of one course. Write in clear Modern Standard Arabic, keeping \
English technical terms in Latin letters.

The student has little time: keep only what is most likely to matter in the exam, and connect ideas \
that appear across lectures instead of repeating them.
- title: the course name and "ملخص ليلة الاختبار". overview: 2 to 3 sentences on what the material covers.
- topics: the core ideas grouped by theme (not necessarily by lecture), each with very short points. \
lecture is the title of the lecture it mostly comes from.
- must_memorize: definitions, numbers, formulas, lists and classifications to know by heart, each with \
a one-line detail.
- pitfalls: points students commonly confuse, and the differences that clear them up.
- self_test: 10 to 20 quick questions with short answers, covering all lectures.
Use only the notes given; do not add facts they do not contain."""


def exam_summary(lectures: list[dict]) -> dict:
    notes = [{"title": l.get("title", ""), "subject": l.get("subject", ""), "overview": l.get("overview", ""),
              "sections": l.get("sections", []), "glossary": l.get("glossary", []),
              "comparisons": l.get("comparisons", [])} for l in lectures]
    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=64000,
            system=EXAM_SYSTEM,
            messages=[{"role": "user", "content": "ملاحظات المحاضرات:\n" + json.dumps(notes, ensure_ascii=False)}],
            output_config={"effort": config.CLAUDE_EFFORT, "format": {"type": "json_schema", "schema": EXAM_SCHEMA}},
            **FALLBACK,
        ) as stream:
            message = stream.get_final_message()
    except anthropic.APIStatusError as e:
        raise AnalysisError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AnalysisError("Could not reach the Claude API") from e
    if message.stop_reason == "max_tokens":
        raise AnalysisError("The summary was too long to finish")
    try:
        return json.loads(_text(message))
    except json.JSONDecodeError as e:
        raise AnalysisError("The model returned invalid JSON") from e


# ---------- spaced repetition (Leitner boxes) ----------
# A card moves up a box each time the student knows it, and back to the first box when they don't.
# Box n is reviewed again after INTERVALS[n] days.

INTERVALS = [1, 2, 4, 7, 15, 30]


def today() -> dt.date:
    from zoneinfo import ZoneInfo

    return dt.datetime.now(ZoneInfo(config.REMINDER_TZ)).date()


def add_cards(deck: list[dict], cards: list[dict], title: str) -> int:
    """Add a lecture's flashcards to the deck, first review tomorrow. Returns how many were added."""
    seen = {(c["front"], c["back"]) for c in deck}
    due = (today() + dt.timedelta(days=1)).isoformat()
    added = 0
    for c in cards:
        key = (c.get("front", ""), c.get("back", ""))
        if key[0] and key not in seen:
            deck.append({"id": uuid.uuid4().hex[:8], "front": key[0], "back": key[1], "box": 0, "due": due,
                         "title": title})
            seen.add(key)
            added += 1
    return added


def due_cards(deck: list[dict]) -> list[dict]:
    t = today().isoformat()
    return sorted((c for c in deck if c["due"] <= t), key=lambda c: (c["box"], c["due"]))


def grade(card: dict, known: bool) -> None:
    card["box"] = min(card["box"] + 1, len(INTERVALS) - 1) if known else 0
    card["due"] = (today() + dt.timedelta(days=INTERVALS[card["box"]])).isoformat()


# ---------- essay grading ----------

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "good": {"type": "string"},
        "missing": {"type": "array", "items": {"type": "string"}},
        "advice": {"type": "string"},
    },
    "required": ["score", "good", "missing", "advice"],
    "additionalProperties": False,
}

GRADE_SYSTEM = """You grade a university student's written answer to an essay question about a lecture, fairly and kindly, in clear Modern Standard Arabic.

You get the question, the model answer from the lecture, the key points a full answer must contain, and the student's answer. Judge the meaning, not the wording: a point counts when the student expressed it correctly in their own words. Do not penalise spelling or style. A wrong statement about the content loses marks.
- score: 0 to 10, in proportion to the key points covered correctly.
- good: one sentence on what the student got right (or that the answer is off topic).
- missing: the key points that are missing or wrong, each as a short corrected statement.
- advice: one sentence on how to make the answer complete."""


def grade_essay(question: dict, answer: str) -> dict:
    prompt = (f"السؤال: {question['question']}\n\nنموذج الإجابة: {question.get('model_answer', '')}\n\n"
              "النقاط الأساسية:\n" + "\n".join(f"- {p}" for p in question.get("key_points", []))
              + f"\n\nإجابة الطالب:\n<answer>\n{answer}\n</answer>")
    client = anthropic.Anthropic()
    try:
        message = client.beta.messages.create(
            model=config.CLAUDE_MODEL, max_tokens=4000, system=GRADE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": GRADE_SCHEMA}}, **FALLBACK,
        )
    except anthropic.APIStatusError as e:
        raise AnalysisError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AnalysisError("Could not reach the Claude API") from e
    try:
        result = json.loads(_text(message))
    except json.JSONDecodeError as e:
        raise AnalysisError("The model returned invalid JSON") from e
    result["score"] = max(0, min(10, int(result.get("score", 0))))
    return result
