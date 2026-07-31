"""Renders assets/generated/stats.svg from data/github_stats.json"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svg_utils import card_frame, font_face_css, TEXT, TEXT_DIM, ACCENT, ACCENT_2  # noqa: E402

W, H = 420, 190


def build(data: dict) -> str:
    rows = [
        ("Total Stars", f"{data['total_stars']:,}"),
        ("Total Repos", f"{data['total_repos']:,}"),
        ("Contributions (1y)", f"{data['total_contributions']:,}"),
        ("Current Streak", f"{data['current_streak']} days"),
        ("Longest Streak", f"{data['longest_streak']} days"),
        ("Followers", f"{data['followers']:,}"),
    ]
    all_text = "".join(l for l, _ in rows) + "".join(v for _, v in rows) + "Stats"
    style = font_face_css(all_text, "SubsetMono") + font_face_css(all_text, "SubsetMonoBold", bold=True)

    svg = card_frame(W, H, "Stats", extra_style=style)
    svg = svg.replace(
        "</style>",
        f"text{{font-family:'SubsetMono',monospace;}}</style>",
    )

    col_w = W // 2
    for i, (label, value) in enumerate(rows):
        col, row = divmod(i, 3)
        x = 24 + col * col_w
        y = 62 + row * 38
        dot_color = ACCENT if i % 2 == 0 else ACCENT_2
        svg += f'  <circle cx="{x}" cy="{y - 5}" r="3" fill="{dot_color}"/>\n'
        svg += f'  <text x="{x + 12}" y="{y}" class="label">{label}</text>\n'
        svg += f'  <text x="{x + 12}" y="{y + 18}" class="value">{value}</text>\n'

    svg += "</svg>\n"
    return svg


def main() -> None:
    with open("data/github_stats.json") as f:
        data = json.load(f)
    os.makedirs("assets/generated", exist_ok=True)
    out = build(data)
    with open("assets/generated/stats.svg", "w") as f:
        f.write(out)
    print("wrote assets/generated/stats.svg")


if __name__ == "__main__":
    main()
