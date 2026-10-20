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


# Trusted sources per discipline: definitions the lecturer did not give are looked up only on these sites.
FIELDS = {
    "sharia": ["dorar.net", "shamela.ws", "islamweb.net", "islamqa.info", "binbaz.org.sa", "binothaimeen.net",
               "alifta.gov.sa", "alukah.net"],
    "medicine": ["msdmanuals.com", "ncbi.nlm.nih.gov", "medlineplus.gov", "who.int", "nhs.uk", "cdc.gov",
                 "mayoclinic.org", "britannica.com"],
    "science": ["britannica.com", "ncbi.nlm.nih.gov", "nature.com", "iupac.org", "nasa.gov", "nist.gov",
                "khanacademy.org"],
    "engineering": ["britannica.com", "nist.gov", "ieee.org", "sciencedirect.com", "engineeringtoolbox.com"],
    "computing": ["developer.mozilla.org", "docs.python.org", "learn.microsoft.com", "ieee.org", "acm.org",
                  "nist.gov", "britannica.com"],
    "business": ["investopedia.com", "ifrs.org", "imf.org", "worldbank.org", "sama.gov.sa", "britannica.com"],
    "law": ["laws.boe.gov.sa", "moj.gov.sa", "law.cornell.edu", "un.org", "britannica.com"],
    "language": ["shamela.ws", "almaany.com", "dorar.net", "britannica.com", "dictionary.cambridge.org",
                 "merriam-webster.com", "oxfordlearnersdictionaries.com"],
    "general": ["britannica.com", "shamela.ws", "ncbi.nlm.nih.gov", "who.int", "un.org"],
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
    "field": {"type": "string", "enum": list(FIELDS)},
    "glossary": {"type": "array", "items": _obj({"term": _S, "arabic": _S, "defined_by_lecturer": {"type": "boolean"},
                                                 "explanation": _S, "definition_quote": _S, "time": _T})},
    "divisions": {"type": "array", "items": _obj({
        "title": _S, "center": _S, "time": _T, "evidence": _S,
        "branches": {"type": "array", "items": _obj({"label": _S, "children": _LIST_S})}})},
    "processes": {"type": "array", "items": _obj({
        "title": _S, "steps": _LIST_S, "cyclic": {"type": "boolean"}, "time": _T, "evidence": _S})},
    "comparisons": {"type": "array", "items": _obj({
        "title": _S, "headers": _LIST_S, "rows": {"type": "array", "items": _LIST_S}, "time": _T, "evidence": _S})},
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

NOTES_KEYS = ("title", "subject", "field", "overview", "sections", "glossary", "divisions", "processes", "comparisons",
              "transcript_fixes")
QUESTION_KEYS = ("mcq", "true_false", "essay", "flashcards")
NOTES_SCHEMA = _obj({k: PROPS[k] for k in NOTES_KEYS})
QUESTIONS_SCHEMA = _obj({k: PROPS[k] for k in QUESTION_KEYS})
SCHEMA = _obj(PROPS)  # everything, for the translation

COMMON = """The transcript comes from automatic speech recognition. Lecturers mix Modern Standard \
Arabic with colloquial speech and English technical terms, and the recognizer sometimes writes English \
terms in Arabic letters or mishears words. Use the context of the whole lecture to understand what was \
meant, and the attached slides or photos, if any, for the correct spelling of terms.

Write in clear, correct Modern Standard Arabic, and write every question and answer in Arabic. Keep a \
term in English only when the lecturer said it in English: write it in Latin letters exactly as used in \
the field (for example Mitochondria, not ميتوكوندريا), with its Arabic meaning where it helps. Never \
translate an Arabic term into English: in a lecture taught in Arabic terms such as التوحيد or الإجماع stay \
in Arabic.

When there is no recording, the lecture's slides, files or photos of book pages are the only source: \
then every "time" value is an empty string, and quotes are taken from the documents' text.

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
- title: a short title for the lecture. subject: the course or field it belongs to. field: the \
discipline, one of: sharia (Islamic sciences), medicine, science, engineering, computing, business, \
law, language (Arabic or other languages and literature), general.
- overview: 2 to 4 sentences on what the lecture covers.
- sections: follow the lecture's own order of ideas. Each section has a heading, the time it starts, \
and the key points as short sentences a student can revise from. Cover every idea the lecturer \
taught, including definitions, steps, lists, formulas and examples.
- glossary: every technical term of the lecture. term: exactly as the lecturer used it. arabic: its \
Arabic equivalent, only when the term is not Arabic; otherwise an empty string. defined_by_lecturer: \
true only when the lecturer stated what the term means. explanation: that definition, faithful to the \
lecturer's words; an empty string when the lecturer did not define the term. Never define a term \
from your own knowledge: definitions the lecturer did not give are looked up separately in trusted \
sources. definition_quote: the lecturer's defining words copied exactly from the transcript (one \
sentence or a short passage, without the timestamp); an empty string when the term was not defined. \
time: where it is defined, or first used.
- divisions: only the classifications the lecturer explicitly made: when they say that something is \
divided into, has types, kinds, parts, stages or categories, and name them. For each one: title (for \
example "أقسام المياه"), center (the thing being divided, 1 to 4 words), branches (exactly the parts the \
lecturer named, in their order, each label 1 to 6 words, with children: the sub-parts the lecturer \
named for it, or one short description from the lecture; an empty list if neither) and time. Never \
turn the outline of the lecture into a division, and never create parts the lecturer did not state. \
evidence: the lecturer's words stating this classification, copied exactly from the transcript (at \
most 30 words, without the timestamp). Use an empty list when the lecture has no explicit classification.
- processes: only ordered steps or stages the lecturer explicitly described in sequence (a mechanism, a \
procedure, a pathway, a cycle, the stages of a disease or of a method): title, steps (exactly the steps \
the lecturer named, in their order, each 2 to 15 words), cyclic (true only when the lecturer said the \
last step leads back to the first), time, and evidence (the lecturer's words stating the sequence, \
copied exactly from the transcript, at most 30 words). Never invent or reorder steps. Use an empty list when the \
lecture describes no sequence.
- comparisons: a table for each comparison the lecturer made between two or more things. headers: \
the first is the aspect being compared, the others are the things compared (2 to 4). Each row starts \
with the aspect, followed by one short cell per compared thing, 3 to 8 rows. Only aspects the lecturer \
discussed. evidence: the lecturer's words making the comparison, copied exactly from the transcript (at \
most 30 words). Use an empty list when the lecture compares nothing.
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


# Dollars per million tokens: input, output, cache read, cache write.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 0.20, 5.0),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20, 2.5),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}


class AnalysisError(Exception):
    pass


REVIEW_SCHEMA = _obj({"verdicts": {"type": "array", "items": _obj({
    "kind": {"type": "string", "enum": ["mcq", "true_false", "essay", "flashcards"]},
    "index": {"type": "integer"}, "keep": {"type": "boolean"}, "reason": _S})}})

REVIEW_SYSTEM = """You are the final check on practice questions written for a recorded Arabic university \
lecture, before students see them. You get the lecture's outline and each question with the quote from \
the lecture that is meant to support its answer.

Give a verdict for every item. keep is false when any of these is true:
- the wording is unclear, ungrammatical or could be read in more than one way;
- the marked answer is not clearly correct according to the quote, or another option could also be \
defended as correct;
- for a true/false statement, it is not definitely true or definitely false;
- it asks about a side remark, a joke, an example of no importance, or something the outline shows \
is not part of the lecture's content;
- it repeats another item.
Otherwise keep is true. reason: a few words. Judge strictly: it is better to drop a doubtful question \
than to show a wrong one."""


def cost_of(usage, model: str) -> dict:
    """Tokens and dollars of one response (priced by the model that actually answered)."""
    p_in, p_out, p_read, p_write = PRICES.get(model, PRICES["claude-opus-5-5"])
    u = {"model": model, "input": usage.input_tokens or 0, "output": usage.output_tokens or 0,
         "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
         "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0}
    u["cost"] = round((u["input"] * p_in + u["output"] * p_out + u["cache_read"] * p_read
                       + u["cache_write"] * p_write) / 1e6, 4)
    return u


def add_usage(total: dict, u: dict) -> dict:
    for k in ("input", "output", "cache_read", "cache_write", "cost"):
        total[k] = round(total.get(k, 0) + u.get(k, 0), 4)
    total["model"] = u.get("model", total.get("model"))
    return total


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
    if segments:
        intro.append(f"مدة المحاضرة: {fmt_time(duration)}.")
    else:
        intro.append("لا يوجد تسجيل لهذه المحاضرة: المصدر هو الملفات والصور المرفقة وحدها.")
    slides = [m for m in materials if m.text and not m.pdf]
    slide_text = "".join(f"\n\nنص الشرائح ({m.name}):\n<slides>\n{m.text[:60000]}\n</slides>" for m in slides)
    transcript = (f"\n\nنص المحاضرة:\n<transcript>\n{_transcript_text(segments)}\n</transcript>" if segments else "")
    content.append({"type": "text", "text": "\n".join(intro) + slide_text + transcript})
    return content


def _call(system: str, content: list[dict], schema: dict, on_text=None, model: str | None = None) -> tuple[dict, dict]:
    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=model or config.CLAUDE_MODEL,
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
    answered_by = getattr(message, "model", None) or model or config.CLAUDE_MODEL
    try:
        return json.loads(text), cost_of(message.usage, answered_by)
    except json.JSONDecodeError as e:
        raise AnalysisError("The model returned invalid JSON") from e


def analyze(segments: list[Segment], major: str | None = None, images: list[tuple[bytes, str]] | None = None,
            duration: float = 0.0, materials: list | None = None, parts: list[tuple[float, str]] | None = None,
            on_section=None, model: str | None = None, questions_model: str | None = None) -> dict:
    """Return the study material (all PROPS keys), plus "_usage": tokens and dollars spent.

    model writes the notes and reviews the questions; questions_model writes the questions.

    materials: lecture files (lecturebot.materials.Material). parts: (start_seconds, title) of each
    recording when several were joined. on_section(section) is called as each summary section is written.
    """
    content = _content(segments, major, images, duration, materials or [], parts)
    questions: dict = {}
    usage: dict = {}
    failure: list[Exception] = []

    def ask_questions():
        try:
            data, u = _call(QUESTIONS_SYSTEM, content, QUESTIONS_SCHEMA, model=questions_model or model)
            questions.update(data)
            questions["_q_usage"] = u
        except Exception as e:  # reported after the notes are done
            failure.append(e)

    worker = threading.Thread(target=ask_questions, daemon=True)
    worker.start()
    sections = _SectionStream(on_section) if on_section else None
    result, u = _call(NOTES_SYSTEM, content, NOTES_SCHEMA, sections.feed if sections else None, model=model)
    add_usage(usage, u)
    if not result.get("sections"):  # a summary file without a summary is worthless: try once more
        result, u = _call(NOTES_SYSTEM, content, NOTES_SCHEMA, model=model)
        add_usage(usage, u)
        if not result.get("sections"):
            raise AnalysisError("The notes came back without a summary")
    worker.join()
    if failure:
        raise failure[0] if isinstance(failure[0], AnalysisError) else AnalysisError(str(failure[0]))
    add_usage(usage, questions.pop("_q_usage"))
    result.update(questions)
    source_text = _transcript_text(segments) + "\n" + "\n".join(m.text for m in (materials or []) if m.text)
    _clean(result, source_text)
    if (questions_model or model) != (model or config.CLAUDE_MODEL) or config.REVIEW_ALWAYS:
        add_usage(usage, _review(result, model))
    if config.DEFINE_TERMS:
        add_usage(usage, define_terms(result, model))
    result["_usage"] = usage
    return result


DEFINE_SYSTEM = """You find definitions of technical terms in trusted reference sources, for university \
students. The lecturer used these terms without defining them.

For each term, search the web (only the trusted sites are available to you) and find where a source \
defines it, in the sense of the course and the lecture given to you. Prefer Arabic sources when the \
term is Arabic.

Rules:
- definition: copy the source's own words exactly, one to three sentences (at most 60 words). Do not \
paraphrase, translate, summarise or combine sources.
- url: the exact address of the search result the definition is copied from. source: the name of the \
site or book, for example "الدرر السنية" or "MSD Manual".
- If you cannot find a definition of the term in this sense in the results, give an empty definition, \
url and source. Never write a definition from your own knowledge: an empty answer is better than one \
without a source.

When you are done, reply with only a JSON array, no other text:
[{"term": "...", "definition": "...", "source": "...", "url": "..."}]"""


WEB_SEARCH_DOLLARS = 0.01  # $10 per 1,000 searches


def _norm_url(url: str) -> str:
    return (url or "").split("#")[0].rstrip("/").replace("http://", "https://").replace("://www.", "://")


def define_terms(result: dict, model: str | None = None) -> dict:
    """Look up, on the trusted sites of the lecture's field, the terms the lecturer did not define.
    A definition is kept only when its url is one the search actually returned. Returns the usage."""
    terms = [g for g in result.get("glossary", []) if not g.get("explanation") and g.get("term")]
    terms = terms[: config.DEFINE_TERMS_MAX]
    if not terms:
        return {}
    domains = FIELDS.get(result.get("field") or "general", FIELDS["general"])
    model = model or config.CLAUDE_MODEL
    ask = (f"المادة: {result.get('subject', '')}\nعنوان المحاضرة: {result.get('title', '')}\n"
           f"نبذة: {result.get('overview', '')}\n\nالمصطلحات:\n" + "\n".join(f"- {g['term']}" for g in terms))
    messages = [{"role": "user", "content": ask}]
    client = anthropic.Anthropic()
    usage, found_urls, text = {}, set(), ""
    try:
        for _ in range(4):  # the server's search loop can pause; resume it a few times
            message = client.beta.messages.create(
                model=model, max_tokens=16000, system=DEFINE_SYSTEM, messages=messages,
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                tools=[{"type": "web_search_20260209", "name": "web_search", "allowed_domains": domains,
                        "max_uses": min(40, 2 * len(terms))}],
                output_config={"effort": config.DEFINE_EFFORT})
            u = cost_of(message.usage, getattr(message, "model", None) or model)
            searches = getattr(getattr(message.usage, "server_tool_use", None), "web_search_requests", 0) or 0
            u["cost"] = round(u["cost"] + searches * WEB_SEARCH_DOLLARS, 4)
            add_usage(usage, u)
            for block in message.content:
                if block.type == "web_search_tool_result" and isinstance(block.content, list):
                    found_urls |= {_norm_url(r.url) for r in block.content if getattr(r, "url", None)}
                elif block.type == "text":
                    text += block.text
            if message.stop_reason != "pause_turn":
                break
            messages = messages[:1] + [{"role": "assistant", "content": message.content}]
            text = ""
    except (anthropic.APIError, ValueError) as e:  # definitions are extra: the lecture goes out without them
        import logging
        logging.getLogger(__name__).warning("term lookup skipped: %s", e)
        return usage
    start, end = text.find("["), text.rfind("]")
    try:
        answers = json.loads(text[start:end + 1]) if start >= 0 else []
    except json.JSONDecodeError:
        answers = []
    by_term = {(a.get("term") or "").strip(): a for a in answers if isinstance(a, dict)}
    for g in terms:
        a = by_term.get(g["term"].strip()) or {}
        if a.get("definition") and _norm_url(a.get("url", "")) in found_urls:
            g["source_definition"] = {"text": a["definition"].strip(), "source": (a.get("source") or "").strip(),
                                      "url": a["url"].strip()}
    return usage


def _review(result: dict, model: str | None) -> dict:
    """Let the notes model check the questions written by the (cheaper) questions model; drop the doubtful ones."""
    items = {"mcq": [{"question": q["question"], "options": q["options"], "answer": q["options"][q["answer_index"]],
                      "quote": q.get("evidence", "")} for q in result.get("mcq", [])],
             "true_false": [{"statement": t["statement"], "answer": t["answer"], "quote": t.get("evidence", "")}
                            for t in result.get("true_false", [])],
             "essay": [{"question": e["question"], "model_answer": e["model_answer"], "quote": e.get("evidence", "")}
                       for e in result.get("essay", [])],
             "flashcards": [{"front": c["front"], "back": c["back"]} for c in result.get("flashcards", [])]}
    outline = [{"heading": s.get("heading", ""), "points": [p.get("text", "") for p in s.get("points", [])]}
               for s in result.get("sections", [])]
    payload = {"outline": outline, "items": {k: [dict(v, index=i) for i, v in enumerate(vs)] for k, vs in items.items()}}
    client = anthropic.Anthropic()
    try:
        message = client.beta.messages.create(
            model=model or config.CLAUDE_MODEL, max_tokens=16000, system=REVIEW_SYSTEM,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            output_config={"effort": config.REVIEW_EFFORT, "format": {"type": "json_schema", "schema": REVIEW_SCHEMA}},
        )
        if message.stop_reason != "end_turn":
            return {}
        verdicts = json.loads("".join(b.text for b in message.content if b.type == "text"))["verdicts"]
    except (anthropic.APIError, json.JSONDecodeError, KeyError) as e:  # the review is a safety net, not a must
        import logging
        logging.getLogger(__name__).warning("question review skipped: %s", e)
        return {}
    drop = {(v["kind"], v["index"]) for v in verdicts if not v.get("keep", True)}
    for kind in ("mcq", "true_false", "essay", "flashcards"):
        result[kind] = [item for i, item in enumerate(result.get(kind, [])) if (kind, i) not in drop]
    result["_dropped_by_review"] = len(drop)
    return cost_of(message.usage, getattr(message, "model", None) or model or config.CLAUDE_MODEL)


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
    """True when most words of the quoted evidence occur in the transcript. Without any source text
    (a lecture made only of photos) there is nothing to check against, so everything passes."""
    if not transcript_words:
        return True
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
    result["comparisons"] = [c for c in comps if supported(c.get("evidence", ""), tw)]
    result["divisions"] = [d for d in result.get("divisions", []) if len(d.get("branches", [])) >= 2
                           and supported(d.get("evidence", ""), tw)]
    result["processes"] = [p for p in result.get("processes", []) if len(p.get("steps", [])) >= 2
                           and supported(p.get("evidence", ""), tw)]
    # A definition only counts as the lecturer's when his words are really in the transcript.
    for g in result.get("glossary", []):
        if not g.get("defined_by_lecturer") or not supported(g.get("definition_quote", ""), tw):
            g["defined_by_lecturer"], g["explanation"], g["definition_quote"] = False, "", ""
    # The model sometimes copies the transcript's "[mm:ss]" brackets into time fields.
    items = (result.get("sections", []) + result["mcq"] + result["true_false"] + result["essay"] + comps
             + result["divisions"] + result["processes"] + result.get("glossary", []) + [pt for sec in result.get("sections", []) for pt in sec.get("points", [])])
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
