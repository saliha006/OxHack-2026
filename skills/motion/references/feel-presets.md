# Feel presets — from an adjective to exact parameters

**Canonical source for every duration, curve and spring value across the v2 skills.**
Other files point here; don't copy numbers elsewhere.

Evidence base: NN/g "Executing UX Animations" (≈100 ms feedback, 200–300 ms substantial changes,
> 400 ms slow, > 500 ms "drag"); Material 3 / Material 1, IBM Carbon, Microsoft Fluent 2 tokens; Apple
WWDC23 *Animate with springs* + SwiftUI presets; Motion source; Dragicevic et al. CHI 2011 (slow-in/
slow-out aids tracking). No peer-reviewed study maps adjectives to numbers — this table is
design-system convention, validated by the visual loop in `motion-review`, not by science.

## Curve tokens
```css
:root {
  /* responses + entrances (decelerate) */
  --ease-out:        cubic-bezier(0.23, 1, 0.32, 1);   /* strong ease-out (quint-like) — default UI */
  --ease-out-quart:  cubic-bezier(0.25, 1, 0.5, 1);    /* softer, "smooth" */
  --ease-out-expo:   cubic-bezier(0.16, 1, 0.3, 1);    /* long tail, "confident/cinematic" */
  --ease-standard:   cubic-bezier(0.2, 0, 0, 1);       /* Material 3 standard — productive */
  /* on-screen A→B moves */
  --ease-in-out:     cubic-bezier(0.77, 0, 0.175, 1);  /* strong in-out (quart-like) */
  --ease-in-out-soft: cubic-bezier(0.65, 0, 0.35, 1);  /* gentle, for slow/ambient */
  /* permanent exits (accelerate) */
  --ease-in:         cubic-bezier(0.3, 0, 1, 1);       /* Material 3 standard-accelerate */
  /* sheets/drawers (iOS-like; Ionic modal + menu source) */
  --ease-drawer:     cubic-bezier(0.32, 0.72, 0, 1);
}
```
CSS `linear()` (Chrome 113+, Firefox 112+, Safari 17.2+) can express springs/overshoot without JS —
generate it from a spring solver; fall back to a cubic-bezier.

## Spring model (Apple / Motion parameterisation)
`{ type: "spring", visualDuration: s, bounce: b }` — **ζ (damping ratio) = 1 − bounce**.
bounce 0 = critically damped (no overshoot) · 0.15 brisk · 0.3 noticeably bouncy · > 0.4 use with
care. SwiftUI: `.smooth` (0.5 s, bounce 0), `.snappy` (0.5 s, 0.15), `.bouncy` (0.5 s, 0.3).
Physics form: ζ = damping / (2·√(stiffness·mass)). Motion's physics defaults (100 / 10 / 1) are
ζ 0.5 ≈ bounce 0.5 — **bouncy**, don't use them by accident. Setting any physics option overrides
`visualDuration`/`bounce`.

## The feel table
| Feel | Duration (UI-size element) | Curve | Spring | Stagger | Extras |
| --- | --- | --- | --- | --- | --- |
| **Instant / none** | 0 ms (feedback ≤ 100 ms) | — | — | — | For keyboard/100+/day actions |
| **Snappy / productive** | 120–200 ms | `--ease-out` or `--ease-standard` | `visualDuration 0.2–0.25, bounce 0` (or 0.1–0.15 for a hint of life) | 20–40 ms | Exit ≈ 70–80 % of enter. Small distances (4–12 px), scale 0.96–0.98 |
| **Smooth / fluid** | 220–350 ms | `--ease-out-quart`; moves `--ease-in-out` | `visualDuration 0.35–0.45, bounce 0` | 40–60 ms | Continuity over flourish; interruptible; consider subtle 2 px blur to bridge crossfades |
| **Springy / playful** | ~0.4–0.6 s perceptual | overshoot `linear()` (fallback `cubic-bezier(0.34, 1.4, 0.64, 1)`) | `visualDuration 0.4–0.5, bounce 0.25–0.35` | 40–70 ms | Bounce only where momentum makes sense (flicks, toggles, celebrations), never on dense UI |
| **Weighty / cinematic** | 450–900 ms (non-blocking only) | `--ease-out-expo`, or Material 3 emphasized-decelerate `cubic-bezier(0.05, 0.7, 0.1, 1)` | `visualDuration 0.6–0.8, bounce 0–0.1` (or `mass 2–3`, `stiffness 120–200`, ζ ≈ 1) | 60–120 ms | Large travel, layered parallax depth, blur-in 4–8 px → 0, scale 1.04 → 1 settles. Marketing/hero only, skippable |
| **Deliberately slow / languid** | 800–2000 ms | `--ease-in-out-soft` or linear for loops | low stiffness (60–100), ζ ≈ 1 | 100–200 ms | Ambient/meditative/brand atmospheres only; never on feedback or navigation; needs pause control if it loops > 5 s |
| **Motion-blurred / speedy** | 150–300 ms travel | `--ease-in-out` (fast middle) | `visualDuration 0.25–0.3, bounce 0` | 20–40 ms | During peak velocity: `filter: blur(2–6px)` *or* stretch `scaleX(1.04–1.1)` along travel, back to 0/1 at rest. Small elements only (blur is costly) |
| **Mechanical / precise** | 100–250 ms | `linear`, `steps(n)` | — | fixed | Tickers, counters, progress, technical UIs |
| **Soft / calm (healthcare, finance)** | 180–280 ms | `--ease-out-quart` | `bounce 0` | 30–50 ms | Opacity + ≤ 8 px moves; no overshoot, no zoom |

## Duration by size and type (default "snappy/smooth" product UI)
| Element | Enter | Notes |
| --- | --- | --- |
| Press feedback, toggle, checkbox | 70–150 ms | Carbon fast-01 70 ms / fast-02 110 ms; NN/g ≈ 100 ms |
| Tooltip, small popover | 120–200 ms | After the first tooltip, subsequent ones open instantly |
| Dropdown, select, menu | 150–250 ms | Carbon moderate 150/240 ms |
| Toast, small panel | 200–300 ms | |
| Modal, drawer, sheet | 250–400 ms | Cap ≈ 400 ms; larger travel → longer (Fluent: "larger elements more time") |
| Full-screen / page transition | 300–500 ms | |
| Marketing / explanatory | 500 ms + | Never blocks the task |

Rules: exit ≈ **70–90 % of enter** (direction is consensus; ratio is convention). Scale duration with
distance and size. Above ~400 ms on functional UI = justify it or cut it.

## Specific values referenced by other files
| Case | Value |
| --- | --- |
| Tens/day interactions (hover, list nav, frequent toggles) | ≤ 150 ms, tiny transform, or none |
| Exit, small surfaces | Shorter **and smaller** than the enter: opacity + 4 px blur + fixed −12 px over ~150 ms (Krehel). Full-height slides only when the destination means something (drawer) |
| Icon swap crossfade | scale 0.25 → 1, opacity 0 → 1, blur 4 → 0 px, spring `visualDuration 0.3, bounce 0` |
| Hold-to-confirm (asymmetric) | Fill 1.5–2 s linear while held; release/snap-back ~200 ms ease-out |
| Group stagger | Per item: see the feel table (typically 30–60 ms). Cap the whole group at ≈ 300–500 ms; beyond ~8–10 items shrink the step or stagger only the first few |
| Stagger of *chunks* ⚠ | Kowalski: 30–80 ms between *items*. Krehel: ~100 ms between *semantic chunks* (title → description → actions), each opacity + 4 px blur + 12 px rise over 300 ms. Not a conflict: items vs chunks |
| Press scale ⚠ | `scale(0.97)` (Kowalski) vs `0.96` / 150 ms ease-out (Krehel); either works, pick one token per product |

## Easing choice
- Entering, responding to input → **ease-out** (decelerate).
- Moving between two on-screen positions → **ease-in-out** (slow-in/slow-out aids tracking — CHI 2011).
- Leaving permanently → **ease-in / accelerate**, short.
- Hover/colour → `ease` or ease-out, short.
- Constant motion (spinner, marquee, scrubbed scroll, progress) → **linear**.
- Never ease-in on entrances or feedback: the slow start lands on the moment the user is watching
  (practitioner consensus across Material, Carbon, NN/g, Kowalski — no controlled study).
- ⚠ Exits: Kowalski uses ease-out for exits too ("never ease-in for UI"); Material, Carbon and NN/g
  use a short accelerate for *permanent* exits (the ledger keeps that). Either is fine if the exit is
  short; pick one per product and tokenise it.

## Writing the feel contract
After the intake, record a one-line contract and extend existing repo tokens rather than forking:
```
Feel: smooth (calm product UI) · base 240 ms --ease-out-quart · exits 180 ms --ease-in ·
springs { visualDuration: 0.4, bounce: 0 } · stagger 40 ms · reduced motion: opacity 150 ms only
```
