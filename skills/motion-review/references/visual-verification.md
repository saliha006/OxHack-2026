# Visual verification of motion — tools, snippets, fallbacks

Goal: the agent *sees* the animation and *measures* it, then iterates. Verified against Playwright
docs (1.45+ clock; tested with 1.64), MDN Web Animations, Chrome DevTools/LoAF docs, devtools-protocol
definitions. Ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

## Pick the capture method
| Motion is driven by… | Best capture | Why |
| --- | --- | --- |
| CSS transitions / `@keyframes` / WAAPI / view transitions | **WAAPI seeking**: `document.getAnimations()` → `pause()` → set `currentTime` | Deterministic, frame-exact, any number of steps |
| JS: rAF loops, Motion JS springs, GSAP, react-spring | **Playwright fake clock**: `page.clock.install()` + `pauseAt()` + `runFor(ms)` | Clock fakes `Date`, timers, `requestAnimationFrame`, `performance.now` — not CSS/compositor animations |
| Scroll-driven | Scroll in fixed steps (`page.mouse.wheel` or `window.scrollTo`) + screenshot per step | Progress is a function of scroll position, not time |
| Anything, for a human-style look | `recordVideo` (≈25 fps) or Claude-in-Chrome GIF | Review aid only — too coarse to measure 60/120 Hz jank |
| Smoothness / jank | rAF interval sampler + `long-animation-frame` observer, CPU throttled via CDP; DevTools trace | Real-time behaviour under load |

## Gotchas (confirmed)
- A CSS transition only exists **after** its triggering style change: trigger first, wait one rAF,
  then `getAnimations()`.
- Finished animations without `fill` drop out of `getAnimations()`. Infinite ones have
  `endTime = Infinity` — exclude them when computing the capture window.
- `page.screenshot({ animations: "disabled" })` fast-forwards finite animations to the end — never use
  it while stepping. Default (`"allow"`) is correct. `toHaveScreenshot` defaults to `"disabled"`.
- `page.clock.install()` keeps time flowing; call `pauseAt()` before triggering, then `runFor()` per step.
- Don't install the fake clock when measuring real frame timing (rAF becomes fake).
- Shadow DOM: also collect `host.getAnimations({ subtree: true })` if components use shadow roots.
- Headless frame pacing ≠ a real display's vsync; rAF intervals measure main-thread frames, while
  compositor-only animations may stay smooth even when rAF stalls (and vice versa). Use both the
  sampler and the frames.
- `recordVideo` saves only on `context.close()`; Chromium encodes at ~1 Mbit/s.

## Scripts (in `../scripts/`, tested Oct 2026)
```bash
npm i -D playwright && npx playwright install chromium
# deterministic frames + curve analysis (CSS/WAAPI)
node capture-frames.mjs http://localhost:3000 --trigger "[data-open]" --target ".popover" --steps 12
# JS-driven motion
node capture-frames.mjs http://localhost:3000 --mode clock --duration 600 --trigger "#go" --target ".sheet"
# reduced-motion pass
node capture-frames.mjs http://localhost:3000 --trigger "[data-open]" --target ".popover" --reduced
# real-time smoothness at ~mid-range phone CPU, with video for scrubbing
node frame-timing.mjs http://localhost:3000 --trigger "[data-open]" --ms 1500 --cpu 4 --video
```
`samples.json → analysis`: `axis` (dominant changing property), `overshoot`, `maxProgress`,
`reaches90pctAtMs`, `totalMs`. Per step: `t`, `progress`, bounding box, opacity, transform, filter, clip-path.

## Reading the curve
Normalised progress p(t) on the dominant axis, vs normalised time:
| Intended | Expect in samples |
| --- | --- |
| Strong ease-out (`--ease-out`) | p ≥ ~0.6 by t = 0.3; ~0.9 by t = 0.5 |
| Ease-in-out | p ≈ 0.1–0.2 at t = 0.25, ≈ 0.5 at 0.5, symmetric |
| Linear | p ≈ t |
| Spring bounce 0 | monotonic, no p > 1 |
| Spring bounce 0.2–0.35 | p peaks ~1.03–1.15 then settles |
| Ease-in on an entrance (bad) | p < 0.2 at t = 0.3 — flag it |

For a rigorous fit, evaluate the intended `cubic-bezier` at each t and report RMSE (≤ 0.05 = match).
Crossfades: if outgoing + incoming opacity stay > ~1.3 for several frames, or both > 0.5, there is
visible double exposure → blur bridge or shorter overlap.

## Inline snippets (when you can't use the scripts)
**Step a CSS/WAAPI animation and record geometry:**
```js
await page.click(TRIGGER);
await page.evaluate(() => new Promise((r) => requestAnimationFrame(r)));
const end = await page.evaluate(() => {
  const a = document.getAnimations(); a.forEach((x) => x.pause()); window.__a = a;
  return Math.max(0, ...a.map((x) => x.effect.getComputedTiming().endTime).filter(Number.isFinite));
});
for (let i = 0; i <= 12; i++) {
  await page.evaluate((t) => window.__a.forEach((x) => (x.currentTime = t)), (end * i) / 12);
  await page.screenshot({ path: `f${i}.png` });
}
```
**Slow everything down via CDP (for video/GIF review) and throttle CPU:**
```js
const cdp = await page.context().newCDPSession(page);
await cdp.send("Animation.enable");
await cdp.send("Animation.setPlaybackRate", { playbackRate: 0.1 });   // experimental domain
await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
```
**Frame-interval sampler (no fake clock):**
```js
const stats = await page.evaluate((ms) => new Promise((res) => {
  const d = []; let last; const t0 = performance.now();
  const tick = (now) => { if (last) d.push(now - last); last = now;
    now - t0 < ms ? requestAnimationFrame(tick) : res({ n: d.length, max: Math.max(...d), over25: d.filter((x) => x > 25).length }); };
  requestAnimationFrame(tick);
}), 1500);
```
**Trace for DevTools (Chromium):** `await browser.startTracing(page, { path: "trace.json", screenshots: true }); …; await browser.stopTracing();`
then load in DevTools → Performance and read the Frames track (green on time, yellow partial, red dropped).

## Fallbacks when tools are missing
1. **Playwright available** → scripts above (preferred; deterministic).
2. **Claude-in-Chrome** → screenshots at intervals + GIF recorder for a look (dedupes identical frames;
   not frame-accurate). Use `javascript` execution to run the same `getAnimations()` seeking in the page.
3. **browser-use / other browser MCP** may be unavailable or disconnected — don't depend on it; say so.
4. **Puppeteer** → same WAAPI/CDP code works (`page.evaluate`, `page.createCDPSession()`).
   **Agentation** (if the user runs it in their app): they click the element that "feels off" and you get
   its selector, source path and computed styles; it can also freeze an animation on a frame.
5. **Nothing** → do the code review, then hand the user exact manual steps: DevTools Animations drawer
   (replay slowly, scrub), Performance panel with 4× CPU throttle (Frames track), Rendering →
   emulate `prefers-reduced-motion`, plus a real phone for gestures. Mark the verdict "unverified visually".

## Iteration discipline
Change one thing, re-capture, compare against the previous `samples.json` and frames. Stop when the
curve matches the feel contract, timing passes under throttle, reduced motion passes, and the
frames look right. Report the evidence, not the intention.
