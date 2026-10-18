"""Build the study PDF (right-to-left Arabic) from the analysis and transcript."""
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
@page wide { size: A4 landscape; margin: 12mm 14mm 16mm 14mm; }
.mmpage { page: wide; page-break-before: always; page-break-after: always; text-align: center; }
.mmpage h2 { text-align: right; margin-top: 0; }
img.mindmap { max-width: 100%; max-height: 160mm; border: 0.6pt solid #cfd8e1; border-radius: 6pt; }
.compare td:first-child { background: #eef3f8; width: 22%; }
.cover-note { font-size: 9pt; color: #7a8796; margin-top: 4pt; }
"""

LETTERS = "أبجدهوزحطي"


def _letter(i: int) -> str:
    return LETTERS[i] if i < len(LETTERS) else str(i + 1)


def _t(time_text: str, source_url: str) -> str:
    label = escape(time_text or "")
    if not label:
        return ""
    url = timestamp_url(source_url, parse_time(time_text))
    if url:
        return f'<a class="t" href="{escape(url)}">{label}</a>'
    return f'<span class="t">{label}</span>'


def build_html(result: dict, paragraphs: list[Segment], source_title: str = "", source_url: str = "",
               duration: float = 0.0) -> str:
    e = escape
    parts = [f"<h1>{e(result.get('title') or source_title or 'ملخص المحاضرة')}</h1>"]
    meta = [m for m in (result.get("subject"), f"المدة {fmt_time(duration)}" if duration else "",
                        dt.date.today().strftime("%Y-%m-%d")) if m]
    parts.append(f'<div class="meta">{" · ".join(e(m) for m in meta)}</div>')
    if source_title and source_title != result.get("title"):
        parts.append(f'<div class="meta">المصدر: {e(source_title)}</div>')
    if result.get("overview"):
        parts.append(f'<div class="overview">{e(result["overview"])}</div>')
    parts.append('<div class="cover-note">الأرقام بجانب النقاط هي وقت شرحها في التسجيل.</div>')

    parts.append("<h2>الملخص</h2>")
    for sec in result.get("sections", []):
        parts.append(f"<h3>{e(sec.get('heading', ''))} {_t(sec.get('time', ''), source_url)}</h3><ul>")
        for p in sec.get("points", []):
            parts.append(f"<li>{e(p.get('text', ''))} {_t(p.get('time', ''), source_url)}</li>")
        parts.append("</ul>")

    mm_png = mindmap.render_png(result.get("mindmap") or {})
    if mm_png:
        b64 = base64.standard_b64encode(mm_png).decode()
        parts.append(f'<div class="mmpage"><h2>الخريطة الذهنية</h2>'
                     f'<img class="mindmap" src="data:image/png;base64,{b64}"></div>')

    comps = result.get("comparisons", [])
    if comps:
        parts.append("<h2>جداول المقارنة</h2>")
        for c in comps:
            head = "".join(f"<th>{e(h)}</th>" for h in c["headers"])
            body = "".join("<tr>" + "".join(f"<td>{'<b>' + e(cell) + '</b>' if j == 0 else e(cell)}</td>"
                                            for j, cell in enumerate(r)) + "</tr>" for r in c["rows"])
            parts.append(f'<h3>{e(c["title"])} {_t(c.get("time", ""), source_url)}</h3>'
                         f'<table class="compare"><thead><tr>{head}</tr></thead>{body}</table>')

    if result.get("glossary"):
        parts.append("<h2>المصطلحات</h2><table><thead><tr><th>المصطلح</th><th>بالعربية</th><th>المعنى</th></tr></thead>")
        for g in result["glossary"]:
            parts.append(f'<tr><td class="en">{e(g.get("term", ""))}</td><td>{e(g.get("arabic", ""))}</td>'
                         f'<td>{e(g.get("explanation", ""))}</td></tr>')
        parts.append("</table>")

    mcq = result.get("mcq", [])
    if mcq:
        parts.append("<h2>أسئلة الاختيار من متعدد</h2>")
        for i, q in enumerate(mcq, 1):
            opts = "".join(f'<li><span class="opt">({_letter(j)})</span> {e(o)}</li>' for j, o in enumerate(q["options"]))
            parts.append(f'<div class="q"><b>{i}. {e(q["question"])}</b><ul>{opts}</ul></div>')
        parts.append('<h3>الإجابات</h3><table class="answers"><thead><tr><th>السؤال</th><th>الإجابة والشرح</th></tr></thead>')
        for i, q in enumerate(mcq, 1):
            ans = q["options"][q["answer_index"]]
            parts.append(f"<tr><td>{i}</td><td><b>({_letter(q['answer_index'])}) {e(ans)}</b><br>{e(q.get('explanation', ''))} "
                         f"{_t(q.get('time', ''), source_url)}</td></tr>")
        parts.append("</table>")

    tf = result.get("true_false", [])
    if tf:
        parts.append("<h2>أسئلة صح أو خطأ</h2>")
        for i, t in enumerate(tf, 1):
            parts.append(f'<div class="q"><b>{i}. {e(t["statement"])}</b> <span class="opt">( &nbsp; &nbsp; )</span></div>')
        parts.append('<h3>الإجابات</h3><table class="answers"><thead><tr><th>السؤال</th><th>الإجابة والشرح</th></tr></thead>')
        for i, t in enumerate(tf, 1):
            verdict = "صح" if t["answer"] else "خطأ"
            parts.append(f"<tr><td>{i}</td><td><b>{verdict}</b><br>{e(t.get('explanation', ''))} "
                         f"{_t(t.get('time', ''), source_url)}</td></tr>")
        parts.append("</table>")

    cards = result.get("flashcards", [])
    if cards:
        parts.append('<h2>بطاقات المراجعة</h2><table class="cards"><thead><tr><th>السؤال</th><th>الجواب</th></tr></thead>')
        for c in cards:
            parts.append(f"<tr><td>{e(c.get('front', ''))}</td><td>{e(c.get('back', ''))}</td></tr>")
        parts.append("</table>")

    if paragraphs:
        parts.append("<h2>النص الكامل</h2>")
        for p in paragraphs:
            parts.append(f'<p class="para">{_t(fmt_time(p.start), source_url)} {e(p.text)}</p>')

    css = CSS.replace("FONTS/", config.FONTS_DIR.as_uri() + "/")
    return f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{css}</style></head>' \
           f'<body>{"".join(parts)}</body></html>'


def write_pdf(html: str, out_path: Path) -> Path:
    from weasyprint import HTML

    out_path.parent.mkdir(parents=True, exist_ok=True)
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
