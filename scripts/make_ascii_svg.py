#!/usr/bin/env python3
"""
make_ascii_svg.py — Step 2 of the ASCII-portrait pipeline.

Converts a prepped grayscale image (see prep_photo.py) into a
self-typing, monochrome ASCII-art SVG. Each row is wrapped in a
clip-path rect that wipes left-to-right with a small cursor block
riding the edge, staggered top to bottom. The whole portrait prints
once and freezes (no looping) using native SMIL <animate>, which
GitHub renders inline in READMEs.

Usage:
    python scripts/make_ascii_svg.py [prepped.png] [output.svg]
Defaults:
    source-prepped.png -> marco-ascii.svg
"""
import sys
import xml.sax.saxutils as sax
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense); leading space = blank
GAMMA = 0.72  # <1 brightens midtones so only true shadows use dense glyphs

COLS = 100
FONT_SIZE = 13
CHAR_W = FONT_SIZE * 0.6
LINE_H = FONT_SIZE * 1.15
CHAR_ASPECT = CHAR_W / LINE_H  # used to pick row count that preserves photo proportions

ROW_STAGGER = 0.032   # seconds between each row starting to wipe
ROW_DUR = 0.34        # seconds for one row's wipe-in
CURSOR_FADE = 0.12    # seconds for the trailing cursor block to fade out


def image_to_ascii_rows(img_path: str, cols: int = COLS) -> list[str]:
    img = Image.open(img_path).convert("L")
    w, h = img.size
    rows = max(1, round(cols * (h / w) * CHAR_ASPECT))

    # Pre-blur so each downsampled cell averages its neighborhood instead of
    # aliasing hair strands / skin texture into salt-and-pepper mid-tones,
    # then nudge the gamma so skin reads as sparse glyphs and only real
    # shadows (hair, glasses, jacket) pull in dense ones.
    blur_radius = max(1, (w // cols) // 2)
    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    small = blurred.resize((cols, rows), Image.LANCZOS)

    arr = np.asarray(small, dtype=np.float32) / 255.0
    arr = np.power(arr, GAMMA)
    small = Image.fromarray((arr * 255).astype(np.uint8))
    pixels = small.load()

    ascii_rows = []
    ramp_max = len(RAMP) - 1
    for y in range(rows):
        line_chars = []
        for x in range(cols):
            brightness = pixels[x, y]  # 0 (black) .. 255 (white)
            idx = round((255 - brightness) / 255 * ramp_max)
            line_chars.append(RAMP[idx])
        ascii_rows.append("".join(line_chars))
    return ascii_rows


def build_svg(rows: list[str]) -> str:
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)
    row_width_px = n_cols * CHAR_W
    canvas_w = round(row_width_px + CHAR_W)
    canvas_h = round(n_rows * LINE_H + LINE_H)

    defs = []
    texts = []

    total_begin = 0.0
    for i, row in enumerate(rows):
        begin = round(i * ROW_STAGGER, 3)
        y = round((i + 1) * LINE_H, 2)
        clip_id = f"c{i}"
        escaped = sax.escape(row)

        defs.append(
            f'<clipPath id="{clip_id}"><rect x="0" y="{round(y - LINE_H, 2)}" '
            f'width="0" height="{round(LINE_H, 2)}">'
            f'<animate attributeName="width" from="0" to="{round(row_width_px, 2)}" '
            f'dur="{ROW_DUR}s" begin="{begin}s" fill="freeze" calcMode="linear"/>'
            f'</rect></clipPath>'
        )

        texts.append(
            f'<text class="row" clip-path="url(#{clip_id})" x="0" y="{y}" '
            f'textLength="{round(row_width_px, 2)}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{escaped}</text>'
        )

        # trailing cursor block that rides the wipe edge, then fades
        cursor_y = round(y - LINE_H, 2)
        texts.append(
            f'<rect class="cursor" x="0" y="{cursor_y}" width="{round(CHAR_W, 2)}" '
            f'height="{round(LINE_H, 2)}" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.001s" '
            f'begin="{begin}s" fill="freeze"/>'
            f'<animate attributeName="x" from="0" to="{round(row_width_px, 2)}" '
            f'dur="{ROW_DUR}s" begin="{begin}s" fill="freeze" calcMode="linear"/>'
            f'<animate attributeName="opacity" from="1" to="0" dur="{CURSOR_FADE}s" '
            f'begin="{round(begin + ROW_DUR, 3)}s" fill="freeze"/>'
            f'</rect>'
        )
        total_begin = max(total_begin, begin + ROW_DUR + CURSOR_FADE)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}"
     width="{canvas_w}" height="{canvas_h}" font-family="SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace">
  <style>
    .row {{ font-size: {FONT_SIZE}px; fill: #57606a; }}
    .cursor {{ fill: #57606a; }}
    @media (prefers-color-scheme: dark) {{
      .row {{ fill: #c9d1d9; }}
      .cursor {{ fill: #c9d1d9; }}
    }}
  </style>
  <defs>
    {"".join(defs)}
  </defs>
  {"".join(texts)}
</svg>
'''
    return svg


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    out = sys.argv[2] if len(sys.argv) > 2 else "marco-ascii.svg"

    rows = image_to_ascii_rows(src)
    svg = build_svg(rows)
    Path(out).write_text(svg, encoding="utf-8")
    print(f"wrote {out} ({len(rows)} rows x {COLS} cols)")
