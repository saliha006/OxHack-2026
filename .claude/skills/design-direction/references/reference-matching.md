# Matching a reference ("make it feel like X")

Goal: capture the **feeling and the system** of a reference, never its pixels, logo, copy or illustrations. Copying reproduces someone else's identity (and possibly their IP); translating gives the user their own.

## 1. Decompose before you build
For a screenshot, URL or named product, write down (5–8 lines):
- **Palette behaviour**: lightness range (dark stage? paper white?), how much chroma is used and where, accent hue family, how many colours actually appear. Run `python scripts/extract_palette.py ref.png` for real values.
- **Type behaviour**: serif/sans/mono; weight contrast; size jumps (is display 3× body or 1.5×?); tracking; case.
- **Layout behaviour**: grid and column count; alignment (centred vs left vs asymmetric); density; whitespace rhythm (tight groups / big gaps?); max content width.
- **Surface behaviour**: borders vs shadows vs flat fills; radius scale; texture or imagery style.
- **Motion behaviour** (if live): what moves, how fast, on what trigger → hand detail to `motion`.
- **The signature**: the one or two moves that make it recognisable. Usually one typographic choice + one structural or colour choice.

For a live site you can inspect, `reverse-engineer-ui` extracts the real tokens (computed styles, font stacks, spacing values).

## 2. Translate, don't transplant
- Keep the **relationships** (contrast ratios between sizes, how much chroma, spacing proportions), change the **values**: your hue (from the brand), your typefaces (similar voice, not the same font unless licensed and asked), your content.
- Build your ramp from the reference's mood: `python scripts/oklch_palette.py --hue <your hue> --chroma <reference's max C>`.
- Keep at most **one** signature move recognisably close; reinterpret the rest. Two references remixed ("Linear's structure × a magazine's type") usually produce something more original than one reference followed closely.
- Re-check contrast for every pair; references are often below AA (light grey text is the most common reason a "premium-looking" reference fails).

## 3. Record it
Add a "Reference translation" block to the direction contract: what was taken (behaviours), what was deliberately changed, and why. This keeps later sessions from drifting back toward a copy.

## Never
- Copy logos, illustrations, photography, copy, or distinctive brand assets.
- Use a paid font from a reference without the user's licence; suggest a similar-voice alternative.
- Match a reference's inaccessible choices (low-contrast text, tiny targets) because "that's the look".
