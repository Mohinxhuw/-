"""Faheem logo: the Arabic letter feh (Cairo Bold). Its dot is a gold sound wave, and the
rising end of its tail is sliced horizontally into lines, like written notes.
The idea: the lecture's sound becomes understood, written text."""
import cairosvg
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

FONT = "/home/user/-/lecture-bot/fonts/Cairo-700.ttf"
NAVY, GOLD, WHITE = "#143f62", "#e3b448", "#ffffff"


def _feh_path() -> str:
    font = TTFont(FONT)
    glyphs = font.getGlyphSet()
    pen = SVGPathPen(glyphs)
    glyphs[font.getBestCmap()[0x06A1]].draw(pen)  # dotless feh; glyph box x 54..971, y 0..502
    return pen.getCommands()


def mark(cuts=((300, 336), (368, 404)), fg=WHITE, accent=GOLD, mask_id="cuts"):
    """Elements in font units (y up). cuts: (y_from, y_to) bands removed from the tail tip."""
    # Keep everything right of x=250, and in the tip only the bands between the cuts.
    edges = [-100] + [y for cut in cuts for y in cut] + [1000]
    keep = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    rects = '<rect x="250" y="-100" width="900" height="1100"/>' + "".join(
        f'<rect x="-100" y="{a}" width="350" height="{b-a}"/>' for a, b in keep)
    clip = f'<clipPath id="{mask_id}" clipPathUnits="userSpaceOnUse">{rects}</clipPath>'
    letter = f'<path d="{_feh_path()}" fill="{fg}" clip-path="url(#{mask_id})"/>'
    w, gap, hs, cx, bottom = 62, 38, (110, 230, 150), 734, 584
    x0 = cx - (len(hs) * w + (len(hs) - 1) * gap) / 2
    wave = "".join(f'<rect x="{x0+i*(w+gap)}" y="{bottom + (230-h)/2}" width="{w}" height="{h}" rx="{w/2}" '
                   f'fill="{accent}"/>' for i, h in enumerate(hs))
    return f"<defs>{clip}</defs>{letter}{wave}", (54, 0, 971, bottom + 230)


def svg(size=512, fg=WHITE, accent=GOLD, bg=NAVY, radius=112, width_ratio=0.64, **kw):
    body, (x0, y0, x1, y1) = mark(fg=fg, accent=accent, **kw)
    s = 512 * width_ratio / (x1 - x0)
    tx = 256 - (x0 + x1) / 2 * s
    ty = 256 + (y0 + y1) / 2 * s  # y is flipped
    bg_el = f'<rect width="512" height="512" rx="{radius}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 512 512">'
            f'{bg_el}<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.5f} {-s:.5f})">{body}</g></svg>')


if __name__ == "__main__":
    variants = {
        "v1": dict(cuts=((314, 344),)),                         # one cut: two lines
        "v2": dict(cuts=((290, 316), (344, 370))),              # two cuts: three lines
        "v3": dict(cuts=((276, 296), (318, 338), (360, 380))),  # three cuts: four lines
    }
    for name, kw in variants.items():
        cairosvg.svg2png(bytestring=svg(**kw).encode(), write_to=f"{name}.png", output_width=512)
