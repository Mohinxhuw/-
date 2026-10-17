import sys, cairosvg
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
FONT='/home/user/-/lecture-bot/fonts/Cairo-700.ttf'
NAVY='#143f62'; GOLD='#e3b448'; WHITE='#ffffff'
def glyph(ch):
    f=TTFont(FONT); gs=f.getGlyphSet(); name=f.getBestCmap()[ord(ch)]
    p=SVGPathPen(gs); gs[name].draw(p); b=BoundsPen(gs); gs[name].draw(b)
    return p.getCommands(), b.bounds
def bars(cx, base_y, hs, w, gap, color):
    n=len(hs); x0=cx-(n*w+(n-1)*gap)/2; out=''
    for i,h in enumerate(hs):
        out+=f'<rect x="{x0+i*(w+gap):.1f}" y="{base_y-h/2:.1f}" width="{w}" height="{h}" rx="{w/2}" fill="{color}"/>'
    return out
def svg(body, bg=NAVY, shape='square'):
    r = 112 if shape=='square' else 256
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><rect width="512" height="512" rx="{r}" fill="{bg}"/>{body}</svg>'

# A: ف — dotless feh with a gold sound wave as its dot
d,(x0,y0,x1,y1)=glyph('ڡ')
gw, gh = x1-x0, y1-y0
s = 300/gw
tx = 256 - (x0+gw/2)*s
ty = 372 + y0*s  # baseline placement (font y-up)
A = f'<path d="{d}" fill="{WHITE}" transform="translate({tx:.1f},{ty+ (y1-y0)*s*0.0:.1f}) scale({s:.4f},{-s:.4f})"/>'
# dot position: above the head (right side top of glyph)
A_dot = bars(tx + (x1 - 0.24*gw)*s, ty - y1*s - 52, [36,76,50], 20, 12, GOLD)
open('A.svg','w').write(svg(A + A_dot))
print('glyph bounds', x0,y0,x1,y1, 's',s,'top y', ty - y1*s, 'bottom', ty - y0*s)

# B: sound becomes notes — waveform on the right turns into text lines on the left (RTL)
B = bars(352, 256, [60,124,184,124,72], 22, 12, GOLD)
for i,(y,L) in enumerate([(196,150),(236,120),(276,150),(316,96)]):
    B += f'<rect x="{246-L}" y="{y-11}" width="{L}" height="22" rx="11" fill="{WHITE}"/>'
open('B.svg','w').write(svg(B))

# C: page with folded corner; top line is a sound wave, the rest are notes, gold highlight
C = ('<path d="M150 104 H312 L372 164 V392 Q372 408 356 408 H156 Q140 408 140 392 V120 Q140 104 156 104 Z" fill="#ffffff"/>'
     '<path d="M312 104 V150 Q312 164 326 164 H372 Z" fill="#c9d6e2"/>')
C += bars(256, 210, [18,40,62,40,26,50,30,16], 14, 9, NAVY)
for y,L,col in [(268,172,'#9fb3c6'),(304,140,'#9fb3c6'),(340,172,GOLD)]:
    C += f'<rect x="{342-L}" y="{y-9}" width="{L}" height="18" rx="9" fill="{col}"/>'
open('C.svg','w').write(svg(C))
for n in 'ABC':
    cairosvg.svg2png(url=f'{n}.svg', write_to=f'{n}.png', output_width=512)
