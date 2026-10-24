---
name: frontend-performance
description: >-
  Front-end-only measured and perceived performance: Core Web Vitals (LCP, INP, CLS) at current
  thresholds, button/input responsiveness (instant feedback, optimistic UI, yielding long tasks),
  smooth scrolling and animation (compositor-only properties, will-change, layout thrashing, rAF,
  long animation frames, content-visibility, scroll-driven animations off the main thread), images,
  fonts, JS bundle cost, perceived-speed techniques (skeletons, prefetch, speculation rules, bfcache,
  view transitions) and how to measure (DevTools Performance panel, Lighthouse 13 insights,
  web-vitals v5, LoAF). Use when a page or interaction is slow, janky, laggy, shifts layout, scores
  badly in Lighthouse/PageSpeed/CrUX, before shipping a heavy animation or marketing page, or when
  asked to "make it faster / feel snappier / fix INP / fix CLS / fix jank". Not for backend,
  database, or CDN/server tuning.
---

# Front-end performance

Performance is a feature and a feel. Find the **actual** bottleneck for this interface, fix the
biggest one, then measure again. Don't optimise what isn't slow.

Related skills: `motion` (designing motion), `motion-review` (frame-level verification of an
animation), `ui-audit` (accessibility/usability review), `design-direction` (visual system),
`reverse-engineer-ui` (costing a borrowed effect). Shared library: `../references/`.

## Targets (field data, 75th percentile, mobile and desktop separately)

| Metric | Good | Poor | What it is |
| --- | --- | --- | --- |
| **LCP** | ≤ 2.5 s | > 4.0 s | When the largest content element rendered |
| **INP** | ≤ 200 ms | > 500 ms | Worst-ish interaction latency: input delay + processing + presentation |
| **CLS** | ≤ 0.1 | > 0.25 | Unexpected layout movement |

INP replaced FID on 12 Mar 2024 — **never cite FID or TTI**. Lighthouse 13 (Oct 2025) replaced most
classic audits with `*-insight` audits. Details: [core-web-vitals.md](references/core-web-vitals.md).

**Felt-speed targets** (beyond CWV):
- Visible response to any press/keypress **≤ 100 ms** (NN/g "instant"); pressed state on pointer-down.
- Animation frames on budget: **~16.7 ms at 60 Hz, ~8.3 ms at 120 Hz**, no long animation frames
  (> 50 ms) during motion or scroll.
- Waits: < 1 s show nothing extra; 2–10 s skeleton (page) or spinner (module); > 10 s determinate
  progress + cancel.

## Workflow
1. **Measure first.** Field data if available (CrUX / PageSpeed / RUM via `web-vitals`), then lab:
   DevTools Performance panel with CPU throttling (4×) and a mid-tier network. Record the specific
   slow interaction, not just page load. → [measurement.md](references/measurement.md)
2. **Name the bottleneck** with evidence: the LCP subpart that dominates, the INP phase that
   dominates (input delay / processing / presentation), the CLS culprit, or the long animation frame
   and its script attribution.
3. **Fix the biggest one** using the playbook below. One change at a time.
4. **Re-measure** under the same conditions; report before/after numbers. If motion was touched, run
   `motion-review`'s frame-timing check.

## Playbook (by symptom)

**Slow LCP** → [loading-assets.md](references/loading-assets.md)
- LCP image discoverable in HTML, `fetchpriority="high"`, never `loading="lazy"`; AVIF/WebP, sized via
  `srcset`/`sizes`. Cut render-blocking CSS/JS; check TTFB before blaming the front end.

**Laggy clicks / typing (INP)** → [core-web-vitals.md](references/core-web-vitals.md)
- Paint feedback first, then yield, then do the heavy work.
- Break tasks > 50 ms: `await scheduler.yield()` (feature-detect; Safari lacks it → `setTimeout` fallback).
- No forced synchronous layout (read-after-write); smaller DOM; `content-visibility: auto` +
  `contain-intrinsic-size` for long off-screen sections; virtualise very long lists.
- Optimistic UI for low-stakes, reversible actions (like, toggle, reorder) — never payments or
  destructive actions.

**Jank in animation or scroll** → [rendering-animation.md](references/rendering-animation.md)
- Animate `transform` and `opacity` (and `filter` in Chromium) — they can run on the compositor.
  Everything else (`width`, `height`, `top`, `left`, `margin`, layout-affecting `padding`) re-runs
  layout/paint on the main thread.
- CSS/WAAPI/scroll-driven animations of compositor properties keep running when the main thread is
  busy; rAF/JS tweens do not. Animating a CSS custom property is never accelerated.
- `will-change` is a last resort for a measured problem, applied just before motion and removed after.
- Scroll effects: `IntersectionObserver` or `animation-timeline: scroll()/view()` (with `@supports`),
  never per-frame `scroll` listeners doing layout reads.

**Layout shift (CLS)**
- `width`/`height` or `aspect-ratio` on every image/video/embed; reserve space for async content.
- Never inject above existing content after load (banners, cookie bars → overlay or reserved slot).
- Fonts: metric-matched fallback + the right `font-display` per role →
  [loading-assets.md](references/loading-assets.md) (the one place font loading lives).
- Animations that move layout count toward CLS; transform-based ones don't.

**Heavy JS** → [loading-assets.md](references/loading-assets.md)
- Budget against Alex Russell's 2026 baseline (≈ 300 KiB JS for a content page, ≈ 620 KiB for a
  JS-heavy app, compressed, critical path, for a 3 s target on a mid-tier phone). Split by route,
  lazy-load below-the-fold widgets, audit third parties first.

**Feels slow even when metrics are fine** → [perceived-speed.md](references/perceived-speed.md)
- Instant press feedback, prefetch/prerender likely next pages (speculation rules, Chromium),
  keep pages bfcache-eligible (no `unload`), view transitions to bridge navigation, skeletons sized
  to the real content for multi-second page loads.

## Rules
- Measure on a mid-range Android with throttling, not only a fast laptop.
- Never sacrifice accessibility (focus, reduced motion, contrast) for a score.
- Never lazy-load above-the-fold content. Never blanket `will-change`/`translateZ(0)`.
- Lab (Lighthouse) finds causes; field data (CrUX/RUM) decides whether you've won.
- Report changes as: *metric, before → after, conditions, what changed.*

## Outdated claims to reject on sight
FID / `onFID` / TTI / First Meaningful Paint · pre-v13 Lighthouse audit names (`uses-rel-preload`,
`offscreen-images`, `preload-fonts`) · "Motion's `x`/`y` aren't hardware-accelerated" (they are) ·
"CSS animations are always off the main thread" (only compositor properties) · "skeletons are proven
faster" (evidence is mixed) · "view transitions / scroll-driven animations are Chrome-only".
Evidence and sources: `Claude instructions/research-ledger.md` §4 motion + performance.
