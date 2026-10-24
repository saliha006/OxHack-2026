#!/usr/bin/env python3
"""Generate an accessible OKLCH token set (light + dark) from one brand hue.

Usage:
    python oklch_palette.py --hue 250                    # restrained SaaS-style accent
    python oklch_palette.py --hue 160 --chroma 0.14      # stronger accent
    python oklch_palette.py --hue 25 --neutral-chroma 0  # pure-grey neutrals
    python oklch_palette.py --hue 250 --css > tokens.css # CSS only, no report

What it does (stdlib only):
1. Builds an 11-step neutral ramp (50..950) tinted a hair toward the brand hue
   and an 11-step accent ramp, holding hue fixed, varying OKLCH lightness and
   tapering chroma at the extremes. Every step is gamut-mapped into sRGB.
2. Maps ramps to semantic roles for light and dark themes.
3. Checks every text/background role pair with the WCAG 2 ratio and nudges the
   accent step until links/buttons pass. Prints a PASS/FAIL table.

The hue is YOUR decision (from the brief), not a default. The output is a
starting point: adjust by eye, then re-run contrast_check.py on any edits.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast_check import oklch_to_srgb_clamped, ratio  # noqa: E402

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
# Lightness targets per step (perceptual, OKLCH L). Roughly even visual spacing.
L_NEUTRAL = [0.985, 0.967, 0.922, 0.870, 0.708, 0.556, 0.439, 0.371, 0.269, 0.205, 0.145]
L_ACCENT = [0.971, 0.936, 0.885, 0.810, 0.707, 0.623, 0.546, 0.488, 0.424, 0.379, 0.282]


def taper(L: float) -> float:
    """Chroma multiplier: full in the mid-tones, reduced near white/black."""
    return max(0.15, 1 - (abs(L - 0.6) / 0.45) ** 2)


def build_ramp(Ls, hue, chroma, tapered=True):
    ramp = {}
    for step, L in zip(STEPS, Ls):
        C = chroma * (taper(L) if tapered else 1)
        rgb01, _ = oklch_to_srgb_clamped(L, C, hue)
        ramp[step] = {"L": L, "C": round(C, 4), "rgb": tuple(c * 255 for c in rgb01)}
    return ramp


def css(v):
    return f"oklch({v['L'] * 100:.1f}% {v['C']:.3f} {HUE:g})"


def hexof(v):
    return "#{:02x}{:02x}{:02x}".format(*(round(c) for c in v["rgb"]))


def pick_accent(acc, bg, start_step, darker=True, need=4.5):
    """Walk the accent ramp from start_step until it reaches `need` against bg."""
    order = STEPS[STEPS.index(start_step):] if darker else STEPS[:STEPS.index(start_step) + 1][::-1]
    for s in order:
        if ratio(acc[s]["rgb"], bg["rgb"]) >= need:
            return s
    return order[-1]


def on_colour(fill):
    white, black = (255, 255, 255), (17, 17, 17)
    return ("#ffffff", white) if ratio(white, fill["rgb"]) >= ratio(black, fill["rgb"]) else ("#111111", black)


def main():
    global HUE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hue", type=float, required=True, help="brand hue 0-360 (OKLCH h)")
    ap.add_argument("--chroma", type=float, default=0.12, help="peak accent chroma (0.08 calm .. 0.2 vivid)")
    ap.add_argument("--neutral-chroma", type=float, default=0.008, help="neutral tint 0..0.02 (0 = pure grey)")
    ap.add_argument("--css", action="store_true", help="print CSS only")
    a = ap.parse_args()
    HUE = a.hue

    neu = build_ramp(L_NEUTRAL, a.hue, a.neutral_chroma, tapered=False)
    acc = build_ramp(L_ACCENT, a.hue, a.chroma)

    light = {"bg": neu[50], "surface": neu[100], "border": neu[200], "border-strong": neu[500], "ink": neu[950], "ink-muted": neu[600]}
    dark = {"bg": neu[900], "surface": neu[800], "border": neu[700], "border-strong": neu[500], "ink": neu[200], "ink-muted": neu[400]}
    light_acc = pick_accent(acc, light["bg"], 600, darker=True)
    dark_acc = pick_accent(acc, dark["bg"], 400, darker=False)
    light["accent"], dark["accent"] = acc[light_acc], acc[dark_acc]

    lines = [":root {", "  color-scheme: light dark;"]
    for s in STEPS:
        lines.append(f"  --neutral-{s}: {css(neu[s])};")
    for s in STEPS:
        lines.append(f"  --accent-{s}: {css(acc[s])};")
    lines.append("}")

    def theme_block(selector, t, acc_step):
        on_hex, _ = on_colour(t["accent"])
        out = [f"{selector} {{"]
        names = {"bg": "--color-bg", "surface": "--color-surface", "border": "--color-border",
                 "border-strong": "--color-border-strong",
                 "ink": "--color-ink", "ink-muted": "--color-ink-muted"}
        for k, var in names.items():
            src = "neutral-" + str([s for s in STEPS if neu[s] is t[k]][0])
            out.append(f"  {var}: var(--{src});")
        out.append(f"  --color-accent: var(--accent-{acc_step});")
        out.append(f"  --color-on-accent: {on_hex};")
        out.append("}")
        return out

    lines += theme_block(":root", light, light_acc)
    lines += ["@media (prefers-color-scheme: dark) {"]
    lines += ["  " + l for l in theme_block(':root:not([data-theme="light"])', dark, dark_acc)]
    lines += ["}"]
    lines += theme_block(':root[data-theme="dark"]', dark, dark_acc)
    print("\n".join(lines))
    if a.css:
        return 0

    print("\n/* ---- contrast report (WCAG 2 ratio) ----")
    failures = 0
    for name, t in (("light", light), ("dark", dark)):
        _, on_rgb = on_colour(t["accent"])
        checks = [
            ("ink on bg", t["ink"]["rgb"], t["bg"], 4.5),
            ("ink on surface", t["ink"]["rgb"], t["surface"], 4.5),
            ("ink-muted on bg", t["ink-muted"]["rgb"], t["bg"], 4.5),
            ("ink-muted on surface", t["ink-muted"]["rgb"], t["surface"], 4.5),
            ("accent (link) on bg", t["accent"]["rgb"], t["bg"], 4.5),
            ("on-accent on accent", on_rgb, t["accent"], 4.5),
            ("border-strong vs bg (UI)", t["border-strong"]["rgb"], t["bg"], 3.0),
            ("border vs bg (decor)*", t["border"]["rgb"], t["bg"], 1.0),
        ]
        print(f"  {name}:")
        for label, fg, bg, need in checks:
            r = ratio(fg, bg["rgb"])
            ok = r >= need
            failures += not ok
            print(f"    {'PASS' if ok else 'FAIL'}  {label:<24} {r:5.2f}:1  (need {need})")
    print("  * --color-border is decorative (dividers, card edges): exempt from WCAG 1.4.11. Any border that is the"
          "\n    only visible boundary of an input/control must use --color-border-strong (>= 3:1).")
    print(f"  accent step chosen: light={light_acc}, dark={dark_acc}")
    print("*/")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
