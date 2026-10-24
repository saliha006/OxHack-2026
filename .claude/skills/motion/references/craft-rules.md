# Craft rules — how good UI motion is built

Largely from Emil Kowalski (emilkowal.ski, animations.dev; Sonner/Vaul), plus Apple WWDC and
platform docs. Values come from [feel-presets.md](feel-presets.md). `motion-review` checks against
this file.

## Should it animate?
| Frequency | Decision |
| --- | --- |
| Keyboard-initiated or 100+/day (shortcuts, command palette, core nav) | None. (Raycast has no open/close animation.) |
| Tens/day (hover, list nav, frequent toggles) | Minimal: tiny transform or none (cap in feel-presets) |
| Occasional (modals, drawers, toasts) | Standard |
| Rare / first-time (onboarding, success, celebration) | Room for delight |

Valid purposes: feedback · spatial consistency · state indication · preventing a jarring change ·
explanation · delight (rare tier). "Looks cool" on frequent UI fails. Functional data the user is
reading doesn't move for style.

## Physicality & origin
- **Never `scale(0)`.** Enter from `scale(0.9–0.97)` + `opacity: 0`.
- **Origin-aware:** popovers/menus/tooltips scale from the trigger — Radix
  `var(--radix-popover-content-transform-origin)`, Base UI `var(--transform-origin)`. Modals stay centred.
- **Press feedback:** `:active { transform: scale(0.97) }` (0.95–0.98; pick one token), on pointer-down.
- **Same path in and out.** A toast that enters from the bottom leaves to the bottom.
- **Exits are smaller, not just shorter:** fade plus a short fixed offset, not the full container
  height, unless the destination means something (a drawer). Values: feel-presets.
- `translate` in **percent of own size** (`translateY(100%)`) instead of hard-coded px.
- `scale()` scales children (text, icons) — fine for press, wrong for resizing containers (use FLIP
  with counter-scaled children or Motion `layout`).

## Interruptibility
- Rapidly re-triggered UI uses **CSS transitions** (retarget from current value) or springs —
  `@keyframes` restart from zero.
- Entry without JS: `@starting-style` (Baseline; plus `transition-behavior: allow-discrete` for
  `display`/overlay, Firefox partial). Fallback: set a `data-mounted` attribute after first paint.
- Gestures: springs with velocity ([gestures-springs.md](gestures-springs.md)).
- **Asymmetric timing:** slow where the user decides (hold-to-confirm fill, linear), fast where the
  system responds (release, ease-out). Values: feel-presets.

## Group motion
- Stagger short and cap the group total (values and the items-vs-chunks distinction: feel-presets).
- Stagger is decorative: never block interaction while it plays.
- `animation-delay: calc(var(--i) * 40ms)` with `style="--i: n"` per item.
- One orchestrated moment per view beats many scattered ones. Fade-and-rise on every scrolled
  section is the AI-default tell — don't.

## Polish techniques
- **Blur bridge:** when a crossfade double-exposes, add `filter: blur(2px)` mid-transition. Keep
  blur small and brief (budget: `frontend-performance/references/rendering-animation.md`).
- **Instant subsequent tooltips:** delay the first, then open neighbours with no delay/animation.
- **clip-path reveals:** `inset(t r b l)` — reveal on scroll (`inset(0 0 100% 0)` → `inset(0)`),
  hold-to-confirm overlays, tab colour transitions (duplicate list, clip the active copy),
  before/after sliders.
- **Height auto:** `grid-template-rows: 0fr → 1fr` (works everywhere) or `interpolate-size:
  allow-keywords` (Chromium only) — not `max-height` hacks.
- **Morphing buttons/labels:** animate the content swap (opacity + small y + blur) inside a
  fixed-size or `layout`-animated container. Icon swaps: crossfade with scale-up + blur (values: feel-presets).
- **Skip state animations on first render** (Motion `AnimatePresence initial={false}`); only an
  intentional hero entrance animates on load.
- **Theme switch:** suppress transitions while swapping themes (add a no-transition class, force a
  style flush with `getComputedStyle`, remove it next frame), or every colour transition smears.
- **Static cue:** every animated state change also leaves a static cue (colour, icon, label); motion
  is never the only feedback.
- **Cohesion:** one feel across the product; one bouncy component in a crisp app is a bug.

## Performance (motion-specific; depth in the `frontend-performance` skill)
- Animate `transform` and `opacity` (and `filter` sparingly). Never `transition: all`.
- Don't animate layout properties (`width`, `height`, `top`, `left`, `margin`, `padding`).
- Don't drive per-frame motion through a CSS variable on a parent (style recalc of the whole subtree,
  never accelerated). Write `el.style.transform` or use motion values.
- Predetermined motion → CSS/WAAPI (survives a busy main thread). Gesture/physics motion → JS springs.
  Motion's independent `x`/`y`/`scale` *are* hardware-accelerated via WAAPI today (the old "use a
  full transform string" advice is outdated).
- WAAPI for programmatic CSS-performance animation:
  ```js
  el.animate([{ clipPath: "inset(0 0 100% 0)" }, { clipPath: "inset(0)" }],
             { duration: 600, easing: "cubic-bezier(0.77, 0, 0.175, 1)", fill: "forwards" });
  ```
- `will-change` only for a measured problem, added before and removed after.

## Touch & hover
- Gate hover motion: `@media (hover: hover) and (pointer: fine)` — touch fires hover on tap.
- Respond on pointer-down; ~10 px slop before committing to a drag direction.

## Reduced motion
Always: replace travel/zoom/parallax with fades; keep meaningful feedback. Details:
[accessibility.md](accessibility.md).

## Debugging
- Slow it down: DevTools Animations drawer (replay slower, scrub) or multiply durations 5–10×.
- Look for: properties finishing out of sync, wrong origin, double exposure, abrupt stops, jumps on
  interrupt.
- Gestures on real devices (USB + remote devtools).
- Review the next day with fresh eyes.
- Then run `motion-review` — it captures frames and timing so judgement isn't only by eye.
