"""Turn a timestamped transcript (and optional slide/board photos) into study material with Claude."""
import base64
import json

import anthropic

from . import config
from .media import fmt_time
from .transcribe import DIALECTS, Segment

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

_point = {
    "type": "object",
    "properties": {"text": {"type": "string"}, "time": {"type": "string"}},
    "required": ["text", "time"],
    "additionalProperties": False,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subject": {"type": "string"},
        "overview": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "time": {"type": "string"},
                    "points": {"type": "array", "items": _point},
                },
                "required": ["heading", "time", "points"],
                "additionalProperties": False,
            },
        },
        "glossary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "arabic": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["term", "arabic", "explanation"],
                "additionalProperties": False,
            },
        },
        "mcq": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer_index": {"type": "integer"},
                    "explanation": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["question", "options", "answer_index", "explanation", "time"],
                "additionalProperties": False,
            },
        },
        "true_false": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "answer": {"type": "boolean"},
                    "explanation": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["statement", "answer", "explanation", "time"],
                "additionalProperties": False,
            },
        },
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"front": {"type": "string"}, "back": {"type": "string"}},
                "required": ["front", "back"],
                "additionalProperties": False,
            },
        },
        "transcript_fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"wrong": {"type": "string"}, "right": {"type": "string"}},
                "required": ["wrong", "right"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "subject", "overview", "sections", "glossary", "mcq", "true_false", "flashcards",
                 "transcript_fixes"],
    "additionalProperties": False,
}

SYSTEM = """You turn recorded Arabic university lectures into study material for students.

The transcript comes from automatic speech recognition. Lecturers mix Modern Standard Arabic with \
colloquial dialect and English technical terms, and the recognizer sometimes writes English terms in \
Arabic letters or mishears words. Use the context of the whole lecture to understand what was meant.

Write everything in clear Modern Standard Arabic, except technical terms: write each English term in \
Latin letters exactly as used in the field (for example Mitochondria, not ميتوكوندريا), with its Arabic \
meaning where it helps.

Rules for the fields:
- title: a short title for the lecture. subject: the course or field it belongs to.
- overview: 2 to 4 sentences on what the lecture covers.
- sections: follow the lecture's own order of ideas. Each section has a heading, the time it starts, \
and the key points as short sentences a student can revise from. Cover every idea the lecturer \
taught, including definitions, steps, lists, formulas, examples and comparisons.
- glossary: every technical term from the lecture, with the term as used, its Arabic equivalent, and \
a one-sentence explanation.
- mcq: multiple-choice questions that test understanding of the lecture, four options each, one \
correct, answer_index counting from 0, a short explanation of why the answer is right, and the time \
in the lecture where the answer is explained. Write about one question per four minutes of lecture, \
at least 5 and at most 20. Keep each question under 280 characters, each option under 90 characters \
and each explanation under 190 characters.
- true_false: statements about the lecture, about half true and half false, each with the correct \
answer, a short explanation (for a false statement, say what is actually right) and the time where it \
is explained. False statements must be plausible, changing one detail of something the lecturer said. \
Write about one per five minutes of lecture, at least 5 and at most 15. Keep each statement under 280 \
characters and each explanation under 190 characters.
- flashcards: front is a question or term, back is the short answer. Between 8 and 25 cards.
- transcript_fixes: words the recognizer got clearly wrong that matter for studying, mostly English \
terms written in Arabic letters, mapped to the correct spelling. Only include fixes you are confident \
about; each "wrong" value must appear exactly as written in the transcript.
- Every "time" value must be a timestamp copied from the transcript lines, in the same format.

Base all content on what the lecturer actually said and on the attached slides, files and photos of \
the board, if any. Do not add facts the lecture did not cover. When the slides add detail the speech \
left out (a diagram label, a formula, a list), include it in the matching section. Use the spelling of \
terms on the slides to correct the transcript. When the recording is made of several parts, cover all \
of them in one coherent summary that follows the order of the parts.

The lecturer may speak a regional dialect. Understand it, but write the study material in Modern \
Standard Arabic; keep a dialect word only when it is itself the subject being taught."""


class AnalysisError(Exception):
    pass


def _transcript_text(segments: list[Segment]) -> str:
    return "\n".join(f"[{fmt_time(s.start)}] {s.text}" for s in segments)


def analyze(segments: list[Segment], major: str | None = None, images: list[tuple[bytes, str]] | None = None,
            duration: float = 0.0, materials: list | None = None, dialect: str | None = None,
            parts: list[tuple[float, str]] | None = None, on_section=None) -> dict:
    """Return the study-material dict described by SCHEMA.

    materials: lecture files (lecturebot.materials.Material). parts: (start_seconds, title) of each
    recording when several were joined. on_section(section) is called as each summary section is written.
    """
    materials = materials or []
    content: list[dict] = []
    for m in materials:
        if m.pdf:
            content.append({"type": "document", "title": m.name,
                            "source": {"type": "base64", "media_type": "application/pdf",
                                       "data": base64.standard_b64encode(m.pdf).decode()}})
    all_images = list(images or []) + [img for m in materials for img in m.images]
    for data, media_type in all_images[: config.MAX_IMAGES_PER_LECTURE]:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.standard_b64encode(data).decode()},
        })

    intro = []
    field = MAJOR_NAMES.get(major or "")
    if field:
        intro.append(f"تخصص الطالب: {field}.")
    if dialect and dialect != "msa" and dialect in DIALECTS:
        intro.append(f"لهجة المحاضر: {DIALECTS[dialect][0]}.")
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
    content.append({
        "type": "text",
        "text": "\n".join(intro) + slide_text
                + f"\n\nنص المحاضرة:\n<transcript>\n{_transcript_text(segments)}\n</transcript>",
    })

    client = anthropic.Anthropic()
    sections = _SectionStream(on_section) if on_section else None
    try:
        with client.beta.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": config.CLAUDE_EFFORT,
                           "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            if sections:
                for text in stream.text_stream:
                    sections.feed(text)
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
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise AnalysisError("The model returned invalid JSON") from e
    _clean(result)
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


def _clean(result: dict) -> None:
    """Drop malformed questions so later steps (PDF, Telegram quiz polls) never break on them."""
    good = []
    for q in result.get("mcq", []):
        opts = [o for o in q.get("options", []) if o.strip()]
        if 2 <= len(opts) <= 10 and 0 <= q.get("answer_index", -1) < len(opts):
            q["options"] = opts
            good.append(q)
    result["mcq"] = good
    result["true_false"] = [t for t in result.get("true_false", [])
                            if (t.get("statement") or "").strip() and isinstance(t.get("answer"), bool)]
    # The model sometimes copies the transcript's "[mm:ss]" brackets into time fields.
    items = result.get("sections", []) + result["mcq"] + result["true_false"] + [pt for sec in result.get("sections", []) for pt in sec.get("points", [])]
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
