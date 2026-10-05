#!/usr/bin/env python3
"""
make_info_card.py — a neofetch-style info panel: title bar, then
key/value rows that fade + slide in on a short stagger, like the panel
is printing next to the ASCII portrait. Freezes after printing once
(no looping). Pure SMIL/CSS inside the SVG, so GitHub renders it with
no JS and no external service.

Set STATIC=1 to emit a frozen, fully-visible frame (useful for a local
Quick Look preview instead of waiting out the animation).

Usage:
    python scripts/make_info_card.py [output.svg]
Default output: info-card.svg
"""
import os
import sys
import xml.sax.saxutils as sax
from pathlib import Path

STATIC = os.environ.get("STATIC") == "1"

WIDTH = 490
PAD_X = 22
TITLE_H = 34
ROW_H = 26
FONT = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

TITLE = "marco@github ~ $ neofetch"

# key/value rows for the panel
ROWS = [
    ("Role", "Front-end Dev · Assistive Tech Research"),
    ("Now", "CINTESP.Br — pesquisa assistiva"),
    ("Prev", "Algar Telecom · DankiCode · Corteva"),
    ("Stack", "React · TS · JS · WordPress · Firebase"),
    ("Based", "Uberlândia, MG — Brasil"),
    ("Highlights", "SisAssistiva · VR Wheelchair · Pax Aeterna"),
]

# classic neofetch color-swatch row at the bottom
SWATCHES = ["#57606a", "#cf222e", "#2da44e", "#bf8700", "#0969da", "#8250df", "#1b7c83", "#8c959f"]

ROW_STAGGER = 0.09
ROW_DUR = 0.28
SLIDE_PX = 10


def esc(s: str) -> str:
    return sax.escape(s)


def build_svg() -> str:
    key_col_w = max(len(k) for k, _ in ROWS) * 8.6 + 4
    content_top = TITLE_H + 20
    height = content_top + len(ROWS) * ROW_H + 40

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" '
        f'width="{WIDTH}" height="{height}" font-family="{FONT}">'
    )
    parts.append(f'''
  <style>
    .bg {{ fill: #f6f8fa; stroke: #d0d7de; stroke-width: 1; }}
    .titlebar {{ fill: #eaeef2; }}
    .dot {{ opacity: 0.55; }}
    .prompt {{ font-size: 13px; fill: #57606a; }}
    .key {{ font-size: 13px; fill: #bf3989; font-weight: 600; }}
    .val {{ font-size: 13px; fill: #24292f; }}
    @media (prefers-color-scheme: dark) {{
      .bg {{ fill: #0d1117; stroke: #30363d; }}
      .titlebar {{ fill: #161b22; }}
      .prompt {{ fill: #8b949e; }}
      .key {{ fill: #ff7b9c; }}
      .val {{ fill: #c9d1d9; }}
    }}
  </style>''')

    # window chrome
    parts.append(f'<rect class="bg" x="0.5" y="0.5" width="{WIDTH-1}" height="{height-1}" rx="10"/>')
    parts.append(f'<path class="titlebar" d="M1,10 a9,9 0 0 1 9,-9.5 h{WIDTH-20} a9,9 0 0 1 9,9.5 v{TITLE_H-10} h-{WIDTH-2} z"/>')
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle class="dot" cx="{PAD_X + i*18}" cy="{TITLE_H/2}" r="5.5" fill="{color}"/>')
    parts.append(
        f'<text class="prompt" x="{WIDTH/2}" y="{TITLE_H/2 + 4.5}" text-anchor="middle">{esc(TITLE)}</text>'
    )

    def anim(begin: float, row_y: float) -> str:
        # NOTE: an <animateTransform> on "transform" replaces the element's
        # whole transform list while active (and after, with fill="freeze")
        # — it does not compose with a static transform="translate(0,Y)" on
        # the same element. So the row's Y offset is baked into both the
        # "from" and "to" of the animation itself; only X actually moves.
        if STATIC:
            return ""
        return (
            f'<animate attributeName="opacity" from="0" to="1" dur="{ROW_DUR}s" '
            f'begin="{begin}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'from="{SLIDE_PX},{row_y}" to="0,{row_y}" dur="{ROW_DUR}s" begin="{begin}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.2 0 0.2 1"/>'
        )

    y = content_top
    for i, (k, v) in enumerate(ROWS):
        begin = round(i * ROW_STAGGER, 3)
        opacity = "1" if STATIC else "0"
        start_transform = f"translate(0,{y})" if STATIC else f"translate({SLIDE_PX},{y})"
        parts.append(
            f'<g transform="{start_transform}" opacity="{opacity}">'
            f'<text class="key" x="{PAD_X}" y="0">{esc(k)}</text>'
            f'<text class="val" x="{PAD_X + key_col_w}" y="0">{esc(v)}</text>'
            f'{anim(begin, y)}'
            f'</g>'
        )
        y += ROW_H

    # color swatch row
    sw_begin = round(len(ROWS) * ROW_STAGGER, 3)
    sw_y = y + 6
    sw_size = 16
    sw_gap = 6
    sw_x0 = PAD_X
    opacity = "1" if STATIC else "0"
    start_transform = f"translate(0,{sw_y})" if STATIC else f"translate({SLIDE_PX},{sw_y})"
    cells = []
    for i, c in enumerate(SWATCHES):
        cells.append(
            f'<rect x="{sw_x0 + i*(sw_size+sw_gap)}" y="0" width="{sw_size}" height="{sw_size}" '
            f'rx="3" fill="{c}"/>'
        )
    parts.append(
        f'<g transform="{start_transform}" opacity="{opacity}">'
        f'{"".join(cells)}'
        f'{anim(sw_begin, sw_y)}'
        f'</g>'
    )

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "info-card.svg"
    svg = build_svg()
    Path(out).write_text(svg, encoding="utf-8")
    print(f"wrote {out}")
