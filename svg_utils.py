"""
Shared helpers for every generator script:
- embeds a subsetted monospace font as base64 so cards render identically
  on every device (no dependence on the viewer's installed fonts)
- common color palette / card frame so all SVGs look like one family
"""
from __future__ import annotations
import base64
import os
import subprocess
import tempfile

# ---- palette -----------------------------------------------------------
BG = "#0d1117"
BG_ALT = "#161b22"
BORDER = "#30363d"
TEXT = "#c9d1d9"
TEXT_DIM = "#8b949e"
ACCENT = "#58a6ff"
ACCENT_2 = "#3fb950"

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "HTML": "#e34c26",
    "CSS": "#563d7c", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051",
    "Go": "#00ADD8", "Rust": "#dea584", "Dockerfile": "#384d54",
    "Vue": "#41b883", "PHP": "#4F5D95", "Ruby": "#701516",
}


def lang_color(name: str) -> str:
    return LANG_COLORS.get(name, "#8b949e")


# ---- font embedding ------------------------------------------------------
# System monospace font used as the source. Subsetting to just the glyphs a
# card actually needs keeps the embedded base64 tiny (a few KB, not the
# ~700KB a full font would add to every generated SVG).
SOURCE_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SOURCE_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

_CACHE: dict[str, str] = {}


def _subset_to_base64(font_path: str, text: str) -> str:
    """Subset `font_path` down to the glyphs in `text` and return a
    base64-encoded WOFF2 string. Requires the `fonttools` package
    (pip install fonttools[woff]) which is already in requirements.txt."""
    key = font_path + "::" + "".join(sorted(set(text)))
    if key in _CACHE:
        return _CACHE[key]

    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "subset.woff2")
        unicodes = ",".join(f"U+{ord(c):04X}" for c in sorted(set(text)))
        subprocess.run(
            [
                "fonttools", "subset", font_path,
                f"--text={text}",
                "--flavor=woff2",
                f"--output-file={out_path}",
                "--layout-features=*",
            ],
            check=True,
            capture_output=True,
        )
        with open(out_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")

    _CACHE[key] = encoded
    return encoded


def font_face_css(text: str, family: str = "SubsetMono", bold: bool = False) -> str:
    """Return a <style> compatible @font-face block embedding only the
    glyphs present in `text`."""
    font_path = SOURCE_FONT_BOLD if bold else SOURCE_FONT
    b64 = _subset_to_base64(font_path, text)
    weight = "700" if bold else "400"
    return (
        f"@font-face{{font-family:'{family}';src:url(data:font/woff2;"
        f"base64,{b64}) format('woff2');font-weight:{weight};}}"
    )


def card_frame(width: int, height: int, title: str, extra_style: str = "") -> str:
    """Opening <svg> + background + title text shared by every card.
    Caller appends body content, then closes with </svg>."""
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
  <style>
    .bg {{ fill: {BG}; }}
    .border {{ fill: none; stroke: {BORDER}; stroke-width: 1; }}
    .title {{ font-family: 'SubsetMonoBold','SubsetMono',monospace; font-size: 16px;
              fill: {TEXT}; font-weight: 700; }}
    .label {{ font-family: 'SubsetMono',monospace; font-size: 12px; fill: {TEXT_DIM}; }}
    .value {{ font-family: 'SubsetMonoBold','SubsetMono',monospace; font-size: 13px;
              fill: {TEXT}; font-weight: 700; }}
    {extra_style}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6"/>
  <rect class="border" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6"/>
  <text x="20" y="30" class="title">{title}</text>
'''
