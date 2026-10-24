# Motion accessibility — reduced motion, vestibular safety, WCAG

Sources (fetched Oct 2026): W3C Understanding SC 2.3.3 / 2.2.2 / 2.3.1; MDN `prefers-reduced-motion`;
Apple HIG Accessibility + Motion and App Store "Reduced motion evaluation criteria"; Val Head, A List
Apart (2020); Eric Bailey, CSS-Tricks (2019); Tatiana Mac "no-motion-first" (2021); Josh Comeau
"Accessible animations in React" (2026); motion.dev accessibility docs. Ledger:
`Claude instructions/research-ledger.md` §4 motion + performance.

## The rules that bind
| WCAG 2.2 | Level | Requirement |
| --- | --- | --- |
| 2.3.1 Three Flashes | A | Nothing flashes more than 3×/second (or stays below flash thresholds). |
| 2.2.2 Pause, Stop, Hide | A | Auto-starting motion that lasts > 5 s and runs alongside other content needs a **persistent** pause/stop/hide control. **Pause-on-hover/focus alone does not satisfy it.** (marquees, carousels, looping hero video, ambient WebGL) |
| 2.3.3 Animation from Interactions | AAA | Motion triggered by interaction (scroll-linked, parallax, slide-ins, page-flip transitions) can be disabled unless essential. Treat as a target, honoured via `prefers-reduced-motion`. |

## Who this is for
Vestibular/balance dysfunction is common and rises steeply with age (US NHANES data: ~18 % in their
40s, ~85 % at 80+ failed a balance test — Agrawal et al. 2009). That's balance, not "screen motion
sensitivity", so **don't quote "35 % of users are motion-sensitive."** It does mean older audiences
deserve extra care. Others affected: migraine, concussion, ADHD/attention, epilepsy (flashing).

## What triggers symptoms (four independent sources agree)
High risk: large or full-viewport movement; parallax / multi-speed layers; scroll-jacking; motion in
a different direction from the scroll; fast 3D zoom/spin across a large distance; peripheral motion;
auto-advancing carousels; vortex/spiral effects; animated blur/depth-of-field.
Low risk: opacity, colour, small blur-free fades, small-distance transforms.

## Reduced motion means *reduce or replace*, not zero
- Replace x/y/z travel, scale-zoom, parallax and spin with a **cross-fade, highlight, or colour shift**
  (Apple's prescribed substitute). Tighten springs (no bounce). Don't animate into/out of blur.
- Keep feedback that carries meaning (press state, focus, state change) — just without travel.
- Stop or provide stills for ambient loops, video backgrounds, WebGL scenes, marquees.
- Don't just shorten everything: with JS springs, cutting duration can make motion *more* abrupt.

### No-motion-first (preferred structure)
```css
.card { opacity: 1; }                                  /* base: no motion */
@media (prefers-reduced-motion: no-preference) {
  .card { transition: transform 220ms var(--ease-out), opacity 220ms var(--ease-out); }
  .card[data-enter] { transform: translateY(8px); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .card { transition: opacity 160ms linear; }           /* substitute: fade only */
}
```
Browsers that don't support the query get no motion — the safe default.

### Global safety net (backstop only, never the whole strategy)
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important; scroll-behavior: auto !important;
  }
}
```
Tiny non-zero values keep `animationend`/`transitionend` firing (`animation: none` wouldn't). It
kills meaningful fades too — that's why it's a backstop.

### JS
```js
const mq = matchMedia("(prefers-reduced-motion: reduce)");
let reduce = mq.matches; mq.addEventListener("change", (e) => (reduce = e.matches));
```
Motion (React): `<MotionConfig reducedMotion="user">` disables transform/layout animation but keeps
opacity/colour; `useReducedMotion()` to branch values. GSAP: `gsap.matchMedia()` with the
reduced-motion query. Lenis: `respectReducedMotion` (default on). View Transitions: disable the
`::view-transition-*` animations or skip `startViewTransition` under reduce.

## Other signals
- `prefers-reduced-transparency` — Chromium only; progressive enhancement (solidify glass surfaces).
- `prefers-contrast: more` — solid backgrounds, defined borders.
- Touch: gate hover motion behind `@media (hover: hover) and (pointer: fine)`.
- Apple visionOS guidance (extrapolated to large-screen web): avoid slow oscillation around 0.2 Hz,
  keep amplitude low, make large moving objects translucent or lower contrast. Weak evidence for 2D web.

## Safety-critical and functional motion
Alerts, errors, and status must never depend on motion alone (colour + icon + text; live region).
Reduced motion must never remove an alert — swap its animation for a static or fade treatment.

## Test
- Playwright: `browser.newContext({ reducedMotion: "reduce" })` or `page.emulateMedia({ reducedMotion: "reduce" })`,
  then run `motion-review`'s capture: x/y/scale deltas ≈ 0, only opacity/colour change.
- DevTools → Rendering → Emulate `prefers-reduced-motion`. Also flip the OS setting once by hand.
