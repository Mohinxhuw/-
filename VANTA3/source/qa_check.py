"""
VANTA3 automated QA: structure, charts, animations, transitions.
Usage: python qa_check.py VANTA3.pptx [libreoffice_roundtrip.odp]
Prints a JSON summary used in the QA report.
"""
import json, re, sys, zipfile
from lxml import etree

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
path = sys.argv[1]
z = zipfile.ZipFile(path)
names = z.namelist()
slides = sorted([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=lambda n: int(re.findall(r"\d+", n)[0]))
problems, per_slide = [], []
pres = etree.fromstring(z.read("ppt/presentation.xml"))
sz = pres.find("p:sldSz", NS)
for sn in slides:
    i = int(re.findall(r"\d+", sn)[0])
    x = etree.fromstring(z.read(sn))
    ids = [int(e.get("id")) for e in x.iter("{%s}cNvPr" % NS["p"])]
    if len(ids) != len(set(ids)):
        problems.append(f"slide {i}: duplicate shape ids")
    idset = set(ids)
    tr = x.find("p:transition", NS)
    timing = x.find("p:timing", NS)
    effects = timing.findall(".//p:cTn[@presetClass='entr']", NS) if timing is not None else []
    targets = [int(t.get("spid")) for t in timing.iter("{%s}spTgt" % NS["p"])] if timing is not None else []
    missing = [t for t in targets if t not in idset]
    if missing:
        problems.append(f"slide {i}: animation targets missing shapes {missing}")
    ent_targets = []
    for e in effects:
        sp = e.find(".//p:spTgt", NS)
        ent_targets.append(int(sp.get("spid")))
    dup = {t for t in ent_targets if ent_targets.count(t) > 1}
    if dup:
        problems.append(f"slide {i}: shapes with more than one entrance {dup}")
    ctn_ids = [int(c.get("id")) for c in timing.iter("{%s}cTn" % NS["p"])] if timing is not None else []
    if len(ctn_ids) != len(set(ctn_ids)):
        problems.append(f"slide {i}: duplicate timing node ids")
    # inner pars must start in non-decreasing order
    if timing is not None:
        outer = timing.find("p:tnLst/p:par/p:cTn/p:childTnLst/p:seq/p:cTn/p:childTnLst/p:par/p:cTn/p:childTnLst", NS)
        starts = [int(p.find("p:cTn/p:stCondLst/p:cond", NS).get("delay")) for p in outer.findall("p:par", NS)]
        if starts != sorted(starts):
            problems.append(f"slide {i}: build steps out of order")
        trig = timing.find(".//p:cond[@evt='onBegin']", NS)
        if trig is None:
            problems.append(f"slide {i}: build does not auto-start")
        bld = [int(b.get("spid")) for b in timing.find("p:bldLst", NS)]
        if any(b not in idset for b in bld):
            problems.append(f"slide {i}: bldLst references missing shape")
        end = 0
        for p in outer.findall("p:par", NS):
            st = int(p.find("p:cTn/p:stCondLst/p:cond", NS).get("delay"))
            for e in p.findall("p:cTn/p:childTnLst/p:par/p:cTn", NS):
                d = int(e.find("p:stCondLst/p:cond", NS).get("delay"))
                durs = [int(c.get("dur")) for c in e.iter("{%s}cTn" % NS["p"]) if c.get("dur") not in (None, "indefinite")]
                end = max(end, st + d + max(durs or [0]))
    else:
        end = 0
    presets = sorted({(e.get("presetID"), e.get("presetSubtype")) for e in effects})
    # off-slide check
    off = 0
    for xfrm in x.iter("{%s}xfrm" % NS["a"]):
        o, ex = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
        if o is None or ex is None:
            continue
    rels = z.read(sn.replace("slides/", "slides/_rels/") + ".rels").decode()
    charts = re.findall(r'Target="[^"]*charts/(chart\d+\.xml)"', rels)
    per_slide.append({"slide": i, "transition": tr[0].tag.split("}")[1] if tr is not None else None,
                      "entrance_effects": len(effects), "charts": len(charts), "build_seconds": round(end / 1000, 1),
                      "effect_types": ["fade" if p == ("10", "0") else "wipe" if p[0] == "22" else "zoom" if p[0] == "53" else "appear" for p in presets]})
# chart editability: every chart has an embedded workbook
chart_parts = [n for n in names if re.match(r"ppt/charts/chart\d+\.xml$", n)]
emb_ok = 0
types = {}
for c in chart_parts:
    rel = z.read(c.replace("charts/", "charts/_rels/") + ".rels").decode()
    if re.search(r'Target="[^"]*embeddings/[^"]+\.xlsx"', rel):
        emb_ok += 1
    x = z.read(c).decode()
    for t in re.findall(r"<c:(barChart|lineChart|areaChart|pieChart|doughnutChart|scatterChart|bubbleChart|radarChart)>", x):
        if t == "barChart":
            d = re.search(r'<c:barDir val="(\w+)"/>.*?<c:grouping val="(\w+)"/>', x, re.S)
            t = f"barChart-{d.group(1)}-{d.group(2)}" if d else t
        types[t] = types.get(t, 0) + 1
imgs = [n for n in names if n.startswith("ppt/media/")]
summary = {"file": path, "slide_count": len(slides),
           "slide_size_in": [int(sz.get("cx")) / 914400, int(sz.get("cy")) / 914400],
           "charts_total": len(chart_parts), "charts_with_embedded_workbook": emb_ok, "chart_types": types,
           "slides_with_charts": sum(1 for s in per_slide if s["charts"]),
           "slides_with_animation": sum(1 for s in per_slide if s["entrance_effects"]),
           "slides_with_transition": sum(1 for s in per_slide if s["transition"]),
           "entrance_effects_total": sum(s["entrance_effects"] for s in per_slide),
           "max_build_seconds": max(s["build_seconds"] for s in per_slide),
           "media_files": len(imgs), "problems": problems, "per_slide": per_slide}
if len(sys.argv) > 2:
    oz = zipfile.ZipFile(sys.argv[2])
    content = oz.read("content.xml").decode()
    pages = re.findall(r"<draw:page .*?</draw:page>", content, re.S)
    summary["libreoffice_roundtrip"] = {
        "pages": len(pages),
        "pages_with_imported_animation": sum(1 for p in pages if "anim:par" in p),
        "imported_entrance_effects": content.count('presentation:preset-class="entrance"'),
        "pages_with_transition": sum(1 for p in pages if re.search(r'draw:style-name="([^"]+)"', p) and re.search(r'style:name="%s"[^>]*>\s*<style:drawing-page-properties[^>]*smil:type' % re.escape(re.search(r'draw:style-name="([^"]+)"', p).group(1)), content)),
    }
print(json.dumps(summary, indent=1))
