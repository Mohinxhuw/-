"""
VANTA3 post-processor.

Takes the raw pptxgenjs output plus the animation plan written by build_deck.js and
produces the final deck:

  * gives every shape on a slide a unique id (pptxgenjs can repeat ids for tables);
  * refines charts: hides helper "Base" series (waterfall / funnel / range band),
    removes empty data points so gaps render as gaps, hides zero labels on
    stacked helper charts;
  * writes native PowerPoint slide transitions (<p:transition>);
  * writes native PowerPoint entrance animations (<p:timing>) — Fade, Wipe,
    Zoom and Appear — on shapes, text, tables and charts.

Usage: python postprocess.py raw.pptx anim_plan.json out.pptx
"""
import json
import re
import sys
import zipfile

RAW, PLAN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

zin = zipfile.ZipFile(RAW)
files = {n: zin.read(n) for n in zin.namelist()}
plan = json.load(open(PLAN))

# ---------------------------------------------------------------- charts
# Per-series refinements, keyed by series name (pptxgenjs cannot set these per series).
OPP_LABELS = ["AI analytics", "Mid-market bundle", "APAC", "Healthcare", "Marketplace", "Usage pricing"]
SERIES_RULES = {
    "_base": {"nofill": True, "nolabel": True, "legend_delete": True},  # invisible helper series
    "Target %": {"nolabel": True, "nomarker": True, "dash": True},
    "Market": {"labelpos": "b"},
    "Gross revenue retention": {"labelpos": "b"},
    "Opportunities": {"labels": OPP_LABELS},
}


def custom_labels(labels):
    pts = "".join(
        f'<c:dLbl><c:idx val="{i}"/><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r>'
        f'<a:rPr lang="en-US" sz="1100" b="1"><a:solidFill><a:srgbClr val="1B1838"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr>'
        f'<a:t>{t}</a:t></a:r></a:p></c:rich></c:tx><c:dLblPos val="r"/><c:showLegendKey val="0"/><c:showVal val="1"/>'
        f'<c:showCatName val="0"/><c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbl>'
        for i, t in enumerate(labels))
    return (f'<c:dLbls>{pts}<c:dLblPos val="r"/><c:showLegendKey val="0"/><c:showVal val="1"/><c:showCatName val="0"/>'
            '<c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbls>')


def _lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def label_ink(fill):
    """White labels stay white only where they reach 4.5:1 on the fill; otherwise use ink."""
    return "FFFFFF" if _contrast("FFFFFF", fill) >= 4.5 else "1B1838"


def fix_label_contrast(ser):
    m = re.search(r"<c:spPr>\s*<a:solidFill><a:srgbClr val=\"([0-9A-F]{6})\"", ser)
    fills = dict(re.findall(r'<c:dPt>\s*<c:idx val="(\d+)"/>.*?<a:srgbClr val="([0-9A-F]{6})"', ser, re.S))

    def per_lbl(mm):
        lbl = mm.group(0)
        idx = re.search(r'<c:idx val="(\d+)"/>', lbl).group(1)
        f = fills.get(idx) or (m.group(1) if m else None)
        return lbl.replace('<a:srgbClr val="FFFFFF"/>', f'<a:srgbClr val="{label_ink(f)}"/>') if f else lbl

    ser = re.sub(r"<c:dLbl>.*?</c:dLbl>", per_lbl, ser, flags=re.S)
    if m and not fills:
        def series_lbls(mm):
            return mm.group(0).replace('<a:srgbClr val="FFFFFF"/>', f'<a:srgbClr val="{label_ink(m.group(1))}"/>')
        ser = re.sub(r"<c:dLbls>.*?</c:dLbls>", series_lbls, ser, count=1, flags=re.S)
    return ser


def fix_chart(xml: str) -> str:
    # drop empty points (pptxgenjs writes <c:v></c:v> for nulls) so lines break cleanly
    xml = re.sub(r"<c:pt idx=\"\d+\"><c:v></c:v></c:pt>", "", xml)
    has_base = False
    hidden_legend = []

    def ser_fix(m):
        nonlocal has_base
        ser = m.group(0)
        nm = re.search(r"<c:tx>\s*<c:strRef>.*?<c:v>(.*?)</c:v>", ser, re.S)
        rule = SERIES_RULES.get(nm.group(1)) if nm else None
        ser = fix_label_contrast(ser)
        if not rule:
            return ser
        if rule.get("nofill"):
            has_base = True
            ser = re.sub(r"<c:spPr>.*?</c:spPr>", "<c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>", ser, count=1, flags=re.S)
        if rule.get("legend_delete"):
            hidden_legend.append(re.search(r'<c:idx val="(\d+)"/>', ser).group(1))
        if rule.get("nolabel"):
            if "<c:dLbls>" in ser:
                ser = re.sub(r"<c:dLbls>.*?</c:dLbls>", '<c:dLbls><c:delete val="1"/></c:dLbls>', ser, count=1, flags=re.S)
            else:
                ser = ser.replace("<c:cat>", '<c:dLbls><c:delete val="1"/></c:dLbls><c:cat>', 1)
        if rule.get("labels"):
            if "<c:dLbls>" in ser:
                ser = re.sub(r"<c:dLbls>.*?</c:dLbls>", custom_labels(rule["labels"]), ser, count=1, flags=re.S)
            else:
                ser = ser.replace("<c:xVal>", custom_labels(rule["labels"]) + "<c:xVal>", 1)
        if rule.get("labelpos"):
            ser = re.sub(r'(<c:dLbls>.*?)<c:dLblPos val="[a-zA-Z]+"/>', rf'\1<c:dLblPos val="{rule["labelpos"]}"/>', ser, count=1, flags=re.S)
        if rule.get("nomarker"):
            ser = re.sub(r"<c:marker>.*?</c:marker>", '<c:marker><c:symbol val="none"/></c:marker>', ser, count=1, flags=re.S)
        if rule.get("dash"):
            ser = ser.replace('<a:prstDash val="solid"/>', '<a:prstDash val="dash"/>', 1)
        return ser

    xml = re.sub(r"<c:ser>.*?</c:ser>", ser_fix, xml, flags=re.S)
    if hidden_legend:
        entries = "".join(f'<c:legendEntry><c:idx val="{i}"/><c:delete val="1"/></c:legendEntry>' for i in hidden_legend)
        xml = re.sub(r'(<c:legendPos val="[a-z]+"/>)', r"\1" + entries, xml, count=1)
    if has_base:
        # zero-height helper segments must not show "0" labels
        xml = xml.replace('formatCode="#,##0" sourceLinked="0"', 'formatCode="#,##0;-#,##0;;" sourceLinked="0"')
    return xml


for n in list(files):
    if re.match(r"ppt/charts/chart\d+\.xml$", n):
        files[n] = fix_chart(files[n].decode("utf8")).encode("utf8")

# ---------------------------------------------------------------- animation XML
WIPE = {"wipeUp": (4, "wipe(up)"), "wipeRight": (8, "wipe(right)"), "wipeLeft": (2, "wipe(left)"), "wipeDown": (1, "wipe(down)")}
PRESET = {"fade": (10, 0), "zoom": (53, 16), "appear": (1, 0)}


class Ids:
    def __init__(self):
        self.i = 0

    def __call__(self):
        self.i += 1
        return self.i


def tgt(spid, ge=""):
    return f'<p:tgtEl><p:spTgt spid="{spid}">{ge}</p:spTgt></p:tgtEl>'


def effect(ids, fx, spid, dur, delay, node_type, ge=""):
    """One entrance effect node (<p:par> containing the effect cTn)."""
    t = tgt(spid, ge)
    vis = (f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
           f'{t}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>')
    if fx in WIPE:
        pid, sub = 22, WIPE[fx][0]
        beh = vis + f'<p:animEffect transition="in" filter="{WIPE[fx][1]}"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>{t}</p:cBhvr></p:animEffect>'
    elif fx == "fade":
        pid, sub = PRESET["fade"]
        beh = vis + f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>{t}</p:cBhvr></p:animEffect>'
    elif fx == "zoom":
        pid, sub = PRESET["zoom"]
        beh = vis
        for attr in ("ppt_w", "ppt_h"):
            beh += (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}" fill="hold"/>{t}'
                    f'<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>'
                    f'<p:tav tm="0"><p:val><p:strVal val="#{attr}*0.6"/></p:val></p:tav>'
                    f'<p:tav tm="100000"><p:val><p:strVal val="#{attr}"/></p:val></p:tav></p:tavLst></p:anim>')
        beh += f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>{t}</p:cBhvr></p:animEffect>'
    else:  # appear
        pid, sub = PRESET["appear"]
        beh = vis
    return (f'<p:par><p:cTn id="{ids()}" presetID="{pid}" presetClass="entr" presetSubtype="{sub}" fill="hold" grpId="0" nodeType="{node_type}">'
            f'<p:stCondLst><p:cond delay="{int(delay)}"/></p:stCondLst><p:childTnLst>{beh}</p:childTnLst></p:cTn></p:par>')


def renumber_ids(xml):
    """Give every cNvPr on the slide a unique id; return xml and name->(id, kind) map."""
    counter = [1]

    def rep(m):
        if 'id="1" name=""' in m.group(0):
            return m.group(0)
        counter[0] += 1
        return re.sub(r'id="\d+"', f'id="{counter[0]}"', m.group(0), count=1)

    xml = re.sub(r"<p:cNvPr [^>]*>", rep, xml)
    return xml


def shape_index(xml):
    """Map object name -> (id, kind, is_placeholder) using the slide's spTree."""
    out = {}
    phs = []
    for kind, tag in (("sp", "p:sp"), ("pic", "p:pic"), ("gf", "p:graphicFrame"), ("cxn", "p:cxnSp")):
        for m in re.finditer(rf"<{tag}>(.*?)</{tag}>", xml, re.S):
            body = m.group(1)
            c = re.search(r'<p:cNvPr id="(\d+)" name="([^"]*)"', body)
            if not c:
                continue
            sid, name = int(c.group(1)), c.group(2)
            is_ph = "<p:ph" in body[:600]
            rid = None
            r = re.search(r'<c:chart [^>]*r:id="([^"]+)"', body)
            if r:
                rid = r.group(1)
            out[name] = (sid, kind, rid)
            if is_ph and "Slide Number" not in name:
                phs.append((sid, kind, rid))
    return out, phs


def build_timing(slide_xml, steps, rels):
    idx, phs = shape_index(slide_xml)
    ids = Ids()
    ids()  # 1 root
    ids()  # 2 main seq
    outer_id = ids()
    inner = []  # list of [start_ms, [effect xml], end_ms]
    cursor = 0  # absolute start of current inner par
    seen = set()
    bld = {}
    cur = None

    def resolve(names):
        out = []
        for n in names:
            if n == "@ph":
                out.extend(phs)
            elif n in idx:
                out.append(idx[n])
            else:
                raise KeyError(f"object {n} not found")
        return out

    for st in steps:
        targets = [t for t in resolve(st["items"]) if t[0] not in seen]
        if not targets:
            continue
        if st["t"] == "after" or cur is None:
            if cur is not None:
                cursor = cur[2]
            cur = [cursor, [], cursor]
            inner.append(cur)
        first_type = "afterEffect" if st["t"] == "after" else "withEffect"
        dur = st["dur"]
        for k, (sid, kind, rid) in enumerate(targets):
            seen.add(sid)
            d = st["delay"] + k * st["stagger"]
            ntype = first_type if (k == 0 and not cur[1]) else "withEffect"
            if kind == "gf" and rid and st.get("build"):
                # Progressive chart reveal: one directional Wipe across the whole chart
                # (left-to-right reveals categories in order, bottom-up grows the columns).
                # Sub-element builds (By Series / By Category) are not written because their
                # element indices cannot be verified without desktop PowerPoint.
                cdur = max(900, dur * 2)
                cur[1].append(effect(ids, st["fx"], sid, cdur, d, ntype))
                cur[2] = max(cur[2], cur[0] + d + cdur)
                bld[sid] = f'<p:bldGraphic spid="{sid}" grpId="0"><p:bldAsOne/></p:bldGraphic>'
            else:
                cur[1].append(effect(ids, st["fx"], sid, dur, d, ntype))
                cur[2] = max(cur[2], cur[0] + d + dur)
                if kind == "sp":
                    bld[sid] = f'<p:bldP spid="{sid}" grpId="0" animBg="1"/>'
                elif kind == "gf":
                    bld[sid] = f'<p:bldGraphic spid="{sid}" grpId="0"><p:bldAsOne/></p:bldGraphic>'

    if not inner:
        return "", 0
    pars = "".join(
        f'<p:par><p:cTn id="{ids()}" fill="hold"><p:stCondLst><p:cond delay="{int(p[0])}"/></p:stCondLst><p:childTnLst>{"".join(p[1])}</p:childTnLst></p:cTn></p:par>'
        for p in inner)
    timing = (
        '<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        f'<p:par><p:cTn id="{outer_id}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst>'
        f'<p:childTnLst>{pars}</p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
        '</p:childTnLst></p:cTn></p:par></p:tnLst>'
        f'<p:bldLst>{"".join(bld.values())}</p:bldLst></p:timing>')
    return timing, max(p[2] for p in inner)


TRANS = {
    "fade": '<p:transition spd="med"><p:fade/></p:transition>',
    "push": '<p:transition spd="slow"><p:push dir="u"/></p:transition>',
}

report = []
for i, sp in enumerate(plan, start=1):
    name = f"ppt/slides/slide{i}.xml"
    xml = files[name].decode("utf8")
    xml = renumber_ids(xml)
    rels_xml = files[f"ppt/slides/_rels/slide{i}.xml.rels"].decode("utf8")
    rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml))
    rels.update({a: b for b, a in re.findall(r'Target="([^"]+)"[^>]*Id="([^"]+)"', rels_xml)})
    timing, total = build_timing(xml, sp["anim"], rels)
    trans = TRANS.get(sp.get("transition", "fade"), TRANS["fade"])
    xml = xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + trans + timing, 1)
    files[name] = xml.encode("utf8")
    n_eff = timing.count('presetClass="entr"')
    report.append({"slide": i, "transition": sp.get("transition", "fade"), "effects": n_eff,
                   "frame_effects": sum(1 for b in re.findall(r"<p:bldGraphic spid=\"(\d+)\"", timing)), "build_ms": int(total)})

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    # [Content_Types].xml must stay first
    order = ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]
    for n in order:
        z.writestr(n, files[n])

json.dump(report, open(OUT.replace(".pptx", "_anim_report.json"), "w"), indent=1)
print("slides:", len(report), "effects:", sum(r["effects"] for r in report), "graphic-frame effects:", sum(r["frame_effects"] for r in report))
