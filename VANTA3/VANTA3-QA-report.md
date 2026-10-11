# VANTA3 — Quality-Assurance Report

**Deliverable:** `VANTA3.pptx`. This is an editable 16:9 PowerPoint deck with native animations, built on 11 October 2026.
**Result:** every automated check passed. The checks, their results and the known limitations follow.

## 1. Summary

| Check | Result |
|---|---|
| Slide count | **60 slides**: 1 cover, 1 agenda, 2 executive slides, 7 chapter dividers, 48 content slides, 1 close |
| Format | 16:9 widescreen, 13.33 × 7.50 in, 4 named slide layouts (Light, Dark, Chapter, Cover) and 9 sections |
| Native charts | **53 charts** on 39 slides, **53/53** with an embedded, editable Excel data sheet |
| Chart forms | Column 19, horizontal bar 5, stacked column 3 (incl. waterfall), stacked bar 4 (incl. funnel, tornado), line 14 (incl. combo, sparklines), area 3 (incl. forecast range band), donut 8 (incl. gauges), radar 1, scatter 1, bubble 1. No chart is an image |
| Animations | **1214 native entrance effects** on **60/60 slides** (Fade, Wipe, subtle Zoom). Every build starts automatically and the longest takes 5.2 s |
| Transitions | **60/60 slides**: Fade on content slides, Push (up) on the 7 chapter dividers |
| Animation integrity | 0 problems. Every target resolves to a real shape, no shape enters twice, shape and timing IDs are unique, and build steps are in time order |
| Images | 46 small PNG line icons (Lucide set). **No photographs and no human images of any kind.** All other visuals are editable shapes |
| Fonts | Cambria (headings) and Calibri (body and charts), both bundled with Microsoft Office on Windows and Mac and available in PowerPoint for the web |
| Existing files | `git status` shows only the new `VANTA3/` folder. No existing file was modified |

## 2. Tests performed

1. **Package and schema validation.** The OOXML validator (schema, relationships, content types, charts and slide checks) reports "All validations PASSED".
2. **Animation structure test** (`source/qa_check.py`). It parses every `<p:timing>` tree and checks:
   - every target exists on its slide;
   - no shape has more than one entrance;
   - timing IDs are unique;
   - start times are in order;
   - each build starts automatically on slide load;
   - the build list references only real shapes.
3. **Second-engine round-trip.** LibreOffice Impress opened the deck and converted it to ODP. It imported **1214 of 1214 entrance effects** on 60/60 slides and transitions on 60/60 slides. This shows the animation XML is well formed and readable by an independent presentation engine.
4. **Library open test.** python-pptx opened the deck and listed all 60 slides and 4 custom layouts.
5. **Visual inspection.** All 60 slides were rendered to images and reviewed in several passes. Fixed along the way:
   - overlapping KPI labels;
   - centred titles (now left-aligned);
   - combo-chart label collisions;
   - concentric-circle label placement;
   - milestone card overlaps;
   - risk-grid and table overlap;
   - chevron label clipping;
   - helper-series bleed in the range chart.
6. **Data consistency check.** Every derived figure was recomputed from the underlying data and corrected where needed: CAGRs, growth rates, shares, bridges, funnel conversions, margins, totals and the FCF conversion. Examples: segment and regional totals = $772M, bridge $664M + $108M = $772M, P&L lines reconcile, funnel 18,400 → 389 (2.1%).
7. **Text check.** There are 58 unique slide titles (no duplicates) and no placeholder or lorem text. Spelling is British English throughout (annualised, programme, utilisation).
8. **Contrast check.** All text meets WCAG AA on its background. Text-safe variants of aqua, coral and saffron are used on light surfaces. Chart labels switch to ink automatically wherever white would fall below 4.5:1.

## 3. Animation implementation

The animations are real PowerPoint timing XML inside each slide (`<p:timing>`, presets 10 Fade, 22 Wipe, 53 Zoom), plus `<p:transition>` elements. They are not simulated.

- **Sequence per slide.** Kicker and title fade in with the slide, then the evidence (chart or table), then the interpretation (cards and insight panel). Cards stagger by 90–150 ms.
- **Charts.**
  - Column charts wipe up, so the bars grow.
  - Bar, line, area and donut charts wipe from the left, revealing categories in reading order.
  - Scatter, bubble and radar charts use a subtle zoom.
  - Tables wipe down.
- **Timelines and dashboards** build step by step: Gantt rows, milestone cards and KPI tiles each start slightly after the previous one.
- All builds use *With / After previous*, so slideshow mode runs without extra clicks. To present on clicks, change *Start* in the Animation Pane.

## 4. Known limitations (stated plainly)

- **Microsoft PowerPoint itself was not available in this build environment.** Checks used the OOXML schema validator, a structural test of every animation tree, a LibreOffice Impress import and python-pptx. The XML follows PowerPoint's own structure. Even so, run the deck once in PowerPoint (Windows or Mac) before distribution, as with any generated file.
- **Chart sub-element builds (By Series / By Category) are not pre-set.** Their XML element indices could not be verified without PowerPoint, so each chart animates as one object with a directional Wipe. This still reveals the data progressively and keeps the chart fully editable. To build by series, select a chart › Animation Pane › Effect Options › Chart Animations › By Series.
- **PowerPoint for the web and mobile** play Fade, Wipe and Zoom entrance effects and Fade/Push transitions. Some mobile viewers simplify or skip entrance effects; the slides remain complete and readable without them.
- **The preview PDF and images were rendered with LibreOffice.** It substitutes the metric-compatible fonts Caladea and Carlito for Cambria and Calibri, so tiny differences in letterforms against PowerPoint are expected. Line breaks match because the metrics are identical.
- All business figures are **illustrative**, and the footer of every slide says so.

## 5. Per-slide register

| # | Title | Charts | Entrance effects | Effect types | Transition | Build time |
|---|---|---|---|---|---|---|
| 1 | Cover — Strategy & Performance Review | 0 | 19 | fade, wipe, wipe, zoom | fade | 3.1 s |
| 2 | Seven chapters, one growth story | 0 | 33 | fade, wipe, zoom | fade | 1.9 s |
| 3 | A record year that sets up the next three | 1 | 26 | fade, wipe, wipe | fade | 2.8 s |
| 4 | The numbers that defined the year | 1 | 23 | fade, wipe, wipe, zoom | fade | 3.4 s |
| 5 | Performance | 0 | 8 | fade, zoom | push | 1.5 s |
| 6 | Twenty quarters of uninterrupted growth | 1 | 18 | fade, wipe | fade | 3.0 s |
| 7 | What added $108M to revenue this year | 1 | 9 | fade, wipe | fade | 1.9 s |
| 8 | Platform Software now drives almost half of revenue | 1 | 11 | fade, wipe | fade | 2.6 s |
| 9 | Each segment plays a distinct role in the portfolio | 1 | 18 | fade, wipe, wipe | fade | 2.5 s |
| 10 | Scale is turning into profitability | 1 | 16 | fade, wipe | fade | 3.2 s |
| 11 | Income statement summary | 1 | 9 | fade, wipe, wipe | fade | 2.7 s |
| 12 | Cost discipline funds more R&D | 1 | 21 | fade, wipe, wipe | fade | 2.9 s |
| 13 | Free cash flow has tripled in four years | 1 | 17 | fade, wipe | fade | 2.2 s |
| 14 | Asia-Pacific is our fastest-growing large region | 2 | 9 | fade, wipe, wipe | fade | 2.8 s |
| 15 | Market | 0 | 8 | fade, zoom | push | 1.5 s |
| 16 | A $48B market with ample headroom | 0 | 23 | fade, wipe, zoom | fade | 3.2 s |
| 17 | We are growing almost twice as fast as the market | 1 | 17 | fade, wipe | fade | 3.8 s |
| 18 | We combine scale with above-market growth | 1 | 18 | fade, zoom | fade | 2.3 s |
| 19 | The top five players hold under a third of the market | 1 | 26 | fade, wipe | fade | 2.3 s |
| 20 | Buyers prioritise automation and security | 1 | 21 | fade, wipe | fade | 2.6 s |
| 21 | Three shifts reshaping demand through 2029 | 3 | 26 | fade, wipe | fade | 3.2 s |
| 22 | Our pricing is competitive where it matters most | 1 | 18 | fade, wipe | fade | 2.7 s |
| 23 | Customers & Sales | 0 | 8 | fade, zoom | push | 1.5 s |
| 24 | From 18,400 leads to 389 new customers | 1 | 22 | fade, wipe | fade | 4.9 s |
| 25 | Digital self-serve is the fastest-growing channel | 1 | 18 | fade, wipe | fade | 3.3 s |
| 26 | We win more often, and deals are getting larger | 1 | 17 | fade, wipe, wipe | fade | 2.7 s |
| 27 | Customers stay longer and spend more each year | 1 | 17 | fade, wipe | fade | 3.3 s |
| 28 | Customers rate us above benchmark on five of six measures | 1 | 27 | fade, zoom | fade | 2.0 s |
| 29 | 9% of customers generate 41% of revenue | 1 | 21 | fade, wipe | fade | 2.7 s |
| 30 | Revenue concentration is healthy but worth watching | 1 | 17 | fade, wipe | fade | 3.2 s |
| 31 | Four of five regional teams beat their quota | 1 | 9 | fade, wipe, wipe | fade | 2.6 s |
| 32 | Operations | 0 | 8 | fade, zoom | push | 1.5 s |
| 33 | Operations scorecard: three of four targets met | 4 | 30 | fade, wipe | fade | 1.9 s |
| 34 | On-time delivery has stayed above target since June | 1 | 20 | fade, wipe | fade | 3.5 s |
| 35 | Order-to-cash: cutting nine days from the cycle | 1 | 41 | fade, wipe | fade | 3.5 s |
| 36 | Capacity is tight in Data Engineering and Cloud Ops | 0 | 16 | fade, wipe | fade | 1.9 s |
| 37 | Each employee now generates $268k of revenue | 1 | 16 | fade, wipe | fade | 3.2 s |
| 38 | Service incidents are down by more than half | 1 | 14 | fade, wipe | fade | 2.3 s |
| 39 | Growth | 0 | 8 | fade, zoom | push | 1.5 s |
| 40 | Where to play: six opportunities mapped | 1 | 7 | fade, wipe, zoom | fade | 2.3 s |
| 41 | Every opportunity returns at least 2.5 times its investment | 1 | 19 | fade, wipe | fade | 3.3 s |
| 42 | A disciplined product pipeline feeds the roadmap | 0 | 43 | fade, wipe, wipe | fade | 2.9 s |
| 43 | Expansion targets: three markets in two waves | 1 | 11 | fade, wipe, wipe, zoom | fade | 2.5 s |
| 44 | How we will invest $120M of growth capital in FY27 | 1 | 30 | fade, wipe, wipe | fade | 3.1 s |
| 45 | Outlook | 0 | 8 | fade, zoom | push | 1.5 s |
| 46 | Base case: revenue reaches $1.18B in FY2029 | 1 | 16 | fade, wipe | fade | 3.4 s |
| 47 | Three scenarios frame the planning range | 1 | 23 | fade, wipe | fade | 2.7 s |
| 48 | Key planning assumptions behind the base case | 0 | 4 | fade, wipe | fade | 1.9 s |
| 49 | Retention is the biggest swing factor for FY2029 | 1 | 8 | fade, wipe | fade | 1.9 s |
| 50 | FY2029 ambition at a glance | 4 | 30 | fade, wipe | fade | 1.8 s |
| 51 | Plan | 0 | 8 | fade, zoom | push | 1.5 s |
| 52 | Four strategic priorities for FY2027–FY2029 | 0 | 38 | fade, wipe | fade | 1.4 s |
| 53 | We ask the board to approve three decisions today | 0 | 26 | fade, wipe | fade | 2.0 s |
| 54 | Implementation roadmap, FY2027–FY2028 | 0 | 45 | fade, wipe | fade | 2.8 s |
| 55 | Milestones the board will see each quarter | 0 | 41 | fade, wipe | fade | 4.0 s |
| 56 | Clear ownership for every workstream | 0 | 18 | fade, wipe | fade | 1.8 s |
| 57 | Top risks and how we will manage them | 0 | 42 | fade, wipe, zoom | fade | 2.9 s |
| 58 | The KPI dashboard we will track every month | 6 | 42 | fade, wipe | fade | 4.8 s |
| 59 | Next steps: the first 90 days | 0 | 35 | fade, wipe | fade | 5.2 s |
| 60 | Closing — Thank you | 0 | 17 | fade, wipe, zoom | fade | 4.5 s |

## 6. Files

| File | Contents |
|---|---|
| `VANTA3.pptx` | The editable, animated presentation |
| `VANTA3.pdf` | 60-page static preview |
| `VANTA3-brand-guide.pdf` | 6-page visual identity guide: colour, type, layout, charts, motion, usage |
| `preview/` | 16 representative slides at 1600 × 900, plus `all-slides-overview.jpg` |
| `qa-results.json` | Machine-readable results of the checks above |
| `source/` | Reproducible build: `build_deck.js` (pptxgenjs), `postprocess.py` (animations, transitions, chart refinements), `qa_check.py`, `brand_guide.html`, `build.sh` |
