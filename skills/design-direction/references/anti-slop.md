# Anti-slop: generic tells, counter-moves, durable vs fad

Evidence: `Claude instructions/research-ledger.md` §3 design + audit → "D6 Premium vs slop".

## Why it happens
Models sample the high-probability centre of web data ("distributional convergence"). Shared libraries already homogenised the web before AI (Bootstrap-era sites measurably converged). **Banning one default just moves convergence to the next one:** Inter → Space Grotesk; purple → cream + serif + terracotta. So treat every list below as the *floor* of a check, then look for whatever new default you're reaching for.

## The core principle
**Conventional structure, distinctive surface.** First-impression research rates low-complexity, *prototypical* layouts most appealing. Users judge in ~50 ms and expect familiar navigation and structure. So keep layout, navigation and interaction familiar; spend distinctiveness on type, colour, imagery, copy and **one** memorable move. Beauty sets expectations and forgives small flaws; it never rescues bad usability.

## Ranked tells → counter-moves
| # | Tell | Counter-move |
|---|---|---|
| 1 | Purple/indigo/blue gradient or glow, on white or near-black | Palette from the brand/subject: one dominant + one accent, named tokens; no decorative gradients |
| 2 | Centred hero + subhead + two buttons + blob | Open with the subject's most characteristic thing: real product UI, real photo, real data; deliberate alignment |
| 3 | Three identical icon/emoji feature cards | 2–4 sections of unequal weight, each doing a job (proof, demo, how-it-works, price) |
| 4 | One radius and one soft grey shadow on everything; cards in cards | Radius scale by role (concentric when nested); one light source, layered tinted shadows; fewer containers, more space |
| 5 | Unchosen Inter/Geist, or its replacements (Space Grotesk, italic display serif) | Type chosen from voice words and register; Inter/system is fine in dense product UI, a deliberate face on brand surfaces |
| 6 | Tracked-caps eyebrow above every heading, badge/pill over the hero, "01 / 02" section numbers, "A · B · C" meta strings, "→" glued to CTAs | Structure only where it encodes information (a real sequence, real metadata) |
| 7 | Gradient text; glowing accents as affordance | Emphasis via size, weight, position; solid colour |
| 8 | Hype copy ("Elevate", "Seamless", "Supercharge", "Unlock the power of"), "Not X, it's Y", "No A. No B.", em-dash cadence | Specific audience + concrete reason to believe; action-named CTAs; sentence case |
| 9 | Prompt/implementation context leaking into the UI ("Built with X", "your files never leave your device" when nobody asked) | Every string serves the reader; audit the copy |
| 10 | Fade-up on every section, hover-lift on every card, pulsing status dots, bounce easing | One orchestrated moment; motion only for state change (see `motion`) |
| 11 | Glassmorphism as the default surface | At most 1–2 floating translucent surfaces, contrast-checked, with a solid `prefers-reduced-transparency` fallback |
| 12 | Emoji as icons; mixed icon sets | One icon family at consistent size/stroke, or none |
| 13 | Thick coloured side-stripe on cards/callouts | Status via icon + text + subtle tint or full hairline border |
| 14 | Hero-metric stat row; invented "10k+ users", fake testimonials, fake logo strips | Real, sourced proof or nothing. Fake reviews/testimonials are illegal in the US (FTC rule, 2024) |
| 15 | Cream/beige body + serif + terracotta (2025–26 "tasteful AI" default); near-black + one acid accent | Background from the brand's own palette; warmth through imagery and type, not a cream reflex |
| 16 | Missing states (empty/error/loading/focus) and sloppy alignment | Every state designed; optical alignment (~1 px nudges); visible focus |

Thin evidence (don't over-police): bento grids by themselves, "sparkles" icon, JetBrains Mono for anything technical, "shadcn look". Flag only when they're unchosen defaults.

## Self-review tests
1. **Swap test:** could a competitor use this page by changing the logo? Then nothing is distinctive yet.
2. **Reflex test (two levels):** could someone guess the palette/theme from the category alone? Could they guess the aesthetic lane from "category + not the obvious one" (e.g. "AI tool that isn't purple → editorial cream serif")? If either is yes, rework.
3. **Count the tells** from the table: 0–1 intentional, 2–3 generic, 4+ template.
4. **Screenshot loop:** render, read the screenshot, critique against the direction contract, fix, repeat. Any correction you make twice belongs in the direction contract.

## Durable vs fad (2024–2026)
| Trend | Verdict | Use it when |
|---|---|---|
| Container queries, subgrid | Durable (Baseline) | Component-level responsiveness |
| View transitions (same-document Baseline Oct 2025) | Durable | Continuity between states/pages, via `motion` |
| Variable fonts | Durable | 3+ weights or optical sizing |
| OKLCH tokens, `light-dark()` | Durable | Always |
| Dark mode | Durable **as an option** | Follow the OS; not the default for a general audience |
| Neo-brutalism | Niche | Expressive brands; watch contrast and unclear states |
| Bento grid | Neutral, overused | Tile sizes encode importance |
| Oversized display type | Neutral | Brand pages, tested at 320 px |
| Grain/noise texture | Fad-leaning | Subtle, one surface, brand reason |
| 3D/WebGL hero | Fad risk | The product is spatial; LCP budget checked (`frontend-performance`) |
| Glassmorphism / Liquid Glass | Fad as a style | Accent only; Apple itself added an opacity option after readability complaints |
| Aurora/glow gradient backgrounds | Fad (AI tell) | Rarely |
| Scroll-jacking | Harmful | Don't |
