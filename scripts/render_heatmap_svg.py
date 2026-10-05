#!/usr/bin/env python3
"""
render_heatmap_svg.py — Step 5b of the heatmap pipeline.

Renders data/contributions.json (see fetch_contributions.py) as the
classic 53-week x 7-day contribution calendar: rounded, colored boxes
with a GitHub-ish green ramp, revealed once in a diagonal line-after-
line slide-down (CSS keyframes, no looping), plus a Less->More legend
and a stats footer. Pure CSS/SMIL inside the SVG — GitHub renders it
with no JS and no third-party service.

Usage:
    python scripts/render_heatmap_svg.py [contributions.json] [output.svg]
Defaults:
    data/contributions.json -> contrib-heatmap.svg
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# none -> brightest; index 5 is a neon top-end reserved for the single
# best day(s) of the year, layered on top of GitHub's own 0-4 levels.
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
PALETTE_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39", "#39d353"]

BOX = 11
GAP = 3
LEFT_LABEL_W = 24
TOP_LABEL_H = 16
PAD = 10

DIAG_STAGGER = 0.022
CELL_DUR = 0.32

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DOW_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # Sun=0 .. Sat=6


def build_weeks(days: list[dict]) -> list[list[dict | None]]:
    by_date = {d["date"]: d for d in days}
    first = datetime.strptime(days[0]["date"], "%Y-%m-%d")
    last = datetime.strptime(days[-1]["date"], "%Y-%m-%d")

    # back up to the Sunday on/before the first day, so every column is a
    # full Sun->Sat week
    grid_start = first - timedelta(days=(first.weekday() + 1) % 7)

    weeks: list[list[dict | None]] = []
    cur = grid_start
    col: list[dict | None] = []
    while cur <= last:
        date_str = cur.strftime("%Y-%m-%d")
        col.append(by_date.get(date_str))
        if len(col) == 7:
            weeks.append(col)
            col = []
        cur += timedelta(days=1)
    if col:
        while len(col) < 7:
            col.append(None)
        weeks.append(col)
    return weeks


def neon_indices(days: list[dict]) -> set[str]:
    """Dates that get the bonus 'neon' palette tier: the single best day."""
    best = max((d["count"] for d in days), default=0)
    if best <= 0:
        return set()
    return {d["date"] for d in days if d["count"] == best}


def build_svg(payload: dict) -> str:
    days = payload["days"]
    weeks = build_weeks(days)
    neon_dates = neon_indices(days)
    n_cols = len(weeks)

    grid_w = n_cols * BOX + (n_cols - 1) * GAP
    grid_h = 7 * BOX + 6 * GAP
    canvas_w = PAD * 2 + LEFT_LABEL_W + grid_w
    footer_h = 46
    legend_h = 20
    canvas_h = PAD * 2 + TOP_LABEL_H + grid_h + legend_h + footer_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" '
        f'width="{canvas_w}" height="{canvas_h}" font-family="SFMono-Regular, Consolas, '
        f"'Liberation Mono', Menlo, monospace\">"
    ]

    # palette as CSS custom properties, swapped per color-scheme
    light_vars = ";".join(f"--l{i}:{c}" for i, c in enumerate(PALETTE_LIGHT))
    dark_vars = ";".join(f"--l{i}:{c}" for i, c in enumerate(PALETTE))
    cell_fill_rules = "\n".join(f"    .lv{i} {{ fill: var(--l{i}); }}" for i in range(len(PALETTE)))

    parts.append(f'''
  <style>
    :root {{ {light_vars}; }}
    @media (prefers-color-scheme: dark) {{ :root {{ {dark_vars}; }} }}
{cell_fill_rules}
    .label {{ font-size: 10px; fill: #57606a; }}
    .footer {{ font-size: 12px; fill: #24292f; }}
    .footer-dim {{ font-size: 11px; fill: #57606a; }}
    @media (prefers-color-scheme: dark) {{
      .label {{ fill: #8b949e; }}
      .footer {{ fill: #c9d1d9; }}
      .footer-dim {{ fill: #8b949e; }}
    }}
    .cell {{
      stroke: rgba(27,31,36,0.06);
      opacity: 0;
      transform-box: fill-box;
      transform-origin: center;
      animation: cellIn {CELL_DUR}s ease-out forwards;
    }}
    @keyframes cellIn {{
      from {{ opacity: 0; transform: translate(-5px, -5px) scale(0.6); }}
      to   {{ opacity: 1; transform: translate(0, 0) scale(1); }}
    }}
  </style>''')

    grid_x0 = PAD + LEFT_LABEL_W
    grid_y0 = PAD + TOP_LABEL_H

    # month labels (one per column where the month changes)
    last_month = None
    for col_i, week in enumerate(weeks):
        first_real = next((d for d in week if d is not None), None)
        if not first_real:
            continue
        month = first_real["date"][:7]
        if month != last_month:
            last_month = month
            m = int(first_real["date"][5:7]) - 1
            x = grid_x0 + col_i * (BOX + GAP)
            parts.append(f'<text class="label" x="{x}" y="{PAD + 10}">{MONTH_ABBR[m]}</text>')

    # day-of-week labels
    for row_i, lbl in DOW_LABELS.items():
        y = grid_y0 + row_i * (BOX + GAP) + BOX - 2
        parts.append(f'<text class="label" x="{PAD}" y="{y}">{lbl}</text>')

    # grid cells, diagonal reveal
    for col_i, week in enumerate(weeks):
        for row_i, day in enumerate(week):
            x = grid_x0 + col_i * (BOX + GAP)
            y = grid_y0 + row_i * (BOX + GAP)
            if day is None:
                continue
            level = day["level"]
            lv_class = "lv5" if day["date"] in neon_dates else f"lv{level}"
            begin = round((col_i + row_i) * DIAG_STAGGER, 3)
            title = f'{day["count"]} contributions on {day["date"]}' if day["count"] else f'No contributions on {day["date"]}'
            parts.append(
                f'<rect class="cell {lv_class}" x="{x}" y="{y}" width="{BOX}" height="{BOX}" '
                f'rx="2.5" style="animation-delay:{begin}s"><title>{title}</title></rect>'
            )

    # legend: Less [swatches] More
    legend_y = grid_y0 + grid_h + 16
    n_swatches = len(PALETTE) - 1  # skip the neon bonus tier in the legend
    less_w = 28
    swatches_w = n_swatches * BOX + (n_swatches - 1) * 3
    legend_w = less_w + 6 + swatches_w + 6 + 32  # "Less" + gap + swatches + gap + "More"
    lx = canvas_w - PAD - legend_w
    parts.append(f'<text class="label" x="{lx}" y="{legend_y}">Less</text>')
    swatch_x0 = lx + less_w + 6
    for i in range(n_swatches):
        sx = swatch_x0 + i * (BOX + 3)
        parts.append(f'<rect class="lv{i}" x="{sx}" y="{legend_y - 9}" width="{BOX}" height="{BOX}" rx="2.5"/>')
    parts.append(f'<text class="label" x="{swatch_x0 + swatches_w + 6}" y="{legend_y}">More</text>')

    # footer stats
    stats = payload.get("stats", {})
    footer_y = legend_y + 26
    total_line = f'{payload["total_contributions"]:,} contributions in the last year'.replace(",", ",")
    parts.append(f'<text class="footer" x="{grid_x0}" y="{footer_y}">{total_line}</text>')
    streak_bits = []
    if stats.get("longest_streak"):
        streak_bits.append(f'longest streak {stats["longest_streak"]}d')
    if stats.get("current_streak"):
        streak_bits.append(f'current streak {stats["current_streak"]}d')
    if stats.get("best_day") and stats["best_day"]["count"]:
        streak_bits.append(f'best day {stats["best_day"]["count"]} ({stats["best_day"]["date"]})')
    if streak_bits:
        parts.append(
            f'<text class="footer-dim" x="{grid_x0}" y="{footer_y + 16}">{" · ".join(streak_bits)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/contributions.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"

    payload = json.loads(Path(src).read_text(encoding="utf-8"))
    svg = build_svg(payload)
    Path(out).write_text(svg, encoding="utf-8")
    print(f"wrote {out}")
