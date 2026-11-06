#!/usr/bin/env python3
"""Fail the build if a patched font lost characters or broke the 2:1 grid."""
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

GLYPH_LIMIT = 65535
LATIN, CJK = 0x41, 0x4E2D
ICONS = {"powerline": 0xE0B0, "font-awesome": 0xF07B, "devicons": 0xE725, "material": 0xF0001}
MIN_MATERIAL_ICONS = 6000
EXPECTED_WEIGHTS = 10


def is_pua(cp):
    return 0xE000 <= cp <= 0xF8FF or cp >= 0xF0000


def check(src_path, out_path):
    src, out = TTFont(src_path), TTFont(out_path)
    src_map, out_map = src.getBestCmap(), out.getBestCmap()
    src_w, out_w = src["hmtx"], out["hmtx"]
    errors = []

    kept = [cp for cp in src_map if not is_pua(cp)]
    lost = [cp for cp in kept if cp not in out_map]
    if lost:
        errors.append(f"{len(lost)} characters lost, first U+{lost[0]:04X}")
    changed = [cp for cp in kept if cp in out_map and src_w[src_map[cp]][0] != out_w[out_map[cp]][0]]
    if changed:
        errors.append(f"{len(changed)} advance widths changed, first U+{changed[0]:04X}")

    half = out_w[out_map[LATIN]][0]
    if out_w[out_map[CJK]][0] != 2 * half:
        errors.append(f"CJK is not twice the Latin width (Latin {half})")
    for name, cp in ICONS.items():
        if cp not in out_map:
            errors.append(f"{name} icon U+{cp:04X} missing")
        elif out_w[out_map[cp]][0] != half:
            errors.append(f"{name} icon U+{cp:04X} is not single-width")

    material = sum(0xF0001 <= cp <= 0xF1AF0 for cp in out_map)
    if material < MIN_MATERIAL_ICONS:
        errors.append(f"only {material} Material icons")
    glyphs = out["maxp"].numGlyphs
    if glyphs > GLYPH_LIMIT:
        errors.append(f"{glyphs} glyphs exceeds the limit")

    family = out["name"].getDebugName(1)
    print(f"{out_path.name}: family={family!r} style={out['name'].getDebugName(2)!r} "
          f"glyphs={glyphs} material={material} errors={len(errors)}")
    for error in errors:
        print(f"  ERROR {error}")
    return not errors


def main(src_dir, out_dir, stem_from, stem_to):
    sources = sorted(Path(src_dir).glob("*.ttf"))
    if len(sources) != EXPECTED_WEIGHTS:
        sys.exit(f"expected {EXPECTED_WEIGHTS} source fonts, found {len(sources)}")
    ok = True
    for src in sources:
        out = Path(out_dir) / src.name.replace(stem_from, stem_to)
        if not out.is_file() or out.stat().st_size == 0:
            print(f"{out.name}: ERROR missing or empty")
            ok = False
            continue
        ok = check(src, out) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
