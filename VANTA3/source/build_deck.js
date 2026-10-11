/*
 * VANTA3 — premium business presentation template
 * Generator: pptxgenjs (native shapes, tables and editable charts).
 * Animations, transitions and chart refinements are added afterwards by
 * postprocess.py, which reads the animation plan written by this script.
 *
 * Run:  NODE_PATH=<node_modules> node build_deck.js <out_dir>
 */
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Lu = require("react-icons/lu");

const OUT = process.argv[2] || ".";

/* ------------------------------------------------------------------ */
/* 1. Visual identity tokens                                           */
/* ------------------------------------------------------------------ */
const C = {
  violet: "5B3DF5", // primary — Vanta Violet
  aqua: "0FB5A5", // secondary — Signal Aqua
  coral: "FF5A4E", // accent — Ember Coral
  saffron: "FFB224", // accent — Saffron
  lavender: "A797FA", // supporting tint of primary
  ink: "1B1838", // text
  night: "14112F", // dark backgrounds
  night2: "221E4A", // raised surface on dark
  mist: "F5F4FB", // light background
  white: "FFFFFF",
  line: "E4E2F1",
  grid: "E7E5F3",
  muted: "66638A",
  muted2: "9C99BC",
  vTint: "ECE8FE",
  aTint: "DCF5F2",
  cTint: "FFE7E4",
  sTint: "FFF1D6",
  track: "ECEAF6",
  // text-safe variants (WCAG AA >= 4.5:1 on white) for numbers and labels on light surfaces
  aquaInk: "097A70",
  coralInk: "D13A2F",
  saffronInk: "9E6400",
};
const SERIES = [C.violet, C.aqua, C.coral, C.saffron, C.lavender, "8E8BAE"];
const HEAD = "Cambria";
const BODY = "Calibri";

const THEME = {
  name: "VANTA3",
  headFontFace: HEAD,
  bodyFontFace: BODY,
  colors: {
    dk1: C.ink, lt1: C.white, dk2: C.night, lt2: C.mist,
    accent1: C.violet, accent2: C.aqua, accent3: C.coral, accent4: C.saffron,
    accent5: C.lavender, accent6: C.muted, hlink: C.violet, folHlink: "7A66F7",
  },
};

const W = 13.333, H = 7.5, M = 0.6;
const CW = W - 2 * M; // content width 12.133
const TOP = 1.72; // content top on light slides
const BOT = 6.78; // content bottom

/* ------------------------------------------------------------------ */
/* 2. Icons (rendered to PNG from Lucide line icons)                   */
/* ------------------------------------------------------------------ */
const iconCache = {};
async function icon(name, color) {
  const key = name + color;
  if (iconCache[key]) return iconCache[key];
  const Comp = Lu[name];
  if (!Comp) throw new Error("Unknown icon " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color: "#" + color, size: 256, strokeWidth: 2 })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  iconCache[key] = "image/png;base64," + buf.toString("base64");
  return iconCache[key];
}
const ICONS = [
  "LuTarget", "LuTrendingUp", "LuGlobe", "LuUsers", "LuShieldCheck", "LuZap", "LuCpu",
  "LuLayers", "LuRocket", "LuCompass", "LuGauge", "LuWorkflow", "LuChartPie",
  "LuHandshake", "LuSparkles", "LuBadgeCheck", "LuClock", "LuCircleDollarSign",
  "LuBuilding2", "LuLeaf", "LuFlag", "LuMail", "LuPhone", "LuMapPin", "LuLightbulb",
  "LuScale", "LuBoxes", "LuRefreshCw", "LuLock", "LuChartColumn", "LuCalendarCheck",
];
const ICON_COLORS = [C.violet, C.aqua, C.coral, C.saffron, C.white, C.lavender];

/* ------------------------------------------------------------------ */
/* 3. Presentation, layouts                                            */
/* ------------------------------------------------------------------ */
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "VANTA3 — Strategy & Performance Review";
pres.subject = "Premium business presentation template";
pres.author = "VANTA3";
pres.company = "VANTA3";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

const footerText = (color) => ({
  text: {
    text: "VANTA3   |   FY2026 Strategy & Performance Review   |   Illustrative data",
    options: { x: M, y: 7.0, w: 8, h: 0.28, fontFace: BODY, fontSize: 9, color, margin: 0 },
  },
});

pres.defineSlideMaster({
  title: "VANTA Light",
  background: { color: C.mist },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { ellipse: { x: M, y: 0.455, w: 0.11, h: 0.11, fill: { color: C.coral }, line: { type: "none" } } },
    { placeholder: { options: { name: "kicker", type: "body", x: 0.8, y: 0.38, w: 9, h: 0.26, fontFace: BODY, fontSize: 11, bold: true, color: C.violet, charSpacing: 2, margin: 0, valign: "middle", align: "left" }, text: "SECTION" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.72, w: CW, h: 0.72, fontFace: HEAD, fontSize: 30, bold: true, color: C.ink, margin: 0, valign: "middle", align: "left" }, text: "Slide title" } },
    footerText(C.muted2),
  ],
  slideNumber: { x: 12.23, y: 7.0, w: 0.5, h: 0.28, fontFace: BODY, fontSize: 9, color: C.muted2, align: "right" },
});

pres.defineSlideMaster({
  title: "VANTA Dark",
  background: { color: C.night },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { ellipse: { x: M, y: 0.455, w: 0.11, h: 0.11, fill: { color: C.coral }, line: { type: "none" } } },
    { placeholder: { options: { name: "kicker", type: "body", x: 0.8, y: 0.38, w: 9, h: 0.26, fontFace: BODY, fontSize: 11, bold: true, color: C.aqua, charSpacing: 2, margin: 0, valign: "middle", align: "left" }, text: "SECTION" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.72, w: CW, h: 0.72, fontFace: HEAD, fontSize: 30, bold: true, color: C.white, margin: 0, valign: "middle", align: "left" }, text: "Slide title" } },
    footerText("8E8AB8"),
  ],
  slideNumber: { x: 12.23, y: 7.0, w: 0.5, h: 0.28, fontFace: BODY, fontSize: 9, color: "8E8AB8", align: "right" },
});

pres.defineSlideMaster({
  title: "VANTA Chapter",
  background: { color: C.night },
  objects: [
    // orbit rings — the VANTA3 signature motif
    { ellipse: { x: 7.35, y: -1.1, w: 8.6, h: 8.6, fill: { type: "none" }, line: { color: C.violet, width: 1.25, transparency: 35 } } },
    { ellipse: { x: 8.35, y: -0.1, w: 6.6, h: 6.6, fill: { type: "none" }, line: { color: C.violet, width: 1.25, transparency: 55 } } },
    { ellipse: { x: 9.35, y: 0.9, w: 4.6, h: 4.6, fill: { color: C.night2 }, line: { color: C.lavender, width: 1, transparency: 60 } } },
    { ellipse: { x: 9.08, y: 3.0, w: 0.4, h: 0.4, fill: { color: C.coral }, line: { type: "none" } } },
    { placeholder: { options: { name: "chapnum", type: "body", x: M, y: 1.35, w: 4, h: 1.5, fontFace: HEAD, fontSize: 96, bold: true, color: C.lavender, margin: 0, valign: "top", align: "left" }, text: "00" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 3.0, w: 6.6, h: 1.5, fontFace: HEAD, fontSize: 44, bold: true, color: C.white, margin: 0, valign: "top", align: "left" }, text: "Chapter title" } },
    { placeholder: { options: { name: "chapsub", type: "body", x: M, y: 4.6, w: 6.0, h: 1.0, fontFace: BODY, fontSize: 16, color: "C9C5EE", margin: 0, valign: "top", align: "left" }, text: "Chapter summary" } },
    footerText("8E8AB8"),
  ],
  slideNumber: { x: 12.23, y: 7.0, w: 0.5, h: 0.28, fontFace: BODY, fontSize: 9, color: "8E8AB8", align: "right" },
});

pres.defineSlideMaster({
  title: "VANTA Cover",
  background: { color: C.night },
  objects: [],
});

/* ------------------------------------------------------------------ */
/* 4. Helpers                                                          */
/* ------------------------------------------------------------------ */
const plan = []; // animation + transition plan per slide
let current = null;

function slide(layout, section, kicker, title, opts = {}) {
  const s = pres.addSlide({ masterName: layout, sectionTitle: section });
  s._n = 0;
  s._plan = { anim: [], transition: opts.transition || "fade" };
  plan.push(s._plan);
  current = s;
  if (kicker !== null && kicker !== undefined) s.addText(kicker, { placeholder: layout === "VANTA Chapter" ? "chapnum" : "kicker" });
  if (title) s.addText(title, { placeholder: "title" });
  if (opts.notes) s.addNotes(opts.notes);
  return s;
}
const nm = (s, p) => `${p}_${++s._n}`;

/** Add an animation step. fx: fade | wipeUp | wipeLeft | wipeDown | wipeRight | zoom | appear
 *  t: after (default) | with | click.  build: series | category (charts only). */
function anim(s, fx, items, o = {}) {
  s._plan.anim.push({ fx, items: [].concat(items).flat(Infinity).filter(Boolean), t: o.t || "after", dur: o.dur || 500, stagger: o.stagger || 0, delay: o.delay || 0, build: o.build || null });
}

/** On light surfaces, swap vivid accents for their text-safe variants. */
function inkFor(color, size, onDark) {
  if (onDark || !color) return color;
  if (color === C.aqua) return C.aquaInk;
  if (color === C.saffron) return C.saffronInk;
  if (color === C.coral && (size || 14) < 24) return C.coralInk;
  return color;
}

function text(s, str, o) {
  const name = o.name || nm(s, "txt");
  o = Object.assign({}, o);
  o.color = inkFor(o.color, o.fontSize, o.onDark);
  if (Array.isArray(str)) str = str.map((r) => (r.options && r.options.color ? { text: r.text, options: Object.assign({}, r.options, { color: inkFor(r.options.color, r.options.fontSize || o.fontSize, o.onDark) }) } : r));
  delete o.onDark;
  s.addText(str, Object.assign({ fontFace: BODY, fontSize: 14, color: C.ink, margin: 0, valign: "top", isTextBox: true, objectName: name }, o, { name: undefined }));
  return name;
}

function shadow() {
  return { type: "outer", color: "2A2160", blur: 14, offset: 2, angle: 90, opacity: 0.09 };
}

function card(s, x, y, w, h, o = {}) {
  const name = o.name || nm(s, "card");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: o.radius === undefined ? 0.1 : o.radius,
    fill: { color: o.fill || C.white }, line: o.line ? { color: o.line, width: 1 } : { type: "none" },
    shadow: o.noShadow ? undefined : shadow(), objectName: name,
  });
  return name;
}

function circle(s, x, y, d, color, o = {}) {
  const name = o.name || nm(s, "dot");
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: o.line ? { color: o.line, width: o.lw || 1 } : { type: "none" }, objectName: name });
  return name;
}

function rect(s, x, y, w, h, color, o = {}) {
  const name = o.name || nm(s, "rect");
  const shape = o.round ? pres.shapes.ROUNDED_RECTANGLE : pres.shapes.RECTANGLE;
  s.addShape(shape, { x, y, w, h, rectRadius: o.round || 0, fill: { color, transparency: o.transparency || 0 }, line: o.line ? { color: o.line, width: o.lw || 1 } : { type: "none" }, objectName: name });
  return name;
}

function line(s, x, y, w, h, color, o = {}) {
  const name = o.name || nm(s, "line");
  s.addShape(pres.shapes.LINE, { x, y, w, h, line: { color, width: o.width || 1, dashType: o.dash || "solid", endArrowType: o.arrow || undefined }, flipV: !!o.flipV, objectName: name });
  return name;
}

async function iconIn(s, iconName, x, y, d, bg, fg, o = {}) {
  const c = circle(s, x, y, d, bg, { name: nm(s, "icbg") });
  const pad = d * 0.25;
  const name = nm(s, "ic");
  s.addImage({ data: await icon(iconName, fg), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name, altText: o.alt || iconName.replace("Lu", "") + " icon" });
  return [c, name];
}

/** Section label inside cards: small caps muted */
function label(s, str, x, y, w, o = {}) {
  return text(s, str, { x, y, w, h: 0.26, fontSize: 11, bold: true, color: o.color || C.muted, charSpacing: 1.5, ...o, name: o.name });
}

/** Big KPI tile. */
function kpi(s, x, y, w, h, { value, labelText, delta, deltaColor, color, dark }) {
  const names = [];
  names.push(card(s, x, y, w, h, { fill: dark ? C.night2 : C.white, noShadow: !!dark }));
  const od = !!dark;
  names.push(text(s, labelText, { onDark: od, x: x + 0.25, y: y + 0.2, w: w - 0.5, h: 0.28, fontSize: 11, bold: true, color: dark ? "B8B4E6" : C.muted, charSpacing: 1 }));
  names.push(text(s, value, { onDark: od, x: x + 0.25, y: y + 0.48, w: w - 0.5, h: 0.6, fontFace: HEAD, fontSize: 30, bold: true, color: color || (dark ? C.white : C.violet), valign: "middle" }));
  if (delta) names.push(text(s, delta, { onDark: od, x: x + 0.25, y: y + 1.1, w: w - 0.5, h: 0.28, fontSize: 12, bold: true, color: deltaColor || C.aqua }));
  return names;
}

/** Shared chart styling (fresh object every call — pptxgenjs mutates options). */
function co(o = {}) {
  return Object.assign({
    catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY, dataLabelFontFace: BODY, legendFontFace: BODY, titleFontFace: BODY,
    catAxisLabelColor: C.muted, valAxisLabelColor: C.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
    catAxisLineShow: true, catAxisLineColor: "D3D0E6", valAxisLineShow: false,
    valGridLine: { color: C.grid, size: 0.75 }, catGridLine: { style: "none" },
    dataLabelColor: C.ink, dataLabelFontSize: 10, dataLabelFontBold: true,
    showLegend: false, legendPos: "t", legendFontSize: 11, legendColor: C.ink,
    showTitle: false, chartColors: SERIES.slice(),
    plotArea: { fill: { color: C.white } },
  }, o);
}
const darkChart = (o = {}) => co(Object.assign({
  catAxisLabelColor: "B8B4E6", valAxisLabelColor: "B8B4E6", catAxisLineColor: "4A4578",
  valGridLine: { color: "34305E", size: 0.75 }, dataLabelColor: C.white, legendColor: C.white,
  plotArea: { fill: { color: C.night2 } },
}, o));

function chart(s, type, data, x, y, w, h, opts) {
  const name = opts.objectName || nm(s, "chart");
  const o = Object.assign({ x, y, w, h }, opts, { objectName: name });
  if (Array.isArray(type)) s.addChart(type, o);
  else s.addChart(type, data, o);
  return name;
}

/** Insight panel: tinted card with heading + bullet list. */
function insight(s, x, y, w, h, heading, bullets, o = {}) {
  const n = [];
  n.push(card(s, x, y, w, h, { fill: o.fill || C.vTint, noShadow: true }));
  n.push(text(s, heading, { x: x + 0.3, y: y + 0.28, w: w - 0.6, h: 0.35, fontFace: HEAD, fontSize: 16, bold: true, color: o.headColor || C.violet }));
  n.push(text(s, bullets.map((b, i) => ({ text: b, options: { bullet: { indent: 14 }, breakLine: i < bullets.length - 1 } })), {
    x: x + 0.3, y: y + 0.78, w: w - 0.6, h: h - 1.0, fontSize: o.fontSize || 14, color: C.ink, paraSpaceAfter: 8, valign: "top",
  }));
  return n;
}

/** Chart card: white card + header label + optional caption; returns names. */
function chartCard(s, x, y, w, h, heading, sub) {
  const n = [card(s, x, y, w, h)];
  n.push(text(s, heading, { x: x + 0.3, y: y + 0.22, w: w - 0.6, h: 0.32, fontSize: 15, bold: true, color: C.ink }));
  if (sub) n.push(text(s, sub, { x: x + 0.3, y: y + 0.52, w: w - 0.6, h: 0.26, fontSize: 11, color: C.muted }));
  return n;
}

function source(s, str, dark) {
  return text(s, str, { x: M, y: 6.72, w: CW, h: 0.24, fontSize: 10, italic: true, color: dark ? "8E8AB8" : C.muted2 });
}

const fmt = (v, d = 0) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/* ------------------------------------------------------------------ */
/* 5. Illustrative data model (internally consistent)                 */
/* ------------------------------------------------------------------ */
const YEARS = ["FY22", "FY23", "FY24", "FY25", "FY26"];
const REV = [412, 486, 571, 664, 772];
const QREV = { FY22: [94, 100, 105, 113], FY23: [111, 117, 123, 135], FY24: [130, 138, 146, 157], FY25: [151, 160, 169, 184], FY26: [176, 186, 197, 213] };
const SEG = { "Platform Software": [152, 193, 239, 286, 348], "Managed Services": [156, 172, 191, 210, 231], "Data & Analytics": [46, 58, 76, 98, 124], Advisory: [58, 63, 65, 70, 69] };
const EBITDA_M = [17.8, 19.1, 20.6, 21.9, 23.4];
const REGIONS = [["North America", 341, 14], ["Europe", 228, 15], ["Asia-Pacific", 139, 24], ["Latin America", 41, 19], ["Middle East & Africa", 23, 28]];
const FORECAST = { base: [892, 1027, 1176], bear: [860, 952, 1045], bull: [918, 1085, 1276] };

/* ------------------------------------------------------------------ */
/* 6. Slides                                                           */
/* ------------------------------------------------------------------ */
async function build() {
  for (const n of ICONS) for (const c of ICON_COLORS) await icon(n, c);

  const SEC = ["Opening", "01 Performance", "02 Market", "03 Customers & Sales", "04 Operations", "05 Growth", "06 Outlook", "07 Plan", "Close"];
  SEC.forEach(() => {});
  let s;

  /* ---------- 1. Cover ---------- */
  pres.addSection({ title: "Opening" });
  s = slide("VANTA Cover", "Opening", null, null, { transition: "fade" });
  {
    const rings = [
      [6.9, -1.6, 9.4, 30], [7.9, -0.6, 7.4, 50], [8.9, 0.4, 5.4, 65],
    ].map(([x, y, d, t]) => { const n = nm(s, "ring"); s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { type: "none" }, line: { color: C.violet, width: 1.25, transparency: t }, objectName: n }); return n; });
    // skyline of rising bars — abstract growth signature
    const bars = [];
    const hs = [1.0, 1.35, 1.2, 1.7, 1.55, 2.1, 2.0, 2.6, 2.45, 3.1];
    const cols = [C.night2, C.night2, "2E2862", "2E2862", "3B3380", "3B3380", C.violet, C.violet, C.aqua, C.coral];
    hs.forEach((h, i) => bars.push(rect(s, 7.35 + i * 0.52, 6.55 - h, 0.36, h, cols[i], { round: 0.06 })));
    const glow = circle(s, 12.08, 2.95, 0.3, C.saffron);
    const brand = text(s, [{ text: "VANTA", options: { bold: true, color: C.white } }, { text: "3", options: { bold: true, color: C.coral } }], { onDark: true, x: M, y: 0.6, w: 3, h: 0.4, fontFace: HEAD, fontSize: 20, charSpacing: 4 });
    const kick = text(s, "ANNUAL BUSINESS REVIEW  ·  FY2026", { onDark: true, x: M, y: 2.2, w: 6.5, h: 0.3, fontSize: 13, bold: true, color: C.aqua, charSpacing: 3 });
    const t = text(s, "Strategy & Performance Review", { x: M, y: 2.6, w: 6.6, h: 1.9, fontFace: HEAD, fontSize: 50, bold: true, color: C.white, valign: "top" });
    const sub = text(s, "Where we stand, where the market is moving, and how we will grow to $1.2 billion by FY2029.", { x: M, y: 4.6, w: 6.0, h: 0.8, fontSize: 17, color: "C9C5EE" });
    const meta = text(s, "Executive Leadership Team   |   October 2026   |   All figures illustrative", { x: M, y: 6.3, w: 6.5, h: 0.3, fontSize: 12, color: "8E8AB8" });
    anim(s, "fade", rings, { t: "with", dur: 900, stagger: 150 });
    anim(s, "wipeUp", bars, { t: "with", dur: 450, stagger: 60, delay: 200 });
    anim(s, "zoom", glow, { dur: 400 });
    anim(s, "fade", [brand, kick], { t: "with", delay: 200 });
    anim(s, "wipeRight", t, { dur: 600 });
    anim(s, "fade", [sub, meta], { stagger: 150 });
    s.addNotes("Cover. Replace the review name, date and audience. The skyline of bars is built from editable shapes.");
  }

  /* ---------- 2. Agenda ---------- */
  s = slide("VANTA Light", "Opening", "AGENDA", "Seven chapters, one growth story");
  {
    const items = [
      ["01", "Performance", "Revenue, margins and cash", C.violet],
      ["02", "Market", "Size, momentum and competition", C.aqua],
      ["03", "Customers & Sales", "Pipeline, retention and loyalty", C.coral],
      ["04", "Operations", "Delivery, quality and productivity", C.saffron],
      ["05", "Growth", "Opportunities worth pursuing", C.violet],
      ["06", "Outlook", "Forecasts, scenarios and risks", C.aqua],
      ["07", "Plan", "Priorities, roadmap and KPIs", C.coral],
    ];
    const cw = (CW - 3 * 0.3) / 4, ch = 2.35;
    const steps = [];
    items.forEach(([n, t, d, col], i) => {
      const r = Math.floor(i / 4), c = i % 4;
      const x = M + c * (cw + 0.3), y = TOP + 0.1 + r * (ch + 0.3);
      const g = [card(s, x, y, cw, ch)];
      g.push(text(s, n, { x: x + 0.3, y: y + 0.28, w: 1.2, h: 0.6, fontFace: HEAD, fontSize: 32, bold: true, color: col }));
      g.push(text(s, t, { x: x + 0.3, y: y + 1.05, w: cw - 0.6, h: 0.4, fontFace: HEAD, fontSize: 19, bold: true }));
      g.push(text(s, d, { x: x + 0.3, y: y + 1.5, w: cw - 0.6, h: 0.6, fontSize: 14, color: C.muted }));
      steps.push(g);
    });
    // summary tile in the 8th slot
    const x = M + 3 * (cw + 0.3), y = TOP + 0.1 + ch + 0.3;
    const g = [card(s, x, y, cw, ch, { fill: C.night, noShadow: true })];
    g.push(text(s, "60 minutes", { x: x + 0.3, y: y + 0.35, w: cw - 0.6, h: 0.55, fontFace: HEAD, fontSize: 26, bold: true, color: C.white }));
    g.push(text(s, "45 minutes of review, 15 minutes for decisions on the FY2027 plan.", { x: x + 0.3, y: y + 1.0, w: cw - 0.6, h: 1.0, fontSize: 14, color: "C9C5EE" }));
    anim(s, "fade", "@ph", { t: "with" });
    steps.forEach((g2, i) => anim(s, "wipeUp", g2, { t: i === 0 ? "after" : "with", delay: i * 90, dur: 450 }));
    anim(s, "zoom", g, { dur: 450 });
  }

  /* ---------- 3. Executive summary ---------- */
  s = slide("VANTA Light", "Opening", "EXECUTIVE SUMMARY", "A record year that sets up the next three");
  {
    const msgs = [
      ["LuTrendingUp", C.violet, C.vTint, "Growth held at 16%", "Revenue reached $772M, up 16.3%, with every quarter ahead of the prior year."],
      ["LuGauge", C.aqua, C.aTint, "Margins expanded again", "EBITDA margin rose 1.5 points to 23.4% as scale and automation paid off."],
      ["LuUsers", C.coral, C.cTint, "Customers buy more", "Net revenue retention climbed to 119%; 389 new logos joined in FY2026."],
      ["LuRocket", C.saffron, C.sTint, "Clear path to $1.2B", "Six prioritised bets add up to $445M of revenue potential by FY2029."],
    ];
    anim(s, "fade", "@ph", { t: "with" });
    msgs.forEach(([ic, col, tint, h, b], i) => {
      const y = TOP + 0.05 + i * 1.27;
      const g = [card(s, M, y, 7.4, 1.1)];
      const icn = [];
      g.push(text(s, h, { x: M + 1.2, y: y + 0.16, w: 5.9, h: 0.36, fontFace: HEAD, fontSize: 17, bold: true }));
      g.push(text(s, b, { x: M + 1.2, y: y + 0.52, w: 6.0, h: 0.5, fontSize: 14, color: C.muted }));
      s._tmp = { g, ic, col, tint, y };
      steps3.push(s._tmp);
    });
    for (const st of steps3) {
      const [a, b] = await iconIn(s, st.ic, M + 0.3, st.y + 0.23, 0.64, st.tint, st.col);
      anim(s, "wipeRight", [...st.g, a, b], { dur: 450, stagger: 0 });
    }
    steps3.length = 0;
    // right: revenue headline chart
    const cc = chartCard(s, 8.3, TOP + 0.05, 4.43, 4.91, "Revenue, $M", "Five-year trajectory");
    const ch = chart(s, pres.charts.BAR, [{ name: "Revenue", labels: YEARS, values: REV }], 8.45, TOP + 0.95, 4.13, 3.9, co({
      barDir: "col", barGapWidthPct: 55, chartColors: [C.lavender, C.lavender, C.lavender, C.lavender, C.violet], invertedColors: [C.lavender],
      showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 900,
    }));
    anim(s, "fade", cc, { t: "with" });
    anim(s, "wipeUp", ch, { t: "with", build: "category", dur: 350 });
  }

  /* ---------- 4. Year at a glance (dark) ---------- */
  s = slide("VANTA Dark", "Opening", "FY2026 AT A GLANCE", "The numbers that defined the year");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const big = text(s, "$772M", { x: M, y: TOP + 0.1, w: 5.4, h: 1.4, fontFace: HEAD, fontSize: 80, bold: true, color: C.white });
    const bigl = text(s, "Total revenue, up 16.3% year on year — the fourth consecutive year of double-digit growth.", { x: M, y: TOP + 1.6, w: 5.0, h: 0.9, fontSize: 16, color: "C9C5EE" });
    anim(s, "zoom", big, { dur: 600 });
    anim(s, "fade", bigl);
    const tiles = [
      ["EBITDA MARGIN", "23.4%", "+1.5 pts", C.aqua],
      ["FREE CASH FLOW", "$118M", "+27% YoY", C.saffron],
      ["NET REVENUE RETENTION", "119%", "+4 pts", C.lavender],
      ["NEW CUSTOMERS", "389", "+21% YoY", C.coral],
    ];
    const tw = 3.05, th = 1.45;
    tiles.forEach(([l, v, d, col], i) => {
      const x = 6.55 + (i % 2) * (tw + 0.2), y = TOP + 0.1 + Math.floor(i / 2) * (th + 0.2);
      anim(s, "wipeUp", kpi(s, x, y, tw, th, { value: v, labelText: l, delta: d, deltaColor: col, color: C.white, dark: true }), { t: i ? "with" : "after", delay: i * 120, dur: 450 });
    });
    const q = [...QREV.FY25, ...QREV.FY26];
    const cn = card(s, M, 5.0, CW, 1.65, { fill: C.night2, noShadow: true });
    const lab = text(s, "QUARTERLY REVENUE, $M — FY25 vs FY26", { x: M + 0.3, y: 5.12, w: 5, h: 0.26, fontSize: 11, bold: true, color: "B8B4E6", charSpacing: 1.5 });
    const ch = chart(s, pres.charts.BAR, [
      { name: "FY25", labels: ["Q1", "Q2", "Q3", "Q4"], values: QREV.FY25 },
      { name: "FY26", labels: ["Q1", "Q2", "Q3", "Q4"], values: QREV.FY26 },
    ], M + 0.2, 5.38, CW - 0.4, 1.25, darkChart({
      barDir: "bar", barGrouping: "clustered", barGapWidthPct: 40, chartColors: ["4A4578", C.aqua], showValue: true, dataLabelPosition: "outEnd",
      valAxisHidden: true, valGridLine: { style: "none" }, showLegend: true, legendPos: "r", catAxisOrientation: "maxMin", valAxisMaxVal: 240, dataLabelFontSize: 9,
    }));
    anim(s, "fade", [cn, lab]);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 500 });
    q.length;
  }

  /* ---------- 5. Chapter 01 ---------- */
  pres.addSection({ title: "01 Performance" });
  await chapter("01", "Performance", "How revenue, margins and cash developed across FY2026.", ["Revenue trajectory & bridge", "Segment and regional mix", "Margins, costs and cash"], "01 Performance");

  /* ---------- 6. Quarterly revenue area ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Twenty quarters of uninterrupted growth", { transition: "fade" });
  {
    anim(s, "fade", "@ph", { t: "with" });
    const labels = [], vals = [];
    YEARS.forEach((y) => QREV[y].forEach((v, i) => { labels.push(`Q${i + 1} ${y}`); vals.push(v); }));
    const cc = chartCard(s, M, TOP, 8.45, 5.0, "Quarterly revenue, $M", "Q1 FY22 – Q4 FY26");
    const ch = chart(s, pres.charts.AREA, [{ name: "Revenue", labels, values: vals }], M + 0.15, TOP + 0.85, 8.15, 4.05, co({
      chartColors: [C.violet], chartColorsOpacity: 85, valAxisMinVal: 0, valAxisMaxVal: 240, valAxisMajorUnit: 60, catAxisLabelFontSize: 9, catAxisLabelRotate: -45,
    }));
    const k1 = kpi(s, 9.35, TOP, 3.38, 1.55, { value: "+127%", labelText: "Q4 FY26 vs Q1 FY22", delta: "$94M → $213M per quarter" });
    const k2 = kpi(s, 9.35, TOP + 1.75, 3.38, 1.55, { value: "18.8%", labelText: "COMPOUND ANNUAL GROWTH", delta: "Q1 FY22 → Q4 FY26, annualised", deltaColor: C.violet });
    const k3 = kpi(s, 9.35, TOP + 3.5, 3.38, 1.5, { value: "$213M", labelText: "RECORD QUARTER", delta: "Q4 FY26, +15.8% YoY", color: C.coral, deltaColor: C.coral });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", dur: 1000 });
    anim(s, "fade", [...k1], {});
    anim(s, "fade", [...k2], {});
    anim(s, "fade", [...k3], {});
  }

  /* ---------- 7. Revenue bridge (waterfall) ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "What added $108M to revenue this year");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const cats = ["FY25 revenue", "New logos", "Expansion", "Pricing", "Churn", "FX", "FY26 revenue"];
    const base = [0, 664, 718, 764, 770, 770, 0];
    const inc = [0, 54, 46, 21, 0, 2, 0];
    const dec = [0, 0, 0, 0, 15, 0, 0];
    const tot = [664, 0, 0, 0, 0, 0, 772];
    const cc = chartCard(s, M, TOP, 8.6, 5.0, "Revenue bridge FY25 → FY26, $M", "Axis starts at $600M to show movement clearly");
    const ch = chart(s, pres.charts.BAR, [
      { name: "_base", labels: cats, values: base },
      { name: "Total", labels: cats, values: tot },
      { name: "Increase", labels: cats, values: inc },
      { name: "Decrease", labels: cats, values: dec },
    ], M + 0.15, TOP + 0.85, 8.3, 4.05, co({
      barDir: "col", barGrouping: "stacked", barGapWidthPct: 45, chartColors: [C.white, C.violet, C.aqua, C.coral],
      valAxisMinVal: 600, valAxisMaxVal: 800, valAxisMajorUnit: 50, showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.white, catAxisLabelFontSize: 11,
    }));
    const ins = insight(s, 9.5, TOP, 3.23, 5.0, "Reading the bridge", [
      "New logos and expansion delivered $100M — 93% of the gain.",
      "Pricing added $21M with no measurable rise in churn.",
      "Churn of $15M was 2.3% of opening revenue, a record low.",
    ]);
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "category", dur: 350 });
    anim(s, "fade", ins);
  }

  /* ---------- 8. Segment mix stacked ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Platform Software now drives almost half of revenue");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const cc = chartCard(s, M, TOP, CW, 5.0, "Revenue by segment, $M", null);
    const ch = chart(s, pres.charts.BAR, Object.entries(SEG).map(([n, v]) => ({ name: n, labels: YEARS, values: v })), M + 0.15, TOP + 0.6, 8.3, 4.3, co({
      barDir: "col", barGrouping: "stacked", barGapWidthPct: 60, showValue: true, dataLabelPosition: "ctr", dataLabelColor: C.white, showLegend: true, legendPos: "t",
      valAxisMaxVal: 800, valAxisMajorUnit: 200,
    }));
    const facts = [
      ["45%", "Platform Software share of FY26 revenue, up from 37% in FY22", C.violet],
      ["+27%", "Data & Analytics growth in FY26 — the fastest segment", C.aqua],
      ["−1%", "Advisory, now managed for margin rather than volume", C.coral],
    ];
    const fn = [];
    facts.forEach(([v, d, col], i) => {
      const y = TOP + 0.65 + i * 1.42;
      fn.push([text(s, v, { x: 9.3, y, w: 3.1, h: 0.6, fontFace: HEAD, fontSize: 30, bold: true, color: col }), text(s, d, { x: 9.3, y: y + 0.6, w: 3.1, h: 0.7, fontSize: 13, color: C.muted })]);
    });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series", dur: 450 });
    fn.forEach((f) => anim(s, "fade", f, { dur: 400 }));
  }

  /* ---------- 9. Segment donut + table ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Each segment plays a distinct role in the portfolio");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const segNames = Object.keys(SEG);
    const fy26 = segNames.map((n) => SEG[n][4]);
    const cc = card(s, M, TOP, 4.6, 5.0);
    const ch = chart(s, pres.charts.DOUGHNUT, [{ name: "FY26 revenue", labels: segNames, values: fy26 }], M + 0.2, TOP + 0.2, 4.2, 4.0, co({
      holeSize: 62, showPercent: true, showValue: false, dataLabelColor: C.white, dataLabelFontSize: 11, showLegend: false, chartColors: SERIES.slice(0, 4), plotArea: undefined,
    }));
    const ctr1 = text(s, "$772M", { x: M + 1.3, y: TOP + 1.85, w: 2.0, h: 0.5, fontFace: HEAD, fontSize: 26, bold: true, align: "center", color: C.ink });
    const ctr2 = text(s, "FY26 revenue", { x: M + 1.3, y: TOP + 2.35, w: 2.0, h: 0.3, fontSize: 12, align: "center", color: C.muted });
    const legend = [];
    segNames.forEach((n, i) => {
      const x = M + 0.35 + (i % 2) * 2.1, y = TOP + 4.25 + Math.floor(i / 2) * 0.33;
      legend.push(circle(s, x, y + 0.06, 0.14, SERIES[i]), text(s, n, { x: x + 0.22, y, w: 1.85, h: 0.28, fontSize: 11, color: C.ink }));
    });
    const hdr = (t) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.night }, fontSize: 12, valign: "middle" } });
    const rows = [[hdr("Segment"), hdr("FY26 $M"), hdr("Growth"), hdr("Gross margin"), hdr("Role")]];
    const meta = [["21.7%", "72%", "Growth engine"], ["10.0%", "48%", "Recurring base"], ["26.5%", "66%", "Fastest riser"], ["−1.4%", "41%", "Door opener"]];
    segNames.forEach((n, i) => rows.push([
      { text: n, options: { bold: true, color: C.ink } }, { text: fmt(fy26[i]), options: { align: "right" } },
      { text: meta[i][0], options: { align: "right", color: i === 3 ? C.coral : C.aquaInk, bold: true } }, { text: meta[i][1], options: { align: "right" } }, { text: meta[i][2], options: { color: C.muted } },
    ]));
    rows.push([{ text: "Total", options: { bold: true } }, { text: "772", options: { bold: true, align: "right" } }, { text: "16.3%", options: { bold: true, align: "right" } }, { text: "61%", options: { bold: true, align: "right" } }, { text: "", options: {} }]);
    const tn = nm(s, "table");
    s.addTable(rows, { x: 5.5, y: TOP, w: 7.23, colW: [2.05, 1.1, 1.05, 1.33, 1.7], rowH: 0.52, fontFace: BODY, fontSize: 13, color: C.ink, fill: { color: C.white }, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.1, 0, 0.1], objectName: tn });
    const ins = insight(s, 5.5, TOP + 3.35, 7.23, 1.65, "Portfolio logic", ["Platform and Data fund growth; Managed Services anchors recurring revenue and cash."], { fontSize: 14 });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 400 });
    anim(s, "fade", [ctr1, ctr2, ...legend], { t: "with" });
    anim(s, "wipeDown", tn, { dur: 600 });
    anim(s, "fade", ins);
  }

  /* ---------- 10. Margin combo ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Scale is turning into profitability");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const ebitda = REV.map((r, i) => Math.round(r * EBITDA_M[i] / 10) / 10);
    const cc = chartCard(s, M, TOP, 7.9, 5.0, "EBITDA ($M, columns) and EBITDA margin (%, line)", null);
    const ch = chart(s, [
      { type: pres.charts.BAR, data: [{ name: "EBITDA $M", labels: YEARS, values: ebitda }], options: { barDir: "col", chartColors: [C.violet], barGapWidthPct: 70, showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.white } },
      { type: pres.charts.LINE, data: [{ name: "EBITDA margin %", labels: YEARS, values: EBITDA_M }], options: { chartColors: [C.coral], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 9, secondaryValAxis: true, secondaryCatAxis: true, showValue: true, dataLabelPosition: "t", dataLabelFormatCode: '0.0"%"' } },
    ], null, M + 0.15, TOP + 0.6, 7.6, 4.3, co({
      showValue: true, showLegend: true, legendPos: "t",
      valAxes: [{ showValAxisTitle: false, valAxisMinVal: 0, valAxisMaxVal: 250, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }, { showValAxisTitle: false, valAxisMinVal: 0, valAxisMaxVal: 30, valGridLine: { style: "none" }, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }],
      catAxes: [{ catAxisTitle: "" }, { catAxisHidden: true }],
      dataLabelPosition: "t",
    }));
    const r = 8.8;
    const k1 = kpi(s, r, TOP, 3.93, 1.5, { value: "$180.6M", labelText: "FY26 EBITDA", delta: "+24.2% year on year" });
    const k2 = kpi(s, r, TOP + 1.7, 3.93, 1.5, { value: "+5.6 pts", labelText: "MARGIN GAIN SINCE FY22", delta: "17.8% → 23.4%", color: C.coral, deltaColor: C.coral });
    const ins = insight(s, r, TOP + 3.4, 3.93, 1.6, "Operating leverage", ["Revenue grew 16.3%; total costs grew 14.0%."], { fontSize: 14 });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series", dur: 600 });
    anim(s, "fade", k1); anim(s, "fade", k2); anim(s, "fade", ins);
  }

  /* ---------- 11. P&L table ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Income statement summary");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const H1 = (t, al) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.violet }, align: al || "right" } });
    const row = (l, a, b, chg, o = {}) => [
      { text: l, options: { bold: !!o.bold, color: C.ink, fill: { color: o.fill || C.white } } },
      { text: a, options: { align: "right", bold: !!o.bold, fill: { color: o.fill || C.white } } },
      { text: b, options: { align: "right", bold: !!o.bold, fill: { color: o.fill || C.white } } },
      { text: chg, options: { align: "right", bold: true, color: o.neg ? C.coral : C.aquaInk, fill: { color: o.fill || C.white } } },
    ];
    const rows = [
      [H1("$ millions", "left"), H1("FY25"), H1("FY26"), H1("Change")],
      row("Revenue", "664.0", "772.0", "+16.3%", { bold: true }),
      row("Cost of revenue", "(266.9)", "(299.5)", "+12.2%", { neg: true }),
      row("Gross profit", "397.1", "472.5", "+19.0%", { bold: true, fill: C.vTint }),
      row("Gross margin", "59.8%", "61.2%", "+1.4 pts"),
      row("Operating expenses", "(251.7)", "(291.9)", "+16.0%", { neg: true }),
      row("EBITDA", "145.4", "180.6", "+24.2%", { bold: true, fill: C.vTint }),
      row("Depreciation & amortisation", "(28.3)", "(31.4)", "+11.0%", { neg: true }),
      row("Operating profit (EBIT)", "117.1", "149.2", "+27.4%", { bold: true }),
      row("Net income", "86.4", "110.9", "+28.4%", { bold: true, fill: C.vTint }),
    ];
    const tn = nm(s, "table");
    s.addTable(rows, { x: M, y: TOP, w: 7.6, colW: [3.4, 1.4, 1.4, 1.4], rowH: 0.47, fontFace: BODY, fontSize: 14, color: C.ink, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.14, 0, 0.14], objectName: tn });
    const cc = chartCard(s, 8.5, TOP, 4.23, 3.1, "Margin profile, % of revenue", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "FY25", labels: ["Gross", "EBITDA", "EBIT", "Net"], values: [59.8, 21.9, 17.6, 13.0] },
      { name: "FY26", labels: ["Gross", "EBITDA", "EBIT", "Net"], values: [61.2, 23.4, 19.3, 14.4] },
    ], 8.6, TOP + 0.55, 4.03, 2.5, co({ barDir: "col", barGapWidthPct: 50, chartColors: [C.lavender, C.violet], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9, valAxisHidden: true, valGridLine: { style: "none" }, showLegend: true, legendPos: "t", valAxisMaxVal: 75, dataLabelFormatCode: "0.0" }));
    const ins = insight(s, 8.5, TOP + 3.3, 4.23, 1.7, "Bottom line", ["Net income grew 28%, almost twice the rate of revenue."], { fontSize: 14 });
    anim(s, "wipeDown", tn, { dur: 700 });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
    anim(s, "fade", ins);
  }

  /* ---------- 12. Cost structure ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Cost discipline funds more R&D");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const cats = ["FY24", "FY25", "FY26"];
    const cc = chartCard(s, M, TOP, 7.6, 5.0, "Operating expenses as % of revenue", "Total opex: 38.3% → 37.9% → 37.8%");
    const ch = chart(s, pres.charts.BAR, [
      { name: "Sales & marketing", labels: cats, values: [18.4, 17.9, 17.2] },
      { name: "Research & development", labels: cats, values: [13.2, 13.6, 14.1] },
      { name: "General & administrative", labels: cats, values: [6.7, 6.4, 6.5] },
    ], M + 0.15, TOP + 0.85, 7.3, 4.05, co({
      barDir: "bar", barGrouping: "stacked", barGapWidthPct: 45, catAxisOrientation: "maxMin", showValue: true, dataLabelPosition: "ctr", dataLabelColor: C.white, dataLabelFormatCode: "0.0",
      showLegend: true, legendPos: "t", valAxisMaxVal: 40, valAxisMajorUnit: 10, chartColors: [C.violet, C.aqua, C.saffron], catAxisLabelFontSize: 12,
    }));
    const items = [
      ["LuCpu", C.violet, C.vTint, "R&D up to 14.1%", "An extra $19M funds AI features and platform reliability."],
      ["LuHandshake", C.aqua, C.aTint, "Sales efficiency", "Partner-led deals cut acquisition cost per $ of new revenue by 9%."],
      ["LuBuilding2", C.saffron, C.sTint, "Lean overhead", "G&A held at 6.5% despite 9% headcount growth."],
    ];
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series" });
    for (let i = 0; i < items.length; i++) {
      const [ic, col, tint, h, b] = items[i];
      const y = TOP + i * 1.72;
      const g = [card(s, 8.5, y, 4.23, 1.56)];
      const [a, bb] = await iconIn(s, ic, 8.75, y + 0.25, 0.56, tint, col);
      g.push(a, bb);
      g.push(text(s, h, { x: 9.5, y: y + 0.22, w: 3.05, h: 0.35, fontFace: HEAD, fontSize: 16, bold: true }));
      g.push(text(s, b, { x: 9.5, y: y + 0.6, w: 3.05, h: 0.85, fontSize: 13, color: C.muted }));
      anim(s, "wipeLeft", g, { dur: 450 });
    }
  }

  /* ---------- 13. Cash flow ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Free cash flow has tripled in four years");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const ocf = [61, 79, 102, 128, 159], capex = [22, 26, 31, 35, 41], fcf = ocf.map((v, i) => v - capex[i]);
    const conv = fcf.map((f, i) => Math.round(f / (REV[i] * EBITDA_M[i] / 100) * 100));
    const k = [
      ["$118M", "FY26 FREE CASH FLOW", "+27% vs FY25", C.violet],
      ["15.3%", "FCF MARGIN", "Up from 9.5% in FY22", C.aqua],
      [conv[4] + "%", "CASH CONVERSION", "FCF as share of EBITDA", C.coral],
    ];
    k.forEach(([v, l, d, col], i) => anim(s, "fade", kpi(s, M + i * 4.12, TOP, 3.89, 1.45, { value: v, labelText: l, delta: d, color: col, deltaColor: C.muted }), { t: i ? "with" : "after", delay: i * 120 }));
    const cc = chartCard(s, M, TOP + 1.65, CW, 3.35, "Operating cash flow, capital expenditure and free cash flow, $M", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "Operating cash flow", labels: YEARS, values: ocf },
      { name: "Capex", labels: YEARS, values: capex },
      { name: "Free cash flow", labels: YEARS, values: fcf },
    ], M + 0.15, TOP + 2.1, CW - 0.3, 2.85, co({ barDir: "col", barGapWidthPct: 70, barOverlapPct: -10, chartColors: [C.violet, C.lavender, C.aqua], showValue: true, dataLabelPosition: "outEnd", showLegend: true, legendPos: "r", valAxisMaxVal: 180, valAxisMajorUnit: 60 }));
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
  }

  /* ---------- 14. Regional performance ---------- */
  s = slide("VANTA Light", "01 Performance", "01 · PERFORMANCE", "Asia-Pacific is our fastest-growing large region");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const cc = chartCard(s, M, TOP, 6.9, 5.0, "FY26 revenue by region, $M", null);
    const ch = chart(s, pres.charts.BAR, [{ name: "Revenue", labels: REGIONS.map((r) => r[0]), values: REGIONS.map((r) => r[1]) }], M + 0.15, TOP + 0.6, 6.6, 4.3, co({
      barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 45, chartColors: [C.violet], showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 12, valAxisMaxVal: 400,
    }));
    const cc2 = chartCard(s, 7.75, TOP, 4.98, 5.0, "Year-on-year growth, %", null);
    const ch2 = chart(s, pres.charts.BAR, [{ name: "Growth %", labels: REGIONS.map((r) => r[0]), values: REGIONS.map((r) => r[2]) }], 7.9, TOP + 0.6, 4.68, 2.9, co({
      barDir: "col", barGapWidthPct: 45, chartColors: [C.aqua, C.aqua, C.coral, C.aqua, C.aqua], showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 10, valAxisMaxVal: 32,
    }));
    const t1 = text(s, [
      { text: "Asia-Pacific ", options: { bold: true, color: C.coral } },
      { text: "added $27M at 24% growth. Middle East & Africa grows faster from a small base.", options: { color: C.ink } },
    ], { x: 8.05, y: TOP + 3.65, w: 4.4, h: 1.2, fontSize: 14 });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 350 });
    anim(s, "fade", cc2);
    anim(s, "wipeUp", ch2, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", t1);
  }

  /* ---------- 15. Chapter 02 ---------- */
  pres.addSection({ title: "02 Market" });
  await chapter("02", "Market", "A large, fragmented market where we are gaining share.", ["Market size and momentum", "Competitive positioning", "What buyers value"], "02 Market");

  /* ---------- 16. TAM SAM SOM ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "A $48B market with ample headroom");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const cx = 3.6, bottom = TOP + 5.0;
    const circ = [[5.0, C.vTint], [3.4, "D6CEFD"], [1.8, C.violet]];
    const cn = circ.map(([d, f]) => { const n = nm(s, "mkt"); s.addShape(pres.shapes.OVAL, { x: cx - d / 2, y: bottom - d, w: d, h: d, fill: { color: f }, line: { color: C.white, width: 2 }, objectName: n }); return n; });
    const lab = (big, small, y, col, scol) => text(s, [{ text: big, options: { bold: true, fontSize: 22, fontFace: HEAD, breakLine: true } }, { text: small, options: { fontSize: 11, bold: true, color: scol } }], { x: cx - 1.1, y, w: 2.2, h: 0.75, align: "center", color: col });
    const l1 = lab("$48B", "TAM", bottom - 5.0 + 0.35, C.violet, C.muted);
    const l2 = lab("$14.2B", "SAM", bottom - 3.4 + 0.3, C.violet, C.muted);
    const l3 = lab("$1.2B", "TARGET", bottom - 1.8 + 0.5, C.white, "D6CEFD");
    const defs = [
      ["Total addressable market", "$48B", "Enterprise workflow, data and managed platform spend across all regions (2026).", C.lavender],
      ["Serviceable available market", "$14.2B", "Mid-market and enterprise buyers in our 23 active countries.", C.violet],
      ["Target by FY2029", "$1.2B", "Our revenue goal — 8.3% of today's SAM, up from 5.4%.", C.coral],
    ];
    anim(s, "zoom", cn[0], { dur: 450 }); anim(s, "fade", l1, { t: "with" });
    anim(s, "zoom", cn[1], { dur: 450 }); anim(s, "fade", l2, { t: "with" });
    anim(s, "zoom", cn[2], { dur: 450 }); anim(s, "fade", l3, { t: "with" });
    defs.forEach(([h, v, d, col], i) => {
      const y = TOP + 0.1 + i * 1.65;
      const g = [card(s, 7.0, y, 5.73, 1.45)];
      g.push(circle(s, 7.3, y + 0.33, 0.22, col));
      g.push(text(s, h, { x: 7.7, y: y + 0.25, w: 3.6, h: 0.35, fontFace: HEAD, fontSize: 16, bold: true }));
      g.push(text(s, v, { x: 11.0, y: y + 0.22, w: 1.5, h: 0.4, fontFace: HEAD, fontSize: 20, bold: true, color: C.violet, align: "right" }));
      g.push(text(s, d, { x: 7.7, y: y + 0.68, w: 4.8, h: 0.6, fontSize: 13, color: C.muted }));
      anim(s, "wipeLeft", g, { t: i ? "after" : "after", dur: 400 });
    });
  }

  /* ---------- 17. Market vs company growth ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "We are growing almost twice as fast as the market");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const idxCo = REV.map((r) => Math.round(r / REV[0] * 100));
    const idxMk = [100, 109, 119, 130, 141];
    const cc = chartCard(s, M, TOP, 8.2, 5.0, "Revenue index (FY22 = 100)", "Company revenue vs addressable market spend");
    const ch = chart(s, pres.charts.LINE, [
      { name: "Our revenue", labels: YEARS, values: idxCo },
      { name: "Market", labels: YEARS, values: idxMk },
    ], M + 0.15, TOP + 0.85, 7.9, 4.05, co({ chartColors: [C.violet, C.aqua], lineSize: 3.5, lineDataSymbol: "circle", lineDataSymbolSize: 10, showValue: true, dataLabelPosition: "t", showLegend: true, legendPos: "t", valAxisMinVal: 80, valAxisMaxVal: 200, valAxisMajorUnit: 30 }));
    const k1 = kpi(s, 9.1, TOP, 3.63, 1.55, { value: "17.0%", labelText: "OUR REVENUE CAGR", delta: "FY22–FY26" });
    const k2 = kpi(s, 9.1, TOP + 1.75, 3.63, 1.55, { value: "9.0%", labelText: "MARKET CAGR", delta: "FY22–FY26", color: C.aqua, deltaColor: C.muted });
    const ins = insight(s, 9.1, TOP + 3.5, 3.63, 1.5, "Share gain", ["SAM share up from 4.1% to 5.4%."], { fontSize: 14 });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 900 });
    anim(s, "fade", k1); anim(s, "fade", k2); anim(s, "fade", ins);
  }

  /* ---------- 18. Competitive scatter ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "We combine scale with above-market growth");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const comps = [["Us", 5.4, 16.3], ["Competitor A", 9.8, 6.1], ["Competitor B", 7.2, 8.4], ["Competitor C", 4.1, 12.7], ["Competitor D", 3.0, 21.5], ["Competitor E", 2.2, 4.0]];
    const cc = chartCard(s, M, TOP, 8.2, 5.0, "Market share vs revenue growth, FY26", "x: share of SAM (%)   ·   y: revenue growth (%)");
    const ch = chart(s, pres.charts.SCATTER, [
      { name: "Share", values: comps.map((c) => c[1]) },
      { name: "Growth", values: comps.map((c) => c[2]), labels: comps.map((c) => c[0]) },
    ], M + 0.15, TOP + 0.85, 7.9, 4.05, co({
      lineSize: 0, lineDataSymbol: "circle", lineDataSymbolSize: 16, chartColors: [C.violet], showLabel: true, dataLabelFormatScatter: "custom", dataLabelPosition: "r",
      valAxisMinVal: 0, valAxisMaxVal: 25, valAxisMajorUnit: 5, catAxisMinVal: 0, catAxisMaxVal: 12, catAxisMajorUnit: 2, catGridLine: { color: C.grid, size: 0.75 },
    }));
    const quad = [
      ["Scale leaders", "A and B hold share but grow below the 9% market rate.", C.lavender],
      ["Challengers", "D grows fastest from a small base; watch its mid-market push.", C.coral],
      ["Our position", "The only player above 5% share growing faster than 15%.", C.violet],
    ];
    anim(s, "fade", cc);
    anim(s, "zoom", ch, { t: "with", dur: 600 });
    quad.forEach(([h, d, col], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, 9.1, y, 3.63, 1.56)];
      g.push(circle(s, 9.35, y + 0.3, 0.2, col));
      g.push(text(s, h, { x: 9.7, y: y + 0.22, w: 2.85, h: 0.35, fontFace: HEAD, fontSize: 16, bold: true }));
      g.push(text(s, d, { x: 9.35, y: y + 0.65, w: 3.2, h: 0.8, fontSize: 13, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    });
  }

  /* ---------- 19. Market share donut ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "The top five players hold under a third of the market");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const share = [["Competitor A", 9.8], ["Competitor B", 7.2], ["Us", 5.4], ["Competitor C", 4.1], ["Competitor D", 3.0], ["Long tail (40+ vendors)", 70.5]];
    const cc = card(s, M, TOP, 5.6, 5.0);
    const ch = chart(s, pres.charts.DOUGHNUT, [{ name: "Share of SAM", labels: share.map((x) => x[0]), values: share.map((x) => x[1]) }], M + 0.3, TOP + 0.3, 5.0, 4.4, co({
      holeSize: 58, chartColors: [C.lavender, "C9C0FC", C.violet, C.aqua, C.saffron, C.track], showPercent: false, showValue: true, dataLabelFormatCode: '0.0"%"', dataLabelColor: C.ink, dataLabelFontSize: 10, showLegend: false, plotArea: undefined,
    }));
    const ctr = text(s, [{ text: "29.5%", options: { fontFace: HEAD, fontSize: 28, bold: true, color: C.violet, breakLine: true } }, { text: "held by top five", options: { fontSize: 12, color: C.muted } }], { x: M + 1.8, y: TOP + 2.0, w: 2.0, h: 0.95, align: "center" });
    const rows = share.map(([n, v], i) => [n, v]);
    const lg = [];
    rows.forEach(([n, v], i) => {
      const y = TOP + 0.1 + i * 0.52;
      const col = [C.lavender, "C9C0FC", C.violet, C.aqua, C.saffron, "C9C6DE"][i];
      lg.push(rect(s, 6.6, y + 0.08, 0.28, 0.28, col, { round: 0.05 }));
      lg.push(text(s, n, { x: 7.05, y: y + 0.06, w: 3.6, h: 0.32, fontSize: 14, bold: n === "Us", color: n === "Us" ? C.violet : C.ink }));
      lg.push(text(s, v.toFixed(1) + "%", { x: 11.0, y: y + 0.06, w: 1.6, h: 0.32, fontSize: 14, bold: true, align: "right" }));
    });
    const ins = insight(s, 6.6, TOP + 3.35, 6.13, 1.65, "Consolidation opportunity", ["40+ subscale vendors make targeted acquisitions a credible lever."], { fontSize: 14 });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", ctr, { t: "with" });
    anim(s, "fade", lg, { dur: 400 });
    anim(s, "fade", ins);
  }

  /* ---------- 20. Demand drivers ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "Buyers prioritise automation and security");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const d = [["Automation & efficiency", 68], ["Data security & compliance", 61], ["Integration with existing stack", 54], ["Total cost of ownership", 47], ["Real-time analytics", 42], ["Vendor support quality", 33]];
    const cc = chartCard(s, M, TOP, 7.9, 5.0, "Share of buyers ranking each factor in their top three, %", "Illustrative buyer survey, n = 640 decision-makers");
    const ch = chart(s, pres.charts.BAR, [{ name: "% of buyers", labels: d.map((x) => x[0]), values: d.map((x) => x[1]) }], M + 0.15, TOP + 0.85, 7.6, 4.05, co({
      barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 40, chartColors: [C.violet, C.violet, C.lavender, C.lavender, C.lavender, C.lavender], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 12, valAxisMaxVal: 80,
    }));
    const pts = [
      ["LuZap", "Automation leads", "Our workflow engine maps directly to the #1 buying criterion."],
      ["LuShieldCheck", "Security is table stakes", "Certifications should feature in every proposal, not only in procurement."],
      ["LuLayers", "Integration decides deals", "Prebuilt connectors shorten evaluations by about three weeks."],
    ];
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 300 });
    for (let i = 0; i < pts.length; i++) {
      const [ic, h, b] = pts[i];
      const y = TOP + i * 1.72;
      const g = [card(s, 8.8, y, 3.93, 1.56)];
      g.push(...await iconIn(s, ic, 9.05, y + 0.25, 0.52, C.vTint, C.violet));
      g.push(text(s, h, { x: 9.75, y: y + 0.24, w: 2.85, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true }));
      g.push(text(s, b, { x: 9.75, y: y + 0.62, w: 2.85, h: 0.85, fontSize: 13, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    }
  }

  /* ---------- 21. Market trends ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "Three shifts reshaping demand through 2029");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const tr = [
      ["LuSparkles", C.violet, C.vTint, "AI moves into workflows", "41%", "of buyers plan to embed AI agents in core processes by 2028.", [12, 19, 28, 41], "Adoption, %"],
      ["LuRefreshCw", C.aqua, C.aTint, "Usage-based buying", "36%", "of new contracts include a consumption component, up from 14% in 2023.", [14, 21, 29, 36], "Share of contracts, %"],
      ["LuScale", C.coral, C.cTint, "Vendor consolidation", "−22%", "fewer vendors per enterprise stack as CFOs rationalise spend.", [100, 94, 86, 78], "Vendors per stack, index"],
    ];
    const cw = (CW - 0.6) / 3;
    for (let i = 0; i < tr.length; i++) {
      const [ic, col, tint, h, v, d, series, cap] = tr[i];
      const x = M + i * (cw + 0.3), y = TOP;
      const g = [card(s, x, y, cw, 5.0)];
      g.push(...await iconIn(s, ic, x + 0.3, y + 0.3, 0.62, tint, col));
      g.push(text(s, h, { x: x + 0.3, y: y + 1.1, w: cw - 0.6, h: 0.4, fontFace: HEAD, fontSize: 18, bold: true }));
      g.push(text(s, v, { x: x + 0.3, y: y + 1.6, w: cw - 0.6, h: 0.65, fontFace: HEAD, fontSize: 36, bold: true, color: col }));
      g.push(text(s, d, { x: x + 0.3, y: y + 2.3, w: cw - 0.6, h: 0.8, fontSize: 13, color: C.muted }));
      g.push(text(s, cap, { x: x + 0.3, y: y + 3.15, w: cw - 0.6, h: 0.25, fontSize: 11, bold: true, color: C.muted2 }));
      const ch = chart(s, pres.charts.BAR, [{ name: cap, labels: ["2023", "2024", "2025", "2026"], values: series }], x + 0.2, y + 3.4, cw - 0.4, 1.5, co({
        barDir: "col", chartColors: [col], barGapWidthPct: 40, showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.white, dataLabelFontSize: 9, valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 10, valAxisMinVal: 0,
      }));
      anim(s, "wipeUp", g, { dur: 450 });
      anim(s, "wipeUp", ch, { t: "with", build: "category", dur: 250 });
    }
  }

  /* ---------- 22. Pricing benchmark ---------- */
  s = slide("VANTA Light", "02 Market", "02 · MARKET", "Our pricing is competitive where it matters most");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const tiers = ["Essential", "Professional", "Enterprise"];
    const cc = chartCard(s, M, TOP, 7.4, 5.0, "Average monthly price per seat, $", "Our list price vs median of five peers");
    const ch = chart(s, pres.charts.BAR, [
      { name: "Our price", labels: tiers, values: [42, 78, 132] },
      { name: "Peer median", labels: tiers, values: [45, 74, 141] },
    ], M + 0.15, TOP + 0.85, 7.1, 4.05, co({ barDir: "col", barGapWidthPct: 80, barOverlapPct: -5, chartColors: [C.violet, "C9C6DE"], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '"$"0', showLegend: true, legendPos: "t", valAxisMaxVal: 160, valAxisMajorUnit: 40, catAxisLabelFontSize: 13 }));
    const rows = [["Essential", "−7%", "Undercut to win SMB volume", C.aqua], ["Professional", "+5%", "Premium justified by automation", C.violet], ["Enterprise", "−6%", "Headroom for a value-based uplift", C.coral]];
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
    rows.forEach(([t, v, d, col], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, 8.3, y, 4.43, 1.56)];
      g.push(text(s, v, { x: 8.55, y: y + 0.3, w: 1.4, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color: col }));
      g.push(text(s, t + " vs peers", { x: 10.0, y: y + 0.3, w: 2.55, h: 0.32, fontSize: 14, bold: true }));
      g.push(text(s, d, { x: 10.0, y: y + 0.65, w: 2.55, h: 0.7, fontSize: 13, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    });
  }

  /* ---------- 23. Chapter 03 ---------- */
  pres.addSection({ title: "03 Customers & Sales" });
  await chapter("03", "Customers & Sales", "A healthier funnel, stronger retention and loyal customers.", ["Funnel and channel performance", "Retention and satisfaction", "Concentration and team results"], "03 Customers & Sales");

  /* ---------- 24. Sales funnel ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "From 18,400 leads to 389 new customers");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const st = [["Leads", 18400], ["Marketing-qualified", 7360], ["Sales-qualified", 2944], ["Opportunities", 1178], ["Won customers", 389]];
    // centred funnel on a sqrt scale so later stages stay visible; the label carries the true value
    const scale = st.map(([, v]) => Math.round(Math.sqrt(v) * 10) / 10);
    const mx = Math.max(...scale);
    const cc = chartCard(s, M, TOP, 7.9, 5.0, "FY26 sales funnel", "Bar width on a square-root scale; labels show actual counts");
    const ch = chart(s, pres.charts.BAR, [
      { name: "_base", labels: st.map((x) => x[0]), values: scale.map((v) => Math.round((mx - v) / 2 * 10) / 10) },
      { name: "Stage", labels: st.map((x) => x[0]), values: scale },
    ], M + 0.15, TOP + 0.85, 7.6, 4.05, co({
      barDir: "bar", barGrouping: "stacked", catAxisOrientation: "maxMin", barGapWidthPct: 18, chartColors: [C.white, C.violet], valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 12, catAxisLineShow: false, valAxisMaxVal: mx,
    }));
    const vals = st.map(([n, v], i) => text(s, fmt(v), { x: M + 2.2 + 0.0, y: TOP + 0.95 + i * 0.79, w: 5.4, h: 0.6, align: "center", valign: "middle", fontSize: 15, bold: true, color: C.white }));
    const conv = [["40%", "Lead → MQL"], ["40%", "MQL → SQL"], ["40%", "SQL → Opportunity"], ["33%", "Opportunity → Win"]];
    const cv = [];
    const ccard = card(s, 8.8, TOP, 3.93, 5.0);
    const hd = text(s, "Stage conversion", { x: 9.1, y: TOP + 0.22, w: 3.3, h: 0.32, fontSize: 15, bold: true });
    conv.forEach(([v, l], i) => {
      const y = TOP + 0.75 + i * 0.95;
      cv.push([text(s, v, { x: 9.1, y, w: 1.3, h: 0.5, fontFace: HEAD, fontSize: 26, bold: true, color: i === 3 ? C.coral : C.violet }), text(s, l, { x: 10.45, y: y + 0.1, w: 2.1, h: 0.32, fontSize: 13, color: C.muted })]);
    });
    const foot = text(s, "Lead-to-customer conversion: 2.1%", { x: 9.1, y: TOP + 4.5, w: 3.4, h: 0.3, fontSize: 13, bold: true, color: C.ink });
    anim(s, "fade", cc);
    anim(s, "wipeDown", ch, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", vals, { t: "with", stagger: 300, delay: 300 });
    anim(s, "fade", [ccard, hd]);
    cv.forEach((g) => anim(s, "fade", g, { dur: 350 }));
    anim(s, "fade", foot);
  }

  /* ---------- 25. Sales by channel ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "Digital self-serve is the fastest-growing channel");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const tot = [57, 58, 61, 60, 62, 64, 64, 65, 68, 68, 70, 75];
    const dShare = months.map((_, i) => 0.12 + i * 0.006); // 12% → 18.6%
    const pShare = months.map((_, i) => 0.30);
    const dig = tot.map((t, i) => Math.round(t * dShare[i] * 10) / 10);
    const par = tot.map((t, i) => Math.round(t * pShare[i] * 10) / 10);
    const dir = tot.map((t, i) => Math.round((t - dig[i] - par[i]) * 10) / 10);
    const cc = chartCard(s, M, TOP, 8.6, 5.0, "Monthly revenue by channel, FY26, $M", "Total FY26 revenue: $772M");
    const ch = chart(s, pres.charts.LINE, [
      { name: "Direct sales", labels: months, values: dir },
      { name: "Partners", labels: months, values: par },
      { name: "Digital self-serve", labels: months, values: dig },
    ], M + 0.15, TOP + 0.85, 8.3, 4.05, co({ chartColors: [C.violet, C.aqua, C.coral], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 7, showLegend: true, legendPos: "t", valAxisMinVal: 0, valAxisMaxVal: 50, valAxisMajorUnit: 10 }));
    const sum = (a) => Math.round(a.reduce((x, y) => x + y, 0));
    const sDir = sum(dir), sPar = sum(par), sDig = 772 - sDir - sPar;
    const k = [["DIRECT SALES", "$" + sDir + "M", "+11% YoY", C.violet], ["PARTNERS", "$" + sPar + "M", "+17% YoY", C.aqua], ["DIGITAL SELF-SERVE", "$" + sDig + "M", "+41% YoY", C.coral]];
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 800 });
    k.forEach(([l, v, d, col], i) => anim(s, "fade", kpi(s, 9.5, TOP + i * 1.72, 3.23, 1.56, { value: v, labelText: l, delta: d, color: col, deltaColor: col }), { dur: 400 }));
  }

  /* ---------- 26. Win rate & deal size ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "We win more often, and deals are getting larger");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const q = ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25", "Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26"];
    const cc = chartCard(s, M, TOP, CW, 3.4, "Average deal size ($k, columns) and win rate (%, line)", null);
    const ch = chart(s, [
      { type: pres.charts.BAR, data: [{ name: "Average deal size $k", labels: q, values: [118, 121, 124, 128, 131, 135, 139, 144] }], options: { barDir: "col", chartColors: [C.lavender], barGapWidthPct: 60, showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.ink } },
      { type: pres.charts.LINE, data: [{ name: "Win rate %", labels: q, values: [27, 28, 29, 30, 30, 31, 33, 34] }], options: { chartColors: [C.violet], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 9, secondaryValAxis: true, secondaryCatAxis: true, showValue: true, dataLabelPosition: "t", dataLabelFormatCode: '0"%"' } },
    ], null, M + 0.15, TOP + 0.55, CW - 0.3, 2.8, co({
      showValue: true, dataLabelPosition: "t", showLegend: true, legendPos: "r",
      valAxes: [{ valAxisMinVal: 0, valAxisMaxVal: 240, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }, { valAxisMinVal: 0, valAxisMaxVal: 40, valGridLine: { style: "none" }, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }],
      catAxes: [{ catAxisTitle: "" }, { catAxisHidden: true }],
    }));
    const tiles = [["+7 pts", "Win rate gain over eight quarters", C.violet], ["+22%", "Average deal size, Q1 FY25 → Q4 FY26", C.aqua], ["61 days", "Median sales cycle, down from 74", C.coral], ["3.4×", "Pipeline coverage entering FY27", C.saffron]];
    const tw = (CW - 0.9) / 4;
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 700 });
    tiles.forEach(([v, d, col], i) => {
      const x = M + i * (tw + 0.3), y = TOP + 3.6;
      const g = [card(s, x, y, tw, 1.4)];
      g.push(text(s, v, { x: x + 0.25, y: y + 0.2, w: tw - 0.5, h: 0.55, fontFace: HEAD, fontSize: 26, bold: true, color: col }));
      g.push(text(s, d, { x: x + 0.25, y: y + 0.78, w: tw - 0.5, h: 0.5, fontSize: 13, color: C.muted }));
      anim(s, "wipeUp", g, { t: i ? "with" : "after", delay: i * 120, dur: 400 });
    });
  }

  /* ---------- 27. Retention ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "Customers stay longer and spend more each year");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const q = ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25", "Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26"];
    const cc = chartCard(s, M, TOP, 8.2, 5.0, "Net and gross revenue retention, trailing 12 months, %", null);
    const ch = chart(s, pres.charts.LINE, [
      { name: "Net revenue retention", labels: q, values: [112, 113, 114, 115, 116, 117, 118, 119] },
      { name: "Gross revenue retention", labels: q, values: [90, 91, 91, 92, 92, 93, 93, 94] },
    ], M + 0.15, TOP + 0.6, 7.9, 4.3, co({ chartColors: [C.violet, C.aqua], lineSize: 3.5, lineDataSymbol: "circle", lineDataSymbolSize: 9, showValue: true, dataLabelPosition: "t", showLegend: true, legendPos: "t", valAxisMinVal: 80, valAxisMaxVal: 130, valAxisMajorUnit: 10 }));
    const right = [
      ["119%", "Net revenue retention", "Every $100 of last year's revenue became $119.", C.violet],
      ["94%", "Gross revenue retention", "Top-quartile for the category (peer median 90%).", C.aqua],
      ["$15M", "Churned revenue", "Concentrated in SMB accounts below $10k.", C.coral],
    ];
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 800 });
    right.forEach(([v, h, d, col], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, 9.1, y, 3.63, 1.56)];
      g.push(text(s, v, { x: 9.35, y: y + 0.2, w: 1.5, h: 0.55, fontFace: HEAD, fontSize: 26, bold: true, color: col }));
      g.push(text(s, h, { x: 10.85, y: y + 0.28, w: 1.8, h: 0.5, fontSize: 13, bold: true }));
      g.push(text(s, d, { x: 9.35, y: y + 0.85, w: 3.2, h: 0.6, fontSize: 12, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    });
  }

  /* ---------- 28. Satisfaction radar ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "Customers rate us above benchmark on five of six measures");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const dims = ["Product quality", "Ease of use", "Support", "Value for money", "Onboarding", "Innovation"];
    const us = [8.7, 8.1, 8.9, 7.6, 7.9, 8.4], bm = [7.9, 7.6, 7.4, 7.8, 7.1, 7.5];
    const cc = chartCard(s, M, TOP, 6.4, 5.0, "Customer satisfaction by dimension, score out of 10", null);
    const ch = chart(s, pres.charts.RADAR, [
      { name: "Our score", labels: dims, values: us },
      { name: "Industry benchmark", labels: dims, values: bm },
    ], M + 0.15, TOP + 0.6, 6.1, 4.3, co({ radarStyle: "marker", chartColors: [C.violet, C.saffron], lineSize: 2.5, lineDataSymbolSize: 7, showLegend: true, legendPos: "b", valAxisMinVal: 5, valAxisMaxVal: 10, valAxisMajorUnit: 1, catAxisLabelFontSize: 12, catAxisLabelColor: C.ink, plotArea: undefined }));
    const nps = card(s, 7.3, TOP, 5.43, 2.2, { fill: C.night, noShadow: true });
    const n1 = text(s, "NET PROMOTER SCORE", { x: 7.6, y: TOP + 0.3, w: 3, h: 0.3, fontSize: 12, bold: true, color: "B8B4E6", charSpacing: 1.5 });
    const n2 = text(s, "+52", { x: 7.6, y: TOP + 0.65, w: 2.2, h: 1.0, fontFace: HEAD, fontSize: 60, bold: true, color: C.white });
    const n3 = text(s, "Up 6 points year on year; industry median is +31.", { x: 10.0, y: TOP + 0.85, w: 2.5, h: 0.9, fontSize: 14, color: "C9C5EE" });
    const gap = [];
    dims.forEach((d, i) => {
      const y = TOP + 2.45 + Math.floor(i / 2) * 0.88, x = 7.3 + (i % 2) * 2.8;
      const diff = Math.round((us[i] - bm[i]) * 10) / 10;
      gap.push(card(s, x, y, 2.63, 0.72));
      gap.push(text(s, d, { x: x + 0.2, y: y + 0.2, w: 1.6, h: 0.32, fontSize: 13, color: C.ink }));
      gap.push(text(s, (diff > 0 ? "+" : "−") + Math.abs(diff).toFixed(1), { x: x + 1.7, y: y + 0.17, w: 0.75, h: 0.38, fontSize: 16, bold: true, align: "right", color: diff > 0 ? C.aquaInk : C.coral }));
    });
    anim(s, "fade", cc);
    anim(s, "zoom", ch, { t: "with", dur: 600 });
    anim(s, "fade", [nps, n1, n2, n3]);
    anim(s, "fade", gap, { dur: 400 });
  }

  /* ---------- 29. Customer segments ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "9% of customers generate 41% of revenue");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const segs = ["Enterprise", "Mid-market", "SMB"];
    const cc = chartCard(s, M, TOP, 7.1, 5.0, "Share of customers vs share of revenue, %", "4,860 active customers in FY26");
    const ch = chart(s, pres.charts.BAR, [
      { name: "Share of customers", labels: segs, values: [9, 28, 63] },
      { name: "Share of revenue", labels: segs, values: [41, 37, 22] },
    ], M + 0.15, TOP + 0.85, 6.8, 4.05, co({ barDir: "col", barGapWidthPct: 70, chartColors: [C.lavender, C.violet], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', showLegend: true, legendPos: "t", valAxisMaxVal: 70, valAxisMajorUnit: 10, catAxisLabelFontSize: 13 }));
    const segInfo = [
      ["Enterprise", "437 customers", "$724k average annual revenue · NRR 126%", C.violet],
      ["Mid-market", "1,361 customers", "$210k average annual revenue · NRR 117%", C.aqua],
      ["SMB", "3,062 customers", "$55k average annual revenue · NRR 104%", C.coral],
    ];
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
    segInfo.forEach(([h, c, d, col], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, 8.0, y, 4.73, 1.56)];
      g.push(rect(s, 8.25, y + 0.3, 0.12, 0.95, col, { round: 0.04 }));
      g.push(text(s, h, { x: 8.6, y: y + 0.25, w: 2, h: 0.35, fontFace: HEAD, fontSize: 17, bold: true }));
      g.push(text(s, c, { x: 10.4, y: y + 0.27, w: 2.1, h: 0.32, fontSize: 13, bold: true, align: "right", color: col }));
      g.push(text(s, d, { x: 8.6, y: y + 0.72, w: 3.95, h: 0.6, fontSize: 13, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    });
  }

  /* ---------- 30. Pareto ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "Revenue concentration is healthy but worth watching");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const dec = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"];
    const share = [46, 18, 11, 8, 6, 4, 3, 2, 1.2, 0.8];
    let acc = 0; const cum = share.map((v) => Math.round((acc += v) * 10) / 10);
    const cc = chartCard(s, M, TOP, 8.6, 5.0, "Revenue share by customer decile (%, columns) and cumulative share (%, line)", "D1 = top 10% of customers by revenue");
    const ch = chart(s, [
      { type: pres.charts.BAR, data: [{ name: "Share of revenue %", labels: dec, values: share }], options: { barDir: "col", chartColors: [C.violet], barGapWidthPct: 35 } },
      { type: pres.charts.LINE, data: [{ name: "Cumulative %", labels: dec, values: cum }], options: { chartColors: [C.coral], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8, secondaryValAxis: true, secondaryCatAxis: true } },
    ], null, M + 0.15, TOP + 0.85, 8.3, 4.05, co({
      showLegend: true, legendPos: "t",
      valAxes: [{ valAxisMinVal: 0, valAxisMaxVal: 50, valAxisMajorUnit: 10, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }, { valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20, valGridLine: { style: "none" }, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }],
      catAxes: [{ catAxisTitle: "" }, { catAxisHidden: true }],
    }));
    const k1 = kpi(s, 9.5, TOP, 3.23, 1.56, { value: "64%", labelText: "TOP 20% OF CUSTOMERS", delta: "Share of FY26 revenue", deltaColor: C.muted });
    const k2 = kpi(s, 9.5, TOP + 1.72, 3.23, 1.56, { value: "3.1%", labelText: "LARGEST SINGLE ACCOUNT", delta: "Below the 5% risk limit", color: C.aqua, deltaColor: C.muted });
    const ins = insight(s, 9.5, TOP + 3.44, 3.23, 1.56, "Action", ["Assign executive sponsors to all top-50 accounts."], { fontSize: 13 });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series", dur: 600 });
    anim(s, "fade", k1); anim(s, "fade", k2); anim(s, "fade", ins);
  }

  /* ---------- 31. Quota attainment ---------- */
  s = slide("VANTA Light", "03 Customers & Sales", "03 · CUSTOMERS & SALES", "Four of five regional teams beat their quota");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const teams = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East & Africa"];
    const att = [108, 103, 117, 96, 112];
    const cc = chartCard(s, M, TOP, 7.6, 5.0, "Quota attainment by regional team, FY26, % (target = 100%)", null);
    const ch = chart(s, [
      { type: pres.charts.BAR, data: [{ name: "Attainment %", labels: teams, values: att }], options: { barDir: "col", chartColors: [C.violet, C.violet, C.aqua, C.coral, C.violet], barGapWidthPct: 50, showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.white, dataLabelFormatCode: '0"%"' } },
      { type: pres.charts.LINE, data: [{ name: "Target %", labels: teams, values: [100, 100, 100, 100, 100] }], options: { chartColors: [C.ink], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none" } },
    ], null, M + 0.15, TOP + 0.6, 7.3, 4.3, co({ valAxisMinVal: 0, valAxisMaxVal: 130, valAxisMajorUnit: 25, catAxisLabelFontSize: 11, showLegend: true, legendPos: "t" }));
    const hdr = (t) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.night } } });
    const rows = [[hdr("Team"), hdr("Reps"), hdr("Bookings $M")]];
    [["North America", 96, 182], ["Europe", 71, 121], ["Asia-Pacific", 44, 84], ["Latin America", 18, 22], ["Middle East & Africa", 11, 14]].forEach(([t, r, b]) => rows.push([t, { text: String(r), options: { align: "right" } }, { text: String(b), options: { align: "right" } }]));
    rows.push([{ text: "Total", options: { bold: true } }, { text: "240", options: { bold: true, align: "right" } }, { text: "423", options: { bold: true, align: "right" } }]);
    const tn = nm(s, "table");
    s.addTable(rows, { x: 8.5, y: TOP, w: 4.23, colW: [2.13, 0.8, 1.3], rowH: 0.44, fontFace: BODY, fontSize: 13, color: C.ink, fill: { color: C.white }, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.1, 0, 0.1], objectName: tn });
    const ins = insight(s, 8.5, TOP + 3.35, 4.23, 1.65, "Latin America at 96%", ["Two senior hires in Q3 should close the gap in H1 FY27."], { fill: C.cTint, headColor: C.coral, fontSize: 13 });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
    anim(s, "wipeDown", tn, { dur: 600 });
    anim(s, "fade", ins);
  }

  /* ---------- 32. Chapter 04 ---------- */
  pres.addSection({ title: "04 Operations" });
  await chapter("04", "Operations", "Reliable delivery at a lower cost to serve.", ["Operational scorecard", "Delivery, process and capacity", "Productivity and quality"], "04 Operations");

  /* ---------- 33. Operational gauges ---------- */
  s = slide("VANTA Light", "04 Operations", "04 · OPERATIONS", "Operations scorecard: three of four targets met");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const g = [
      ["On-time delivery", 96.5, 95, C.violet, "H2 FY26 average"],
      ["Capacity utilisation", 78, 80, C.coral, "Target 80% — slightly below"],
      ["First-contact resolution", 84, 80, C.aqua, "Support tickets solved at first touch"],
      ["Process automation", 63, 60, C.saffron, "Share of tasks with no manual step"],
    ];
    const cw = (CW - 0.9) / 4;
    g.forEach(([l, v, t, col, d], i) => {
      const x = M + i * (cw + 0.3);
      const names = [card(s, x, TOP, cw, 5.0)];
      names.push(text(s, l, { x: x + 0.25, y: TOP + 0.25, w: cw - 0.5, h: 0.35, fontSize: 15, bold: true, align: "center" }));
      const chn = chart(s, pres.charts.DOUGHNUT, [{ name: l, labels: ["Achieved", "Remaining"], values: [v, Math.round((100 - v) * 10) / 10] }], x + 0.25, TOP + 0.75, cw - 0.5, cw - 0.5, co({
        holeSize: 74, chartColors: [col, C.track], showValue: false, showPercent: false, showLegend: false, plotArea: undefined, dataNoEffects: true,
      }));
      const vv = text(s, (v % 1 ? v.toFixed(1) : v) + "%", { x: x + 0.25, y: TOP + 0.75 + (cw - 0.5) / 2 - 0.35, w: cw - 0.5, h: 0.7, fontFace: HEAD, fontSize: 22, bold: true, align: "center", valign: "middle", color: C.ink });
      const met = v >= t;
      const badge = rect(s, x + (cw - 1.9) / 2, TOP + 3.75, 1.9, 0.38, met ? C.aTint : C.cTint, { round: 0.19 });
      const bt = text(s, (met ? "Target met · " : "Below target · ") + t + "%", { x: x + (cw - 1.9) / 2, y: TOP + 3.75, w: 1.9, h: 0.38, fontSize: 11, bold: true, align: "center", valign: "middle", color: met ? C.aquaInk : C.coral });
      const dd = text(s, d, { x: x + 0.25, y: TOP + 4.25, w: cw - 0.5, h: 0.6, fontSize: 12, align: "center", color: C.muted });
      anim(s, "fade", names, { t: i ? "with" : "after", delay: i * 150 });
      anim(s, "wipeRight", chn, { t: "with", delay: i * 150 + 150, dur: 700 });
      anim(s, "fade", [vv, badge, bt, dd], { t: "with", delay: i * 150 + 450 });
    });
  }

  /* ---------- 34. On-time delivery line ---------- */
  s = slide("VANTA Light", "04 Operations", "04 · OPERATIONS", "On-time delivery has stayed above target since June");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const otd = [93.1, 93.8, 94.2, 94.0, 94.9, 95.3, 95.8, 95.6, 96.2, 96.8, 97.1, 97.4];
    const cc = chartCard(s, M, TOP, CW, 3.55, "On-time delivery rate, FY26 monthly, %", null);
    const ch = chart(s, pres.charts.LINE, [
      { name: "On-time delivery %", labels: months, values: otd },
      { name: "Target %", labels: months, values: months.map(() => 95) },
    ], M + 0.15, TOP + 0.55, CW - 0.3, 2.95, co({ chartColors: [C.violet, C.coral], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8, showValue: false, showLegend: true, legendPos: "r", valAxisMinVal: 90, valAxisMaxVal: 100, valAxisMajorUnit: 2, dataLabelFormatCode: "0.0" }));
    const steps = [
      ["LuWorkflow", "Automated scheduling", "Introduced in May; removed 1,900 manual hand-offs a month."],
      ["LuClock", "Earlier risk alerts", "Delays are now flagged 6 days ahead, up from 2 days."],
      ["LuBadgeCheck", "Supplier scorecards", "Bottom-quartile suppliers moved to quarterly reviews."],
    ];
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 900 });
    const cw = (CW - 0.6) / 3;
    for (let i = 0; i < steps.length; i++) {
      const [ic, h, d] = steps[i];
      const x = M + i * (cw + 0.3), y = TOP + 3.75;
      const g = [card(s, x, y, cw, 1.25)];
      g.push(...await iconIn(s, ic, x + 0.25, y + 0.3, 0.6, C.vTint, C.violet));
      g.push(text(s, h, { x: x + 1.05, y: y + 0.2, w: cw - 1.3, h: 0.32, fontSize: 15, bold: true }));
      g.push(text(s, d, { x: x + 1.05, y: y + 0.52, w: cw - 1.3, h: 0.62, fontSize: 12, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    }
  }

  /* ---------- 35. Order-to-cash process ---------- */
  s = slide("VANTA Light", "04 Operations", "04 · OPERATIONS", "Order-to-cash: cutting nine days from the cycle");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const st = [["Quote", 2.1, 1.5], ["Contract", 6.4, 4.0], ["Provision", 3.2, 2.0], ["Invoice", 1.0, 0.5], ["Collect", 38.0, 34.0]];
    const gap = 0.3, bw = (CW - 4 * gap - 0.25) / 5;
    st.forEach(([n, now, tgt], i) => {
      const x = M + i * (bw + gap), y = TOP + 0.2;
      const g = [];
      const sn = nm(s, "chev");
      s.addShape(i === 0 ? pres.shapes.PENTAGON : pres.shapes.CHEVRON, { x, y, w: bw + 0.25, h: 1.0, fill: { color: [C.violet, "6E54F6", "8169F7", "947FF8", C.coral][i] }, line: { color: C.mist, width: 2 }, objectName: sn });
      g.push(sn);
      g.push(text(s, `${i + 1}  ${n}`, { x: x + (i ? 0.6 : 0.3), y, w: bw - 0.6, h: 1.0, fontSize: 16, bold: true, color: C.white, valign: "middle" }));
      const cy = TOP + 1.45;
      g.push(card(s, x, cy, bw, 1.75));
      g.push(text(s, "TODAY", { x: x + 0.2, y: cy + 0.18, w: 1, h: 0.25, fontSize: 10, bold: true, color: C.muted, charSpacing: 1 }));
      g.push(text(s, now.toFixed(1) + " d", { x: x + 0.2, y: cy + 0.4, w: bw - 0.4, h: 0.5, fontFace: HEAD, fontSize: 24, bold: true, color: C.ink }));
      g.push(text(s, "TARGET", { x: x + 0.2, y: cy + 0.98, w: 1, h: 0.25, fontSize: 10, bold: true, color: C.muted, charSpacing: 1 }));
      g.push(text(s, tgt.toFixed(1) + " d", { x: x + 0.2, y: cy + 1.2, w: bw - 0.4, h: 0.4, fontFace: HEAD, fontSize: 18, bold: true, color: i === 4 ? C.coral : C.violet }));
      anim(s, i === 0 ? "wipeRight" : "wipeRight", g, { dur: 400 });
    });
    const cc = chartCard(s, M, TOP + 3.45, CW, 1.6, "Total cycle, days", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "Quote", labels: ["Today", "Target FY27"], values: [2.1, 1.5] },
      { name: "Contract", labels: ["Today", "Target FY27"], values: [6.4, 4.0] },
      { name: "Provision", labels: ["Today", "Target FY27"], values: [3.2, 2.0] },
      { name: "Invoice", labels: ["Today", "Target FY27"], values: [1.0, 0.5] },
      { name: "Collect", labels: ["Today", "Target FY27"], values: [38.0, 34.0] },
    ], 2.4, TOP + 3.5, CW - 1.95, 1.5, co({ barDir: "bar", barGrouping: "stacked", catAxisOrientation: "maxMin", barGapWidthPct: 35, chartColors: [C.violet, "6E54F6", "8169F7", "947FF8", C.coral], valAxisHidden: true, valGridLine: { style: "none" }, showLegend: false, valAxisMaxVal: 52, catAxisLabelFontSize: 11 }));
    const tot = text(s, [{ text: "50.7 → 42.0 days", options: { bold: true, color: C.violet } }], { x: M + 0.3, y: TOP + 4.25, w: 1.6, h: 0.6, fontSize: 13 });
    anim(s, "fade", [cc, tot]);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 500 });
  }

  /* ---------- 36. Capacity heat map ---------- */
  s = slide("VANTA Light", "04 Operations", "04 · OPERATIONS", "Capacity is tight in Data Engineering and Cloud Ops");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const teams = ["Platform Engineering", "Data Engineering", "Cloud Operations", "Customer Success", "Professional Services", "Support Desk"];
    const q = ["Q1", "Q2", "Q3", "Q4"];
    const u = [[74, 76, 79, 81], [82, 86, 91, 94], [80, 84, 88, 92], [71, 73, 72, 75], [66, 69, 71, 70], [77, 75, 74, 73]];
    const heat = (v) => (v >= 90 ? [C.coral, C.white] : v >= 85 ? ["FF9A8F", C.ink] : v >= 78 ? [C.lavender, C.ink] : v >= 72 ? ["D6CEFD", C.ink] : [C.vTint, C.ink]);
    const hdr = (t) => ({ text: t, options: { bold: true, color: C.muted, fill: { color: C.mist }, align: "center", fontSize: 12 } });
    const rows = [[{ text: "Team  ·  utilisation %", options: { bold: true, color: C.muted, fill: { color: C.mist }, fontSize: 12 } }, ...q.map(hdr), hdr("Trend")]];
    u.forEach((r, i) => rows.push([
      { text: teams[i], options: { bold: true, fill: { color: C.white } } },
      ...r.map((v) => { const [f, c] = heat(v); return { text: String(v), options: { align: "center", bold: true, color: c, fill: { color: f } } }; }),
      { text: (r[3] - r[0] >= 0 ? "+" : "−") + Math.abs(r[3] - r[0]) + " pts", options: { align: "center", color: r[3] - r[0] > 5 ? C.coral : C.muted, bold: true, fill: { color: C.white } } },
    ]));
    const tn = nm(s, "table");
    s.addTable(rows, { x: M, y: TOP, w: 8.1, colW: [2.9, 1.0, 1.0, 1.0, 1.0, 1.2], rowH: 0.62, fontFace: BODY, fontSize: 14, color: C.ink, border: { type: "solid", pt: 2, color: C.mist }, valign: "middle", margin: [0, 0.12, 0, 0.12], objectName: tn });
    const leg = [];
    [["< 72", C.vTint], ["72–77", "D6CEFD"], ["78–84", C.lavender], ["85–89", "FF9A8F"], ["≥ 90", C.coral]].forEach(([l, col], i) => {
      leg.push(rect(s, M + i * 1.4, TOP + 4.6, 0.3, 0.3, col, { round: 0.05 }), text(s, l, { x: M + i * 1.4 + 0.4, y: TOP + 4.6, w: 0.95, h: 0.3, fontSize: 11, color: C.muted, valign: "middle" }));
    });
    const ins = insight(s, 9.0, TOP, 3.73, 5.0, "Implications", [
      "Data Engineering and Cloud Operations ran above 90% in Q4 — a burnout and delivery risk.",
      "Professional Services has ~15% spare capacity to redeploy.",
      "Plan: hire 26 engineers in H1 FY27 and cross-train 12 consultants.",
    ], { fontSize: 13 });
    anim(s, "wipeDown", tn, { dur: 800 });
    anim(s, "fade", leg, { t: "with", delay: 400 });
    anim(s, "fade", ins);
  }

  /* ---------- 37. Productivity combo ---------- */
  s = slide("VANTA Light", "04 Operations", "04 · OPERATIONS", "Each employee now generates $268k of revenue");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const rpe = [206, 221, 236, 251, 268], hc = [2000, 2199, 2419, 2645, 2881];
    const cc = chartCard(s, M, TOP, 8.2, 5.0, "Headcount (columns) and revenue per employee ($k, line)", null);
    const ch = chart(s, [
      { type: pres.charts.BAR, data: [{ name: "Headcount", labels: YEARS, values: hc }], options: { barDir: "col", chartColors: [C.aqua], barGapWidthPct: 70, showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.white } },
      { type: pres.charts.LINE, data: [{ name: "Revenue per employee $k", labels: YEARS, values: rpe }], options: { chartColors: [C.violet], lineSize: 3.5, lineDataSymbol: "circle", lineDataSymbolSize: 10, secondaryValAxis: true, secondaryCatAxis: true } },
    ], null, M + 0.15, TOP + 0.6, 7.9, 4.3, co({
      showValue: true, dataLabelPosition: "t", showLegend: true, legendPos: "t", dataLabelFormatCode: "#,##0",
      valAxes: [{ valAxisMinVal: 0, valAxisMaxVal: 3500, valAxisMajorUnit: 500, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }, { valAxisMinVal: 0, valAxisMaxVal: 300, valAxisMajorUnit: 100, valGridLine: { style: "none" }, valAxisLabelColor: C.muted, valAxisLabelFontFace: BODY }],
      catAxes: [{ catAxisTitle: "" }, { catAxisHidden: true }],
    }));
    const k1 = kpi(s, 9.1, TOP, 3.63, 1.56, { value: "+30%", labelText: "REVENUE PER EMPLOYEE", delta: "FY22 → FY26" });
    const k2 = kpi(s, 9.1, TOP + 1.72, 3.63, 1.56, { value: "2,881", labelText: "EMPLOYEES, FY26 YEAR-END", delta: "+9% vs FY25", color: C.aqua, deltaColor: C.muted });
    const ins = insight(s, 9.1, TOP + 3.44, 3.63, 1.56, "Productivity driver", ["Automation absorbed growth in support and finance."], { fontSize: 13 });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series", dur: 600 });
    anim(s, "fade", k1); anim(s, "fade", k2); anim(s, "fade", ins);
  }

  /* ---------- 38. Quality ---------- */
  s = slide("VANTA Light", "04 Operations", "04 · OPERATIONS", "Service incidents are down by more than half");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const q = ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25", "Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26"];
    const inc = [4.8, 4.4, 4.1, 3.6, 3.3, 2.9, 2.6, 2.3];
    const k = [["−52%", "Incident rate since Q1 FY25", C.aqua], ["99.95%", "Platform availability, FY26", C.violet], ["38 min", "Mean time to recover, down from 71", C.coral]];
    k.forEach(([v, d, col], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, M, y, 3.63, 1.56)];
      g.push(text(s, v, { x: M + 0.3, y: y + 0.22, w: 3.0, h: 0.6, fontFace: HEAD, fontSize: 30, bold: true, color: col }));
      g.push(text(s, d, { x: M + 0.3, y: y + 0.86, w: 3.1, h: 0.5, fontSize: 13, color: C.muted }));
      anim(s, "fade", g, { t: i ? "with" : "after", delay: i * 150 });
    });
    const cc = chartCard(s, 4.53, TOP, 8.2, 5.0, "Severity 1–2 incidents per 1,000 deployments", null);
    const ch = chart(s, pres.charts.AREA, [{ name: "Incidents per 1,000 deployments", labels: q, values: inc }], 4.68, TOP + 0.6, 7.9, 4.3, co({ chartColors: [C.aqua], chartColorsOpacity: 70, showValue: true, dataLabelPosition: "t", dataLabelFormatCode: "0.0", valAxisMinVal: 0, valAxisMaxVal: 6, valAxisMajorUnit: 1 }));
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", dur: 1000 });
  }

  /* ---------- 39. Chapter 05 ---------- */
  pres.addSection({ title: "05 Growth" });
  await chapter("05", "Growth", "Six opportunities, prioritised by value and our ability to win.", ["Opportunity map and sizing", "Product pipeline", "Expansion and investment"], "05 Growth");

  /* ---------- 40. Opportunity bubble matrix ---------- */
  s = slide("VANTA Light", "05 Growth", "05 · GROWTH", "Where to play: six opportunities mapped");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const op = [["AI-assisted analytics", 8.6, 7.9, 120], ["Mid-market bundle", 7.1, 8.4, 75], ["APAC expansion", 8.0, 6.2, 95], ["Healthcare vertical", 7.4, 5.1, 60], ["Partner marketplace", 6.2, 7.2, 40], ["Usage-based pricing", 6.8, 6.6, 55]];
    const cc = chartCard(s, M, TOP, 7.9, 5.0, "Market attractiveness (x) vs ability to win (y); bubble = FY29 revenue potential", null);
    const ch = chart(s, pres.charts.BUBBLE, [
      { name: "Attractiveness", values: op.map((o) => o[1]) },
      { name: "Opportunities", values: op.map((o) => o[2]), sizes: op.map((o) => o[3]) },
    ], M + 0.15, TOP + 0.6, 7.6, 4.3, co({ chartColors: [C.violet], chartColorsOpacity: 70, valAxisMinVal: 4, valAxisMaxVal: 10, valAxisMajorUnit: 1, catAxisMinVal: 5, catAxisMaxVal: 10, catAxisMajorUnit: 1, catGridLine: { color: C.grid, size: 0.75 }, showValue: false }));
    const hdr = (t, al) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.night }, align: al || "left" } });
    const rows = [[hdr("#"), hdr("Opportunity"), hdr("FY29 $M", "right")]];
    op.slice().sort((a, b) => b[3] - a[3]).forEach((o, i) => rows.push([{ text: String(i + 1), options: { bold: true, color: C.violet } }, o[0], { text: String(o[3]), options: { align: "right", bold: true } }]));
    rows.push([{ text: "", options: {} }, { text: "Total potential", options: { bold: true } }, { text: "445", options: { bold: true, align: "right", color: C.violet } }]);
    const tn = nm(s, "table");
    s.addTable(rows, { x: 8.8, y: TOP, w: 3.93, colW: [0.45, 2.38, 1.1], rowH: 0.5, fontFace: BODY, fontSize: 13, color: C.ink, fill: { color: C.white }, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.1, 0, 0.1], objectName: tn });
    const note = text(s, "Top-right = pursue now. Bubble positions are in the chart's editable data.", { x: 8.8, y: TOP + 4.25, w: 3.93, h: 0.6, fontSize: 12, italic: true, color: C.muted });
    anim(s, "fade", cc);
    anim(s, "zoom", ch, { t: "with", dur: 600 });
    anim(s, "wipeDown", tn, { dur: 700 });
    anim(s, "fade", note);
  }

  /* ---------- 41. Value vs investment ---------- */
  s = slide("VANTA Light", "05 Growth", "05 · GROWTH", "Every opportunity returns at least 2.5 times its investment");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const o = [["AI-assisted analytics", 120, 38], ["APAC expansion", 95, 31], ["Mid-market bundle", 75, 14], ["Healthcare vertical", 60, 24], ["Usage-based pricing", 55, 9], ["Partner marketplace", 40, 11]];
    const cc = chartCard(s, M, TOP, 8.3, 5.0, "FY29 revenue potential vs investment required, $M", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "Revenue potential", labels: o.map((x) => x[0]), values: o.map((x) => x[1]) },
      { name: "Investment", labels: o.map((x) => x[0]), values: o.map((x) => x[2]) },
    ], M + 0.15, TOP + 0.6, 8.0, 4.3, co({ barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 45, chartColors: [C.violet, C.saffron], showValue: true, dataLabelPosition: "outEnd", showLegend: true, legendPos: "t", valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 12, valAxisMaxVal: 140 }));
    const r = o.map((x) => [x[0], (x[1] / x[2]).toFixed(1) + "×"]).sort((a, b) => parseFloat(b[1]) - parseFloat(a[1]));
    const pan = card(s, 9.2, TOP, 3.53, 5.0);
    const ph = text(s, "Revenue per $ invested", { x: 9.45, y: TOP + 0.22, w: 3.1, h: 0.32, fontSize: 15, bold: true });
    const lst = [];
    r.forEach(([n, v], i) => {
      const y = TOP + 0.75 + i * 0.68;
      lst.push(text(s, v, { x: 9.45, y, w: 0.95, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, color: i < 2 ? C.coral : C.violet }));
      lst.push(text(s, n, { x: 10.45, y: y + 0.08, w: 2.15, h: 0.35, fontSize: 13 }));
    });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 600 });
    anim(s, "fade", [pan, ph]);
    anim(s, "fade", lst, { t: "with", stagger: 100, delay: 200, dur: 300 });
  }

  /* ---------- 42. Product pipeline stage gate ---------- */
  s = slide("VANTA Light", "05 Growth", "05 · GROWTH", "A disciplined product pipeline feeds the roadmap");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const st = [["Discover", 14, "Problem and market validated", C.lavender], ["Validate", 8, "Prototype tested with customers", "8C78F8"], ["Build", 5, "Funded and in development", C.violet], ["Pilot", 3, "Live with design partners", C.aqua], ["Launch", 2, "General availability in FY27", C.coral]];
    const bw = 2.2, gp = 0.283;
    st.forEach(([n, c, d, col], i) => {
      const x = M + i * (bw + gp), y = TOP + 0.1;
      const g = [card(s, x, y, bw, 2.85)];
      g.push(circle(s, x + bw / 2 - 0.55, y + 0.3, 1.1, col));
      g.push(text(s, String(c), { x: x + bw / 2 - 0.55, y: y + 0.3, w: 1.1, h: 1.1, fontFace: HEAD, fontSize: 32, bold: true, color: col === C.lavender || col === C.aqua ? C.ink : C.white, align: "center", valign: "middle", onDark: true }));
      g.push(text(s, n, { x: x + 0.15, y: y + 1.55, w: bw - 0.3, h: 0.35, fontFace: HEAD, fontSize: 17, bold: true, align: "center" }));
      g.push(text(s, d, { x: x + 0.2, y: y + 1.95, w: bw - 0.4, h: 0.7, fontSize: 12, color: C.muted, align: "center" }));
      if (i < st.length - 1) g.push(line(s, x + bw + 0.03, y + 0.85, gp - 0.06, 0, C.muted2, { width: 1.5, arrow: "triangle" }));
      anim(s, "wipeRight", g, { dur: 350 });
    });
    const launches = [["LuSparkles", "Insight Copilot", "AI assistant for analysts · GA Q2 FY27"], ["LuBoxes", "Mid-market Bundle", "Pre-configured platform tiers · GA Q3 FY27"]];
    for (let i = 0; i < launches.length; i++) {
      const [ic, h, d] = launches[i];
      const x = M + i * 6.2, y = TOP + 3.25;
      const g = [card(s, x, y, 5.93, 1.75, { fill: C.night, noShadow: true })];
      g.push(...await iconIn(s, ic, x + 0.3, y + 0.5, 0.75, C.night2, C.saffron));
      g.push(text(s, "NEXT LAUNCH", { onDark: true, x: x + 1.3, y: y + 0.35, w: 3, h: 0.25, fontSize: 10, bold: true, color: C.aqua, charSpacing: 1.5 }));
      g.push(text(s, h, { x: x + 1.3, y: y + 0.62, w: 4.4, h: 0.4, fontFace: HEAD, fontSize: 20, bold: true, color: C.white }));
      g.push(text(s, d, { x: x + 1.3, y: y + 1.07, w: 4.4, h: 0.35, fontSize: 13, color: "C9C5EE" }));
      anim(s, "wipeUp", g, { t: i ? "with" : "after", delay: i * 150 });
    }
  }

  /* ---------- 43. Geographic expansion ---------- */
  s = slide("VANTA Light", "05 Growth", "05 · GROWTH", "Expansion targets: three markets in two waves");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const hdr = (t, al) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.violet }, align: al || "left" } });
    const mk = [["Japan", "1.9", "11%", "Partner-led", "Wave 1 · Q1 FY27"], ["India", "1.2", "17%", "Direct + partner", "Wave 1 · Q2 FY27"], ["Saudi Arabia & UAE", "0.8", "15%", "Joint venture", "Wave 2 · Q1 FY28"]];
    const rows = [[hdr("Market"), hdr("SAM $B", "right"), hdr("Growth", "right"), hdr("Entry model"), hdr("Timing")]];
    mk.forEach((m) => rows.push([{ text: m[0], options: { bold: true } }, { text: m[1], options: { align: "right" } }, { text: m[2], options: { align: "right", color: C.aquaInk, bold: true } }, m[3], { text: m[4], options: { color: C.muted } }]));
    const tn = nm(s, "table");
    s.addTable(rows, { x: M, y: TOP, w: CW, colW: [3.0, 1.6, 1.6, 2.9, 3.033], rowH: 0.5, fontFace: BODY, fontSize: 14, color: C.ink, fill: { color: C.white }, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.14, 0, 0.14], objectName: tn });
    const cc = chartCard(s, M, TOP + 2.25, 7.6, 2.75, "Expected revenue from new markets, $M", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "Japan", labels: ["FY27", "FY28", "FY29"], values: [8, 22, 41] },
      { name: "India", labels: ["FY27", "FY28", "FY29"], values: [4, 13, 29] },
      { name: "Saudi Arabia & UAE", labels: ["FY27", "FY28", "FY29"], values: [0, 9, 25] },
    ], M + 0.15, TOP + 2.65, 7.3, 2.3, co({ barDir: "col", barGrouping: "stacked", barGapWidthPct: 70, chartColors: [C.violet, C.aqua, C.coral], showValue: true, dataLabelPosition: "ctr", dataLabelColor: C.white, dataLabelFormatCode: "#,##0;-#,##0;;", showLegend: true, legendPos: "r", valAxisMaxVal: 100, valAxisMajorUnit: 25 }));
    const k = kpi(s, 8.5, TOP + 2.25, 4.23, 2.75, { value: "$95M", labelText: "FY29 REVENUE FROM NEW MARKETS", delta: "24% of FY26–29 growth" });
    k.push(text(s, "A $31M entry investment returns 3.1× by FY29. Japan breaks even in FY28; India in FY29.", { x: 8.75, y: TOP + 3.75, w: 3.73, h: 0.9, fontSize: 13, color: C.muted }));
    anim(s, "wipeDown", tn, { dur: 600 });
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
    anim(s, "zoom", k, { dur: 450 });
  }

  /* ---------- 44. Investment allocation ---------- */
  s = slide("VANTA Light", "05 Growth", "05 · GROWTH", "How we will invest $120M of growth capital in FY27");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const inv = [["Product & AI", 46], ["Go-to-market", 34], ["Geographic expansion", 22], ["Operations & automation", 12], ["Talent & capabilities", 6]];
    const cols = [C.violet, C.aqua, C.coral, C.saffron, C.lavender];
    const cc = card(s, M, TOP, 5.0, 5.0);
    const ch = chart(s, pres.charts.DOUGHNUT, [{ name: "FY27 growth investment $M", labels: inv.map((x) => x[0]), values: inv.map((x) => x[1]) }], M + 0.25, TOP + 0.25, 4.5, 4.5, co({ holeSize: 60, chartColors: cols, showValue: true, showPercent: false, dataLabelColor: C.white, dataLabelFontSize: 12, showLegend: false, plotArea: undefined }));
    const ctr = text(s, [{ text: "$120M", options: { fontFace: HEAD, fontSize: 28, bold: true, color: C.ink, breakLine: true } }, { text: "FY27 growth capital", options: { fontSize: 12, color: C.muted } }], { x: M + 1.4, y: TOP + 2.0, w: 2.2, h: 0.95, align: "center" });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", ctr, { t: "with" });
    const desc = ["Insight Copilot, platform scale and security certifications", "Mid-market sales pod, partner incentives and brand", "Japan and India entry; Gulf joint venture preparation", "Order-to-cash automation and capacity tooling", "Data science and leadership development programmes"];
    inv.forEach(([n, v], i) => {
      const y = TOP + i * 1.0;
      const g = [card(s, 5.9, y, 6.83, 0.86)];
      g.push(rect(s, 6.15, y + 0.28, 0.3, 0.3, cols[i], { round: 0.06 }));
      g.push(text(s, n, { x: 6.65, y: y + 0.12, w: 3.6, h: 0.32, fontSize: 14, bold: true }));
      g.push(text(s, desc[i], { x: 6.65, y: y + 0.45, w: 4.8, h: 0.3, fontSize: 11, color: C.muted }));
      g.push(text(s, "$" + v + "M", { x: 11.4, y: y + 0.2, w: 1.1, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, align: "right", color: cols[i] === C.lavender ? C.violet : cols[i] === C.saffron ? C.saffronInk : cols[i] }));
      anim(s, "wipeLeft", g, { dur: 350 });
    });
  }

  /* ---------- 45. Chapter 06 ---------- */
  pres.addSection({ title: "06 Outlook" });
  await chapter("06", "Outlook", "A base case of $1.18B by FY2029, with a clear view of the range.", ["Three-year forecast", "Scenarios and assumptions", "Sensitivities and targets"], "06 Outlook");

  /* ---------- 46. Forecast with range ---------- */
  s = slide("VANTA Light", "06 Outlook", "06 · OUTLOOK", "Base case: revenue reaches $1.18B in FY2029");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const yrs = [...YEARS, "FY27F", "FY28F", "FY29F"];
    const actual = [...REV, null, null, null];
    const base = [null, null, null, null, 772, ...FORECAST.base];
    const lo = [...REV, ...FORECAST.bear];
    const rng = [0, 0, 0, 0, 0, ...FORECAST.bull.map((b, i) => b - FORECAST.bear[i])];
    const cc = chartCard(s, M, TOP, 8.6, 5.0, "Revenue, $M — actuals, base-case forecast and bear-to-bull range", null);
    const ch = chart(s, [
      { type: pres.charts.AREA, data: [{ name: "_base", labels: yrs, values: lo }, { name: "Scenario range", labels: yrs, values: rng }], options: { barGrouping: "stacked", chartColors: [C.white, C.vTint] } },
      { type: pres.charts.LINE, data: [{ name: "Actual", labels: yrs, values: actual }, { name: "Base-case forecast", labels: yrs, values: base }], options: { chartColors: [C.violet, C.coral], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8 } },
    ], null, M + 0.15, TOP + 0.6, 8.3, 4.3, co({ showLegend: true, legendPos: "t", valAxisMinVal: 0, valAxisMaxVal: 1400, valAxisMajorUnit: 200, valAxisLabelFormatCode: "#,##0" }));
    const k1 = kpi(s, 9.5, TOP, 3.23, 1.56, { value: "15.1%", labelText: "BASE-CASE CAGR FY26–29", delta: "vs 17.0% FY22–26", deltaColor: C.muted });
    const k2 = kpi(s, 9.5, TOP + 1.72, 3.23, 1.56, { value: "$1,176M", labelText: "FY29 BASE CASE", delta: "Range $1,045M – $1,276M", color: C.coral, deltaColor: C.muted });
    const ins = insight(s, 9.5, TOP + 3.44, 3.23, 1.56, "Built bottom-up", ["Segment, region and channel plans."], { fontSize: 13 });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "series", dur: 700 });
    anim(s, "fade", k1); anim(s, "fade", k2); anim(s, "fade", ins);
  }

  /* ---------- 47. Scenarios ---------- */
  s = slide("VANTA Light", "06 Outlook", "06 · OUTLOOK", "Three scenarios frame the planning range");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const yrs = ["FY27", "FY28", "FY29"];
    const cc = chartCard(s, M, TOP, 7.0, 5.0, "Revenue by scenario, $M", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "Bear", labels: yrs, values: FORECAST.bear },
      { name: "Base", labels: yrs, values: FORECAST.base },
      { name: "Bull", labels: yrs, values: FORECAST.bull },
    ], M + 0.15, TOP + 0.6, 6.7, 4.3, co({ barDir: "col", barGapWidthPct: 60, barOverlapPct: -5, chartColors: [C.lavender, C.violet, C.aqua], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", dataLabelFontSize: 9, showLegend: true, legendPos: "t", valAxisMinVal: 0, valAxisMaxVal: 1400, valAxisMajorUnit: 350, valAxisLabelFormatCode: "#,##0" }));
    const sc = [
      ["Bull", "$1,276M", "18.2% CAGR", "AI products scale fast; NRR reaches 124%; both expansion waves on time.", C.aqua, C.aTint],
      ["Base", "$1,176M", "15.1% CAGR", "Current momentum continues; NRR 120%; Wave 2 slips one quarter.", C.violet, C.vTint],
      ["Bear", "$1,045M", "10.6% CAGR", "Macro slowdown lengthens cycles; NRR falls to 112%; Wave 2 deferred.", C.coral, C.cTint],
    ];
    anim(s, "fade", cc);
    anim(s, "wipeUp", ch, { t: "with", build: "series" });
    sc.forEach(([n, v, c, d, col, tint], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, 7.9, y, 4.83, 1.56)];
      g.push(rect(s, 8.15, y + 0.25, 0.8, 0.36, tint, { round: 0.18 }));
      g.push(text(s, n.toUpperCase(), { x: 8.15, y: y + 0.25, w: 0.8, h: 0.36, fontSize: 10, bold: true, color: col, align: "center", valign: "middle" }));
      g.push(text(s, v, { x: 9.1, y: y + 0.2, w: 1.8, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, color: C.ink }));
      g.push(text(s, c, { x: 10.9, y: y + 0.27, w: 1.6, h: 0.32, fontSize: 12, bold: true, color: col, align: "right" }));
      g.push(text(s, d, { x: 8.15, y: y + 0.75, w: 4.35, h: 0.7, fontSize: 12, color: C.muted }));
      anim(s, "fade", g, { dur: 400 });
    });
  }

  /* ---------- 48. Key assumptions ---------- */
  s = slide("VANTA Light", "06 Outlook", "06 · OUTLOOK", "Key planning assumptions behind the base case");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const hdr = (t, al) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.night }, align: al || "center" } });
    const rows = [[hdr("Driver", "left"), hdr("FY26 actual"), hdr("FY27"), hdr("FY28"), hdr("FY29"), hdr("Confidence")]];
    const conf = (t, col, f) => ({ text: t, options: { bold: true, color: col, fill: { color: f }, align: "center" } });
    const data = [
      ["Market growth", "9.0%", "8.8%", "8.5%", "8.5%", conf("High", C.aquaInk, C.aTint)],
      ["New customers", "389", "430", "475", "520", conf("Medium", C.saffronInk, C.sTint)],
      ["Net revenue retention", "119%", "120%", "120%", "121%", conf("Medium", C.saffronInk, C.sTint)],
      ["Average price change", "+2.8%", "+3.0%", "+3.0%", "+2.5%", conf("High", C.aquaInk, C.aTint)],
      ["New-market revenue ($M)", "—", "12", "44", "95", conf("Low", C.coral, C.cTint)],
      ["EBITDA margin", "23.4%", "24.5%", "25.8%", "27.0%", conf("Medium", C.saffronInk, C.sTint)],
      ["Headcount, year-end", "2,881", "3,120", "3,350", "3,560", conf("High", C.aquaInk, C.aTint)],
    ];
    data.forEach((r, i) => rows.push([{ text: r[0], options: { bold: true, fill: { color: i % 2 ? C.white : "FAF9FE" } } }, ...r.slice(1, 5).map((v, j) => ({ text: v, options: { align: "center", bold: j === 3, color: j === 3 ? C.violet : C.ink, fill: { color: i % 2 ? C.white : "FAF9FE" } } })), r[5]]));
    const tn = nm(s, "table");
    s.addTable(rows, { x: M, y: TOP, w: CW, colW: [3.6, 1.7, 1.6, 1.6, 1.8, 1.833], rowH: 0.53, fontFace: BODY, fontSize: 14, color: C.ink, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.14, 0, 0.14], objectName: tn });
    const note = text(s, "Confidence reflects data quality and controllability of each driver. New-market revenue carries the widest range and is excluded from management bonus targets until Wave 1 is live.", { x: M, y: TOP + 4.45, w: CW, h: 0.55, fontSize: 12, italic: true, color: C.muted });
    anim(s, "wipeDown", tn, { dur: 900 });
    anim(s, "fade", note);
  }

  /* ---------- 49. Tornado sensitivity ---------- */
  s = slide("VANTA Light", "06 Outlook", "06 · OUTLOOK", "Retention is the biggest swing factor for FY2029");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const d = [["Net revenue retention ±5 pts", -62, 58], ["New-logo growth ±10%", -41, 44], ["Price realisation ±3%", -35, 35], ["Gross churn ±1 pt", -22, 20], ["FX rates ±5%", -18, 18]];
    const cc = chartCard(s, M, TOP, 8.3, 5.0, "Impact on FY29 base-case revenue of $1,176M, $M", null);
    const ch = chart(s, pres.charts.BAR, [
      { name: "Downside", labels: d.map((x) => x[0]), values: d.map((x) => x[1]) },
      { name: "Upside", labels: d.map((x) => x[0]), values: d.map((x) => x[2]) },
    ], M + 0.15, TOP + 0.6, 8.0, 4.3, co({
      barDir: "bar", barGrouping: "stacked", catAxisOrientation: "maxMin", barGapWidthPct: 35, chartColors: [C.coral, C.aqua], showValue: true, dataLabelPosition: "ctr", dataLabelColor: C.white, dataLabelFormatCode: '+#,##0;−#,##0',
      showLegend: true, legendPos: "t", valAxisMinVal: -80, valAxisMaxVal: 80, valAxisMajorUnit: 20, valAxisLabelFormatCode: "#,##0;−#,##0", catAxisLabelPos: "low", catAxisLabelFontSize: 12,
    }));
    const ins = insight(s, 9.2, TOP, 3.53, 5.0, "So what", [
      "One point of NRR is worth about $12M of FY29 revenue.",
      "Customer success capacity is therefore a revenue lever, not a cost line.",
      "FX exposure is modest and partly hedged.",
    ], { fontSize: 13 });
    anim(s, "fade", cc);
    anim(s, "wipeRight", ch, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", ins);
  }

  /* ---------- 50. FY29 targets (dark) ---------- */
  s = slide("VANTA Dark", "06 Outlook", "06 · OUTLOOK", "FY2029 ambition at a glance");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const t = [
      ["REVENUE", "$1.18B", "from $772M", "LuCircleDollarSign", C.lavender, [772, 892, 1027, 1176]],
      ["EBITDA MARGIN", "27.0%", "from 23.4%", "LuGauge", C.aqua, [23.4, 24.5, 25.8, 27.0]],
      ["NET REVENUE RETENTION", "121%", "from 119%", "LuRefreshCw", C.saffron, [119, 120, 120, 121]],
      ["FREE CASH FLOW", "$230M", "from $118M", "LuTrendingUp", C.coral, [118, 148, 186, 230]],
    ];
    const cw = (CW - 0.9) / 4;
    for (let i = 0; i < t.length; i++) {
      const [l, v, f, ic, col, series] = t[i];
      const x = M + i * (cw + 0.3), y = TOP + 0.1;
      const g = [card(s, x, y, cw, 4.85, { fill: C.night2, noShadow: true })];
      g.push(...await iconIn(s, ic, x + 0.3, y + 0.3, 0.62, "322C6A", col));
      g.push(text(s, l, { x: x + 0.3, y: y + 1.15, w: cw - 0.6, h: 0.3, fontSize: 11, bold: true, color: "B8B4E6", charSpacing: 1 }));
      g.push(text(s, v, { x: x + 0.3, y: y + 1.45, w: cw - 0.6, h: 0.75, fontFace: HEAD, fontSize: 36, bold: true, color: C.white }));
      g.push(text(s, f + " in FY26", { onDark: true, x: x + 0.3, y: y + 2.2, w: cw - 0.6, h: 0.3, fontSize: 13, color: col }));
      const ch = chart(s, pres.charts.BAR, [{ name: l, labels: ["FY26", "FY27", "FY28", "FY29"], values: series }], x + 0.15, y + 2.65, cw - 0.3, 2.05, darkChart({
        barDir: "col", chartColors: ["4A4578", "4A4578", "4A4578", col], barGapWidthPct: 45, valAxisHidden: true, valGridLine: { style: "none" }, showValue: false, catAxisLabelFontSize: 10, plotArea: { fill: { color: C.night2 } },
      }));
      anim(s, "wipeUp", g, { t: i ? "with" : "after", delay: i * 150, dur: 450 });
      anim(s, "wipeUp", ch, { t: "with", delay: i * 150 + 300, dur: 500 });
    }
  }

  /* ---------- 51. Chapter 07 ---------- */
  pres.addSection({ title: "07 Plan" });
  await chapter("07", "Plan", "Turning strategy into owned, sequenced and measured action.", ["Priorities and recommendations", "Roadmap, milestones and governance", "Risks, KPIs and next steps"], "07 Plan");

  /* ---------- 52. Strategic priorities ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "Four strategic priorities for FY2027–FY2029");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const p = [
      ["LuSparkles", C.violet, C.vTint, "Lead with AI", "Make Insight Copilot standard in every Platform tier.", "$120M", "FY29 revenue"],
      ["LuUsers", C.aqua, C.aTint, "Win the mid-market", "Bundle, price and sell to 600+ new mid-market accounts.", "+600", "new accounts"],
      ["LuGlobe", C.coral, C.cTint, "Expand in Asia", "Enter Japan and India; prepare the Gulf joint venture.", "$95M", "FY29 revenue"],
      ["LuGauge", C.saffron, C.sTint, "Run lean at scale", "Automate order-to-cash and lift EBITDA margin to 27%.", "+3.6 pts", "EBITDA margin"],
    ];
    const cw = (CW - 0.9) / 4;
    for (let i = 0; i < p.length; i++) {
      const [ic, col, tint, h, d, v, vl] = p[i];
      const x = M + i * (cw + 0.3), y = TOP;
      const g = [card(s, x, y, cw, 5.0)];
      g.push(text(s, "0" + (i + 1), { x: x + 0.3, y: y + 0.3, w: 1, h: 0.4, fontFace: HEAD, fontSize: 16, bold: true, color: C.muted2 }));
      g.push(...await iconIn(s, ic, x + cw - 1.0, y + 0.25, 0.7, tint, col));
      g.push(text(s, h, { x: x + 0.3, y: y + 1.15, w: cw - 0.6, h: 0.8, fontFace: HEAD, fontSize: 20, bold: true, valign: "top" }));
      g.push(text(s, d, { x: x + 0.3, y: y + 2.05, w: cw - 0.6, h: 1.2, fontSize: 14, color: C.muted }));
      g.push(rect(s, x + 0.3, y + 3.45, cw - 0.6, 1.25, tint, { round: 0.08 }));
      g.push(text(s, v, { x: x + 0.5, y: y + 3.55, w: cw - 1.0, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color: col === C.saffron ? C.saffronInk : col }));
      g.push(text(s, vl, { x: x + 0.5, y: y + 4.15, w: cw - 1.0, h: 0.35, fontSize: 13, color: C.ink }));
      anim(s, "wipeUp", g, { t: i ? "with" : "after", delay: i * 150, dur: 500 });
    }
  }

  /* ---------- 53. Recommendations ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "We ask the board to approve three decisions today");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const r = [
      ["Approve the $120M FY27 growth investment", "Phased release tied to quarterly milestones; 40% committed in H1.", "$445M", "revenue potential by FY29"],
      ["Launch Japan and India in FY27", "Partner-led entry in Japan, direct and partner model in India.", "$70M", "revenue by FY29"],
      ["Fund 26 engineering hires in H1", "Relieves Data Engineering and Cloud Operations capacity above 90%.", "−9 pts", "peak utilisation"],
    ];
    r.forEach(([h, d, v, vl], i) => {
      const y = TOP + i * 1.72;
      const g = [card(s, M, y, CW, 1.56)];
      g.push(circle(s, M + 0.3, y + 0.38, 0.8, C.violet));
      g.push(text(s, String(i + 1), { x: M + 0.3, y: y + 0.38, w: 0.8, h: 0.8, fontFace: HEAD, fontSize: 26, bold: true, color: C.white, align: "center", valign: "middle" }));
      g.push(text(s, h, { x: M + 1.4, y: y + 0.3, w: 7.2, h: 0.42, fontFace: HEAD, fontSize: 19, bold: true }));
      g.push(text(s, d, { x: M + 1.4, y: y + 0.8, w: 7.2, h: 0.5, fontSize: 14, color: C.muted }));
      g.push(rect(s, 9.3, y + 0.25, 3.18, 1.06, C.vTint, { round: 0.08 }));
      g.push(text(s, v, { x: 9.5, y: y + 0.3, w: 2.8, h: 0.5, fontFace: HEAD, fontSize: 24, bold: true, color: C.violet }));
      g.push(text(s, vl, { x: 9.5, y: y + 0.8, w: 2.8, h: 0.35, fontSize: 12, color: C.ink }));
      anim(s, "wipeRight", g, { dur: 500 });
    });
  }

  /* ---------- 54. Gantt roadmap ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "Implementation roadmap, FY2027–FY2028");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const qs = ["Q1 FY27", "Q2 FY27", "Q3 FY27", "Q4 FY27", "Q1 FY28", "Q2 FY28", "Q3 FY28", "Q4 FY28"];
    const lx = M, lw = 3.0, gx = M + lw, gw = CW - lw, qw = gw / 8;
    const hdr = [];
    qs.forEach((q, i) => hdr.push(text(s, q, { x: gx + i * qw, y: TOP, w: qw, h: 0.35, fontSize: 11, bold: true, color: C.muted, align: "center", valign: "middle" })));
    const grid = [];
    for (let i = 0; i <= 8; i++) grid.push(line(s, gx + i * qw, TOP + 0.4, 0, 4.35, C.line, { width: 0.75 }));
    const ws = [
      ["AI · Insight Copilot", 0, 2, C.violet, "Build & pilot"], ["AI · Copilot GA & upsell", 2, 6, C.violet, "Scale"],
      ["Mid-market bundle", 1, 4, C.aqua, "Design → GA"], ["Mid-market sales pod", 2, 8, C.aqua, "Hire & ramp 40 reps"],
      ["Japan entry", 0, 3, C.coral, "Partner launch"], ["India entry", 1, 5, C.coral, "Direct + partner"],
      ["Gulf joint venture", 4, 8, C.coral, "Set-up & launch"], ["Order-to-cash automation", 0, 5, C.saffron, "Phase 1–3"],
    ];
    const rh = 0.53;
    anim(s, "fade", [...hdr, ...grid]);
    ws.forEach(([n, a, b, col, l], i) => {
      const y = TOP + 0.5 + i * rh;
      const g = [text(s, n, { x: lx, y, w: lw - 0.1, h: rh - 0.12, fontSize: 13, bold: true, valign: "middle" })];
      const bar = rect(s, gx + a * qw + 0.05, y + 0.04, (b - a) * qw - 0.1, rh - 0.2, col, { round: 0.12 });
      const bl = text(s, l, { x: gx + a * qw + 0.15, y: y + 0.04, w: (b - a) * qw - 0.3, h: rh - 0.2, fontSize: 11, bold: true, color: col === C.violet ? C.white : C.ink, valign: "middle" });
      anim(s, "fade", g, { t: i ? "with" : "after", delay: i * 100, dur: 300 });
      anim(s, "wipeRight", [bar, bl], { t: "with", delay: i * 100 + 100, dur: 500 });
    });
    const today = line(s, gx + 0.02, TOP + 0.35, 0, 4.4, C.coral, { width: 2, dash: "dash" });
    const tl = text(s, "Plan start · 1 Feb FY27", { x: gx + 0.1, y: TOP + 4.8, w: 2.5, h: 0.25, fontSize: 10, bold: true, color: C.coral });
    anim(s, "fade", [today, tl]);
  }

  /* ---------- 55. Milestones timeline ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "Milestones the board will see each quarter");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const ms = [
      ["Q1 FY27", "Japan partner launch", "First 10 Japanese customers live"],
      ["Q2 FY27", "Insight Copilot GA", "Available in all Platform tiers"],
      ["Q3 FY27", "Mid-market bundle GA", "Target: 150 new mid-market logos"],
      ["Q4 FY27", "$892M revenue", "EBITDA margin 24.5%"],
      ["Q2 FY28", "Gulf JV signed", "Regulatory approvals secured"],
      ["Q4 FY28", "$1.03B revenue", "Billion-dollar milestone"],
    ];
    const y0 = TOP + 2.05;
    const axis = line(s, M, y0, CW, 0, C.violet, { width: 3 });
    anim(s, "wipeRight", axis, { dur: 900 });
    // cards alternate above / below the axis, so each can span almost two slots
    const sp = (CW + 0.3) / 7, cw = 2 * sp - 0.3;
    ms.forEach(([q, h, d], i) => {
      const cx = M + cw / 2 + i * sp;
      const up = i % 2 === 0;
      const g = [circle(s, cx - 0.17, y0 - 0.17, 0.34, i === 5 ? C.coral : C.white, { line: i === 5 ? undefined : C.violet, lw: 3 })];
      const by = up ? TOP : TOP + 2.75;
      g.push(line(s, cx, up ? by + 1.3 : y0 + 0.17, 0, up ? y0 - 0.17 - (by + 1.3) : by - (y0 + 0.17), C.muted2, { width: 1, dash: "dash" }));
      const bx = cx - cw / 2;
      g.push(card(s, bx, by, cw, 1.3));
      g.push(text(s, q, { x: bx + 0.25, y: by + 0.17, w: cw - 0.5, h: 0.28, fontSize: 11, bold: true, color: i === 5 ? C.coral : C.violet, charSpacing: 1 }));
      g.push(text(s, h, { x: bx + 0.25, y: by + 0.45, w: cw - 0.5, h: 0.35, fontFace: HEAD, fontSize: 16, bold: true }));
      g.push(text(s, d, { x: bx + 0.25, y: by + 0.85, w: cw - 0.5, h: 0.3, fontSize: 12, color: C.muted }));
      anim(s, "fade", g, { dur: 350 });
    });
    const foot = card(s, M, TOP + 4.3, CW, 0.7, { fill: C.vTint, noShadow: true });
    const ft = text(s, [{ text: "Reporting rhythm:  ", options: { bold: true, color: C.violet } }, { text: "milestone status in every quarterly board pack, with red/amber/green ratings and owner commentary.", options: { color: C.ink } }], { x: M + 0.3, y: TOP + 4.3, w: CW - 0.6, h: 0.7, fontSize: 14, valign: "middle" });
    anim(s, "fade", [foot, ft]);
  }

  /* ---------- 56. Governance RACI ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "Clear ownership for every workstream");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const roles = ["CEO", "CFO", "CPO", "CRO", "COO"];
    const ws = [["AI · Insight Copilot", "A", "C", "R", "C", "I"], ["Mid-market growth", "A", "C", "C", "R", "I"], ["Asia expansion", "A", "C", "I", "R", "C"], ["Order-to-cash automation", "I", "A", "I", "C", "R"], ["Capacity & hiring", "I", "C", "C", "I", "A/R"], ["Investment governance", "C", "A/R", "I", "I", "I"]];
    const sty = { R: [C.violet, C.white], A: [C.coral, C.white], "A/R": [C.coral, C.white], C: [C.aTint, C.aquaInk], I: [C.track, C.muted] };
    const hdr = (t) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.night }, align: "center" } });
    const rows = [[{ text: "Workstream", options: { bold: true, color: C.white, fill: { color: C.night } } }, ...roles.map(hdr)]];
    ws.forEach((w) => rows.push([{ text: w[0], options: { bold: true, fill: { color: C.white } } }, ...w.slice(1).map((v) => ({ text: v, options: { bold: true, align: "center", fill: { color: sty[v][0] }, color: sty[v][1] } }))]));
    const tn = nm(s, "table");
    s.addTable(rows, { x: M, y: TOP, w: 8.4, colW: [3.15, 1.05, 1.05, 1.05, 1.05, 1.05], rowH: 0.6, fontFace: BODY, fontSize: 14, color: C.ink, border: { type: "solid", pt: 2, color: C.mist }, valign: "middle", margin: [0, 0.14, 0, 0.14], objectName: tn });
    const key = [["R", "Responsible — delivers the work", C.violet], ["A", "Accountable — owns the outcome", C.coral], ["C", "Consulted — gives input", C.aqua], ["I", "Informed — kept up to date", C.muted2]];
    const kc = [card(s, 9.3, TOP, 3.43, 5.0)];
    kc.push(text(s, "Key", { x: 9.55, y: TOP + 0.22, w: 3, h: 0.32, fontSize: 15, bold: true }));
    key.forEach(([k, d, col], i) => {
      const y = TOP + 0.75 + i * 0.68;
      kc.push(rect(s, 9.55, y, 0.45, 0.45, col, { round: 0.08 }), text(s, k, { x: 9.55, y, w: 0.45, h: 0.45, fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle" }), text(s, d, { x: 10.15, y: y + 0.02, w: 2.45, h: 0.45, fontSize: 12, color: C.ink, valign: "middle" }));
    });
    kc.push(text(s, "Steering committee meets monthly; CFO chairs investment reviews each quarter.", { x: 9.55, y: TOP + 3.65, w: 2.95, h: 1.1, fontSize: 12, color: C.muted }));
    anim(s, "wipeDown", tn, { dur: 800 });
    anim(s, "fade", kc);
  }

  /* ---------- 57. Risk matrix ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "Top risks and how we will manage them");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const gx = M + 0.5, gy = TOP + 0.1, cs = 0.8;
    const sev = (r, c) => { const v = (c + 1) * (5 - r); return v >= 15 ? "FF8A80" : v >= 8 ? "FFD48A" : v >= 4 ? "D6CEFD" : C.vTint; };
    const cells = [];
    for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) cells.push(rect(s, gx + c * cs, gy + r * cs, cs - 0.05, cs - 0.05, sev(r, c), { round: 0.06 }));
    const ax = [text(s, "Likelihood →", { x: gx, y: gy + 5 * cs + 0.05, w: 5 * cs, h: 0.3, fontSize: 12, bold: true, color: C.muted, align: "center" })];
    const yl = nm(s, "ylab");
    s.addText("Impact →", { x: M - 1.05, y: gy + 2.5 * cs - 0.15, w: 2.3, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: C.muted, align: "center", rotate: 270, margin: 0, isTextBox: true, objectName: yl });
    ax.push(yl);
    const risks = [
      [1, "Slower enterprise buying", 3, 3, "Shift mix to mid-market; tighten pipeline governance", "CRO"],
      [2, "AI product delay", 2, 3, "Stage-gated releases with design partners", "CPO"],
      [3, "Engineering attrition", 3, 2, "Retention grants; relieve capacity hot spots", "COO"],
      [4, "Data security incident", 1, 4, "Zero-trust programme; quarterly red-team tests", "CTO"],
      [5, "Japan partner under-delivers", 2, 2, "Dual-partner model; 6-month exit clause", "CRO"],
      [6, "Adverse FX movement", 3, 1, "Natural hedging plus 12-month forward cover", "CFO"],
    ];
    const marks = [];
    const slotUse = {};
    risks.forEach(([n, , lk, im]) => {
      const key = lk + "," + im; slotUse[key] = (slotUse[key] || 0) + 1;
      const off = (slotUse[key] - 1) * 0.3;
      const x = gx + lk * cs + cs / 2 - 0.2 + off, y = gy + (4 - im) * cs + cs / 2 - 0.2;
      marks.push(circle(s, x, y, 0.4, C.night), text(s, String(n), { x, y, w: 0.4, h: 0.4, fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle" }));
    });
    anim(s, "fade", [...cells, ...ax], { dur: 500 });
    anim(s, "zoom", marks, { t: "after", stagger: 80, dur: 300 });
    const hdr = (t, al) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.night }, align: al || "left" } });
    const rows = [[hdr("#", "center"), hdr("Risk"), hdr("Mitigation"), hdr("Owner", "center")]];
    risks.forEach(([n, r, , , m, o]) => rows.push([{ text: String(n), options: { bold: true, align: "center", color: C.violet } }, { text: r, options: { bold: true } }, { text: m, options: { color: C.muted } }, { text: o, options: { align: "center", bold: true } }]));
    const tn = nm(s, "table");
    s.addTable(rows, { x: 5.25, y: TOP + 0.1, w: 7.48, colW: [0.45, 2.3, 3.93, 0.8], rowH: 0.66, fontFace: BODY, fontSize: 12, color: C.ink, fill: { color: C.white }, border: { type: "solid", pt: 0.75, color: C.line }, valign: "middle", margin: [0, 0.08, 0, 0.08], objectName: tn });
    anim(s, "wipeDown", tn, { dur: 700 });
  }

  /* ---------- 58. KPI dashboard ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "The KPI dashboard we will track every month");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const tiles = [
      ["REVENUE, $M (QUARTERLY)", "$213M", "Q4 FY26 · +15.8% YoY", QREV.FY25.concat(QREV.FY26), C.violet],
      ["EBITDA MARGIN, %", "23.4%", "FY26 · +1.5 pts", EBITDA_M, C.aqua],
      ["NET REVENUE RETENTION, %", "119%", "Q4 FY26 · +4 pts YoY", [112, 113, 114, 115, 116, 117, 118, 119], C.coral],
      ["PIPELINE COVERAGE", "3.4×", "Entering FY27 · target 3.0×", [2.6, 2.8, 2.7, 3.0, 3.1, 3.0, 3.2, 3.4], C.saffron],
    ];
    const tw = (CW - 0.9) / 4;
    tiles.forEach(([l, v, d, series, col], i) => {
      const x = M + i * (tw + 0.3), y = TOP;
      const g = [card(s, x, y, tw, 1.95)];
      g.push(text(s, l, { x: x + 0.25, y: y + 0.18, w: tw - 0.5, h: 0.26, fontSize: 10, bold: true, color: C.muted, charSpacing: 1 }));
      g.push(text(s, v, { x: x + 0.25, y: y + 0.45, w: 1.45, h: 0.6, fontFace: HEAD, fontSize: 26, bold: true, color: C.ink, fit: "shrink" }));
      g.push(text(s, d, { x: x + 0.25, y: y + 1.55, w: tw - 0.5, h: 0.26, fontSize: 11, bold: true, color: col === C.saffron ? C.saffronInk : col }));
      const sp = chart(s, pres.charts.LINE, [{ name: l, labels: series.map((_, j) => String(j + 1)), values: series }], x + 1.6, y + 0.45, tw - 1.75, 1.0, co({
        chartColors: [col], lineSize: 2.5, lineDataSymbol: "none", valAxisHidden: true, catAxisHidden: true, valGridLine: { style: "none" }, catAxisLineShow: false, valAxisMinVal: Math.min(...series) * 0.92, valAxisMaxVal: Math.max(...series) * 1.04,
      }));
      anim(s, "fade", g, { t: i ? "with" : "after", delay: i * 120 });
      anim(s, "wipeRight", sp, { t: "with", delay: i * 120 + 200, dur: 600 });
    });
    const c1 = chartCard(s, M, TOP + 2.2, 5.0, 2.8, "Revenue by segment, Q4 FY26, $M", null);
    const ch1 = chart(s, pres.charts.BAR, [{ name: "Q4 FY26 $M", labels: ["Platform", "Managed", "Data", "Advisory"], values: [97, 63, 35, 18] }], M + 0.1, TOP + 2.6, 4.8, 2.35, co({ barDir: "bar", catAxisOrientation: "maxMin", chartColors: [C.violet], barGapWidthPct: 40, showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" }, valAxisMaxVal: 120 }));
    const c2 = chartCard(s, M + 5.3, TOP + 2.2, 3.4, 2.8, "Revenue by channel, FY26", null);
    const ch2 = chart(s, pres.charts.DOUGHNUT, [{ name: "Channel mix", labels: ["Direct", "Partners", "Digital"], values: [54.6, 30.0, 15.4] }], M + 5.4, TOP + 2.6, 3.2, 2.35, co({ holeSize: 55, chartColors: [C.violet, C.aqua, C.coral], showPercent: true, showValue: false, dataLabelColor: C.white, showLegend: true, legendPos: "r", legendFontSize: 10, plotArea: undefined }));
    const c3 = chartCard(s, M + 9.0, TOP + 2.2, 3.133, 2.8, "Status vs plan", null);
    const st = [["Revenue", "On track", C.aquaInk, C.aTint], ["Margin", "On track", C.aquaInk, C.aTint], ["Retention", "Ahead", C.violet, C.vTint], ["Capacity", "At risk", C.coral, C.cTint]];
    const sn = [];
    st.forEach(([k, v, col, tint], i) => {
      const y = TOP + 2.8 + i * 0.52;
      sn.push(text(s, k, { x: M + 9.25, y, w: 1.3, h: 0.4, fontSize: 13, valign: "middle" }), rect(s, M + 10.65, y + 0.04, 1.28, 0.34, tint, { round: 0.17 }), text(s, v, { x: M + 10.65, y: y + 0.04, w: 1.28, h: 0.34, fontSize: 11, bold: true, color: col, align: "center", valign: "middle" }));
    });
    anim(s, "fade", c1); anim(s, "wipeRight", ch1, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", c2); anim(s, "wipeRight", ch2, { t: "with", build: "category", dur: 300 });
    anim(s, "fade", c3); anim(s, "fade", sn, { t: "with", stagger: 60, delay: 150 });
  }

  /* ---------- 59. Next steps 30/60/90 ---------- */
  s = slide("VANTA Light", "07 Plan", "07 · PLAN", "Next steps: the first 90 days");
  {
    anim(s, "fade", "@ph", { t: "with" });
    const cols = [
      ["30", "DAYS", C.violet, ["Board approval of FY27 plan and budget", "Appoint workstream leads and PMO", "Release first $48M tranche"]],
      ["60", "DAYS", C.aqua, ["Sign Japan distribution partner", "Open 26 engineering requisitions", "Start Copilot pilot with 12 customers"]],
      ["90", "DAYS", C.coral, ["Mid-market pod fully staffed", "Order-to-cash phase 1 live", "First quarterly milestone review"]],
    ];
    const cw = (CW - 0.6) / 3;
    for (let i = 0; i < cols.length; i++) {
      const [n, u, col, items] = cols[i];
      const x = M + i * (cw + 0.3), y = TOP;
      const g = [card(s, x, y, cw, 5.0)];
      g.push(text(s, [{ text: n, options: { fontFace: HEAD, fontSize: 54, bold: true, color: col } }, { text: "  " + u, options: { fontSize: 14, bold: true, color: C.muted, charSpacing: 2 } }], { x: x + 0.35, y: y + 0.25, w: cw - 0.7, h: 1.0, valign: "middle" }));
      anim(s, "wipeUp", g, { dur: 400 });
      const it = [];
      for (let j = 0; j < items.length; j++) {
        const yy = y + 1.55 + j * 1.08;
        it.push(...await iconIn(s, "LuCalendarCheck", x + 0.35, yy, 0.5, col === C.violet ? C.vTint : col === C.aqua ? C.aTint : C.cTint, col));
        it.push(text(s, items[j], { x: x + 1.05, y: yy - 0.02, w: cw - 1.4, h: 0.85, fontSize: 14, color: C.ink }));
      }
      anim(s, "fade", it, { t: "with", stagger: 120, delay: 250, dur: 350 });
    }
  }

  /* ---------- 60. Closing ---------- */
  pres.addSection({ title: "Close" });
  s = slide("VANTA Cover", "Close", null, null, { transition: "fade" });
  {
    const rings = [[-2.4, 1.2, 8.2, 35], [-1.4, 2.2, 6.2, 55], [-0.4, 3.2, 4.2, 70]].map(([x, y, d, t]) => { const n = nm(s, "ring"); s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { type: "none" }, line: { color: C.violet, width: 1.25, transparency: t }, objectName: n }); return n; });
    const dot = circle(s, 3.55, 3.05, 0.34, C.coral);
    const brand = text(s, [{ text: "VANTA", options: { bold: true, color: C.white } }, { text: "3", options: { bold: true, color: C.coral } }], { onDark: true, x: 6.2, y: 0.9, w: 3, h: 0.4, fontFace: HEAD, fontSize: 20, charSpacing: 4 });
    const t = text(s, "Thank you", { x: 6.2, y: 1.9, w: 6.5, h: 1.2, fontFace: HEAD, fontSize: 60, bold: true, color: C.white });
    const sub = text(s, "Questions, discussion and decisions on the FY2027 plan.", { x: 6.2, y: 3.15, w: 6.2, h: 0.5, fontSize: 18, color: "C9C5EE" });
    const contacts = [];
    const ci = [["LuMail", "strategy@yourcompany.com"], ["LuPhone", "+1 (555) 010-2026"], ["LuMapPin", "Strategy Office, Floor 12"]];
    for (let i = 0; i < ci.length; i++) {
      const y = 4.35 + i * 0.62;
      contacts.push(...await iconIn(s, ci[i][0], 6.2, y, 0.44, C.night2, C.aqua));
      contacts.push(text(s, ci[i][1], { x: 6.8, y: y + 0.05, w: 5, h: 0.35, fontSize: 15, color: C.white, valign: "middle" }));
    }
    const note = text(s, "All figures in this template are illustrative.", { x: 6.2, y: 6.55, w: 6, h: 0.3, fontSize: 11, italic: true, color: "8E8AB8" });
    anim(s, "fade", rings, { t: "with", dur: 900, stagger: 150 });
    anim(s, "zoom", dot, { dur: 400 });
    anim(s, "fade", brand, { t: "with" });
    anim(s, "wipeRight", t, { dur: 600 });
    anim(s, "fade", sub);
    anim(s, "fade", contacts, { stagger: 100, dur: 350 });
    anim(s, "fade", note);
  }

  const file = path.join(OUT, "VANTA3_raw.pptx");
  await pres.writeFile({ fileName: file });
  fs.writeFileSync(path.join(OUT, "anim_plan.json"), JSON.stringify(plan, null, 1));
  fs.writeFileSync(path.join(OUT, "theme.json"), JSON.stringify(THEME, null, 1));
  console.log("Wrote", file, "slides:", plan.length);
}

const steps3 = [];

/** Chapter divider */
async function chapter(num, title, sub, items, section) {
  const s = slide("VANTA Chapter", section, num, title, { transition: "push" });
  s.addText(sub, { placeholder: "chapsub" });
  const names = [];
  items.forEach((it, i) => {
    const y = 5.65 + i * 0;
    names.push(text(s, [{ text: String(i + 1).padStart(2, "0") + "  ", options: { bold: true, color: C.coral } }, { text: it, options: { color: C.white } }], { onDark: true, x: M + i * 3.0, y: 5.75, w: 2.8, h: 0.6, fontSize: 13 }));
  });
  const ic = await iconIn(s, { "01": "LuChartColumn", "02": "LuCompass", "03": "LuUsers", "04": "LuWorkflow", "05": "LuRocket", "06": "LuTrendingUp", "07": "LuFlag" }[num], 10.85, 2.4, 1.6, C.violet, C.white);
  anim(s, "fade", "@ph", { t: "with", dur: 700 });
  anim(s, "zoom", ic, { t: "with", delay: 200, dur: 600 });
  anim(s, "fade", names, { stagger: 150, dur: 400 });
  s.addNotes(`Chapter ${num}: ${title}. ${sub}`);
  return s;
}

build().catch((e) => { console.error(e); process.exit(1); });
