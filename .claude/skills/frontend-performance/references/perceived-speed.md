# Perceived speed

Making the interface *feel* fast. Sources: NN/g "Response Times: The 3 Important Limits" and
"Skeleton Screens 101"; web.dev bfcache; MDN Speculation Rules; Viget skeleton study (2017);
Harrison et al. 2010 "Faster Progress Bars" (CHI). Ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

## Response-time limits (NN/g, Miller 1968 / Card 1991 lineage)
| Delay | Feels | Do |
| --- | --- | --- |
| ≤ 0.1 s | Instant, direct | Nothing special — just paint the result/feedback |
| ≤ 1 s | Flow kept, delay noticed | Immediate press feedback; no spinner needed |
| 1–10 s | Attention wavers | From ~2 s: skeleton (whole page) or spinner (one module) |
| > 10 s | Attention lost | Determinate progress, time estimate, cancel; let them do something else |

For direct manipulation (drag, ink, scroll-linked), the bar is far lower: HCI studies find users
notice touch latency well below 100 ms (tens of ms for dragging). Keep drag paths on the compositor
and handlers tiny.

## Techniques
- **Instant acknowledgement** — pressed state on pointer-down; pending state on the button itself
  within one frame, *then* do the work (see INP yielding in [core-web-vitals.md](core-web-vitals.md)).
- **Optimistic UI** — apply the result immediately, reconcile on response, roll back visibly on
  failure. Only for low-stakes, reversible actions; never payments, destructive or safety-critical actions.
- **Skeletons** — sized exactly like the real content (no CLS), for 2–10 s page-level loads. Evidence
  that they *feel* faster than spinners is mixed (Viget 2017 found the opposite); their real wins are
  layout stability and showing structure. Don't show anything for < 1 s waits (flash of skeleton is worse).
- **Progress indicators** — determinate beats indeterminate when you can estimate. For 5–15 s waits,
  progress that accelerates toward the end feels faster and pauses near the end feel slower
  (Harrison et al. UIST 2007); backwards-moving ribbing cut perceived duration ~11 % (Harrison et al.
  CHI 2010). Applies to progress bars only — not to 200 ms UI animation easing.
- **Spinner speed** — a spinner is a "still alive" signal, not a speed claim; keep it smooth (CSS,
  compositor) so it doesn't freeze under load.
- **Prefetch / prerender** — Speculation Rules (Chromium; Safari has it off by default):
  ```html
  <script type="speculationrules">
  { "prefetch": [{ "where": { "href_matches": "/*" }, "eagerness": "moderate" }],
    "prerender": [{ "where": { "selector_matches": "[data-prerender]" }, "eagerness": "moderate" }] }
  </script>
  ```
  Prefetch broadly, prerender sparingly; guard side-effecting URLs (`Sec-Purpose` header,
  `document.prerendering`). Elsewhere: prefetch on hover/viewport via the framework router.
- **bfcache** — instant back/forward. Never use `unload` (use `pagehide`), add `beforeunload` only
  while there are unsaved changes, avoid `Cache-Control: no-store` except on sensitive pages, test in
  DevTools → Application → Back/forward cache.
- **View transitions** — bridge navigations so content appears to move rather than reload. They mask,
  not remove, latency: keep the update fast.
- **Progressive rendering** — stream HTML, render above-the-fold first, defer the rest.
- **Animation speed affects perceived speed** — short ease-out motion (fast start) reads as responsive;
  long or ease-in motion on frequent UI reads as lag. See the `motion` skill feel presets.

## Caution
- Too-fast results on heavy operations can reduce trust in some contexts ("labour illusion"); if
  you add a beat, make it honest progress, never a fake delay on routine actions.
- Never hide real slowness behind decoration — fix the bottleneck first.
