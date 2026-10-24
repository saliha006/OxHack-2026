# Signature effects of best-in-class sites — how they're built

How the effects on award-winning sites work, what they cost, and when to use them. Research Oct 2026
(gsap.com, motion.dev, Lenis README, developer.chrome.com, WebKit blog, MDN, NN/g, W3C, Ryan
Mulligan, HN threads). Ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

**Spend boldness once.** One signature moment per page; everything else quiet. Every effect here
needs a reduced-motion path ([accessibility.md](accessibility.md)) and must be verified with
`motion-review` (frames + frame timing under 4× CPU throttle).

## Defaults
| Default on (progressive enhancement) | Situational | Avoid by default |
| --- | --- | --- |
| View transitions · layout/FLIP · CSS scroll-progress + reveals · SVG line drawing · static grain · number tickers · mask/clip reveals | Scrub + pin · subtle parallax · Lenis (brand sites) · split-text on hero headings · marquee with pause button · sticky stacking cards · one WebGL scene · Rive/Lottie | Horizontal scroll-jacks · custom cursors that hide the system cursor · tilt cards · preloaders · gooey blobs · anything on frequent/keyboard actions |

## Recipes
**Scroll-driven / scrubbed** — progress bound to scroll; reverses on scroll-up.
CSS first: `animation-timeline: scroll()` (page progress) or `view()` (element's trip through the
viewport) + `animation-range`, inside `@supports (animation-timeline: scroll())`. Runs off the main
thread for compositor properties. Support: Chrome 115+, Safari 26+, Firefox flagged → static fallback.
Need pinning or a multi-step timeline? GSAP ScrollTrigger: `scrub: true` (locked) or `scrub: 1`
(1 s catch-up, smoother feel), `pin: true`, `anticipatePin: 1`; animate children of the pinned
element, not the pinned element itself. Main-thread (rAF).

**Parallax** — layers at different speeds. `view()` timeline on `translate` with small distances
(≤ 10–15 % of the layer height). Doesn't improve usability (Frederick 2015) and is a named vestibular
trigger → subtle, decorative layers only, off under reduced motion.

**Smooth scroll (Lenis)** — eases wheel input toward the target for a "buttery" feel. Wraps native
scroll (sticky, anchors, find-in-page still work). Keep `syncTouch: false` (native touch momentum;
true is unstable on older iOS). Costs: main-thread rAF loop, conflicts with CSS scroll-snap, nested
scrollers need `data-lenis-prevent`, iframes don't smooth. `respectReducedMotion` defaults on.
Brand/portfolio only — never e-commerce, docs, or task UIs (NN/g: altered scroll speed hurts
task-oriented users; HN consensus strongly against scroll-jacking).

**View transitions / shared-element morph** —
```js
if (!document.startViewTransition || reduce) update(); else document.startViewTransition(update);
```
```css
.thumb[data-active], .hero { view-transition-name: product-hero; }   /* unique per page state */
::view-transition-group(product-hero) { animation-duration: 280ms; animation-timing-function: var(--ease-out); }
@view-transition { navigation: auto; }                                /* MPA, both pages */
@media (prefers-reduced-motion: reduce) { ::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) { animation: none; } }
```
Same-document is Baseline (Oct 2025); cross-document Chrome 126+/Safari 18.2+, Firefox partial.

**Layout / FLIP** — measure First, apply Last, Invert with a transform, Play to identity (Paul
Lewis). React: Motion `layout` / `layoutId` + `AnimatePresence`; put `layout` on children to stop
text stretching; `layout="position"` for images.

**Text split reveal** — split into lines/words, wrap each in an `overflow: clip` mask, translate up
100 % with a short stagger ([feel-presets.md](feel-presets.md)). GSAP SplitText (free since Apr 2025): `mask: "lines"`, `autoSplit`
+ `onSplit()` to re-split on resize/font load, `revert()` after. Default `aria: "auto"` labels the
parent — breaks nested links; then use `aria: "none"` + a visually-hidden copy. Hero headings only;
split by line/word, not character, for body text.

**Marquee / ticker** — duplicate the track (`aria-hidden="true"` on the copy), animate
`translateX(calc(-100% - var(--gap)))` linear, infinite. Needs a **real pause button** (WCAG 2.2.2 —
hover-pause doesn't count) and stops under reduced motion.

**Sticky stacking cards** — each card `position: sticky; top: <offset>`; scale/darken earlier cards
with a `view()` timeline (`scale: 1 → 0.92`). CSS-native, cheap.

**Mask / clip-path reveal** — `clip-path: inset(0 0 100% 0) → inset(0)` on scroll entry or route
change; `circle()` for iris. Clip-path animation usually repaints → verify on a throttled CPU; keep
the area modest. Soft edges: `mask-image` gradient.

**Magnetic button** — on `pointermove` within a radius, translate toward the pointer by ~0.2–0.4 × the
offset (spring/lerp), spring back on leave. Fine-pointer only; never hide the native cursor.

**Cursor spotlight** — set `--x/--y` on the *card itself* (not a shared parent) from `pointermove`,
feed a `radial-gradient`. Subtle; fine-pointer only.

**3D tilt** — `perspective` + `rotateX/Y` ≤ 5–8° from pointer position, spring back. Off under
reduced motion and on touch.

**SVG line drawing** — `pathLength="1"`, `stroke-dasharray: 1`, animate `stroke-dashoffset: 1 → 0`.
Cheap; reduced motion shows the finished drawing.

**Number ticker** — count with rAF/Motion when in view; `font-variant-numeric: tabular-nums`;
expose the final value to screen readers (`aria-label` / visually-hidden final number); reduced motion
shows the final number.

**Noise / grain** — static tiled PNG or SVG `feTurbulence` (keep `numOctaves` ≤ 3) at low opacity,
`pointer-events: none`. Never animate it (repaints every frame).

**WebGL / shader backgrounds, image distortion** — Three.js / R3F / OGL, or no-code Unicorn Studio.
Heavy: lazy-init near viewport, pause off-screen and when `document.hidden`, cap DPR at 2, one scene
per page (browsers cap WebGL contexts ~16, ~8 on Android), static poster for reduced motion and
weak GPUs.

**Scroll progress bar** — `scroll(root)` timeline on `transform: scaleX()`. Long reads only.

**Horizontal scroll section** — pinned section, vertical scroll drives `x`. Disorienting, poor on
mobile (NN/g) → avoid unless the content is genuinely a horizontal sequence; provide normal scroll on
touch and reduced motion.

**Preloader / intro** — delays content and LCP. Only when assets truly need preloading; skippable,
< ~1 s, never on repeat visits.

**Lottie / Rive** — Lottie for simple designer loops; Rive for interactive state machines (vendor
size/perf claims unverified — benchmark your own files). Pause off-screen; static frame for reduced motion.

## Libraries (Oct 2026)
| Library | Use for | Licence |
| --- | --- | --- |
| CSS (transitions, `@starting-style`, scroll-driven, view transitions) | Anything it can express — zero JS | — |
| Motion (`motion`, formerly Framer Motion) | React/vanilla UI motion, springs, gestures, layout | MIT (Motion+ paid add-on) |
| GSAP (+ ScrollTrigger, SplitText, MorphSVG…) | Complex timelines, pinning, text splitting | Free incl. all plugins since 29 Apr 2025, **not open source**; licence bars use in Webflow-competing no-code builders; revocable by Webflow |
| Lenis | Smooth wheel scroll | MIT |
| anime.js v4 | Lightweight timelines, scroll observer, text split | MIT |
| Three.js / R3F / OGL | WebGL scenes | MIT |

Community consensus (HN 2023–25): Motion by default for React UI; GSAP for scroll-story sites;
scroll-jacking is near-universally disliked.
