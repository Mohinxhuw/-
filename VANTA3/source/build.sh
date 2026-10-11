#!/bin/bash
# Build VANTA3.pptx: generate with pptxgenjs, apply theme, post-process animations.
# Requires: node with pptxgenjs, react, react-dom, react-icons, sharp on NODE_PATH; python3; APPLY_THEME=path to apply_theme.js (applies THEME colours to the theme part).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/../.build}"
mkdir -p "$WORK"
node "$HERE/build_deck.js" "$WORK"
node -e "require(process.argv[1]).applyTheme(process.argv[2], require(process.argv[3])).then(()=>console.log('theme applied'))" "$APPLY_THEME" "$WORK/VANTA3_raw.pptx" "$WORK/theme.json"
python3 "$HERE/postprocess.py" "$WORK/VANTA3_raw.pptx" "$WORK/anim_plan.json" "$WORK/VANTA3.pptx"
