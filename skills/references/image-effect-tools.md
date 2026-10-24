# Image-effect / ASCII / dither tools (browser, upload → sidebar effects → export)

**The need:** a free, highly customisable browser tool. Upload an image, stack effects from a sidebar (ASCII, dithering, halftone, glitch, motion/radial blur, cinematic grading), export.
**The finding:** no single free tool does *all* of it well. The pick depends on whether you need the blur/grading family.
Verified 2026-10-16 from each tool's own pages/pricing. Community signal is thin: HN has no threads ranking these tools, only adjacent dithering explainers that score highly ([visualrambling Dithering pt 1](https://visualrambling.space/dithering-part-1/), 461 pts). Treat feature lists as vendor claims.

## Winner: ASCII Magic, [ascii-magic.com](https://www.ascii-magic.com/)
- **What it is:** 100+ styles (ASCII, dither, pixel, voxel, halftone, glitch, mosaic…). A real-time post-processing stack: vignette, scanlines, CRT curvature, chromatic aberration, bloom, film grain, glitch, RGB split, **blur**, halftone, pixelate, film dust, colour overlay. One-click "recipes", image + video.
- **Free tier, per its pricing page:** "No account, no watermark, no time limit". Every *core* style (ASCII, dither, pixel, voxel). Unlimited image/video export. Pro is $8/mo (from $4 yearly) and unlocks all 100+ effects, 4K and AI renders.
- **Licence of output:** "Whatever you export is yours to use commercially… on both the free and Pro plans". You still need rights to the source image.
- **Agent bonus:** it ships an **MCP server**, so an agent can run effects itself.
- **Verdict: KEEP (winner).** It has the best free + customisable + export-rights combination. **Caveat:** some post-effects are Pro-only, and true motion/radial blur and grading are limited.

## Runners-up
| Tool | Strength | Free? | Verdict |
|---|---|---|---|
| **Grainrad**, [grainrad.com](https://grainrad.com/) | The purest match to "sidebar of effects": ASCII, Dithering, Halftone, Matrix Rain, Dots, Contour, Pixel Sort, Blockify, Threshold, Edge Detection, Crosshatch, Wave Lines, Noise Field, Voronoi, VHS. Brightness/contrast/saturation/hue/sharpness/gamma. Export PNG/JPG/GIF/MP4/**SVG/TXT/Three.js HTML**. Image, video, GIF, GLB, webcam | **Fully free, no account** ("So this one's free") | **KEEP (runner-up #1)** for ASCII/dither/halftone. **WEAK on maintenance:** last changelog v1.0.2, Jan 2025. No blur/grading |
| **Ditther**, [ditther.com](https://www.ditther.com/) | 75+ effects in families: pixel/retro, print/analog, glitch, colour/light. Includes **Motion Blur, Duotone (grading), Light Leak, Risograph, Bloom, Fisheye, Chromatic Aberration**. Layers, text/shape/mask, animation, saved "Looks" | Freemium. Free = 8 pixel effects + duotone + 1080p video. **Pro $8/mo or $69 lifetime** for the "Visual effects", 4K, no watermark | **KEEP (runner-up #2)** when you need the blur/grade/print family. Free tier is narrow |
| **Stippling**, [stippling.app](https://stippling.app/) | Two modes: vector halftone/stipple with **SVG export**, and an FX editor (ASCII, pixel, glitch, light trails, VHS, motion). On-device. Figma plugin | Free core. Several looks marked Pro | **KEEP** for print-grade vector halftone |
| **Turbo Dither**, [turbodither.com](https://www.turbodither.com/) | Floyd–Steinberg/Atkinson/Bayer/JJN, retro palettes (Game Boy, CGA, PICO-8…), paint mode, webcam, Web Workers | "Completely free… without any watermarks, tracking, or account" | **KEEP** for pure dithering only |
| **Photopea**, [photopea.com](https://www.photopea.com/) | Photoshop-like editor: adjustment layers (curves, levels, hue/sat), **cinematic grading**, Blur Gallery, smart filters | Free with ads. Premium removes them | **WEAK (unverified detail).** Blur Gallery and adjustments are documented. Motion/radial blur assumed from Photoshop parity, so confirm in the app. Best for grading + blur, not ASCII |
| DitherEffect, [dithereffect.com](https://dithereffect.com/) | Claims 67 dither styles, CRT/VHS/glitch, CMYK plates | Free (claims) | **WEAK.** The page wouldn't render without JS for verification |
| sticker-gliph / halftone (GitHub) | Open-source stackable effects | MIT / unclear licence | **DO NOT USE.** 0–1★, brand-new, unmaintained-risk |

## How to choose
1. ASCII/dither/halftone, fully free → **Grainrad**.
2. Plus post-FX and an agent-drivable workflow → **ASCII Magic**.
3. Need motion blur, duotone grading, light leaks or poster layouts → **Ditther** (Pro for full control) or **Photopea** for grading.
4. Vector/SVG halftone for print or large hero art → **Stippling**.

Web perf note: export a *static* asset (AVIF/WebP, or an SVG for halftone) rather than running the effect live. Only use a live shader (Canvas UI, Three.js) when the effect must react to input. That decision needs frontend-performance.
