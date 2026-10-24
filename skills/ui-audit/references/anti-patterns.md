# Anti-patterns: detector + manual checklist

## Running the bundled detector

```bash
node <ui-audit>/scripts/detector/detect-antipatterns.mjs src/                # text output
node <ui-audit>/scripts/detector/detect-antipatterns.mjs --json index.html  # JSON for synthesis
node <ui-audit>/scripts/detector/detect-antipatterns.mjs --scope type,layout src/
node <ui-audit>/scripts/detector/detect-antipatterns.mjs https://localhost:3000   # needs puppeteer
```
- Exit `0` clean, `2` findings. Node ≥ 18, no network for files.
- **Engines.** `.html` files get static HTML+CSS cascade analysis *if* the optional parsers are installed (`npm i --no-save htmlparser2 css-select css-tree domutils` inside the skill folder); otherwise everything uses regex rules (fewer contrast/heading/layout checks). Other files (CSS, JSX/TSX, Vue, Svelte) always use regex rules. URLs render in headless Chrome via `puppeteer`.
- **Skip big trees.** It skips `node_modules`, build output etc.; still, scope it to the changed surface when the repo is large.
- **Ignores** (legacy names kept from upstream): file-level `<!-- impeccable-disable rule-id -- reason -->`, line-level `/* impeccable-disable-line rule-id */`, next line `// impeccable-disable-next-line rule-id`. Project-wide: `.impeccable/config.json` → `{"detector":{"ignoreRules":[],"ignoreFiles":[],"ignoreValues":[]}}`. Only suggest ignores the user approves.
- Treat output as **evidence, not verdict**. It finds patterns; you judge whether each one hurts users here.

## Rule map → severity guidance

| Rule id | What it flags | Default severity |
|---|---|---|
| `low-contrast` | Text below 4.5:1 (3:1 large) | **P1** (P0 if body copy on a core flow < 3:1) |
| `gray-on-color` | Grey text on a coloured surface | P2 (P1 if it fails contrast) |
| `tiny-text` | Body text below ~12–14 px | P1/P2 by context |
| `skipped-heading` | h1 → h3 etc. | P2 (P1 if headings are the only structure) |
| `layout-transition` | Animating width/height/top/left | P2 (perf/jank; see `motion-review`) |
| `line-length` | Prose lines far beyond ~75ch | P2 |
| `tight-leading`, `justified-text`, `all-caps-body`, `wide-tracking` | Readability | P2 |
| `text-overflow`, `clipped-overflow-container`, `body-text-viewport-edge`, `cramped-padding` | Clipping / crowding | P1 if content is lost, else P2 |
| `broken-image` | Missing/placeholder images | P1 on primary content |
| `design-system-*` | Value outside the project's DESIGN.md tokens | P2/P3 |
| `side-tab`, `border-accent-on-rounded`, `gradient-text`, `ai-color-palette`, `cream-palette`, `dark-glow`, `nested-cards`, `monotonous-spacing`, `flat-type-hierarchy`, `icon-tile-stack`, `hero-eyebrow-chip`, `repeated-section-kickers`, `numbered-section-markers`, `italic-serif-display`, `oversized-h1`, `extreme-negative-tracking`, `bounce-easing`, `overused-font`, `single-font`, `em-dash-overuse`, `marketing-buzzword`, `aphoristic-cadence` and the other `slop` rules | "Generated-looking" tells | **P3 advisory**; raise only if it also harms legibility, hierarchy or trust |

`overused-font` / `single-font` are taste calls. A single well-tuned UI sans (incl. Inter or the system stack) is legitimate in product UI; flag only on brand surfaces where distinctiveness is the brief.

## Manual slop checklist (what a scanner can't see)

Count the tells; 0–1 = intentional, 2–3 = generic, 4+ = template. Always pair each with a concrete counter-move.

| Tell | Counter-move to propose |
|---|---|
| Centred hero + gradient blob + three identical icon cards | Lead with the real product/content; vary section structure by what each section must do |
| Purple/indigo → blue gradients, glowing accents on near-black | Hue chosen from the brand/subject; solid colour; glow only where light is the subject |
| Generic copy ("Unlock the power of…", "Seamless", "Elevate", "Revolutionize") | Specific claims a competitor couldn't make; numbers with sources; plain verbs |
| Fake social proof (lorem logos, "10k+ happy users", stock testimonials) | Real proof or none |
| Emoji or mismatched icon sets as UI icons | One icon family at consistent size/stroke |
| Same radius and same soft shadow on every element | Radius/elevation scale tied to component role |
| Nested rounded corners that don't line up | Concentric radii: outer = inner + padding (+ border); past ~24 px padding treat them as separate surfaces |
| Borders faking elevation, shadows faking structure | Shadows for elevation, borders for structure |
| Images blending into a same-tone background | 1 px inset outline at `oklch(0 0 0 / .1)` (light) or `oklch(1 0 0 / .1)` (dark), neutral, never tinted |
| Glass/blur cards over gradients as default surface | Opaque surfaces; translucency only on floating chrome with legible contrast |
| Fade-and-slide-up on every section | Motion only where it explains change (hand to `motion-review`) |
| Every section the same rhythm and width | Tight groups, generous separations, one full-bleed moment |
| Placeholder imagery or coloured blocks where photos belong | Real/credible imagery, verified URLs |

## Severity reminder
Slop findings never outrank accessibility or task failures. A beautiful page that can't be used by keyboard is a P0; an ugly accessible one is a P3 conversation.
