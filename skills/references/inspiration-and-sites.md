# Inspiration, moodboards & sites worth studying

## Moodboard / discovery tools
| Resource | What it is | Use when | Cost | Verdict |
|---|---|---|---|---|
| **Cosmos**, [cosmos.so](https://www.cosmos.so/) | Ad-free visual moodboarding: collections, **colour search**, "find similar", web clipper, collaboration, and an **AI-image filter** (show/blur/hide images flagged as AI-generated) | Building a direction board before design-direction commits. Hunting by colour | Free to join | **KEEP.** The AI filter is the differentiator vs Pinterest. Designers share landing-page collections there ([HN](https://news.ycombinator.com/item?id=50104043)). An unofficial Cosmos MCP exists (unvetted, so don't install it by default) |
| **Mobbin**, [mobbin.com](https://mobbin.com/) | Screens + flows from real iOS/web apps | Pattern research for a specific flow (onboarding, paywall) | Freemium | **KEEP** (via floguo hub) |
| **Awwwards**, [awwwards.com](https://www.awwwards.com/) | Award gallery + Elements clips | Spotting ambitious techniques | Free | **WEAK→KEEP as inspiration only.** Spectacle bias, so check perf |
| **Behance** | Portfolio platform | Brand/identity systems | Free | **KEEP** (blocks bots; read via a browser or `r.jina.ai`) |

### Behance pieces: what makes them good
**[a to A](https://www.behance.net/gallery/254443291/a-to-A)**: Samsung Design Membership (Hyunbin Seo lead, Junwoo Lim, Joowon Surh, Minjung Kim, Jiwoo Lee), 2026. It's a speculative exhibition set in 2051 about "127", a counterculture that runs local AI on *wearable servers*. What to learn:
- **One typographic idea drives everything.** The repeated lowercase "a" (people as AI-classified *types*) gives way to one uppercase "A" (an individual with a name). The grid of repeats vs. the single break becomes the graphic system for posters, the archive and motion. *Borrow:* derive the visual system from one semantic transformation, not from a mood.
- **Narrative structure.** Each section is a headline + subhead + short paragraph + film/3D render ("Mainstream and Counterculture" → "Model Convergence" → "Visible Resistance"). It reads like a scroll-told story. *Borrow:* section rhythm for long-scroll storytelling pages.
- **Product, 3D and motion are integrated.** Rhino/KeyShot renders, motion clips and editorial layout share one language. Exposed cables and connection points become the aesthetic, so *function shown honestly becomes style*.

**[Solune — Brand Identity Design](https://www.behance.net/gallery/257037263/Solune-Brand-Identity-Design)**: a solar-energy brand, credited on the page to Typefool / Jon Nuredini. Tools: Illustrator, After Effects. What to learn:
- **Strategy first, then form.** One line, "Energy beyond daylight", drives the system.
- **A constructed geometric mark:** a hexagon referencing solar-cell structure and energy flow. Precise construction signals reliability.
- **Restrained palette:** cool greys plus one vivid **Solar Orange**. Precision vs. energy in one contrast. A minimal typographic system.
- **Proof across touchpoints:** UI, packaging, installation gear, vehicles, environmental graphics, merch. *Borrow:* define tokens as "neutral ramp + one signal hue", and test the system on 5+ surfaces before calling it done.

## Sites worth studying
Measured 2026-10-16 from the initial HTML only: script tags and compressed transfer of the JS/CSS they reference. Lazy-loaded code is **not** counted, so real totals are higher. Lighthouse/CrUX quota was exhausted, so run `lighthouse_audit` (DevTools MCP) before quoting scores.

| Site | Signature techniques worth borrowing | Pitfalls | Measured (initial) |
|---|---|---|---|
| **A24**, a24films.com | Film-poster art direction: imagery-first, big editorial type, restrained UI chrome, so the content *is* the design | Image-heavy pages. Make sure hero media is sized/priority-loaded | 24 scripts · ~704 KB JS |
| **Apple**, apple.com | Scroll-scrubbed product storytelling (canvas image-sequence "flipbook", sticky sections; [CSS-Tricks 2020](https://css-tricks.com/lets-make-one-of-those-fancy-scrolling-animations-used-on-apple-product-pages/)). Huge type contrast. Native-feeling easing. Disciplined whitespace | Frame sequences are heavy (that demo: ~148 frames). Needs fallbacks for slow connections and reduced motion | **Leanest of the set:** 13 scripts · ~398 KB JS · 2 `<video>` |
| **OpenAI**, openai.com | Calm editorial layout, neutral palette, generous measure, media-led launch pages | Script count is high for a mostly-editorial site | 105 scripts · ~2.5 MB JS (heaviest) |
| **ElevenLabs**, elevenlabs.io | Product-as-demo: interactive audio samples above the fold. Crisp, startup-minimal look that HN users singled out as "concise, simple, super fast" ([HN](https://news.ycombinator.com/item?id=40719069)) | ~440 KB inline JS. Big HTML (956 KB) | 76 scripts · ~1.2 MB JS · 2 canvas |
| **heyclicky**, heyclicky.com | Personality via voice: all-lowercase copy, kaomoji `( ^ ω ^ )`, filenames as captions (`it-draws-too-omg.mov`). **Demo videos instead of illustrations** (13 `<video>`). Tiny JS | 13 videos need lazy-loading + posters, or bandwidth balloons. The playful voice won't suit every brand | 13 scripts · ~282 KB JS (lightest) |
| **Figma**, figma.com | Bold colour blocking, product-UI-as-illustration, playful cursors/multiplayer motifs | **~1.47 MB of inline JS in the HTML** (hydration payload). Big HTML hurts TTFB/parse on mid-range phones | 27 scripts · ~1.5 MB JS + 1.47 MB inline |
| **Stripe**, stripe.com | The animated mesh **WebGL gradient** (widely reconstructed: Kevin Hufnagl's minigl gist; [Codrops 2022](https://tympanus.net/codrops/2022/09/26/how-to-recreate-stripes-lava-lamp-gradient-with-three-js)). Skewed section edges. Meticulous type and spacing. Docs-quality code samples as hero art | **Feels sluggish because:** 81 scripts / ~1.2 MB JS + 253 KB inline JS + a continuously running WebGL canvas compete for the main thread and GPU, and on low-end laptops the always-on shader burns CPU/GPU (users report Stripe's *dashboard* pegging CPU: [HN](https://news.ycombinator.com/item?id=45039600)). *Borrow the gradient idea; pause it off-screen and under reduced motion; cap its frame rate* | 81 scripts · ~1.2 MB JS · 1 canvas |
| **Cursor**, cursor.com | Dark, product-screenshot-led, IDE-as-hero. Crisp typography | **Feels sluggish because:** ~1.66 MB JS from 38 scripts + 173 KB inline, i.e. a heavy client bundle for a marketing page. Long hydration means interactions lag on first load (inferred; trace it). HN repeatedly complains about sites that **hijack the cursor or scroll** ("laggy orb": [1](https://news.ycombinator.com/item?id=44030714), [2](https://news.ycombinator.com/item?id=43048064)), so never replace the native cursor | 38 scripts · ~1.66 MB JS |

**Cross-site lesson:** the sites that *feel* fastest (Apple, heyclicky) ship the least JS and put motion in video/CSS. The ones that feel sluggish (Stripe, Cursor, Figma) pay for always-on JS/WebGL or large hydration payloads. Borrow the look, re-budget the cost (see frontend-performance).
