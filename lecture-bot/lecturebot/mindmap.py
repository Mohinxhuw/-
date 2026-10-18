"""Draw a classification the lecturer made: the thing being divided, its parts, and their sub-parts,
as a one-sided tree (the whole on the right, its parts to its left, in Arabic reading order).

Boxes are HTML (so WeasyPrint shapes the Arabic text properly) placed at computed positions, with the
connecting curves drawn as SVG underneath. The page itself is left-to-right because WeasyPrint misplaces
absolutely positioned boxes in a right-to-left page; the text inside each box is right-to-left. Rendered to PNG for Telegram and for the study PDF.
"""
import math
from html import escape

from . import config

MARGIN = 40
CENTER_W, BRANCH_W, CHILD_W = 300, 290, 300
GAP_X, GAP_Y, CHILD_GAP = 70, 34, 12
COLORS = ["#2a6f97", "#c0841a", "#2f8f6f", "#8a4f9e", "#b5523b", "#3f6fb5", "#7a8a1f", "#a3466e"]
NAVY, GOLD = "#143f62", "#e3b448"


def _height(text: str, width: int, size: int) -> int:
    """Rough box height: Cairo at this size fits about width/(0.55*size) characters per line."""
    per_line = max(8, int((width - 28) / (size * 0.55)))
    lines = max(1, math.ceil(len(text) / per_line))
    return int(lines * size * 1.55 + 22)


def _layout(data: dict):
    out, total = [], 0
    for b in [b for b in data.get("branches", []) if b.get("label")][:10]:
        bh = _height(b["label"], BRANCH_W, 24)
        kids = [(c, _height(c, CHILD_W, 19)) for c in b.get("children", [])[:6] if c]
        kh = sum(h for _, h in kids) + CHILD_GAP * max(0, len(kids) - 1)
        out.append((b, bh, kids, max(bh, kh)))
        total += max(bh, kh)
    total += GAP_Y * max(0, len(out) - 1)
    return out, total


def build_html(data: dict, rtl: bool = True) -> str:
    items, total = _layout(data)
    has_kids = any(kids for _, _, kids, _ in items)
    W = 2 * MARGIN + CENTER_W + GAP_X + BRANCH_W + ((GAP_X + CHILD_W) if has_kids else 0)
    center = data.get("center") or ""
    ch = _height(center, CENTER_W, 30)
    H = max(total, ch) + 2 * MARGIN + 30
    sign = -1 if rtl else 1  # parts grow to the left in Arabic, to the right in English
    cx = W - MARGIN - CENTER_W / 2 if rtl else MARGIN + CENTER_W / 2
    cy = H / 2
    boxes = [f'<div class="node center" style="left:{cx - CENTER_W / 2}px;top:{cy - ch / 2}px;width:{CENTER_W}px;'
             f'height:{ch}px">{escape(center)}</div>']
    paths = []
    bx = cx + sign * (CENTER_W / 2 + GAP_X + BRANCH_W / 2)
    kx = bx + sign * (BRANCH_W / 2 + GAP_X + CHILD_W / 2)
    y = cy - total / 2
    for color_i, (b, bh, kids, block_h) in enumerate(items):
        color = COLORS[color_i % len(COLORS)]
        by = y + block_h / 2
        boxes.append(f'<div class="node branch" style="left:{bx - BRANCH_W / 2}px;top:{by - bh / 2}px;'
                     f'width:{BRANCH_W}px;height:{bh}px;background:{color}">{escape(b["label"])}</div>')
        x0, x1 = cx + sign * CENTER_W / 2, bx - sign * BRANCH_W / 2
        paths.append(f'<path d="M{x0} {cy} C{(x0 + x1) / 2} {cy} {(x0 + x1) / 2} {by} {x1} {by}" '
                     f'stroke="{color}" stroke-width="6" fill="none" stroke-linecap="round"/>')
        kh_total = sum(h for _, h in kids) + CHILD_GAP * max(0, len(kids) - 1)
        ky = by - kh_total / 2
        for text, h in kids:
            mid = ky + h / 2
            boxes.append(f'<div class="node child" style="left:{kx - CHILD_W / 2}px;top:{ky}px;width:{CHILD_W}px;'
                         f'height:{h}px;border-color:{color}">{escape(text)}</div>')
            a, c = bx + sign * BRANCH_W / 2, kx - sign * CHILD_W / 2
            paths.append(f'<path d="M{a} {by} C{(a + c) / 2} {by} {(a + c) / 2} {mid} {c} {mid}" '
                         f'stroke="{color}" stroke-width="3" fill="none" opacity=".7"/>')
            ky += h + CHILD_GAP
        y += block_h + GAP_Y
    fonts = config.FONTS_DIR.as_uri()
    return f"""<!doctype html><html lang="ar"><head><meta charset="utf-8"><style>
@font-face {{ font-family: Cairo; src: url("{fonts}/Cairo-400.ttf"); font-weight: 400; }}
@font-face {{ font-family: Cairo; src: url("{fonts}/Cairo-700.ttf"); font-weight: 700; }}
@page {{ size: {W}px {H}px; margin: 0; }}
html, body {{ margin: 0; }}
body {{ width: {W}px; height: {H}px; position: relative; background: #f6f8fb; font-family: Cairo; }}
svg {{ position: absolute; left: 0; top: 0; }}
.node {{ position: absolute; box-sizing: border-box; display: flex; align-items: center; justify-content: center;
         text-align: center; padding: 8px 14px; direction: {'rtl' if rtl else 'ltr'}; border-radius: 16px; line-height: 1.5; }}
.center {{ background: {NAVY}; color: #fff; font-size: 30px; font-weight: 700; border: 5px solid {GOLD}; }}
.branch {{ color: #fff; font-size: 24px; font-weight: 700; }}
.child {{ background: #fff; color: #1d2733; font-size: 19px; border: 2.5px solid; }}
.brand {{ direction: rtl; position: absolute; {"left" if rtl else "right"}: 18px; bottom: 10px; font-size: 18px; color: #9aa7b4; font-weight: 700; }}
</style></head><body>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{''.join(paths)}</svg>
{''.join(boxes)}
<div class="brand">فَهيم</div>
</body></html>"""


def render_png(data: dict, width_px: int = 2400, rtl: bool = True) -> bytes:
    """PNG of the mind map (empty bytes if there is nothing to draw)."""
    if not data or not data.get("branches"):
        return b""
    import io

    import pypdfium2
    from weasyprint import HTML

    pdf = HTML(string=build_html(data, rtl)).write_pdf()
    page = pypdfium2.PdfDocument(pdf)[0]
    img = page.render(scale=width_px / page.get_width()).to_pil()
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
