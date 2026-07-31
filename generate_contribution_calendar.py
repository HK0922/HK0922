"""Renders assets/generated/calendar.svg from data/github_stats.json
A GitHub-style contribution heatmap, drawn from scratch (no third-party
badge/image service)."""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svg_utils import card_frame, font_face_css  # noqa: E402

CELL = 11
GAP = 3
LEFT_PAD = 20
TOP_PAD = 46

# intensity buckets -> color, loosely matching GitHub's own scale
SCALE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def bucket(count: int) -> str:
    if count == 0:
        return SCALE[0]
    if count <= 2:
        return SCALE[1]
    if count <= 5:
        return SCALE[2]
    if count <= 8:
        return SCALE[3]
    return SCALE[4]


def build(data: dict) -> str:
    weeks = data["calendar_weeks"]
    n_weeks = len(weeks)
    w = LEFT_PAD + n_weeks * (CELL + GAP) + 20
    h = TOP_PAD + 7 * (CELL + GAP) + 30

    style = font_face_css("Contribution Calendar" + str(data["total_contributions"]), "SubsetMono")
    svg = card_frame(w, h, "Contribution Calendar", extra_style=style)

    for wi, week in enumerate(weeks):
        for di, count in enumerate(week):
            x = LEFT_PAD + wi * (CELL + GAP)
            y = TOP_PAD + di * (CELL + GAP)
            color = bucket(count)
            svg += (
                f'  <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{color}"><title>{count} contributions</title></rect>\n'
            )

    legend_y = h - 18
    svg += f'  <text x="{LEFT_PAD}" y="{legend_y}" class="label">Less</text>\n'
    lx = LEFT_PAD + 40
    for color in SCALE:
        svg += f'  <rect x="{lx}" y="{legend_y - 10}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>\n'
        lx += CELL + GAP
    svg += f'  <text x="{lx + 6}" y="{legend_y}" class="label">More</text>\n'
    svg += (
        f'  <text x="{w - 20}" y="{legend_y}" text-anchor="end" class="label">'
        f'{data["total_contributions"]:,} contributions, last 12 months</text>\n'
    )

    svg += "</svg>\n"
    return svg


def main() -> None:
    with open("data/github_stats.json") as f:
        data = json.load(f)
    os.makedirs("assets/generated", exist_ok=True)
    out = build(data)
    with open("assets/generated/calendar.svg", "w") as f:
        f.write(out)
    print("wrote assets/generated/calendar.svg")


if __name__ == "__main__":
    main()
