"""The bot's description picture (shown above "What can this bot do?"), 16:9."""
import pypdfium2
from weasyprint import HTML

import make_final as logo

CUTS = ((276, 296), (318, 338), (360, 380))
FONTS = "/home/user/-/lecture-bot/fonts"
W, H = 1280, 720

mark = logo.svg(cuts=CUTS, bg=None, width_ratio=0.92).replace('width="512" height="512"', 'width="470" height="470"')
wave = "".join(f'<span style="height:{h}px"></span>' for h in
               (14, 26, 44, 30, 60, 38, 22, 48, 70, 40, 24, 54, 34, 18, 42, 28, 16))
features = ["ملخص مرتب", "أسئلة اختبار", "بطاقات مراجعة", "ملف PDF"]

html = f"""<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
@font-face {{ font-family: Cairo; src: url("file://{FONTS}/Cairo-400.ttf"); font-weight: 400; }}
@font-face {{ font-family: Cairo; src: url("file://{FONTS}/Cairo-700.ttf"); font-weight: 700; }}
@page {{ size: {W}px {H}px; margin: 0; }}
html, body {{ margin: 0; }}
body {{ width: {W}px; height: {H}px; background: {logo.NAVY}; font-family: Cairo; color: #fff;
        position: relative; overflow: hidden; }}
.glow {{ position: absolute; width: 900px; height: 900px; border-radius: 50%; right: -210px; top: -90px;
         background: #1b4d75; }}
.mark {{ position: absolute; right: 40px; top: 36px; width: 470px; height: 470px; }}
.name {{ position: absolute; right: 40px; top: 500px; width: 470px; text-align: center;
         font-size: 104px; font-weight: 700; line-height: 1; }}
.copy {{ position: absolute; right: 540px; width: 700px; top: 78px; text-align: center; }}
h1 {{ margin: 0; font-size: 108px; line-height: 1.2; font-weight: 700; }}
h1 b {{ color: {logo.GOLD}; }}
p {{ margin: 14px 0 0; font-size: 40px; line-height: 1.45; color: #c9d6e2; }}
.chips {{ margin: 30px auto 0; width: 640px; text-align: center; }}
.chips span {{ display: inline-block; margin: 0 7px 14px; padding: 4px 24px; border-radius: 30px;
               border: 2px solid #4f7597; font-size: 32px; font-weight: 700; color: #fff; }}
.wave {{ position: absolute; left: 80px; bottom: 70px; height: 70px; display: flex; align-items: center;
         direction: ltr; }}
.wave span {{ display: inline-block; width: 10px; margin-right: 9px; border-radius: 5px; background: {logo.GOLD};
              opacity: .55; }}
</style></head><body>
<div class="glow"></div>
<div class="mark">{mark}</div>
<div class="name">فَهيم</div>
<div class="copy">
  <h1>محاضرتك<b>..</b><br>صارت <b>مذكرتك</b></h1>
  <p>أرسل تسجيل المحاضرة،<br>واستلم كل ما تحتاجه للمذاكرة</p>
  <div class="chips">{''.join(f'<span>{f}</span>' for f in features)}</div>
</div>
</body></html>"""

if __name__ == "__main__":
    pdf = "description/description.pdf"
    HTML(string=html).write_pdf(pdf)
    page = pypdfium2.PdfDocument(pdf)[0]
    for name, width in (("faheem-description.png", 1280), ("faheem-description-640.png", 640)):
        img = page.render(scale=width / page.get_width()).to_pil()
        img.save(f"description/{name}")
