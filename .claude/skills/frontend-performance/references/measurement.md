# Measuring front-end performance

## Lab vs field
- **Lab** (Lighthouse, DevTools, WebPageTest): reproducible, finds *causes*. Doesn't see real devices,
  networks or real interactions (Lighthouse can't measure INP from a page load — use TBT as a proxy
  or a user-flow/timespan run).
- **Field** (CrUX via PageSpeed Insights / CrUX dashboard / Search Console, or your own RUM): decides
  whether users actually got faster. p75, per device class.

## DevTools Performance panel (Chrome 2024–26)
- Opens with **live local LCP / CLS / INP**, compared to CrUX field data for the URL, with suggested
  CPU/network throttling to match your users.
- Record → the **Insights** sidebar (Chrome 131+) explains LCP phases, INP breakdown, CLS culprits,
  render-blocking requests, third parties, DOM size.
- **Frames** track shows dropped and partially presented frames; click a frame to see the
  main-thread work under it.
- Always record with CPU throttling (4× ≈ mid-range phone; 6× for low-end) and record the specific
  interaction, not just load.
- Rendering drawer: Paint flashing, Layout shift regions, Layer borders, Frame rendering stats,
  `prefers-reduced-motion` emulation.
- Animations drawer: replay at 25 % / 10 %, scrub, inspect timing curves.

## Lighthouse 13
Insight audits (`lcp-phases-insight`, `interaction-to-next-paint-insight`, `cls-culprits-insight`,
`render-blocking-insight`, `third-parties-insight`, `image-delivery-insight`, `font-display-insight`,
`dom-size-insight`) + diagnostics like `non-composited-animations`. Node 22.19+ for the CLI. Use
**timespan** mode to measure an interaction, **navigation** for load.

## RUM with web-vitals v5
```js
import { onLCP, onINP, onCLS } from "web-vitals/attribution";
const send = (m) => navigator.sendBeacon("/rum", JSON.stringify({
  name: m.name, value: m.value, rating: m.rating, id: m.id,
  // INP attribution: which element/event, which phase dominated, which script (via LoAF)
  attribution: m.attribution,
}));
onLCP(send); onINP(send); onCLS(send);
```
`reportSoftNavs: true` (Chromium 151+) for SPA route changes. Safari/Firefox don't expose LoAF or
soft navigations — expect gaps there.

## Interaction-level checks (automatable)
- `PerformanceObserver` for `long-animation-frame` (scripts that blocked a frame) and `event`
  entries (`durationThreshold: 16`) to time specific interactions.
- Playwright + CDP `Emulation.setCPUThrottlingRate` to reproduce mid-range devices in CI; see
  `motion-review/scripts/frame-timing.mjs` for a ready-made rAF + LoAF sampler.

## Reporting format
| Metric | Before | After | Conditions | Change |
| --- | --- | --- | --- | --- |
| INP (field p75, mobile) | 340 ms | 170 ms | CrUX 28-day | Yield after optimistic update in `Cart.tsx` |
