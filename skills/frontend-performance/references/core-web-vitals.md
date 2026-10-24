# Core Web Vitals + responsiveness (as of Oct 2026)

Sources: web.dev Web Vitals, INP, LCP, Optimize LCP, Optimize long tasks; Chrome Lighthouse 13 and
Soft Navigations docs; MDN `scheduler.yield()`. Full ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

## Thresholds (p75 of page loads, mobile and desktop scored separately)
| | Good | Needs improvement | Poor |
| --- | --- | --- | --- |
| LCP | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s |
| INP | ≤ 200 ms | 200–500 ms | > 500 ms |
| CLS | ≤ 0.1 | 0.1–0.25 | > 0.25 |

History to know: INP replaced FID 12 Mar 2024 (FID removed from CrUX/PSI Sep 2024). TTI has had
zero Lighthouse weight since v10. Lighthouse 13 (10 Oct 2025) moved to insight audits:
`lcp-phases-insight`, `lcp-discovery-insight`, `cls-culprits-insight`,
`interaction-to-next-paint-insight`, `dom-size-insight`, `render-blocking-insight`,
`third-parties-insight`, `image-delivery-insight`, `font-display-insight`.
`non-composited-animations` and `unsized-images` remain as diagnostics.

**SPAs:** Chrome 151+ measures soft navigations by default (`interaction-contentful-paint`); CrUX
reporting for them is still TBD. Chromium only — Safari/Firefox RUM will have gaps.

## LCP subparts (web.dev guideline split)
| Subpart | Aim | Typical fix |
| --- | --- | --- |
| TTFB | ~40 % | Caching/CDN/SSR (often not front-end) |
| Resource load delay | < 10 % | Make the LCP resource discoverable in HTML; `fetchpriority="high"`; preload CSS backgrounds |
| Resource load duration | ~40 % | Smaller image (AVIF/WebP, right size), fewer competing requests |
| Element render delay | < 10 % | Less render-blocking CSS/JS; no client-only rendering of the hero |

## INP = input delay + processing duration + presentation delay
- **Input delay** (main thread busy when the user acts) → break up long tasks; defer hydration and
  third-party work; avoid big timers on load.
- **Processing** (your handlers) → do the minimum to paint feedback, then yield:
  ```js
  const yieldToMain = () =>
    globalThis.scheduler?.yield ? scheduler.yield() : new Promise((r) => setTimeout(r, 0));

  button.addEventListener("click", async () => {
    button.dataset.pending = "true";   // visual feedback paints next frame
    await yieldToMain();
    await doExpensiveWork();           // chunk further with yieldToMain() inside loops
  });
  ```
  `scheduler.yield()`: Chrome/Edge 129+, Firefox 142+, **not Safari** (Oct 2026). The `setTimeout`
  fallback goes to the back of the queue and nested timeouts clamp to ~4 ms.
- **Presentation delay** (rendering the next frame) → smaller DOM, no forced sync layout,
  `content-visibility: auto` (+ `contain-intrinsic-size: auto 500px`) on long off-screen sections
  (Baseline Sep 2025), avoid huge style recalcs (e.g. toggling a class on `<body>` that restyles
  thousands of nodes).

### Forced synchronous layout (layout thrashing)
```js
// Bad: read → write → read → write forces layout every iteration
items.forEach((el) => { el.style.height = el.offsetHeight * 2 + "px"; });
// Good: batch reads, then batch writes (or do writes in rAF)
const hs = items.map((el) => el.offsetHeight);
items.forEach((el, i) => { el.style.height = hs[i] * 2 + "px"; });
```

## Long Animation Frames (LoAF) — the diagnostic for both INP and jank
A LoAF is a rendering update delayed > 50 ms. It reports `duration`, `blockingDuration`, and the
`scripts` that ran (`invoker`, `sourceURL`, `sourceFunctionName`, `duration`). Chrome/Edge 123+ only.
```js
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) console.table(e.scripts.map((s) => ({ invoker: s.invoker, src: s.sourceURL, ms: Math.round(s.duration) })));
}).observe({ type: "long-animation-frame", buffered: true });
```
It supersedes the Long Tasks API as the primary tool.

## CLS checklist
- Dimensions or `aspect-ratio` on all media and embeds; reserve ad/iframe slots.
- Skeletons the same size as the content they replace.
- No content inserted above the fold after load; banners overlay or occupy a reserved slot.
- Font swap shift: fix per [loading-assets.md](loading-assets.md) § Fonts (metric-matched fallback,
  `font-display` by role).
- Animate `transform`, not `top`/`height`, so movement isn't counted as shift.
