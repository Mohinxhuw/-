"""Faheem logo: the letter feh drawn with rounded strokes; its dot is a sound wave
and its tail breaks into text-like dashes (lecture sound -> written notes)."""
import cairosvg

NAVY, GOLD, WHITE = "#143f62", "#e3b448", "#ffffff"
SW = 40          # stroke width
BASE = 340       # baseline y in local coordinates
GAP = 26         # visible gap between tail pieces


def _pieces(lengths, start):
    """lengths of tail pieces (0 = dot) placed leftwards from x=start with visible gaps."""
    out, x = [], start
    for n in lengths:
        x -= GAP + SW            # rounded caps add SW/2 on each side
        out.append((x, x - n))
        x -= n
    return out


def mark(fg=WHITE, accent=GOLD, tail_end=244, lengths=(40, 0)):
    pieces = _pieces(lengths, tail_end)
    head = f'<rect x="306" y="214" width="104" height="{BASE-214}" rx="50" fill="none" stroke="{fg}" stroke-width="{SW}"/>'
    tail = (f'<path d="M410 260 V{BASE-24} Q410 {BASE} 386 {BASE} H{tail_end}" fill="none" stroke="{fg}" '
            f'stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"/>')
    dash = "".join(f'<line x1="{r}" y1="{BASE}" x2="{l}" y2="{BASE}" stroke="{fg}" stroke-width="{SW}" '
                   f'stroke-linecap="round"/>' for r, l in pieces)
    w, gap, hs, cx, cy = 20, 12, (36, 76, 50), 358, 136
    x0 = cx - (len(hs) * w + (len(hs) - 1) * gap) / 2
    wave = "".join(f'<rect x="{x0+i*(w+gap)}" y="{cy-h/2}" width="{w}" height="{h}" rx="{w/2}" fill="{accent}"/>'
                   for i, h in enumerate(hs))
    # bounding box, used to centre the mark
    left = pieces[-1][1] - SW / 2 if pieces else tail_end - SW / 2
    box = (left, cy - max(hs) / 2, 410 + SW / 2, BASE + SW / 2)
    return head + tail + dash + wave, box


def svg(lengths=(40, 0), tail_end=244, fg=WHITE, accent=GOLD, bg=NAVY, radius=112, scale=0.78):
    body, (x0, y0, x1, y1) = mark(fg, accent, tail_end, lengths)
    tx = 256 - (x0 + x1) / 2 * scale
    ty = 256 - (y0 + y1) / 2 * scale
    bg_el = f'<rect width="512" height="512" rx="{radius}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">{bg_el}'
            f'<g transform="translate({tx:.1f} {ty:.1f}) scale({scale})">{body}</g></svg>')


if __name__ == "__main__":
    variants = {"v1": dict(lengths=(40, 0)), "v2": dict(lengths=(64, 18)), "v3": dict(lengths=(0, 0, 0))}
    for name, kw in variants.items():
        cairosvg.svg2png(bytestring=svg(**kw).encode(), write_to=f"{name}.png", output_width=512)
