"""Build the study PDF from the analysis and transcript: Arabic (right to left) or English (left to right)."""
import base64
import datetime as dt
from html import escape
from pathlib import Path

from . import config, mindmap
from .media import fmt_time, parse_time, timestamp_url
from .transcribe import Segment

CSS = """
@font-face { font-family: Cairo; src: url("FONTS/Cairo-400.ttf"); font-weight: 400; }
@font-face { font-family: Cairo; src: url("FONTS/Cairo-700.ttf"); font-weight: 700; }
@page { size: A4; margin: 18mm 16mm 20mm 16mm;
        @bottom-center { content: "صفحة " counter(page) " من " counter(pages); font-family: Cairo; font-size: 9pt; color: #7a8796; } }
html { direction: rtl; }
body { font-family: Cairo, sans-serif; font-size: 11pt; line-height: 1.75; color: #1d2733; }
h1 { font-size: 22pt; line-height: 1.35; margin: 0 0 6pt; color: #143f62; }
h2 { font-size: 15pt; color: #143f62; border-bottom: 2pt solid #e3b448; padding-bottom: 3pt; margin: 22pt 0 10pt;
     page-break-after: avoid; }
h3 { font-size: 12.5pt; margin: 14pt 0 4pt; color: #1d2733; page-break-after: avoid; }
.meta { color: #5b6876; font-size: 10pt; }
.overview { background: #f3f6f9; border-right: 4pt solid #143f62; padding: 8pt 12pt; margin: 12pt 0; }
.t { display: inline-block; direction: ltr; font-size: 8.5pt; font-weight: 700; color: #143f62; background: #e8eef4;
     border-radius: 3pt; padding: 0 4pt; margin-inline-start: 4pt; text-decoration: none; }
ul { margin: 0; padding-right: 16pt; }
li { margin: 2pt 0; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0; font-size: 10pt; }
th, td { border: 0.6pt solid #cfd8e1; padding: 4pt 6pt; vertical-align: top; text-align: right; }
th { background: #143f62; color: #fff; font-weight: 700; }
tr:nth-child(even) td { background: #f7f9fb; }
.en { direction: ltr; unicode-bidi: isolate; font-weight: 700; }
.q { page-break-inside: avoid; margin: 0 0 10pt; }
.q ul { margin: 2pt 0 0; padding-right: 6pt; list-style: none; }
.opt { font-weight: 700; color: #143f62; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
.answers td:first-child { width: 12%; text-align: center; }
.cards td { width: 50%; }
.para { margin: 0 0 6pt; text-align: justify; }
.division { page-break-inside: avoid; margin-bottom: 10pt; }
img.mindmap { max-width: 100%; max-height: 95mm; border: 0.6pt solid #cfd8e1; border-radius: 6pt; }
.answer { background: #f3f6f9; border-radius: 4pt; padding: 6pt 10pt; margin-top: 4pt; font-size: 10.5pt; }
.compare td:first-child { background: #eef3f8; width: 22%; }
.cover-note { font-size: 9pt; color: #7a8796; margin-top: 4pt; }
.kind { display: inline-block; background: #e3b448; color: #143f62; font-weight: 700; font-size: 10pt;
        border-radius: 3pt; padding: 1pt 8pt; margin-bottom: 4pt; }
.process { page-break-inside: avoid; margin-bottom: 12pt; }
.step { border: 1pt solid #143f62; background: #f3f6f9; border-radius: 6pt; padding: 5pt 10pt; margin: 0 14%; }
.step .num { display: inline-block; background: #143f62; color: #fff; font-weight: 700; border-radius: 50%;
             min-width: 14pt; text-align: center; margin-inline-end: 4pt; }
.arrow { text-align: center; color: #e3b448; font-size: 12pt; line-height: 1.2; }
.cycle { text-align: center; font-weight: 700; color: #143f62; }
.warn { color: #c62828; font-size: 10.5pt; font-weight: 700; text-align: center; margin: -10mm 0 8pt; }
.glossary td.term { font-weight: 700; width: 24%; }
tr.pb { break-before: page; }
.glossary .none { color: #7a8796; }
@page { @footnote { border-top: 0.6pt solid #cfd8e1; padding-top: 3pt; } }
.fn { float: footnote; font-size: 8.5pt; line-height: 1.5; color: #4a5866; }
.fn a { color: #143f62; word-break: break-all; }
.fn::footnote-call { content: attr(data-n); vertical-align: super; font-size: 7.5pt; font-weight: 700; color: #7a5b00; }
.fn::footnote-marker { content: attr(data-n) ". "; font-weight: 700; }
.term-hl { color: #2e7d32; font-weight: 700; }
.def-hl { background: #e6e9ed; border-radius: 2pt; }
"""

# Left-to-right version of the stylesheet for the English PDF.
CSS_EN = """
@page { @bottom-center { content: "Page " counter(page) " of " counter(pages); } }
html { direction: ltr; }
.overview { border-right: 0; border-left: 4pt solid #143f62; }
ul { padding-right: 0; padding-left: 16pt; }
.q ul { padding-right: 0; padding-left: 6pt; }
th, td { text-align: left; }
"""

LABELS = {
    "ar": {"summary_title": "ملخص المحاضرة", "duration": "المدة", "source": "المصدر",
           "times_note": "الأرقام بجانب النقاط هي وقت شرحها في التسجيل.", "summary": "الملخص",
           "mindmap": "التقسيمات", "comparisons": "جداول المقارنة", "essay": "أسئلة مقالية",
           "model_answer": "نموذج الإجابة", "glossary": "المصطلحات",
           "term": "المصطلح", "arabic": "بالعربية", "meaning": "المعنى", "mcq": "أسئلة الاختيار من متعدد",
           "answers": "الإجابات", "question": "السؤال", "answer_expl": "الإجابة والشرح", "tf": "أسئلة صح أو خطأ",
           "true": "صح", "false": "خطأ", "cards": "بطاقات المراجعة", "card_q": "السؤال", "card_a": "الجواب",
           "transcript": "النص الكامل", "letters": "أبجدهوزحطي",
           "processes": "المراحل والخطوات", "back_to": "ثم تعود الدورة إلى:", "definition": "التعريف",
           "glossary_note": "تعريف المحاضر مكتوب كما ذكره، وما لم يعرّفه نُقل تعريفه من مصدر موثوق "
           "ومرجعه في حاشية الصفحة، وما لم يُعثر له على تعريف موثوق وُضع أمامه خط.",
           "transcript_note": "المصطلحات ملوّنة بالأخضر، وتعريف المحاضر لها مظلَّل بالرمادي.",
           "visuals_warning": "صُممت هذه التقاسيم بـAI بالاعتماد على ما أرسلته، والخطأ وارد، فتنبّه."},
    "en": {"summary_title": "Lecture summary", "duration": "Duration", "source": "Source",
           "times_note": "The times next to each point show where it is explained in the recording.",
           "summary": "Summary", "mindmap": "Classifications", "comparisons": "Comparison tables",
           "glossary": "Glossary", "essay": "Essay questions", "model_answer": "Model answer",
           "term": "Term", "arabic": "Arabic", "meaning": "Meaning", "mcq": "Multiple-choice questions",
           "answers": "Answers", "question": "Question", "answer_expl": "Answer and explanation",
           "tf": "True or false", "true": "True", "false": "False", "cards": "Flashcards", "card_q": "Question",
           "card_a": "Answer", "transcript": "Full transcript", "letters": "ABCDEFGHIJ",
           "processes": "Stages and steps", "back_to": "Then the cycle returns to:", "definition": "Definition",
           "glossary_note": "", "transcript_note": "",
           "visuals_warning": "These diagrams were made by AI from your lecture and may contain mistakes."},
}



def _dir(text: str) -> str:
    """Questions of a lecture taught in English read left to right inside the Arabic page."""
    latin = sum(c.isascii() and c.isalpha() for c in text)
    arabic = sum("\u0600" <= c <= "\u06ff" for c in text)
    return ' dir="ltr"' if latin > 2 * arabic else ""

def _letter(i: int, letters: str = LABELS["ar"]["letters"]) -> str:
    return letters[i] if i < len(letters) else str(i + 1)


def _t(time_text: str, source_url: str) -> str:
    label = escape(time_text or "")
    if not label:
        return ""
    url = timestamp_url(source_url, parse_time(time_text))
    if url:
        return f'<a class="t" href="{escape(url)}">{label}</a>'
    return f'<span class="t">{label}</span>'


def _header(result: dict, L: dict, source_title: str, duration: float, kind_title: str = "") -> list[str]:
    e = escape
    title = result.get("title") or source_title or L["summary_title"]
    parts = [f'<div class="kind">{e(kind_title)}</div>' if kind_title else "", f"<h1>{e(title)}</h1>"]
    meta = [m for m in (result.get("subject"), f"{L['duration']} {fmt_time(duration)}" if duration else "",
                        dt.date.today().strftime("%Y-%m-%d")) if m]
    parts.append(f'<div class="meta">{" · ".join(e(m) for m in meta)}</div>')
    if source_title and source_title != result.get("title"):
        parts.append(f'<div class="meta">{L["source"]}: {e(source_title)}</div>')
    return parts


def _summary(result: dict, L: dict, source_url: str) -> list[str]:
    e, parts = escape, []
    if result.get("overview"):
        parts.append(f'<div class="overview">{e(result["overview"])}</div>')
    parts.append(f'<div class="cover-note">{L["times_note"]}</div>')
    parts.append(f"<h2>{L['summary']}</h2>")
    for sec in result.get("sections", []):
        parts.append(f"<h3>{e(sec.get('heading', ''))} {_t(sec.get('time', ''), source_url)}</h3><ul>")
        for p in sec.get("points", []):
            parts.append(f"<li>{e(p.get('text', ''))} {_t(p.get('time', ''), source_url)}</li>")
        parts.append("</ul>")
    return parts


def _visuals(result: dict, L: dict, source_url: str, lang: str) -> list[str]:
    """Classification trees, step-by-step processes and comparison tables: only what the lecturer stated."""
    e, parts = escape, []
    divisions = result.get("divisions") or []
    if divisions:
        parts.append(f'<h2>{L["mindmap"]}</h2>')
        for d in divisions:
            png = mindmap.render_png(d, rtl=lang == "ar")
            if png:
                b64 = base64.standard_b64encode(png).decode()
                parts.append(f'<div class="division"><h3>{e(d.get("title", ""))} {_t(d.get("time", ""), source_url)}</h3>'
                             f'<img class="mindmap" src="data:image/png;base64,{b64}"></div>')
    processes = [p for p in result.get("processes") or [] if len(p.get("steps", [])) >= 2]
    if processes:
        parts.append(f'<h2>{L["processes"]}</h2>')
        for p in processes:
            steps = p["steps"]
            flow = '<div class="arrow">⬇</div>'.join(
                f'<div class="step"><span class="num">{i}</span> {e(st)}</div>' for i, st in enumerate(steps, 1))
            if p.get("cyclic"):
                flow += f'<div class="arrow">⬇</div><div class="cycle">↻ {L["back_to"]} {e(steps[0])}</div>'
            parts.append(f'<div class="process"><h3>{e(p.get("title", ""))} {_t(p.get("time", ""), source_url)}</h3>'
                         f'{flow}</div>')
    comps = result.get("comparisons", [])
    if comps:
        parts.append(f"<h2>{L['comparisons']}</h2>")
        for c in comps:
            head = "".join(f"<th>{e(h)}</th>" for h in c["headers"])
            body = "".join("<tr>" + "".join(f"<td>{'<b>' + e(cell) + '</b>' if j == 0 else e(cell)}</td>"
                                            for j, cell in enumerate(r)) + "</tr>" for r in c["rows"])
            parts.append(f'<h3>{e(c["title"])} {_t(c.get("time", ""), source_url)}</h3>'
                         f'<table class="compare"><thead><tr>{head}</tr></thead>{body}</table>')
    return parts


def term_definition(g: dict) -> tuple[str, dict | None]:
    """(definition, source) of a glossary term: the lecturer's own, or one copied from a trusted
    source (with that source), or ("", None) when neither was found."""
    if g.get("explanation"):
        return g["explanation"], None
    src = g.get("source_definition") or {}
    return (src["text"], src) if src.get("text") else ("", None)


def _glossary(result: dict, L: dict, source_url: str = "") -> list[str]:
    e, parts, notes = escape, [], []
    glossary = result.get("glossary") or []
    if not glossary:
        return parts
    with_arabic = any(g.get("arabic") for g in glossary)
    head = f"<th>{L['term']}</th>" + (f"<th>{L['arabic']}</th>" if with_arabic else "") + f"<th>{L['definition']}</th>"
    parts.append(f'<h2>{L["glossary"]}</h2><div class="cover-note">{L["glossary_note"]}</div>'
                 f'<table class="glossary"><thead><tr>{head}</tr></thead>')
    for g in glossary:
        text, src = term_definition(g)
        if src:
            notes.append(src)
            # A footnote at the bottom of its page; write_pdf numbers them from 1 on every page.
            cell = (f'{e(text)}<span class="fn" data-id="{len(notes)}" data-n="{len(notes)}">'
                    f'{e(src.get("source") or "")} <a href="{e(src["url"])}">{e(src["url"])}</a></span>')
        elif text:
            cell = f'{e(text)} {_t(g.get("time", ""), source_url)}'
        else:
            cell = '<span class="none">—</span>'
        row = f'<tr data-fn="{len(notes)}">' if src else "<tr>"
        parts.append(f'{row}<td class="term"{_dir(g.get("term", ""))}>{e(g.get("term", ""))}</td>'
                     + (f'<td>{e(g.get("arabic", ""))}</td>' if with_arabic else "") + f"<td>{cell}</td></tr>")
    parts.append("</table>")
    return parts


def _questions(result: dict, L: dict, source_url: str) -> list[str]:
    e, parts = escape, []
    letter = lambda i: _letter(i, L["letters"])  # noqa: E731
    mcq = result.get("mcq", [])
    if mcq:
        parts.append(f"<h2>{L['mcq']}</h2>")
        for i, q in enumerate(mcq, 1):
            mark = (lambda j: _letter(j, LABELS["en"]["letters"])) if _dir(q["question"]) else letter
            opts = "".join(f'<li><span class="opt">({mark(j)})</span> {e(o)}</li>' for j, o in enumerate(q["options"]))
            parts.append(f'<div class="q"{_dir(q["question"])}><b>{i}. {e(q["question"])}</b><ul>{opts}</ul></div>')
        parts.append(f'<h3>{L["answers"]}</h3><table class="answers"><thead><tr><th>{L["question"]}</th>'
                     f'<th>{L["answer_expl"]}</th></tr></thead>')
        for i, q in enumerate(mcq, 1):
            ans = q["options"][q["answer_index"]]
            mark = (lambda j: _letter(j, LABELS["en"]["letters"])) if _dir(q["question"]) else letter
            parts.append(f"<tr><td>{i}</td><td><b>({mark(q['answer_index'])}) {e(ans)}</b><br>{e(q.get('explanation', ''))} "
                         f"{_t(q.get('time', ''), source_url)}</td></tr>")
        parts.append("</table>")

    tf = result.get("true_false", [])
    if tf:
        parts.append(f"<h2>{L['tf']}</h2>")
        for i, t in enumerate(tf, 1):
            parts.append(f'<div class="q"{_dir(t["statement"])}><b>{i}. {e(t["statement"])}</b> '
                         '<span class="opt">( &nbsp; &nbsp; )</span></div>')
        parts.append(f'<h3>{L["answers"]}</h3><table class="answers"><thead><tr><th>{L["question"]}</th>'
                     f'<th>{L["answer_expl"]}</th></tr></thead>')
        for i, t in enumerate(tf, 1):
            verdict = L["true"] if t["answer"] else L["false"]
            parts.append(f"<tr><td>{i}</td><td><b>{verdict}</b><br>{e(t.get('explanation', ''))} "
                         f"{_t(t.get('time', ''), source_url)}</td></tr>")
        parts.append("</table>")

    essays = result.get("essay", [])
    if essays:
        parts.append(f"<h2>{L['essay']}</h2>")
        for i, q in enumerate(essays, 1):
            parts.append(f'<div class="q"{_dir(q["question"])}><b>{i}. {e(q["question"])}</b> '
                         f'{_t(q.get("time", ""), source_url)}<div class="answer"><b>{L["model_answer"]}:</b> '
                         f'{e(q.get("model_answer", ""))}</div></div>')

    cards = result.get("flashcards", [])
    if cards:
        parts.append(f'<h2>{L["cards"]}</h2><table class="cards"><thead><tr><th>{L["card_q"]}</th>'
                     f'<th>{L["card_a"]}</th></tr></thead>')
        for c in cards:
            parts.append(f"<tr><td>{e(c.get('front', ''))}</td><td>{e(c.get('back', ''))}</td></tr>")
        parts.append("</table>")
    return parts


def _marked(text: str, terms: list[str], quotes: list[str]) -> str:
    """The paragraph with the lecture's terms in green and the lecturer's definitions shaded."""
    low = text.lower()
    shade, green = [False] * len(text), [False] * len(text)
    for q in quotes:
        i = text.find(q)
        if i >= 0:
            shade[i:i + len(q)] = [True] * len(q)
    for t in terms:
        i = low.find(t)
        while i >= 0:
            green[i:i + len(t)] = [True] * len(t)
            i = low.find(t, i + len(t))
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and (shade[j], green[j]) == (shade[i], green[i]):
            j += 1
        chunk = escape(text[i:j])
        if green[i]:
            chunk = f'<span class="term-hl">{chunk}</span>'
        if shade[i]:
            chunk = f'<span class="def-hl">{chunk}</span>'
        out.append(chunk)
        i = j
    return "".join(out)


def _transcript(paragraphs: list[Segment], L: dict, source_url: str, glossary: list | None = None) -> list[str]:
    if not paragraphs:
        return []
    terms = sorted({(g.get("term") or "").strip().lower() for g in glossary or []} - {""}, key=len, reverse=True)
    terms = [t for t in terms if len(t) >= 3]
    quotes = [g["definition_quote"].strip() for g in glossary or [] if (g.get("definition_quote") or "").strip()]
    head = [f"<h2>{L['transcript']}</h2>"]
    if terms:
        head.append(f'<div class="cover-note">{L["transcript_note"]}</div>')
    return head + [f'<p class="para">{_t(fmt_time(p.start), source_url)} {_marked(p.text, terms, quotes)}</p>'
                   for p in paragraphs]


def _page(parts: list[str], lang: str = "ar") -> str:
    css = CSS.replace("FONTS/", config.FONTS_DIR.as_uri() + "/") + (CSS_EN if lang == "en" else "")
    direction = "rtl" if lang == "ar" else "ltr"
    return f'<!doctype html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8"><style>{css}</style>' \
           f'</head><body>{"".join(parts)}</body></html>'


def build_html(result: dict, paragraphs: list[Segment], source_title: str = "", source_url: str = "",
               duration: float = 0.0, lang: str = "ar") -> str:
    """Everything in one document (the English version)."""
    L = LABELS[lang]
    return _page(_header(result, L, source_title, duration) + _summary(result, L, source_url)
                 + _visuals(result, L, source_url, lang) + _glossary(result, L) + _questions(result, L, source_url)
                 + _transcript(paragraphs, L, source_url), lang)


# The files a student gets for each lecture, in the order they are sent.
FILES = (("summary", "الملخص"), ("questions", "الأسئلة"), ("glossary", "المصطلحات"), ("visuals", "الرسوم التوضيحية"))


def build_files(result: dict, paragraphs: list[Segment], source_title: str = "", source_url: str = "",
                duration: float = 0.0) -> dict[str, str]:
    """kind -> HTML of each file the lecture has content for (see FILES)."""
    L = LABELS["ar"]
    visuals = _visuals(result, L, source_url, "ar")
    bodies = {"summary": _summary(result, L, source_url) + _transcript(paragraphs, L, source_url,
                                                                       result.get("glossary")),
              "questions": _questions(result, L, source_url),
              "glossary": _glossary(result, L, source_url),
              "visuals": visuals}
    names = dict(FILES)
    return {kind: _page(([f'<div class="warn">{L["visuals_warning"]}</div>'] if kind == "visuals" else [])
                        + _header(result, L, source_title, duration, names[kind]) + body)
            for kind, body in bodies.items() if body}


def _number_footnotes_per_page(html: str) -> str:
    """Number footnotes from 1 on every page. The document is laid out to see where each footnote
    falls; a row whose footnote would be pushed to the next page starts that page instead, so a
    number and its note are always on the same page."""
    import re
    from weasyprint import HTML

    def walk(box):
        yield box
        for child in getattr(box, "children", None) or []:
            yield from walk(child)

    for _ in range(8):
        calls, notes = {}, {}
        for i, page in enumerate(HTML(string=html, base_url=str(config.BASE_DIR)).render().pages):
            areas = [b for b in walk(page._page_box) if type(b).__name__ == "FootnoteAreaBox"]
            in_area = {id(b) for a in areas for b in walk(a)}
            for box in walk(page._page_box):
                el = getattr(box, "element", None)
                if el is not None and el.get("class") == "fn":
                    (notes if id(box) in in_area else calls).setdefault(el.get("data-id"), i)
        late = [k for k, page in calls.items() if notes.get(k, page) != page]
        if not late:
            break
        k = min(late, key=int)
        html = html.replace(f'<tr data-fn="{k}">', f'<tr data-fn="{k}" class="pb">', 1)
    numbers, count = {}, {}
    for k in sorted(notes, key=int):
        count[notes[k]] = count.get(notes[k], 0) + 1
        numbers[k] = count[notes[k]]
    return re.sub(r'data-id="(\d+)" data-n="\d+"',
                  lambda m: f'data-id="{m.group(1)}" data-n="{numbers.get(m.group(1), m.group(1))}"', html)


def write_pdf(html: str, out_path: Path) -> Path:
    from weasyprint import HTML

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if 'class="fn"' in html:
        html = _number_footnotes_per_page(html)
    HTML(string=html, base_url=str(config.BASE_DIR)).write_pdf(str(out_path))
    return out_path


def transcript_txt(paragraphs: list[Segment]) -> str:
    return "\n\n".join(f"[{fmt_time(p.start)}] {p.text}" for p in paragraphs)


def build_exam_html(summary: dict, lecture_titles: list[str]) -> str:
    """The exam-night summary across several lectures."""
    e = escape
    parts = [f"<h1>{e(summary.get('title') or 'ملخص ليلة الاختبار')}</h1>",
             f'<div class="meta">{len(lecture_titles)} محاضرة · {dt.date.today().strftime("%Y-%m-%d")}</div>']
    if summary.get("overview"):
        parts.append(f'<div class="overview">{e(summary["overview"])}</div>')
    parts.append('<div class="cover-note">المحاضرات: ' + "، ".join(e(t) for t in lecture_titles) + "</div>")

    parts.append("<h2>أهم الأفكار</h2>")
    for t in summary.get("topics", []):
        src = f' <span class="t">{e(t["lecture"])}</span>' if t.get("lecture") else ""
        parts.append(f"<h3>{e(t.get('heading', ''))}{src}</h3><ul>"
                     + "".join(f"<li>{e(p)}</li>" for p in t.get("points", [])) + "</ul>")
    if summary.get("must_memorize"):
        parts.append("<h2>احفظها جيداً</h2><table><thead><tr><th>العنصر</th><th>التفصيل</th></tr></thead>"
                     + "".join(f"<tr><td><b>{e(m['item'])}</b></td><td>{e(m['detail'])}</td></tr>"
                               for m in summary["must_memorize"]) + "</table>")
    if summary.get("pitfalls"):
        parts.append("<h2>انتبه: نقاط يخلط فيها الطلاب</h2><ul>"
                     + "".join(f"<li>{e(p)}</li>" for p in summary["pitfalls"]) + "</ul>")
    if summary.get("self_test"):
        parts.append("<h2>اختبر نفسك</h2>")
        parts += [f'<div class="q"><b>{i}. {e(q["question"])}</b></div>' for i, q in enumerate(summary["self_test"], 1)]
        parts.append('<h3>الإجابات</h3><table class="answers"><thead><tr><th>السؤال</th><th>الإجابة</th></tr></thead>'
                     + "".join(f"<tr><td>{i}</td><td>{e(q['answer'])}</td></tr>"
                               for i, q in enumerate(summary["self_test"], 1)) + "</table>")
    css = CSS.replace("FONTS/", config.FONTS_DIR.as_uri() + "/")
    return f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{css}</style></head>' \
           f'<body>{"".join(parts)}</body></html>'
