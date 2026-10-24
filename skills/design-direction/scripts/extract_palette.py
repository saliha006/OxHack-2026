#!/usr/bin/env python3
"""Read the real dominant colours of a reference image (hex + OKLCH + share).

Usage:
    python extract_palette.py reference.png [n_colours]

Use it to *react to* a reference (screenshot, moodboard, photo), not to copy it:
note the lightness range, how much chroma the reference actually uses, and the
hue family of the accent. Then build your own ramp with oklch_palette.py.

Requires Pillow (`pip install pillow`). Exits cleanly with a message if missing.
"""
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast_check import _srgb_to_linear  # noqa: E402

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Run:  pip install pillow")
    raise SystemExit(2)


def srgb_to_oklch(rgb):
    r, g, b = (_srgb_to_linear(c / 255) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return L, C, H


def extract(path: str, n: int = 6):
    img = Image.open(path).convert("RGB")
    img.thumbnail((200, 200))  # speed; distribution is preserved
    method = getattr(getattr(Image, "Quantize", None), "MEDIANCUT", 0)  # Pillow < 9.1 fallback
    q = img.quantize(colors=max(n * 4, 16), method=method)
    palette = q.getpalette()
    data = q.get_flattened_data() if hasattr(q, "get_flattened_data") else q.getdata()
    counts = Counter(data)
    total = img.width * img.height
    out = []
    for idx, c in counts.most_common(n):
        rgb = tuple(palette[idx * 3: idx * 3 + 3])
        out.append((rgb, round(100 * c / total, 1)))
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    print(f"Dominant colours in {sys.argv[1]} (react to these, don't paste them in):")
    print("  hex       share   oklch")
    for rgb, pct in extract(sys.argv[1], n):
        L, C, H = srgb_to_oklch(rgb)
        hue = f"{H:5.1f}" if C > 0.02 else "  -  "
        print(f"  #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}   {pct:5.1f}%  L {L:.2f}  C {C:.3f}  H {hue}")
    print("\nRead it: L range = light/dark mood; max C = how loud the reference is (<0.05 muted,"
          " >0.15 vivid); the chromatic hue = accent family.\nNext: python oklch_palette.py --hue <H> --chroma <C>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
