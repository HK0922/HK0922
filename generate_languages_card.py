"""Renders assets/generated/languages.svg from data/github_stats.json"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from svg_utils import card_frame, font_face_css, lang_color, TEXT_DIM  # noqa: E402

W = 420
ROW_H = 26
TOP_PAD = 48
BOTTOM_PAD = 16


def build(data: dict) -> str:
    langs = data["top_languages"]
    h = TOP_PAD + len(langs) * ROW_H + BOTTOM_PAD

    all_text = "Top Languages" + "".join(l["name"] for l in langs) + "".join(
        f"{l['percent']}%" for l in langs
    )
    style = font_face_css(all_text, "SubsetMono") + font_face_css(all_text, "SubsetMonoBold", bold=True)
    style += ".pct{font-family:'SubsetMono',monospace;font-size:12px;fill:%s;}" % TEXT_DIM

    svg = card_frame(W, h, "Top Languages", extra_style=style)

    bar_x, bar_w = 140, 220
    for i, lang in enumerate(langs):
        y = TOP_PAD + i * ROW_H
        color = lang_color(lang["name"])
        filled = max(4, bar_w * lang["percent"] / 100)
        svg += f'  <text x="20" y="{y + 14}" class="label">{lang["name"]}</text>\n'
        svg += (
            f'  <rect x="{bar_x}" y="{y + 4}" width="{bar_w}" height="8" rx="4" '
            f'fill="#21262d"/>\n'
        )
        svg += (
            f'  <rect x="{bar_x}" y="{y + 4}" width="{filled:.1f}" height="8" rx="4" '
            f'fill="{color}"/>\n'
        )
        svg += f'  <text x="{bar_x + bar_w + 10}" y="{y + 14}" class="pct">{lang["percent"]}%</text>\n'

    svg += "</svg>\n"
    return svg


def main() -> None:
    with open("data/github_stats.json") as f:
        data = json.load(f)
    os.makedirs("assets/generated", exist_ok=True)
    out = build(data)
    with open("assets/generated/languages.svg", "w") as f:
        f.write(out)
    print("wrote assets/generated/languages.svg")


if __name__ == "__main__":
    main()
