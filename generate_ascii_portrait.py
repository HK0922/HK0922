"""
Turns assets/source_photo.jpg into an animated ASCII-art SVG.

Pipeline:
  1. GrabCut background removal (classical CV -- no model download, so it
     stays fast and dependency-light in CI. Swap in `rembg` later for
     nicer edges if you want; see the note at the bottom of this file).
  2. CLAHE contrast enhancement on the foreground.
  3. Bilateral filter to smooth sensor noise without losing edges.
  4. Downsample to a character grid, map cell brightness -> ASCII density.
  5. Render as an SVG where each row fades/rises in with a staggered CSS
     animation delay -- this animates in any GitHub README, because
     markdown embeds it as an <img>, and the browser runs an <img>'s
     internal SVG animations same as any other image resource.
"""
from __future__ import annotations
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from svg_utils import font_face_css, BG  # noqa: E402

# sparse -> dense, i.e. dark background pixels map to the left end (space),
# bright/foreground pixels map to the right end (dense glyph)
RAMP = " .:-=+*#%@"

COLS = 100          # character columns
CHAR_ASPECT = 0.52   # monospace glyphs are taller than wide; corrects row count
FONT_SIZE = 8
LINE_HEIGHT = FONT_SIZE / CHAR_ASPECT * 0.62


def remove_background(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Returns (grayscale_foreground, foreground_mask 0/1) using GrabCut
    seeded with a centered rectangle covering ~85% of the frame."""
    h, w = bgr.shape[:2]
    rect = (int(w * 0.06), int(h * 0.04), int(w * 0.88), int(h * 0.92))

    mask = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype("uint8")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = np.where(fg_mask == 1, gray, 0).astype("uint8")
    return gray, fg_mask


def enhance(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    smoothed = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    return smoothed


def to_ascii_grid(gray: np.ndarray, mask: np.ndarray, cols: int = COLS) -> list[str]:
    h, w = gray.shape
    rows = max(1, round(cols * (h / w) * CHAR_ASPECT))
    small_gray = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    small_mask = cv2.resize(mask.astype("float32"), (cols, rows), interpolation=cv2.INTER_AREA)

    lines = []
    ramp_last = len(RAMP) - 1
    for r in range(rows):
        line_chars = []
        for c in range(cols):
            if small_mask[r, c] < 0.35:
                line_chars.append(" ")
                continue
            intensity = small_gray[r, c] / 255.0
            idx = min(ramp_last, int(intensity * ramp_last + 0.5))
            line_chars.append(RAMP[idx])
        lines.append("".join(line_chars))
    return lines


def escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace(" ", "\u00A0"))


def build_svg(lines: list[str]) -> str:
    cols = max(len(l) for l in lines)
    char_w = FONT_SIZE * 0.6
    width = int(cols * char_w) + 20
    height = int(len(lines) * LINE_HEIGHT) + 20

    alphabet = "".join(sorted(set("".join(lines)))) or " "
    style = font_face_css(alphabet, "AsciiMono")

    keyframes = """
    @keyframes rowIn { from { opacity: 0; transform: translateY(-2px); } to { opacity: 1; transform: translateY(0); } }
    .row { font-family: 'AsciiMono', monospace; font-size: %dpx;
           fill: #58a6ff; white-space: pre; animation: rowIn 0.4s ease-out both; }
    """ % FONT_SIZE

    svg = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ASCII portrait">',
        f'<style>{style}{keyframes}</style>',
        f'<rect width="{width}" height="{height}" fill="{BG}"/>',
    ]
    for i, line in enumerate(lines):
        y = 14 + i * LINE_HEIGHT
        delay = i * 0.035
        svg.append(
            f'  <text x="10" y="{y:.1f}" class="row" '
            f'style="animation-delay:{delay:.2f}s">{escape(line)}</text>'
        )
    svg.append("</svg>\n")
    return "\n".join(svg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="assets/source_photo.jpg")
    ap.add_argument("--out", default="assets/generated/ascii_portrait.svg")
    ap.add_argument("--cols", type=int, default=COLS)
    args = ap.parse_args()

    if not os.path.exists(args.source):
        sys.exit(
            f"No source photo at {args.source}. Add a photo there "
            "(square-ish crop, subject roughly centered) and re-run."
        )

    bgr = cv2.imread(args.source)
    if bgr is None:
        sys.exit(f"Could not read {args.source} -- is it a valid image file?")

    gray, mask = remove_background(bgr)
    gray = enhance(gray)
    lines = to_ascii_grid(gray, mask, cols=args.cols)
    svg = build_svg(lines)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out} ({len(lines)} rows x {args.cols} cols)")


if __name__ == "__main__":
    main()

# --- optional upgrade -------------------------------------------------
# GrabCut is classical CV: fast, no downloads, but it struggles with messy
# backgrounds or low subject/background contrast. For meaningfully better
# segmentation, swap remove_background() for `rembg` (U^2-Net):
#
#   pip install rembg[cpu]
#   from rembg import remove
#   rgba = remove(bgr_bytes)   # returns RGBA with alpha as the mask
#
# The tradeoff: rembg downloads a ~170MB model on first run, which adds
# real time to a daily CI job unless you cache it (actions/cache keyed on
# the model file). GrabCut avoids that entirely, which is why it's the
# default here.
