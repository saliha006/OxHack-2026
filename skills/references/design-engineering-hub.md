# Design-engineering learning hub: floguo.com crawl

Source: [floguo.com/notes/design-engineering](https://www.floguo.com/notes/design-engineering), "a living doc" by Flo (ex-Vercel Design Engineering, now founding design engineer at Paradigm). Crawled 2026-10-16. Linked pages were opened where marked ✓.
Skills found through it are distilled in [harvested-skill-notes.md](harvested-skill-notes.md).

## By subject: most valuable first
### Agent skills & guidelines (the jackpot)
| Resource | What it is | Use for | Cost | Verdict |
|---|---|---|---|---|
| ✓ [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines) ([repo](https://github.com/vercel-labs/web-interface-guidelines), MIT, `command.md` = agent review command) | ~100 concrete rules: a11y, focus, forms, animation, typography, images, perf, URL state, touch, dark mode, i18n, hydration, copy | The ui-audit checklist backbone | Free | **KEEP** |
| ✓ [UI Skills](https://www.ui-skills.com/) (`npx ui-skills`, MCP) | A curated catalogue routing to skills by Emil Kowalski, Jakub Krehel, ibelick, shadcn, Anthropic `frontend-design`, Impeccable, React Doctor, Raphael Salaja's "12 principles of animation", Addy Osmani… | Finding the right specialist skill live | Free | **KEEP**, the best index |
| ✓ [skills.sh](https://skills.sh/) (Vercel) | Open skills directory + leaderboard (`npx skills add <owner/repo>`), 1.35M installs tracked, with an audits tab | Discovery by popularity, but **popularity ≠ quality**, so read before installing | Free | **WEAK→KEEP** as discovery only |
| ✓ [Rams](https://www.rams.ai/) | Scored design review: 356 rules, 9 categories, criticals cap the score. Skill, MCP, GitHub App, Action | Automated PR design gate. Its public rules list is a good checklist | Free on 1 public repo, $33/mo+ private | **KEEP** (rules), **WEAK** (paid service, vendor claims) |

### Craft writing (read when tuning detail)
| Resource | Subject | Verdict |
|---|---|---|
| ✓ [Details that make interfaces feel better](https://jakub.kr/writing/details-that-make-interfaces-feel-better) (Jakub Król) | Concentric radii, optical alignment, shadows vs borders, enter/exit motion. Same author as `jakubkrehel/skills` | **KEEP** |
| ✓ [Interfaces](https://interfaces.rauno.me/) (Rauno Freiberg) | Interaction-detail principles (Vercel heritage) | **KEEP** |
| [Ahmad Shadeed articles](https://ishadeed.com/articles/) | Deep CSS layout/defensive CSS | **KEEP** (long-standing reference) |
| ✓ [ui.land resources](https://ui.land/resources) (Emil Kowalski) | Curated design-engineering resource list | **KEEP** |
| [Fancy Components](https://www.fancycomponents.dev/) | MIT animated components | **KEEP** (see effects-and-components) |

### Courses (paid, high signal)
- [animations.dev](https://animations.dev/) (Emil Kowalski). The source philosophy behind his skills. **KEEP** for motion.
- [Devouring Details](https://devouringdetails.com/) (Rauno). Interaction craft. **KEEP**.
- [Interface Craft](https://www.interfacecraft.dev/) (Josh Puckett). **KEEP**.
- [svg.guide](https://www.svg.guide/) (Nanda Syahrasyad). Interactive SVG animation. **KEEP**.
- [UI Engineering 101 for Designers](https://maven.com/pixeljanitor/uiengineering-101-for-designers). **WEAK** (cohort timing).
- [designengineer.xyz engineering track](https://www.designengineer.xyz/course/engineering-track) (Karl Koch). **WEAK** (not opened).

### Tools
- ✓ [Agentation](https://agentation.dev/). Annotate elements for agents (selectors, source path, computed styles, animation pause). Free for individuals/internal use. **KEEP**.
- [Remotion](https://www.remotion.dev/). Programmatic video in React (product demo videos). **KEEP**. Licence: free for individuals/small teams, a company licence above a threshold, so check.
- [Before and After](https://www.jm.sv/before-and-after). Before/after screenshots in PRs, good for ui-audit evidence. **WEAK** (not opened).
- [Locale](https://joshpuckett.me/locale) (preview local fonts). [CMYK Emulator](https://cmyk.danielpetho.com/). Niche. **WEAK**.

### Pattern libraries
- [Mobbin](https://mobbin.com/) (iOS/web flows). **KEEP**.
- [aiverse.design](https://www.aiverse.design/browse) and [shapeof.ai](https://www.shapeof.ai/) (AI-UX patterns). **WEAK→KEEP** for AI-product UI.

### Role definition & perspective (context, not technique)
Maggie Appleton "Design Engineers", Kathryn Gonzalez "Attributes of a Design Engineer", Vercel "Design Engineering at Vercel", Yann-Edern Gillet "Rosetta Stone of Design Engineering", Trys Mudford, Marcel Wichmann. **KEEP as background.** Flo's own three notes are worth internalising:
1. **Material understanding beats tool proficiency.** Think in the final medium.
2. **Collapse the handoff.** Idea → validation time shrinks when design and build are one person.
3. **Prototyping is visible, but foundations** (systems, components, patterns) are the deeper value.

### Communities
designengineer.io (jobs and resources), @designengclub on X. Low priority for agents.
