"""Turn a timestamped transcript (and optional slides / board photos) into study material with Claude.

Two requests run side by side so neither has to do everything at once:
- the notes: summary, glossary, divisions (only the classifications the lecturer actually made) and
  comparison tables, streamed so the student can start reading early;
- the questions: multiple choice, true/false, essay and flashcards. Every question carries a short
  quote from the transcript that supports its answer; questions whose quote is not in the transcript
  are dropped, so the student is never tested on something the lecturer did not say.
"""
import base64
import json
import re
import threading

import anthropic

from . import config
from .media import fmt_time
from .transcribe import Segment

MAJOR_NAMES = {
    "medicine": "الطب والعلوم الصحية",
    "engineering": "الهندسة",
    "science": "العلوم",
    "computing": "الحاسب وتقنية المعلومات",
    "business": "الإدارة والمحاسبة",
    "sharia": "العلوم الشرعية",
    "law": "القانون",
    "languages": "اللغات والآداب",
}


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_S, _T = {"type": "string"}, {"type": "string"}
_LIST_S = {"type": "array", "items": _S}

PROPS = {
    "title": _S,
    "subject": _S,
    "overview": _S,
    "sections": {"type": "array", "items": _obj({
        "heading": _S, "time": _T, "points": {"type": "array", "items": _obj({"text": _S, "time": _T})}})},
    "glossary": {"type": "array", "items": _obj({"term": _S, "arabic": _S, "explanation": _S})},
    "divisions": {"type": "array", "items": _obj({
        "title": _S, "center": _S, "time": _T,
        "branches": {"type": "array", "items": _obj({"label": _S, "children": _LIST_S})}})},
    "comparisons": {"type": "array", "items": _obj({
        "title": _S, "headers": _LIST_S, "rows": {"type": "array", "items": _LIST_S}, "time": _T})},
    "transcript_fixes": {"type": "array", "items": _obj({"wrong": _S, "right": _S})},
    "mcq": {"type": "array", "items": _obj({
        "question": _S, "options": _LIST_S, "answer_index": {"type": "integer"}, "explanation": _S, "time": _T,
        "evidence": _S})},
    "true_false": {"type": "array", "items": _obj({
        "statement": _S, "answer": {"type": "boolean"}, "explanation": _S, "time": _T, "evidence": _S})},
    "essay": {"type": "array", "items": _obj({
        "question": _S, "model_answer": _S, "key_points": _LIST_S, "time": _T, "evidence": _S})},
    "flashcards": {"type": "array", "items": _obj({"front": _S, "back": _S})},
}

NOTES_KEYS = ("title", "subject", "overview", "sections", "glossary", "divisions", "comparisons", "transcript_fixes")
QUESTION_KEYS = ("mcq", "true_false", "essay", "flashcards")
NOTES_SCHEMA = _obj({k: PROPS[k] for k in NOTES_KEYS})
QUESTIONS_SCHEMA = _obj({k: PROPS[k] for k in QUESTION_KEYS})
SCHEMA = _obj(PROPS)  # everything, for the translation

COMMON = """The transcript comes from automatic speech recognition. Lecturers mix Modern Standard \
Arabic with colloquial speech and English technical terms, and the recognizer sometimes writes English \
terms in Arabic letters or mishears words. Use the context of the whole lecture to understand what was \
meant, and the attached slides or photos, if any, for the correct spelling of terms.

Write in clear, correct Modern Standard Arabic. Write each English technical term in Latin letters \
exactly as used in the field (for example Mitochondria, not ميتوكوندريا), with its Arabic meaning where \
it helps.

Accuracy matters more than anything else: students will study from this and be examined on it.
- Every statement must be something the lecturer actually said or showed. Do not add facts, even true \
ones, that the lecture did not cover.
- If a passage is unclear, garbled or you are not sure what was said, leave it out. Never guess.
- Do not compress so much that the meaning changes: keep conditions, exceptions, numbers, units, \
names and the direction of relationships exactly as the lecturer stated them.
- Each point or question must be a complete sentence that a student can understand on its own, \
without having heard the lecture.
- Every "time" value is a timestamp copied from the transcript lines, in the same format, where that \
idea is explained."""

NOTES_SYSTEM = f"""You write the study notes for a recorded Arabic university lecture.

{COMMON}

Fields:
- title: a short title for the lecture. subject: the course or field it belongs to.
- overview: 2 to 4 sentences on what the lecture covers.
- sections: follow the lecture's own order of ideas. Each section has a heading, the time it starts, \
and the key points as short sentences a student can revise from. Cover every idea the lecturer \
taught, including definitions, steps, lists, formulas and examples.
- glossary: the technical terms of the lecture, each with the term as used, its Arabic equivalent and \
a one-sentence explanation as the lecturer explained it.
- divisions: only the classifications the lecturer explicitly made: when they say that something is \
divided into, has types, kinds, parts, stages or categories, and name them. For each one: title (for \
example "أقسام المياه"), center (the thing being divided, 1 to 4 words), branches (exactly the parts the \
lecturer named, in their order, each label 1 to 6 words, with children: the sub-parts the lecturer \
named for it, or one short description from the lecture; an empty list if neither) and time. Never \
turn the outline of the lecture into a division, and never create parts the lecturer did not state. \
Use an empty list when the lecture has no explicit classification.
- comparisons: a table for each comparison the lecturer made between two or more things. headers: \
the first is the aspect being compared, the others are the things compared (2 to 4). Each row starts \
with the aspect, followed by one short cell per compared thing, 3 to 8 rows. Only aspects the lecturer \
discussed. Use an empty list when the lecture compares nothing.
- transcript_fixes: words the recognizer got clearly wrong that matter for studying, mostly English \
terms written in Arabic letters, mapped to the correct spelling. Only fixes you are sure of; each \
"wrong" value must appear exactly as written in the transcript.

When the recording is made of several parts, cover all of them in one coherent set of notes that \
follows the order of the parts."""

QUESTIONS_SYSTEM = f"""You write the practice questions for a recorded Arabic university lecture.

{COMMON}

Rules for every question:
- It tests an important idea of the lecture, is worded clearly and unambiguously, and has exactly one \
correct answer according to what the lecturer said.
- evidence: a short quote (at most 25 words) copied word for word from the transcript lines that \
supports the answer, without the timestamp. If you cannot point to such a quote, do not write the \
question.
- Do not ask about unclear passages, side remarks or jokes.

Fields:
- mcq: multiple-choice questions with four options of the same kind and similar length, one correct, \
answer_index counting from 0, no "all of the above" or "none of the above". explanation: why the \
answer is right, in one sentence. About one question per four minutes of lecture, at least 5 and at \
most 20. Keep each question under 280 characters, each option under 90 and each explanation under 190.
- true_false: statements about the lecture, about half true and half false. A false statement changes \
one clear detail of something the lecturer said, so that it is definitely false, not debatable. \
explanation: for a false statement, what is actually right. About one per five minutes, at least 5 and \
at most 15. Statements under 280 characters, explanations under 190.
- essay: 3 to 6 questions that need an explained answer (explain, compare, justify, describe the \
steps). model_answer: a complete answer from the lecture in 3 to 8 sentences. key_points: the 3 to 6 \
points a full answer must contain, used to grade the student.
- flashcards: front is a question or a term, back is the short answer. Between 8 and 25 cards."""


class AnalysisError(Exception):
    pass


def _transcript_text(segments: list[Segment]) -> str:
    return "\n".join(f"[{fmt_time(s.start)}] {s.text}" for s in segments)


def _content(segments, major, images, duration, materials, parts) -> list[dict]:
    content: list[dict] = []
    for m in materials:
        if m.pdf:
            content.append({"type": "document", "title": m.name,
                            "source": {"type": "base64", "media_type": "application/pdf",
                                       "data": base64.standard_b64encode(m.pdf).decode()}})
    all_images = list(images or []) + [img for m in materials for img in m.images]
    for data, media_type in all_images[: config.MAX_IMAGES_PER_LECTURE]:
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                    "data": base64.standard_b64encode(data).decode()}})
    intro = []
    field = MAJOR_NAMES.get(major or "")
    if field:
        intro.append(f"تخصص الطالب: {field}.")
    if materials:
        intro.append("مرفق ملفات المحاضرة: " + "، ".join(m.name for m in materials) + ".")
    if images:
        intro.append(f"مرفق {len(images)} صورة من شرائح العرض أو السبورة.")
    if parts and len(parts) > 1:
        intro.append("التسجيل مكوّن من عدة أجزاء متتالية: "
                     + "، ".join(f"الجزء {i} يبدأ عند {fmt_time(t)}" + (f" ({name})" if name else "")
                                for i, (t, name) in enumerate(parts, 1)) + ".")
    intro.append(f"مدة المحاضرة: {fmt_time(duration)}.")
    slides = [m for m in materials if m.text and not m.pdf]
    slide_text = "".join(f"\n\nنص الشرائح ({m.name}):\n<slides>\n{m.text[:60000]}\n</slides>" for m in slides)
    content.append({"type": "text", "text": "\n".join(intro) + slide_text
                    + f"\n\nنص المحاضرة:\n<transcript>\n{_transcript_text(segments)}\n</transcript>"})
    return content


def _call(system: str, content: list[dict], schema: dict, on_text=None) -> dict:
    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": config.CLAUDE_EFFORT, "format": {"type": "json_schema", "schema": schema}},
            system=system,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            if on_text:
                for text in stream.text_stream:
                    on_text(text)
            message = stream.get_final_message()
    except anthropic.APIStatusError as e:
        raise AnalysisError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AnalysisError("Could not reach the Claude API") from e
    if message.stop_reason == "refusal":
        raise AnalysisError("The model declined to process this lecture")
    if message.stop_reason == "max_tokens":
        raise AnalysisError("The study material was too long to finish")
    text = "".join(b.text for b in message.content if b.type == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AnalysisError("The model returned invalid JSON") from e


def analyze(segments: list[Segment], major: str | None = None, images: list[tuple[bytes, str]] | None = None,
            duration: float = 0.0, materials: list | None = None, parts: list[tuple[float, str]] | None = None,
            on_section=None) -> dict:
    """Return the study material (all PROPS keys).

    materials: lecture files (lecturebot.materials.Material). parts: (start_seconds, title) of each
    recording when several were joined. on_section(section) is called as each summary section is written.
    """
    content = _content(segments, major, images, duration, materials or [], parts)
    questions: dict = {}
    failure: list[Exception] = []

    def ask_questions():
        try:
            questions.update(_call(QUESTIONS_SYSTEM, content, QUESTIONS_SCHEMA))
        except Exception as e:  # reported after the notes are done
            failure.append(e)

    worker = threading.Thread(target=ask_questions, daemon=True)
    worker.start()
    sections = _SectionStream(on_section) if on_section else None
    result = _call(NOTES_SYSTEM, content, NOTES_SCHEMA, sections.feed if sections else None)
    worker.join()
    if failure:
        raise failure[0] if isinstance(failure[0], AnalysisError) else AnalysisError(str(failure[0]))
    result.update(questions)
    _clean(result, _transcript_text(segments))
    return result


class _SectionStream:
    """Picks complete objects out of the "sections" array while the JSON is still being written,
    so the student can start reading before the whole answer is done."""

    def __init__(self, callback):
        self.callback, self.buf, self.pos = callback, "", -1
        self.depth, self.in_str, self.esc, self.obj_start, self.done = 0, False, False, -1, False

    def feed(self, text: str) -> None:
        self.buf += text
        if self.done:
            return
        if self.pos < 0:
            key = self.buf.find('"sections"')
            if key < 0:
                return
            bracket = self.buf.find("[", key)
            if bracket < 0:
                return
            self.pos = bracket + 1
        while self.pos < len(self.buf):
            c = self.buf[self.pos]
            if self.in_str:
                if self.esc:
                    self.esc = False
                elif c == "\\":
                    self.esc = True
                elif c == '"':
                    self.in_str = False
            elif c == '"':
                self.in_str = True
            elif c == "{":
                if self.depth == 0:
                    self.obj_start = self.pos
                self.depth += 1
            elif c == "}":
                self.depth -= 1
                if self.depth == 0:
                    self._emit(self.buf[self.obj_start:self.pos + 1])
            elif c == "]" and self.depth == 0:
                self.done = True
                return
            self.pos += 1

    def _emit(self, raw: str) -> None:
        try:
            section = json.loads(raw)
        except json.JSONDecodeError:
            return
        for item in [section] + section.get("points", []):
            if isinstance(item.get("time"), str):
                item["time"] = item["time"].strip(" []")
        try:
            self.callback(section)
        except Exception:  # a failed preview must never break the analysis
            pass


# ---------- checks ----------

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟـ]")


def _words(text: str) -> list[str]:
    t = _DIACRITICS.sub("", text or "")
    t = re.sub("[إأآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
    return [w for w in re.findall(r"\w+", t.lower()) if len(w) > 1]


def supported(evidence: str, transcript_words: set[str]) -> bool:
    """True when most words of the quoted evidence occur in the transcript."""
    words = _words(evidence)
    if len(words) < 3:
        return False
    return sum(w in transcript_words for w in words) / len(words) >= 0.7


def _clean(result: dict, transcript: str) -> None:
    """Drop malformed or unsupported items so the PDF and the quizzes never show them."""
    tw = set(_words(transcript))
    mcq = []
    for q in result.get("mcq", []):
        opts = [o for o in q.get("options", []) if o.strip()]
        if 2 <= len(opts) <= 10 and 0 <= q.get("answer_index", -1) < len(opts) and supported(q.get("evidence", ""), tw):
            q["options"] = opts
            mcq.append(q)
    result["mcq"] = mcq
    result["true_false"] = [t for t in result.get("true_false", [])
                            if (t.get("statement") or "").strip() and isinstance(t.get("answer"), bool)
                            and supported(t.get("evidence", ""), tw)]
    result["essay"] = [e for e in result.get("essay", [])
                       if e.get("question", "").strip() and e.get("model_answer", "").strip()
                       and supported(e.get("evidence", ""), tw)]
    comps = []
    for c in result.get("comparisons", []):
        n = len(c.get("headers", []))
        rows = [r for r in c.get("rows", []) if len(r) == n]
        if n >= 2 and rows:
            c["rows"] = rows
            comps.append(c)
    result["comparisons"] = comps
    result["divisions"] = [d for d in result.get("divisions", []) if len(d.get("branches", [])) >= 2]
    # The model sometimes copies the transcript's "[mm:ss]" brackets into time fields.
    items = (result.get("sections", []) + result["mcq"] + result["true_false"] + result["essay"] + comps
             + result["divisions"] + [pt for sec in result.get("sections", []) for pt in sec.get("points", [])])
    for item in items:
        if isinstance(item.get("time"), str):
            item["time"] = item["time"].strip(" []")


def apply_fixes(segments: list[Segment], fixes: list[dict]) -> list[Segment]:
    pairs = [(f["wrong"], f["right"]) for f in fixes if f.get("wrong") and f.get("right") and f["wrong"] != f["right"]]
    if not pairs:
        return segments
    out = []
    for s in segments:
        text = s.text
        for wrong, right in pairs:
            text = text.replace(wrong, right)
        out.append(Segment(s.start, s.end, text))
    return out
