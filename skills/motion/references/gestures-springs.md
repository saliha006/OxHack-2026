# Springs, gestures, interruptibility

Derived from Apple WWDC 2018 *Designing Fluid Interfaces* and WWDC 2023 *Animate with springs*,
plus Emil Kowalski's work on Sonner/Vaul, translated to the web (Pointer Events, rAF, WAAPI, Motion).
Spring parameter presets live in [feel-presets.md](feel-presets.md) — this file is the *how*.

The through-line: **an interface feels alive when motion starts from the current on-screen value,
inherits the user's velocity, projects momentum forward, and can be grabbed and reversed at any instant.**

## When to use a spring vs a curve
| Situation | Use |
| --- | --- |
| Anything the user can grab, drag, flick, or reverse mid-flight | Spring (velocity-aware, interruptible) |
| Decorative pointer-following (tilt, magnetic, cursor follower) | Spring or lerp on the raw pointer value |
| Rapidly re-triggered state (toasts stacking, toggles) | CSS **transition** (retargets) or spring — not `@keyframes` (restarts) |
| Predetermined, non-interactive (entrance, reveal, loader) | CSS transition/animation or WAAPI with a curve |
| Must stay smooth while the main thread is busy (route change, hydration) | CSS/WAAPI on `transform`/`opacity` (compositor) — not rAF-driven JS |

## 1. Response — kill latency
- Show feedback on **pointer-down**, commit on release. Waiting for `click` to show a press state feels dead.
- Audit everything on the input path: debounces, artificial timers, waits for a transition to end.
- During a drag, slider, or sheet, update **1:1 with the pointer every frame** — never only at the end.

## 2. Direct manipulation (1:1 tracking)
- `setPointerCapture(e.pointerId)` on pointerdown so tracking survives leaving the element.
- Keep the **grab offset** — never snap the element's centre to the pointer.
- Keep a short history (last ~5 `pointermove` samples with timestamps) to compute release velocity.
- Ignore extra pointers once a drag begins (multi-touch jumps).
- Write `transform` directly on the element; don't set a CSS variable on a parent that many children
  inherit (style recalculation storm).
- `touch-action: none` (or `pan-y` for horizontal drags) on the draggable so the browser doesn't
  fight you for the gesture.

## 3. Interruptibility — the most important principle
- Never lock out input during a transition. A closing sheet the user grabs follows the finger.
- **Animate from the presentation (current) value**, never from the logical target. On interrupt, read
  the live value (`getComputedStyle(el).transform`, or the motion value) and start from there.
- On reversal, **carry velocity** into the new target. A hard cut is a "brick wall." Springs that
  retarget with current velocity (Motion, react-spring) avoid it; CSS transitions retarget position
  but reset velocity — acceptable for small UI, not for flung objects.
- Decompose 2D motion into **independent x and y springs**.
- Decide commit vs cancel at release by **velocity sign/magnitude first**, distance second.

## 4. Velocity handoff (no seam between drag and animation)
Pass release velocity into the spring. Motion takes absolute units/s:
```js
import { animate } from "motion";
animate(el, { y: target }, { type: "spring", velocity: releaseVelocityPxPerSec, bounce: 0.15, visualDuration: 0.35 });
```
APIs that want *relative* velocity (SwiftUI/UIKit style): `v_rel = v_px_per_s / (target − current)`.

## 5. Momentum projection (animate to where the gesture is going)
Don't snap to the nearest point from the *release* position — project the resting point first.
Apple's sample-code projection (exponential decay, same as scroll deceleration):
```js
// decelerationRate: 0.998 ≈ normal scroll, 0.99 ≈ fast/snappy
const project = (v /* px/s */, d = 0.998) => (v / 1000) * d / (1 - d);
const target = nearestSnapPoint(current + project(releaseVelocity));
animateSpringTo(target, { velocity: releaseVelocity });
```
Flick-to-dismiss heuristic (Sonner): dismiss if `|distance| ≥ threshold` **or**
`|distance| / elapsedMs > ~0.11` px/ms. A quick flick is enough; tune per component.

## 6. Rubber-banding (soft boundaries)
Progressive resistance past an edge reads as "responsive, nothing more here"; a hard stop reads as frozen.
```js
// c ≈ 0.55 is the iOS-like constant; d = viewport/container dimension on that axis
const rubberband = (overshoot, d, c = 0.55) => (overshoot * d * c) / (d + c * Math.abs(overshoot));
```
On release, spring back to the bound with the release velocity.

## 7. Gesture details
- **Tap**: highlight on down, commit on up; allow cancel by dragging away; ~10 px slop.
- **Drag/swipe**: ~10 px hysteresis before locking a direction, then 1:1.
- Detect plausible gestures in parallel from the first move; cancel the losers once intent is clear.
- Only pay double-tap disambiguation delay where double-tap actually exists.

## 8. Spatial consistency
- Enter and exit along the **same path** (in from right → out to right).
- Anchor to the source: `transform-origin` at the trigger (Radix
  `var(--radix-popover-content-transform-origin)`, Base UI `var(--transform-origin)`). Modals stay centred.
- Hint toward the outcome: intermediate frames should point where the element is going.

## 9. Spring math (for converting between APIs)
- Damping ratio `ζ = c / (2·√(k·m))`. ζ = 1 → critically damped (no overshoot); ζ < 1 → overshoot.
- Example: Motion's physics defaults `stiffness 100, damping 10, mass 1` → ζ = 0.5 → visibly bouncy.
  Don't use them for "no bounce" UI; prefer the `bounce` + `visualDuration` form.
- Apple/Motion "duration + bounce" form: bounce 0 ≈ ζ 1; positive bounce = under-damped. *Duration*
  here is perceptual — the spring keeps micro-settling slightly after.
- Pure CSS springs: generate a `linear()` easing (e.g. from a spring solver) for non-interactive
  springy entrances; it can't carry gesture velocity, so keep JS springs for gestures.

## 10. Multimodal feedback (sound/haptics)
Causality (fire on the causal event), harmony (same frame as the visual), utility (only meaningful
moments). Never play sound without opt-in. Vibration API is Android-only on the web.
