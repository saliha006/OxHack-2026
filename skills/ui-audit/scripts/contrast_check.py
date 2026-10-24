#!/usr/bin/env python3
"""WCAG 2.x contrast ratio between two colours (stdlib only).

Usage:
    python contrast_check.py "#595959" "#ffffff"
    python contrast_check.py "oklch(0.55 0.12 250)" "oklch(0.98 0.005 250)"
    python contrast_check.py "rgba(0,0,0,.6)" "#fafafa"        # alpha is composited over bg
    python contrast_check.py --pairs pairs.txt                  # one "fg bg" pair per line

Accepted formats: #rgb, #rrggbb, #rrggbbaa, r,g,b, rgb()/rgba(), oklch(L C H [/ a])
(L as 0-1 or %). Out-of-sRGB-gamut OKLCH is chroma-reduced to fit and flagged.

Prints the ratio and pass/fail per WCAG 2.2 threshold. Exit 0 if the pair meets
AA for normal text (4.5:1), else 1. Use --min 3 for large text / UI components.

Notes:
- Large text = >= 24px regular or >= 18.66px (14pt) bold.
- WCAG 2 ratio is the legal/normative test. APCA (WCAG 3 draft) is advisory only;
  check it separately (e.g. apcacontrast.com) for dark themes and thin type.
"""
import math
import re
import sys


def _srgb_to_linear(c: float) -> float:
    # WCAG 2.2 uses the sRGB spec threshold 0.04045 (0.03928 in older text; same result).
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def oklch_to_srgb(L: float, C: float, H: float):
    """OKLCH -> sRGB floats in 0..1 (may be out of gamut)."""
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_linear_to_srgb(x) if x >= 0 else -_linear_to_srgb(-x) for x in (r, g, bl))


def _in_gamut(rgb, eps=1e-4):
    return all(-eps <= c <= 1 + eps for c in rgb)


def oklch_to_srgb_clamped(L, C, H):
    """Reduce chroma (binary search) until the colour fits sRGB. Returns (rgb01, clipped?)."""
    rgb = oklch_to_srgb(L, C, H)
    if _in_gamut(rgb):
        return tuple(min(1, max(0, c)) for c in rgb), False
    lo, hi = 0.0, C
    for _ in range(30):
        mid = (lo + hi) / 2
        if _in_gamut(oklch_to_srgb(L, mid, H)):
            lo = mid
        else:
            hi = mid
    return tuple(min(1, max(0, c)) for c in oklch_to_srgb(L, lo, H)), True


def parse(colour: str):
    """Return (r, g, b, alpha) with rgb in 0..255 floats, plus a note."""
    s = colour.strip().lower()
    note = ""
    m = re.fullmatch(r"oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)(?:deg)?\s*(?:/\s*([\d.]+)(%?))?\s*\)", s)
    if m:
        L = float(m.group(1)) / (100 if m.group(2) else 1)
        alpha = 1.0
        if m.group(5):
            alpha = float(m.group(5)) / (100 if m.group(6) else 1)
        rgb, clipped = oklch_to_srgb_clamped(L, float(m.group(3)), float(m.group(4)))
        if clipped:
            note = "out of sRGB gamut; chroma reduced to fit"
        return tuple(c * 255 for c in rgb) + (alpha,), note
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)\s*(?:[,/]\s*([\d.]+)(%?))?\s*\)", s)
    if m:
        alpha = 1.0 if not m.group(4) else float(m.group(4)) / (100 if m.group(5) else 1)
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)), alpha), note
    if "," in s:
        parts = [float(x) for x in s.split(",")]
        return (parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else 1.0), note
    s = s.lstrip("#")
    if len(s) in (3, 4):
        s = "".join(ch * 2 for ch in s)
    if len(s) in (6, 8):
        vals = [int(s[i:i + 2], 16) for i in range(0, len(s), 2)]
        alpha = vals[3] / 255 if len(vals) == 4 else 1.0
        return (float(vals[0]), float(vals[1]), float(vals[2]), alpha), note
    raise ValueError(f"cannot parse colour: {colour!r}")


def composite(fg, bg):
    """Alpha-composite fg (r,g,b,a) over an opaque bg (r,g,b)."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def luminance(rgb) -> float:
    r, g, b = (_srgb_to_linear(c / 255.0) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg_rgb, bg_rgb) -> float:
    l1, l2 = luminance(fg_rgb), luminance(bg_rgb)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def check(fg_s: str, bg_s: str, minimum: float) -> bool:
    fg, fg_note = parse(fg_s)
    bg, bg_note = parse(bg_s)
    if bg[3] < 1:
        print(f"  note: background alpha ignored (composite it over its own backdrop first)")
    fg_rgb = composite(fg, bg[:3]) if fg[3] < 1 else fg[:3]
    r = ratio(fg_rgb, bg[:3])
    hexes = "#{:02x}{:02x}{:02x}".format(*(round(c) for c in fg_rgb)), "#{:02x}{:02x}{:02x}".format(*(round(c) for c in bg[:3]))
    print(f"{fg_s}  on  {bg_s}   ({hexes[0]} on {hexes[1]})")
    for n in (fg_note, bg_note):
        if n:
            print(f"  note: {n}")
    print(f"  Contrast ratio: {r:.2f}:1")
    for label, need in (("AA  normal text      4.5:1", 4.5), ("AA  large text / UI  3:1  ", 3.0),
                        ("AAA normal text      7:1  ", 7.0), ("AAA large text       4.5:1", 4.5)):
        print(f"    {'PASS' if r >= need else 'FAIL'}  {label}")
    ok = r >= minimum
    if not ok:
        print(f"  -> below required {minimum}:1")
    return ok


def main(argv) -> int:
    minimum = 4.5
    if "--min" in argv:
        i = argv.index("--min")
        minimum = float(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if len(argv) == 2 and argv[0] == "--pairs":
        all_ok = True
        with open(argv[1], encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                # split on two+ spaces or a tab so "oklch(a b c)" survives
                parts = re.split(r"\s{2,}|\t", line)
                if len(parts) < 2:
                    print(f"skip (need 'fg<TAB or 2 spaces>bg'): {line}")
                    continue
                all_ok &= check(parts[0], parts[1], minimum)
                print()
        return 0 if all_ok else 1
    if len(argv) != 2:
        print(__doc__)
        return 2
    return 0 if check(argv[0], argv[1], minimum) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
