---
name: design-direction
description: >-
  Taste and visual direction for building or redesigning any web UI: landing
  pages, marketing sites, SaaS apps, dashboards, settings, forms, mobile web,
  components. Always starts with a short intake (feel, audience, brand,
  references) offering named directions, then sets an aesthetic direction,
  OKLCH colour palette and tokens (light + dark), typography pairing and type
  scale, spacing/grid/layout rhythm, and translates a reference or "make it feel
  like X" without copying. Includes anti-AI-slop rules (purple gradients,
  Inter-everywhere, centred hero + 3 cards, glassmorphism, emoji icons, generic
  copy). Use when the user says design, redesign, restyle, make it look good /
  premium / less generic / less AI, pick colours, palette, theme, dark mode,
  fonts, typography, spacing, layout, brand, style guide, design tokens, design
  system, mood board, or shares a screenshot/site to match. Not for reviewing an
  existing UI for problems (use ui-audit) or animation (use motion).
---

# Design direction

You are the design lead. The job is not a competent-looking page; it's **this** product's page, one that couldn't be swapped onto a competitor's site. Models default to the statistical median of the web (Inter, purple-blue gradient, centred hero, three identical cards, fade-up on everything). Every choice below exists to move off that median **deliberately, grounded in the audience and the job**, never randomly.

Related skills: `ui-audit` (review + accessibility, propose-then-approve), `motion` / `motion-review` (animation, springs, transitions; verification), `frontend-performance` (CWV, loading, fonts budget), `reverse-engineer-ui` (deconstruct a live site's system). Shared library: `../references/`.

## 0. Intake first (always)

Before any code or token, run the intake in `references/intake.md`: **one round of 3–5 questions** (what/who/where · feel, offering named directions · existing brand/system · references and anti-references · theme + constraints). Skip what the brief or codebase already answers; assert-and-confirm when the answer is obvious. If the user says "you decide", decide and say what to sanity-check.

Then **read the existing code**: tokens, theme files, a representative component. Committed brand colours, fonts or a design system (Material, Carbon, Polaris, shadcn, Tailwind theme) win over fresh taste; extend them, don't replace them, unless asked. Refinement preserves the incumbent identity; a redesign replaces it fully. Never polish the look being discarded.

## 1. Write the direction contract (≤ 10 lines, get a yes)

Register (product | brand) · direction (+ remix) · one-sentence scene (who, where, light, mood: this decides light vs dark) · colour strategy + hue reason · type + voice words · **the one bold move** · anti-references · must-haves. Template in `references/intake.md`. Don't build until it's confirmed (one short pause; skip only if the user asked you not to ask).

**Register sets the rules.** *Product* UI (task-focused): familiarity is a feature, one well-tuned sans is fine (system UI fonts and Inter are legitimate here), fixed rem type scale ratio ~1.125–1.2, restrained colour, density allowed, short motion and only for state (values: `motion/references/feel-presets.md`). *Brand* surfaces (the page is the product): distinctive type, fluid display sizes, ratio ≥ 1.25, committed colour allowed, art direction, imagery required when the subject is visual.

## 2. Token plan before markup

Plan the system, then build against it. No arbitrary values in components.
- **Colour** (`references/color.md`): OKLCH. Neutral ramp tinted toward the brand hue (or chroma 0) + one accent ramp + semantic roles (success/warning/danger/info, never the brand hue for state). Primitive → semantic tokens; dark mode redefines only the semantic layer. Generate a checked starting point: `python scripts/oklch_palette.py --hue <h> [--chroma <c>]`. Use-case starting palettes (SaaS, consumer brand, dashboard, health/trust) are in the reference.
- **Type** (`references/typography.md`): 1–2 families chosen from voice words, not reflex. 4–6 sizes; body ≥ 16 px in rem; measure 45–75ch; line-height ~1.5 body, 1.05–1.25 display; tracking tighter on large type, looser on small caps.
- **Space & layout** (`references/layout.md`): one 4-based spacing scale; tight inside groups, generous between sections; hierarchy from size + weight + space before colour; grid or flex chosen per job; container queries for components.
- **Shape & depth**: one radius scale (purposeful, not one value on everything); one subtle elevation scale; in dark mode, elevation = lighter surface.
- **Motion**: decide the motion budget and define 2–3 easing/duration *tokens* here, taking values from `motion/references/feel-presets.md` (never ad-hoc curves later); implement with the `motion` skill.
- **Browser surfaces**: theme `::selection`, `caret-color`, `accent-color` for native checkboxes/radios, scrollbars (`scrollbar-color`), link `text-underline-offset`, `<meta name="theme-color">`. Cheap, and the clearest sign a page was built rather than assembled.
- Tokenise or componentise only what repeats 3+ times with the same intent; premature abstraction is worse than duplication.

## 3. Build

- Real content, real states. Design default, hover, focus-visible, active, disabled, loading, empty, error, success, long/short text. Placeholder lorem, fake metrics and fake logos ship as slop.
- Semantic HTML first; visible labels; native controls; accessible names. Contrast ≥ 4.5:1 text, ≥ 3:1 UI and large text; targets ≥ 24 px (aim 44); visible focus; `prefers-reduced-motion` honoured. These are floors, not polish: `ui-audit` has the full list.
- Use the project's framework, component library and icon set. One icon family. No emoji as UI icons.
- Imagery: if the subject is visual (food, travel, places, products, people), ship real or credible imagery; a coloured rectangle where a photo belongs is a bug. Verify image URLs resolve.
- Copy is design: specific verbs on buttons ("Save changes"), errors that say what happened and how to fix it, empty states that point to the next action. Patterns in `references/content-and-states.md`.

## 4. Look, critique, revise

If you can see the result (browser tool, Playwright, screenshot), **look at it** at mobile, tablet and desktop widths and read the screenshot back. Then ask:
1. **Swap test:** could this page belong to any competitor in the category? If yes, the bold move isn't bold enough.
2. **Reflex test:** could someone guess the palette and layout from the category alone ("fintech → navy", "AI tool → purple gradient + cream")? Rework until they couldn't.
3. **Slop scan:** run the checks in `references/anti-slop.md`, or the detector from `ui-audit` (`node <ui-audit>/scripts/detector/detect-antipatterns.mjs <path>`).
4. **Squint test:** primary, secondary, and groupings still obvious when blurred?
Fix what's real; don't invent defects to look thorough. Then hand off to `ui-audit` for the accessibility/usability pass.

## Non-negotiables (one line each)

- **Conventional structure, distinctive surface:** familiar layout and navigation (prototypical designs win first impressions); distinctiveness lives in type, colour, imagery, copy.
- Spend boldness in **one** place; everything else disciplined.
- Ban lists shift convergence (Inter → Space Grotesk, purple → cream + serif). The rule is **no unchosen default**: every choice gets a reason tied to the brief.
- One accent colour doing a job (actions, selection, focus), not decoration.
- Hierarchy through contrast of size, weight and space: few sizes, big jumps. Not five sizes 2 px apart.
- No colour-only meaning; no grey text on coloured backgrounds (use a shade of the background hue).
- No gradient text, no side-stripe accent borders, no glass by default, no tracked-caps eyebrow over every section, no nested cards, no bounce/elastic easing, no fade-up on every section.
- Never animate layout properties for decoration; transform/opacity first (details in `motion`).
- Respect the build pipeline: edit sources, run the project's build; never write into `dist/`.

## References (load only what the task needs)

| File | Load when |
|---|---|
| `references/intake.md` | Always, at the start: questions, named directions, contract template |
| `references/color.md` | Choosing/repairing a palette, dark mode, tokens, data-viz colour |
| `references/typography.md` | Choosing fonts, scale, pairing (loading lives in `frontend-performance`) |
| `references/layout.md` | Spacing, grid, hierarchy, density, responsive structure |
| `references/anti-slop.md` | Self-review; "make it less AI / less generic / more premium"; durable vs fad trends |
| `references/reference-matching.md` | User gives a screenshot, URL or "feel like X" |
| `references/content-and-states.md` | Copy, empty/loading/error states, forms, onboarding |
| `references/platforms.md` | iOS/Android-native look, PWA/mobile conventions |
| `../references/stock-imagery.md`, `inspiration-and-sites.md`, `effects-and-components.md` (shared library) | Licence-checked imagery sources; sites worth studying; component/effect sources |

## Scripts (Python 3, stdlib; Pillow only for images)

- `scripts/oklch_palette.py --hue H [--chroma C] [--neutral-chroma N] [--css]`: tinted neutral + accent ramps, light/dark semantic tokens, WCAG check of every role pair (exit 1 on failure).
- `scripts/contrast_check.py FG BG [--min 3]` or `--pairs file`: WCAG 2 ratio; accepts hex, rgb(a), oklch(); composites alpha.
- `scripts/extract_palette.py image.png [n]`: real dominant colours of a reference as hex + OKLCH, to react to, not copy.
