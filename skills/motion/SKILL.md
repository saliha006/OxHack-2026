---
name: motion
description: >-
  Design and build UI motion that feels intentional: transitions, micro-interactions, springs,
  gestures (drag, swipe, flick, sheets), scroll-driven and scroll-triggered effects, view/page
  transitions, layout/FLIP, hero and marketing effects (parallax, text reveals, marquees, sticky
  stacks, clip/mask reveals, WebGL backgrounds, smooth scroll), and reduced-motion handling. Starts
  with a feel intake (snappy, smooth, springy, weighty/cinematic, slow, motion-blurred…) mapped to
  exact durations, curves and spring values. Three modes: build, find (read-only animation
  opportunities with exact values), improve (audit existing motion → prioritized plans). Includes a
  reverse-lookup animation vocabulary ("what's it called when…"). Use for "animate this", "make it
  feel alive/smoother/snappier", "add a transition", "what could be animated", "audit/improve the
  animations", "what's this effect called", springs, easing, durations. After any motion change,
  run the motion-review skill.
---

# Motion

Motion is a feel, not a garnish. Decide **whether** to animate, **what it should feel like**, then
build it with exact values — and verify it visually before calling it done.

Credits: craft rules and modes adapted from Emil Kowalski (emilkowal.ski, animations.dev); fluid
gesture principles from Apple WWDC 2018 *Designing Fluid Interfaces* and WWDC 2023 *Animate with
springs*. Evidence and source ledger: `Claude instructions/research-ledger.md` §4 motion + performance.

## Step 0 — Feel intake (always first)

Unless the user has already said it, or the repo has documented motion tokens, **ask** (one short
question, with options):

> What should this motion feel like?
> **snappy** (crisp, productive) · **smooth / fluid** · **springy / playful** · **weighty / cinematic** ·
> **deliberately slow / languid** · **motion-blurred / speedy** · **mechanical / precise** ·
> **soft / calm** · or point me at a reference (site, app, video).

Also confirm, if unclear: who uses it and how often (power users → less motion), and whether it's
product UI or a marketing surface. If the user says "you decide", infer from personality (dashboard
→ snappy; consumer/brand → smooth or springy; healthcare/finance → soft/calm) and **state** the choice.

Map the answer to exact values with [feel-presets.md](references/feel-presets.md) and write a
one-line **feel contract** (base duration + curve, exit timing, spring config, stagger, reduced-motion
substitute). Extend the repo's existing tokens; never fork a parallel set.

A reference ("make it feel like Linear / Apple / that site") → name the effects with
[vocabulary.md](references/vocabulary.md), then pick the nearest preset and adjust. (Deep reference
deconstruction belongs to the `reverse-engineer-ui` skill.)

## Step 1 — Should it animate at all?

| Seen… | Decision |
| --- | --- |
| Keyboard-initiated or 100+/day | **No animation.** Instant is the feature. |
| Tens/day | Minimal: tiny transform or none (cap in feel-presets) |
| Occasionally | Standard motion per the feel contract |
| Rarely / first time | Delight budget lives here |

It must have a purpose: **feedback, spatial consistency, state indication, preventing a jarring
change, explanation, or (rare tier) delight.** If the only reason is "looks cool" on frequent UI,
don't. Data the user is reading or acting on doesn't move for style. When unsure, the strongest move
is usually *less* motion.

## Step 2 — Build (core rules)

Full rules: [craft-rules.md](references/craft-rules.md). The ones that matter most:

1. **Easing:** entrances/responses ease-out; on-screen moves ease-in-out; permanent exits short
   ease-in; constant motion linear. Never ease-in on entrances or feedback. Use the curve tokens, not
   CSS built-ins.
2. **Duration:** from the feel contract and the size table in [feel-presets.md](references/feel-presets.md);
   exits shorter (and smaller) than enters; bigger/farther = longer. Past the functional-UI cap needs a reason.
3. **Physicality:** never `scale(0)` (start 0.9–0.97 + opacity); popovers grow from their trigger
   (modals stay centred); enter and exit along the same path; press feedback `scale(0.97)` on
   pointer-down.
4. **Interruptible:** transitions or springs for anything re-triggered or grabbable; `@keyframes`
   only for one-shot or looping sequences. Gestures: 1:1 tracking, velocity handoff, momentum
   projection, rubber-banding → [gestures-springs.md](references/gestures-springs.md).
5. **Compositor-friendly:** `transform`/`opacity` (and `filter` sparingly); never `transition: all`
   or layout properties; CSS/WAAPI for predetermined motion so it survives a busy main thread.
6. **Reduced motion:** no-motion-first; replace travel/zoom/parallax with fades; keep meaningful
   feedback; persistent pause for anything auto-moving > 5 s → [accessibility.md](references/accessibility.md).
7. **Hover** motion gated by `@media (hover: hover) and (pointer: fine)`.
8. **Restraint:** one signature moment per view; no fade-and-rise on every section.

Tech choice: CSS (transitions, `@starting-style`, `animation-timeline`, view transitions) first →
WAAPI for programmatic control → Motion for React springs/gestures/layout → GSAP for complex
timelines, pinning, text splitting. Recipes for top-site effects:
[signature-effects.md](references/signature-effects.md).

## Modes

| Mode | Trigger | What happens | Reference |
| --- | --- | --- | --- |
| **build** (default) | "animate this", "add a transition" | Intake → gate → implement → `motion-review` | this file |
| **find** | "what could be animated?", "make it feel more alive" | Read-only sweep, gated, ≤ 5–7 proposals with exact values + rejected list | [opportunities.md](references/opportunities.md) |
| **improve** | "audit / improve the animations" | Recon → 8-category audit → vetted table → user picks → self-contained plans in `plans/` | [improve-audit.md](references/improve-audit.md) |
| **name it** | "what's it called when…" | Reverse lookup: term + feel + how it's built + alternates | [vocabulary.md](references/vocabulary.md) |

## Step 3 — Verify (not optional)

After building or changing motion, invoke **`motion-review`**: it captures frames of the animation,
checks the sampled curve against the feel contract, measures frame timing under CPU throttle, checks
the reduced-motion path, and iterates until it passes. "It compiles" is not done; "it looks right in
the frames and holds frame rate" is.

## Output conventions
- State the feel contract at the top of any motion work.
- Every suggested value is exact (properties, ms, curve token or spring config, reduced-motion branch).
- When proposing changes to existing code, use a `| Before | After | Why |` table.
- If feel can't be judged from code alone, say so and verify visually rather than guessing.

## Related skills
`motion-review` (verify every change) · `frontend-performance` (jank, INP, CLS, loading) ·
`design-direction` (overall aesthetic/brand feel) · `ui-audit` (whole-UI review) ·
`reverse-engineer-ui` (deconstruct a reference site). Shared library: `../references/`.
