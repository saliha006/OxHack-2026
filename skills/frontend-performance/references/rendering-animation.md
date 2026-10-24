# Smooth rendering, scrolling and animation

Sources: MDN "CSS and JavaScript animation performance", MDN `will-change`, web.dev animations
guide, Chrome "hardware-accelerated animations" + scroll-driven animation case study, motion.dev
performance docs. Ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

## The pipeline, in one paragraph
Each frame the browser may run: JS → style → layout → paint → composite. Changing a layout property
(`width`, `height`, `top`, `left`, `margin`, `padding`, `font-size`, `border-width`) re-runs layout and
everything after it. Paint-only properties (`color`, `background-color`, `box-shadow`) skip layout
but repaint. `transform` and `opacity` (and `filter` in Chromium) can be animated by the compositor
alone, on its own thread — so they stay smooth even when JavaScript is busy.

Budget per frame: ~16.7 ms at 60 Hz, ~8.3 ms at 120 Hz (and the browser needs some of that).

## Which animation tech runs where
| Tech | Compositor-property animations | Other properties | Survives a busy main thread? |
| --- | --- | --- | --- |
| CSS transition / `@keyframes` | Off main thread | Main thread | Yes (compositor props only) |
| WAAPI `el.animate()` | Off main thread | Main thread | Yes (compositor props only) |
| CSS scroll-driven (`animation-timeline`) | Off main thread | Main thread | Yes (compositor props only) |
| Motion (motion.dev) | Uses WAAPI where it can — incl. independent `x`/`y`/`scale` | rAF | Mostly; springs with velocity/gestures run on rAF |
| GSAP, rAF loops, React state per frame | Main thread | Main thread | **No** |
| Animating a CSS custom property | Never accelerated, even if it feeds `transform` | — | No |

`clip-path` and `background-color` compositor animation are rolling out in Chromium only; treat as
progressive enhancement and verify with the Performance panel.

## Rules
- Prefer `transform`/`opacity`. Express size changes as `scale` (FLIP), reveals as `clip-path`
  (verify cost), and expand/collapse via `grid-template-rows: 0fr → 1fr` or FLIP rather than `height`.
  `interpolate-size: allow-keywords` / `calc-size()` (animate to `height: auto`) is Chromium-only
  (129+) — progressive enhancement.
- **`will-change`**: only for a measured problem; set just before the motion, remove after; never on
  many elements (each promoted layer costs GPU memory). `transform: translateZ(0)` hacks are the
  same thing — don't blanket them.
- Bound expensive effects: `filter: blur()`/`backdrop-filter` on large or many surfaces is costly,
  especially on Safari and low-end GPUs. Keep blur radii small and areas isolated; `contain: paint`
  helps. Animated blur: small and short-lived, never continuous or on large surfaces. ⚠ Limits differ
  (ibelick ≤ 8 px; Kowalski/Rams < 20 px) and no primary benchmark backs either: use ≤ 8 px for
  continuous or large areas, ≤ 20 px only for brief one-shots, and verify with a trace.
- Avoid `transition: all` — it animates properties you didn't intend, some off the compositor.
- Don't drive per-frame motion via React/Vue state; write `style.transform` or use motion values.
- Batch DOM reads before writes; do writes in `requestAnimationFrame`.
- Scroll: no per-frame `scroll` listeners reading layout. Use `IntersectionObserver` (reveal, lazy
  init) or scroll-driven animations; mark touch/wheel listeners `{ passive: true }`.
- Long pages: `content-visibility: auto` + `contain-intrinsic-size` for off-screen sections;
  virtualise lists with thousands of rows.
- Heavy visuals (WebGL, canvas, video backgrounds): lazy-initialise near viewport, pause when
  off-screen (`IntersectionObserver`) and when `document.hidden`, cap device-pixel-ratio (≤ 2),
  provide a static fallback for reduced motion and weak GPUs. OffscreenCanvas in a worker for
  heavy 2D/3D rendering.

## Scroll-driven animations (CSS)
```css
@supports (animation-timeline: scroll()) {
  .progress { transform-origin: 0 50%; animation: grow linear both; animation-timeline: scroll(root); }
  .reveal   { animation: rise linear both; animation-timeline: view(); animation-range: entry 0% cover 30%; }
}
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes rise { from { opacity: 0; translate: 0 2rem; } to { opacity: 1; translate: 0 0; } }
@media (prefers-reduced-motion: reduce) { .reveal { animation: none; } }
```
Support (Oct 2026): Chrome 115+, Safari 26+; Firefox still behind a flag in stable → always ship the
static fallback outside `@supports`.

## View transitions
- Same-document (`document.startViewTransition`): Baseline since Oct 2025 (Chrome 111, Safari 18,
  Firefox 144).
- Cross-document (`@view-transition { navigation: auto; }`): Chrome 126+, Safari 18.2+, Firefox partial.
- Snapshots are composited, but the DOM update inside the callback is on the main thread — keep it
  fast. Name only the elements that should morph (`view-transition-name`), keep durations short, and
  disable/shorten under reduced motion.

## Diagnose jank
1. DevTools → Performance → record with 4× CPU throttle → look at the **Frames** track (dropped /
   partially presented frames) and the main-thread flame chart under them.
2. Rendering tab: Paint flashing, Layer borders, Frame rendering stats.
3. LoAF entries name the script that blocked the frame.
4. Lighthouse diagnostic `non-composited-animations` lists animations that couldn't be composited and why.
5. `motion-review/scripts/frame-timing.mjs` automates rAF-interval + LoAF capture under throttling.
