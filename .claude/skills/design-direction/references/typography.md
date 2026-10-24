# Typography

Evidence and sources: `Claude instructions/research-ledger.md` §3 design + audit → "Typography".

## 1. Choosing faces
1. Write **three voice words** that describe physical things, not adjectives ("calm, clinical, careful"; "warm, mechanical, opinionated"). "Modern" and "clean" don't count.
2. List the 3 fonts you'd reach for by reflex. Treat them as suspects. Look for the voice in a real catalogue (Google Fonts, Fontshare, foundries such as Klim, Commercial Type, Pangram Pangram, Future Fonts, ABC Dinamo, Velvetyne) through the lens of a physical object: a museum caption, a 1970s manual, a train timetable, a hardback novel.
3. Cross-check: "elegant" doesn't have to be serif, "technical" doesn't have to be mono, "friendly" doesn't have to be rounded. If the final pick equals the reflex, justify it in one sentence or look again.

**Register matters more than any ban list.**
- *Product UI:* one well-tuned sans for everything is often right. The system stack (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`) or a workhorse like Inter is legitimate here: zero/low download, excellent hinting, tabular figures. Personality comes from colour, density, copy and one display moment.
- *Brand surfaces:* distinctiveness is part of the brief. The current over-used set in generated sites (Inter, Geist, Space Grotesk, DM Sans, Plus Jakarta Sans, Outfit, Fraunces, Playfair, Instrument Serif, IBM Plex) needs a reason ("it matches X"), not a default.
- Licensed brand fonts already in the project always win.

**Pairing:** contrast on one clear axis (serif + sans, condensed display + regular text, grotesk + mono for data) or one family in several weights. Don't pair two similar-but-different faces (two geometric sans). Max 2 families + optionally a mono. This is craft convention: there's no study proving a pairing rule, so judge by eye.

## 2. Sizes and scale
- **Body:** 16 px minimum (`1rem`, root left at 100%); 17–20 px for reading-heavy pages. WCAG sets **no** minimum font size (that's a myth); it requires text to resize to 200% (1.4.4). 16 px is the craft and platform default (Material body-large 16/24, iOS body 17 pt).
- **Inputs** computed ≥ 16 px, or iOS Safari zooms on focus. Never "fix" that with `maximum-scale=1` / `user-scalable=no`.
- Smallest text ~12 px, metadata only, never paragraphs.
- **Product UI:** a fixed rem token scale, hand-tuned (e.g. 12 / 14 / 16 / 20 / 24 / 32), ratio ~1.125–1.2. Material, Carbon and Apple all use fixed scales in product UI.
- **Brand/editorial:** modular ratio 1.25–1.333+, fewer steps with bigger jumps; display can be 3–5× body. Choosing 1.25 over 1.333 is taste; no evidence either way.
- **Fluid type:** `clamp(min-rem, rem + vw, max-rem)`. Never `vw` alone (fails WCAG 1.4.4, F94). Keep max ≤ 2.5 × min; test at 200% zoom. Body text stays fixed.
- Hero display max ~6rem; beyond that it's usually shouting, and long words overflow on mobile. Test the real headline at 320 px.

## 3. Measure, leading, tracking
- **Measure:** prose `max-width: 45–75ch` (≈ 65ch default), never > 80ch. This rests on reading comfort and preference (lab studies show long lines aren't slower); shorter measures help weaker and dyslexic readers. Data tables are exempt.
- **Line-height:** body 1.4–1.6 unitless; headings 1.05–1.25; add 0.05–0.1 for light text on dark and for long measures. Layouts must survive WCAG 1.4.12 overrides (line-height 1.5, letter 0.12em, word 0.16em, paragraph 2×): no fixed-height text boxes.
- **Tracking:** body 0; display ≥ ~32 px: −0.01 to −0.02em (never tighter than −0.04em); all-caps and small caps: +0.05 to +0.12em.
- `text-wrap: balance` on headings (applies to ≤ 6 lines in Chromium); `text-wrap: pretty` on body as progressive enhancement.
- Left-align body text; don't justify on the web (uneven word gaps, no reliable hyphenation). Paragraph spacing **or** first-line indent, not both.
- `font-variant-numeric: tabular-nums` for tables, prices, timers; `lining-nums` in UI.

## 4. Hierarchy
- Few sizes, strong contrast: size jumps of 1.5–3× between levels read as intentional; 14/15/16 reads as muddy.
- Combine 2–3 dimensions: size + weight + space (+ colour last). Weight steps should be visible (400 vs 600/700, not 400 vs 500).
- Use semantic token names: `--text-body`, `--text-label`, `--text-display`, not `--font-16`.

## 5. Loading
Font loading (formats, subsetting, `font-display`, fallback metrics, preload) lives in one place: `frontend-performance/references/loading-assets.md`. Pick faces here; load them per that file.

## 6. Checklist
- [ ] Voice words written; faces justified against them (and the register)
- [ ] ≤ 2 families (+ mono); scale defined as tokens; no arbitrary sizes
- [ ] Body ≥ 16 px in rem; inputs ≥ 16 px; prose ≤ 75ch; leading per role
- [ ] Display tracking tightened, caps tracked open; headlines don't overflow at 320 px
- [ ] 200% zoom and text-spacing overrides don't clip anything
