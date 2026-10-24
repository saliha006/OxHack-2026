# Animation vocabulary — reverse lookup

Turn a vague description ("the bouncy thing when a popover opens") into the exact term, so the user
can ask a designer or an agent for it. Format every answer as:

```
**Term** — what it is. Feels: <sensation>. Built with: <mechanism>.
Close alternates: **X** (if …), **Y** (if …).
```

Rules: read for the *sensation*, not keywords. Best match first, then 1–2 alternates with the
distinguishing detail. If nothing fits exactly, say it's an approximation and compose terms
("a *stagger* of *scale-in* entrances"). Don't invent terms. A naming question wants a name, not an
essay. For build recipes of the signature effects, see [signature-effects.md](signature-effects.md).

Base glossary adapted from Emil Kowalski's animation vocabulary (animations.dev); "feels" and
"built with" columns and the signature-effects section added.

## Quick reverse lookup (what people say → term)

| They say… | Term |
| --- | --- |
| "grows out of the button" | Origin-aware animation |
| "bounces into place" | Pop in (spring with bounce) |
| "pulls and snaps back at the edge" | Rubber-banding |
| "keeps going after I let go" | Momentum / inertia (velocity handoff + projection) |
| "one after another" | Stagger |
| "thumbnail grows into the page" | Shared-element transition (View Transition / layoutId) |
| "shape turns into another shape" | Morph |
| "moves as I scroll, backwards when I scroll up" | Scroll-driven (scrubbed) animation |
| "plays once when it scrolls into view" | Scroll reveal (scroll-triggered) |
| "background moves slower than the text" | Parallax |
| "scroll feels buttery / floaty" | Smooth scroll (Lenis-style inertial scroll) |
| "cards pile on top of each other as you scroll" | Sticky stacking cards |
| "button pulls toward my cursor" | Magnetic button |
| "letters/words rise in one by one" | Text split reveal |
| "text slides endlessly sideways" | Marquee / ticker |
| "image wipes in from one side" | Clip-path (or mask) reveal |
| "gradient blob / liquid background" | Shader (WebGL) background |
| "film-grain texture over everything" | Noise / grain overlay |
| "pen drawing the outline" | Line drawing (SVG stroke-dashoffset) |
| "numbers spin up to the value" | Number ticker / rolling digits |
| "card tilts toward the mouse" | 3D tilt (pointer-driven rotateX/Y) |
| "light follows the cursor on the card" | Cursor spotlight (pointer-tracked radial gradient) |
| "page loads with a sequence/countdown" | Preloader / intro sequence |
| "looks smeared when moving fast" | Motion blur (directional blur/stretch) |
| "squishes when it lands" | Squash & stretch |
| "small backwards wind-up first" | Anticipation |
| "wobbles a bit after stopping" | Follow-through / settle (under-damped spring) |
| "stutters / hitches" | Jank (dropped frames) |

## Entrances & exits
- **Fade in / out** — opacity change. Feels: soft, neutral. Built with: `opacity` transition.
- **Slide in** — enters from off-screen along one axis. Feels: directional, spatial. Built with: `translate` (prefer `%` of own size).
- **Scale in** — grows from slightly smaller (never 0) with a fade. Feels: "arrives", light. Built with: `scale(0.95)→1` + opacity.
- **Pop in** — scale-in with slight overshoot. Feels: playful, alive. Built with: spring with bounce, or overshooting `cubic-bezier`/`linear()`.
- **Reveal** — content uncovered progressively. Feels: editorial, deliberate. Built with: `clip-path` or `mask`.
- **Enter / exit** — the animation played when an element mounts/unmounts. Built with: `@starting-style`, `AnimatePresence`, View Transitions.
- **Blur-in** — starts blurred and sharpens. Feels: cinematic, "focus pull". Built with: `filter: blur()` + opacity (keep radius small).

## Sequencing & timing
- **Keyframes** — defined waypoints the browser interpolates between.
- **Interpolation / tween** — generated in-between frames from start to end.
- **Stagger** — items start one after another with a fixed small delay. Feels: cascade, rhythm.
- **Orchestration / choreography** — several animations timed as one gesture (e.g. parent then children).
- **Delay / duration / fill mode** — wait before start / length / whether first/last frame styles persist (`forwards`).
- **Stepped animation** — discrete jumps (`steps()`), e.g. countdowns, sprite sheets.
- **Timeline** — a controllable sequence of tweens (GSAP timeline, WAAPI group).

## Movement & transforms
- **Translate / scale / rotate / skew** — move, resize, spin, shear.
- **3D tilt / flip** — `rotateX/Y` with `perspective`; lower perspective = stronger depth.
- **Transform origin** — the anchor a scale/rotation grows from.
- **Origin-aware animation** — grows from its trigger rather than its own centre (popovers yes, modals no).

## Transitions between states
- **Crossfade** — old fades out while new fades in, same spot.
- **Continuity transition** — before and after visibly connected (the same rectangle resizes).
- **Morph** — one shape becomes another (Dynamic Island).
- **Shared-element transition** — an element travels and transforms between two views (thumbnail → detail). Built with: View Transitions (`view-transition-name`) or Motion `layoutId`.
- **Layout animation (FLIP)** — size/position change animates instead of snapping. Built with: First-Last-Invert-Play transforms, Motion `layout`.
- **Accordion / collapse** — height expand/collapse. Built with: `grid-template-rows: 0fr→1fr`, `interpolate-size`, or FLIP.
- **Direction-aware transition** — forward slides one way, back the other.
- **Page / view transition** — animation between routes or documents (View Transitions API, same- or cross-document).

## Scroll
- **Scroll reveal (scroll-triggered)** — plays once when entering the viewport (IntersectionObserver / `view()` timeline). Feels: presentational.
- **Scroll-driven (scrubbed) animation** — progress bound to scroll position; reverses when scrolling back. Built with: CSS `animation-timeline: scroll()|view()` or GSAP ScrollTrigger `scrub`.
- **Pinning** — a section sticks while its inner animation scrubs (`position: sticky` or ScrollTrigger `pin`).
- **Parallax** — layers move at different speeds for depth. Vestibular risk.
- **Smooth / inertial scroll** — scroll position eased toward target (Lenis). Feels: floaty, premium — or laggy/hijacked.
- **Horizontal scroll section** — vertical scroll drives horizontal travel inside a pinned section.
- **Scroll progress indicator** — bar tracking read progress (`scroll()` timeline on `scaleX`).
- **Scroll snap** — native resting points (`scroll-snap-type`). Not an animation, but shapes the feel.

## Feedback & interaction
- **Hover effect** — change on pointer-over; gate behind `(hover: hover) and (pointer: fine)`.
- **Press / tap feedback** — subtle scale-down (0.95–0.98) on press.
- **Hold to confirm** — fill progresses while held; snaps back on release.
- **Drag / drag to reorder / swipe to dismiss** — direct manipulation with momentum.
- **Rubber-banding** — progressive resistance past a boundary, then snap back.
- **Shake / wiggle** — horizontal jitter for rejection/error.
- **Ripple** — circle expanding from the tap point.
- **Magnetic button** — element (or its label) translates a fraction toward the nearby pointer, springing back on leave.
- **Custom cursor / cursor follower** — DOM element trailing the pointer with a spring/lerp.
- **Cursor spotlight** — radial gradient whose centre tracks the pointer.

## Easing
- **Easing** — rate of speed change over time.
- **Ease-out** — fast start, gentle stop. Default for anything responding to the user.
- **Ease-in** — slow start, fast end. Exits that leave the screen, rarely anything else.
- **Ease-in-out** — slow-fast-slow. On-screen A→B moves.
- **Linear** — constant speed. Spinners, marquees, scrubbed scroll, progress.
- **Cubic-bezier** — custom curve via two control points.
- **`linear()` easing** — piecewise curve in CSS; how springs/bounces are expressed without JS.
- **Asymmetric easing** — different acceleration and deceleration rates.
- **Overshoot** — curve exceeds the target then settles (`y` control point > 1).

## Springs & physics
- **Spring** — motion from a physical model (stiffness, damping, mass), not a fixed duration.
- **Stiffness / tension** — pull toward target; higher = snappier.
- **Damping** — resistance; lower = more oscillation.
- **Damping ratio (ζ)** — `damping / (2·√(stiffness·mass))`. 1 = no overshoot (critically damped), <1 = bounces.
- **Mass** — inertia; more = heavier, slower to start and stop.
- **Bounce** — designer-friendly overshoot amount (0 = none). Apple/Motion parameterisation with *duration*.
- **Response / perceptual duration** — how long the spring *feels* (it keeps micro-settling after).
- **Momentum / inertia / velocity** — speed carried from a gesture into the next motion.
- **Velocity handoff** — release velocity becomes the spring's initial velocity (no seam).
- **Momentum projection** — predict where a flick would come to rest, snap to nearest target there.
- **Interruptible animation** — can be redirected mid-flight from its current value.
- **Additive animation** — new motion blends on top of the in-flight one instead of replacing it.

## Looping & ambient
- **Marquee / ticker** — content scrolls in an endless loop (duplicated track, `translateX(-50%)`, linear).
- **Loop / alternate (yoyo)** — repeat; yoyo reverses each iteration.
- **Orbit / pulse / float / idle animation** — circling; attention throb; gentle drift; waiting-state motion.
- **Shimmer / skeleton** — moving sheen over a placeholder while loading.
- **Gooey / blob morph** — shapes merge like liquid (SVG blur + contrast filter, or shader).

## Polish & effects
- **Blur** — softens, or masks the double-exposure of a crossfade (small radius).
- **Clip-path** — hard-edged clipping for reveals, wipes, before/after sliders.
- **Mask** — like clip-path but soft/gradient edges (`mask-image`).
- **Line drawing** — SVG path draws itself (`stroke-dasharray` + `stroke-dashoffset`, or `pathLength="1"`).
- **Text morph** — characters animate when text changes.
- **Text split reveal** — text split into lines/words/chars, each masked and staggered up.
- **Typewriter** — characters appear one at a time.
- **Number ticker** — digits roll/count to a value; needs **tabular numbers** (`font-variant-numeric: tabular-nums`).
- **Noise / grain** — static or animated film grain over the page (tiled PNG or SVG `feTurbulence`).
- **Shader / WebGL background** — GPU-rendered gradient, fluid, or distortion field (Three.js, OGL, R3F).
- **Image distortion on hover** — WebGL displacement/ripple on an image texture.
- **Motion blur** — directional smear encoding speed.
- **Glassmorphism / materialize** — `backdrop-filter` surface arriving by animating blur + scale together.
- **Lottie / Rive** — designer-authored vector animations played at runtime.

## Performance terms
- **Frame budget** — ~16.7 ms at 60 Hz, ~8.3 ms at 120 Hz, for all work in a frame.
- **Jank / dropped frame** — a frame missed its deadline; visible hitch.
- **Long animation frame (LoAF)** — a frame whose rendering took > 50 ms (measurable API).
- **Compositing** — the GPU moves/fades a layer without re-layout or repaint (`transform`, `opacity`).
- **will-change** — hint to promote a layer ahead of motion; use sparingly.
- **Layout thrashing** — interleaved DOM reads and writes forcing repeated synchronous layout.
- **Main-thread vs compositor animation** — JS/rAF animations stall when the main thread is busy; compositor ones don't.

## Principles
- **Purposeful animation** — every motion orients, gives feedback, shows relationships, or prevents a jarring change.
- **Frequency of use** — the more often seen, the shorter and subtler (or none).
- **Spatial consistency** — exit the way you entered; keep identity across states.
- **Anticipation / follow-through / squash & stretch / slow-in slow-out** — Disney's 12 principles applied to UI.
- **Perceived performance** — motion that makes waiting feel shorter.
- **Reduced motion** — honouring `prefers-reduced-motion` with gentler, non-vestibular substitutes.
