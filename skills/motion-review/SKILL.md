---
name: motion-review
description: >-
  Review and verify animation/motion against a high craft bar, then prove it visually: capture
  frames of the animation (Playwright WAAPI seeking or fake clock, screenshots, video, Claude-in-Chrome
  GIFs, DevTools traces), compare the sampled motion curve against the intended feel, measure dropped
  frames and long animation frames under CPU throttling, check the reduced-motion path, and iterate
  before declaring done. Default to flagging; approval is earned. Invoke explicitly after ANY motion
  change (new or edited transition, animation, spring, gesture, scroll effect, view transition), when
  reviewing a diff or PR that touches animation, or when the user says "review the animation",
  "does this feel right", "it feels janky/off/sluggish", "check the motion".
---

# Motion review

Two halves, both required: **(A) code review against the standards** and **(B) the visual
verification loop.** Motion that "works" but feels sluggish, lands from the wrong origin, fires too
often, or drops frames is a regression. Default to flagging; approval is earned.

Standards derive from Emil Kowalski's review-animations skill and Apple WWDC fluid-interface
guidance. Values are canonical in `../motion/references/feel-presets.md` and
`../motion/references/craft-rules.md` — cite them, don't approximate. Evidence ledger:
`Claude instructions/research-ledger.md` §4 motion + performance.

Related skills: `motion` (builds it; owns the values) · `frontend-performance` (root-causing jank,
INP) · `ui-audit` (whole-UI review) · `design-direction` · `reverse-engineer-ui`. Shared library:
`../references/`.

**First, get the intended feel.** Find the feel contract (in the change, the PR, the repo tokens, or
ask the user: snappy / smooth / springy / weighty / slow / motion-blurred…). You can't judge
"feels right" without a target.

## A. Standards (each violation is a finding)
1. **Justified** — a named purpose; no motion on keyboard-initiated or 100+/day actions.
2. **Frequency-appropriate** — tens/day = minimal; occasional = standard; rare = delight allowed.
3. **Easing** — ease-out for entrances/responses, ease-in-out for on-screen moves, short ease-in only
   for permanent exits, linear for constant motion; strong curve tokens, not weak built-ins.
4. **Duration** — inside the feel contract's band and the size table in `../motion/references/feel-presets.md`; exits
   shorter than enters.
5. **Origin & physicality** — trigger-anchored `transform-origin` (modals exempt); no `scale(0)`;
   same path in and out; press feedback on pointer-down.
6. **Interruptible** — transitions/springs for re-triggerable or grabbable UI; gestures carry velocity.
7. **Compositor-friendly** — `transform`/`opacity`; no `transition: all`, no layout properties, no
   parent CSS-variable driving child motion.
8. **Accessible** — reduced-motion path that replaces travel with fades and keeps feedback;
   persistent pause for auto-motion > 5 s; hover gated to fine pointers; no > 3 flashes/s.
9. **Asymmetric where deliberate** — slow decide-phase (hold), fast system response.
10. **Cohesive** — matches the product's feel; one signature moment, not many.

**Escalate on sight:** `transition: all` · `scale(0)` · ease-in on an entrance/feedback · motion on a
shortcut/command palette · functional UI past the feel-presets cap, unexplained · `transform-origin: center` on a popover ·
`@keyframes` on toasts/toggles · animated `width/height/top/left/margin` · per-frame React state or
parent CSS variable · no reduced-motion path on movement · ungated `:hover` motion · marquee/carousel
with hover-only pause · scroll-jacking on a task UI · everything-at-once group entrance.

**Remedy order (prefer earlier):** delete → reduce → fix easing → fix origin/physicality → make
interruptible → move to compositor → asymmetric timing → polish (blur bridge, stagger,
`@starting-style`) → accessibility & cohesion.

## B. Visual verification loop (autonomous)
Full how-to, tool fallbacks and snippets: [visual-verification.md](references/visual-verification.md).
Scripts: `scripts/capture-frames.mjs`, `scripts/frame-timing.mjs` (Node + Playwright; tested).

1. **Run the UI** (dev server or static file). Identify a trigger selector and a target selector.
2. **Capture deterministic frames:**
   `node scripts/capture-frames.mjs <url> --trigger "<sel>" --target "<sel>" --steps 12`
   (CSS/WAAPI). JS/rAF/spring motion: add `--mode clock --duration <ms>`. Output: PNG frames,
   `contact-sheet.html`, `samples.json` with per-step geometry/opacity and an analysis block
   (dominant axis, overshoot, time to 90 %).
3. **Inspect the frames** (open the PNGs/contact sheet with the image reader) and check:
   origin correct · nothing appears from nothing · properties finish together · no double exposure in
   crossfades · no jump at start/end · final frame matches the static design.
4. **Check the curve against the feel:** ease-out → ≥ ~60 % progress by 30 % of the time; ease-in-out →
   symmetric S; linear → progress ≈ time; spring with bounce 0 → no overshoot; bounce > 0 →
   overshoot present and settling. Duration within the contract band.
5. **Measure smoothness in real time, under load:**
   `node scripts/frame-timing.mjs <url> --trigger "<sel>" --cpu 4`
   Pass: janky frames ≈ 0 %, p95 interval ≤ 1.5× refresh interval, no long animation frame
   during the motion. If it fails, the LoAF script attribution says what blocked the frame.
6. **Reduced motion:** re-run step 2 with `--reduced`: no x/y/scale travel, only opacity/colour;
   feedback still visible; alerts still present.
7. **Interrupt test** (interactive UI): trigger twice rapidly / reverse mid-flight — no restart from
   zero, no jump (capture with `--steps` right after the second trigger, or record video).
8. **Iterate:** fix, re-run 2–7. Only then give a verdict. Report what you saw, not what you assume.

If no browser automation is available at all, say so explicitly, do part A, and give the user the
exact manual DevTools steps (Animations drawer at slow playback, Performance panel Frames track at
4× CPU, Rendering → emulate reduced motion). Never claim visual verification you didn't do.

## Output
**Part 1 — Findings table** (one row per issue; never a Before:/After: list)

| Location | Before | After | Why | Evidence |
| --- | --- | --- | --- | --- |
| `Popover.css:12` | `transition: all 300ms ease-in` | `transition: transform 180ms var(--ease-out), opacity 180ms var(--ease-out)` | ease-in delays the watched moment; `all` animates unintended props | frame 3/12: 18 % progress at 30 % time |

**Part 2 — Verification evidence** — frames inspected (count, notable frames), curve check result,
frame-timing report (throttle, janky %, worst LoAF), reduced-motion result, interrupt result.

**Part 3 — Verdict** grouped by tier (feel-breaking → missed deletions → performance →
interruptibility/timing → origin/cohesion → accessibility), then exactly one of:
- **Block** — any feel-breaking regression, motion on high-frequency/keyboard actions, `scale(0)`,
  ease-in on UI, a janky frame-timing result with an available compositor fix, or a missing
  reduced-motion path on movement.
- **Approve** — standards met **and** the visual loop passed (frames match the feel, timing smooth
  under 4× throttle, reduced motion verified).
- **Approve with notes** — only LOW polish items remain.
