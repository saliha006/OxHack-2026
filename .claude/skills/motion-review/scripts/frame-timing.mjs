// Real-time smoothness check: does the animation hold frame rate, and does it survive load?
//
// Usage:
//   node frame-timing.mjs <url> [--trigger "<selector>"] [--ms 1500] [--cpu 4] [--video] [--out ./motion-timing]
//
// Measures, while the interaction plays in real time:
//   - rAF frame intervals → p50/p95/max interval, frames over 1.5× the median interval ("janky")
//   - Long Animation Frames (PerformanceObserver 'long-animation-frame', Chromium) → count, worst duration,
//     blocking scripts (sourceURL / invoker) so you know WHAT stalled the frame
//   - Optional CPU throttling via CDP (--cpu 4 ≈ mid-range phone) to expose main-thread-dependent motion
//   - Optional video (--video) for a human/agent to scrub; Playwright video is a review aid, not a
//     frame-accurate timing source.
// Requires: npm i -D playwright && npx playwright install chromium

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const url = process.argv[2];
const argv = process.argv.slice(3);
const opt = (k, d) => { const i = argv.indexOf(`--${k}`); return i < 0 ? d : (argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : true); };
if (!url) { console.error("usage: node frame-timing.mjs <url> [--trigger sel] [--ms 1500] [--cpu 4] [--video] [--out dir]"); process.exit(1); }

const outDir = opt("out", "./motion-timing");
await fs.mkdir(outDir, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  ...(opt("video", false) ? { recordVideo: { dir: outDir, size: { width: 1280, height: 800 } } } : {}),
});
const page = await context.newPage();
const cpu = Number(opt("cpu", 1));
if (cpu > 1) {
  const cdp = await context.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: cpu });
}
await page.goto(url, { waitUntil: "networkidle" });

// Start sampling before the trigger so the first frames are captured.
await page.evaluate((ms) => {
  window.__timing = { intervals: [], loaf: [] };
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        window.__timing.loaf.push({
          start: Math.round(e.startTime), duration: Math.round(e.duration), blockingDuration: Math.round(e.blockingDuration ?? 0),
          scripts: (e.scripts ?? []).map((s) => ({ invoker: s.invoker, source: s.sourceURL, fn: s.sourceFunctionName, ms: Math.round(s.duration) })),
        });
      }
    }).observe({ type: "long-animation-frame", buffered: false });
  } catch { window.__timing.loafUnsupported = true; }
  let last = performance.now();
  const end = last + ms;
  const tick = (now) => { window.__timing.intervals.push(now - last); last = now; if (now < end) requestAnimationFrame(tick); else window.__timing.done = true; };
  requestAnimationFrame(tick);
}, Number(opt("ms", 1500)));

if (opt("trigger", false)) await page.click(opt("trigger"));
await page.waitForFunction(() => window.__timing?.done === true, null, { timeout: 30000 });
const t = await page.evaluate(() => window.__timing);

const iv = t.intervals.slice(1).sort((a, b) => a - b);
const q = (p) => iv[Math.min(iv.length - 1, Math.floor(p * iv.length))];
const median = q(0.5);
const janky = t.intervals.filter((x) => x > median * 1.5).length;
const report = {
  url, cpuThrottle: cpu, frames: iv.length,
  refreshHzEstimate: Math.round(1000 / median),
  intervalMs: { p50: +median.toFixed(2), p95: +q(0.95).toFixed(2), max: +iv[iv.length - 1].toFixed(2) },
  jankyFrames: janky, jankyPct: +((janky / iv.length) * 100).toFixed(1),
  longAnimationFrames: t.loafUnsupported ? "unsupported in this browser" : t.loaf.length,
  worstLoAF: t.loaf.sort((a, b) => b.duration - a.duration)[0] ?? null,
  verdict: janky === 0 ? "smooth" : (janky / iv.length < 0.02 ? "minor hitches — inspect worstLoAF" : "janky — fix before approving"),
};
await fs.writeFile(path.join(outDir, "timing.json"), JSON.stringify({ report, raw: t }, null, 2));
console.log(JSON.stringify(report, null, 2));
await context.close(); // flushes the video file if recording
await browser.close();
