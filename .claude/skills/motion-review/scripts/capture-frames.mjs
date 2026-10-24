// Deterministic animation frame capture for motion review.
//
// Usage:
//   node capture-frames.mjs <url> [--trigger "<css selector to click>"] [--target "<css selector to measure>"]
//        [--steps 12] [--out ./motion-frames] [--reduced] [--width 1280 --height 800]
//
// What it does:
//   1. Opens the page (Chromium) and, if --trigger is given, pauses the document timeline right
//      after clicking so the animation it starts can be stepped deterministically.
//   2. Collects every running animation (CSS animations, CSS transitions, WAAPI — all appear in
//      document.getAnimations()), pauses them, and seeks them to N evenly spaced times.
//   3. At each step saves a screenshot and records the target's bounding box, opacity and
//      computed transform, so you can compare the sampled curve against the intended easing.
//   4. Writes frames/*.png + samples.json (+ a contact sheet HTML for quick visual review).
//
// Limits: JS-driven animations (rAF loops, Motion's JS springs, GSAP) are NOT in getAnimations()
// unless they use WAAPI. For those, use --mode=clock (Playwright's fake clock drives rAF/timers)
// or record a video and run frame-timing.mjs. Requires: npm i -D playwright && npx playwright install chromium

import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const args = Object.fromEntries(
  process.argv.slice(3).reduce((acc, a, i, arr) => {
    if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true]);
    return acc;
  }, [])
);
const url = process.argv[2];
if (!url) { console.error("usage: node capture-frames.mjs <url> [--trigger sel] [--target sel] [--steps N] [--out dir] [--mode waapi|clock] [--reduced]"); process.exit(1); }

const steps = Number(args.steps ?? 12);
const outDir = args.out ?? "./motion-frames";
const mode = args.mode ?? "waapi";
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: Number(args.width ?? 1280), height: Number(args.height ?? 800) },
  reducedMotion: args.reduced ? "reduce" : "no-preference",
  deviceScaleFactor: 1,
});
const page = await context.newPage();
const T0 = new Date("2030-01-01T00:00:00Z");
if (mode === "clock") await page.clock.install({ time: T0 }); // fake Date, timers, rAF, performance.now
await page.goto(url, { waitUntil: "networkidle" });
// install() lets time keep flowing; freeze it so every step advances exactly the requested ms.
if (mode === "clock") await page.clock.pauseAt(new Date(T0.getTime() + 60_000));

const measure = async () =>
  args.target
    ? page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return { x: r.x, y: r.y, w: r.width, h: r.height, opacity: Number(cs.opacity), transform: cs.transform, filter: cs.filter, clipPath: cs.clipPath };
      }, args.target)
    : null;

const samples = [];

if (mode === "clock") {
  // JS-driven motion: advance fake time in fixed increments.
  if (args.trigger) await page.click(args.trigger);
  const totalMs = Number(args.duration ?? 1000);
  for (let i = 0; i <= steps; i++) {
    const t = Math.round((totalMs * i) / steps);
    if (i > 0) await page.clock.runFor(Math.round(totalMs / steps));
    const file = path.join(outDir, `frame-${String(i).padStart(3, "0")}.png`);
    await page.screenshot({ path: file });
    samples.push({ step: i, t, file, metrics: await measure() });
  }
} else {
  // CSS / WAAPI motion: freeze, then seek every animation.
  if (args.trigger) {
    await page.click(args.trigger);
    // Give the style system one frame to create the transition/animation objects.
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r())));
  }
  const info = await page.evaluate(() => {
    const anims = document.getAnimations();
    anims.forEach((a) => a.pause());
    window.__anims = anims;
    return anims.map((a) => {
      const t = a.effect?.getComputedTiming?.() ?? {};
      return {
        type: a.constructor.name, // CSSTransition | CSSAnimation | Animation
        name: a.animationName ?? a.transitionProperty ?? a.id ?? "",
        target: a.effect?.target?.tagName?.toLowerCase() + (a.effect?.target?.className ? "." + String(a.effect.target.className).split(" ").join(".") : ""),
        delay: t.delay, duration: t.duration, endTime: t.endTime, easing: a.effect?.getTiming?.().easing,
      };
    });
  });
  if (!info.length) console.warn("No WAAPI/CSS animations found. JS-driven? Re-run with --mode clock --duration <ms>.");
  const end = Math.max(0, ...info.map((a) => (Number.isFinite(a.endTime) ? a.endTime : 0)));
  for (let i = 0; i <= steps; i++) {
    const t = (end * i) / steps;
    await page.evaluate((t) => window.__anims.forEach((a) => { a.currentTime = t; }), t);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r())));
    const file = path.join(outDir, `frame-${String(i).padStart(3, "0")}.png`);
    await page.screenshot({ path: file, animations: "allow" });
    samples.push({ step: i, t: Math.round(t), file, metrics: await measure() });
  }
  samples.unshift({ animations: info });
}

// Normalised progress of the target (0 → 1) on its dominant axis, to compare against the intended
// curve: an ease-out should be ≳ 0.6 by 30 % of the time; a linear tween ≈ t; values > 1 = overshoot.
const frames = samples.filter((s) => s.file);
const pts = frames.map((s) => s.metrics).filter(Boolean);
if (pts.length > 1) {
  const a = pts[0], b = pts[pts.length - 1];
  const axes = ["x", "y", "w", "h", "opacity"].map((k) => [k, b[k] - a[k]]).sort((p, q) => Math.abs(q[1]) - Math.abs(p[1]));
  const [axis, delta] = axes[0];
  if (Math.abs(delta) > 0.001) {
    frames.forEach((s) => s.metrics && (s.progress = +((s.metrics[axis] - a[axis]) / delta).toFixed(3)));
    const prog = frames.map((s) => s.progress ?? 0);
    const idx90 = prog.findIndex((p) => p >= 0.9);
    samples.push({ analysis: {
      axis, delta: +delta.toFixed(2),
      overshoot: +(Math.max(...prog) - 1).toFixed(3) > 0.005,
      maxProgress: Math.max(...prog),
      reaches90pctAtStep: idx90, reaches90pctAtMs: idx90 >= 0 ? frames[idx90].t : null,
      totalMs: frames[frames.length - 1].t,
    } });
  }
}
await fs.writeFile(path.join(outDir, "samples.json"), JSON.stringify(samples, null, 2));
await fs.writeFile(
  path.join(outDir, "contact-sheet.html"),
  `<!doctype html><meta charset="utf-8"><title>frames</title><style>body{font:12px system-ui;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:8px}img{width:100%;border:1px solid #ccc}</style>` +
    frames.map((s) => `<figure><img src="${path.basename(s.file)}"><figcaption>step ${s.step} · t=${s.t}ms ${s.metrics ? `· y=${s.metrics.y.toFixed(1)} op=${s.metrics.opacity}` : ""}</figcaption></figure>`).join("")
);
console.log(`Saved ${frames.length} frames + samples.json + contact-sheet.html to ${outDir}`);
await browser.close();
