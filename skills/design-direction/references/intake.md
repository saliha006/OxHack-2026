# Intake: the questions to ask before designing

Ask **one round, 3–5 questions**, using the harness's question tool if it has one; otherwise ask in chat and stop. Skip any question the brief, the codebase or an existing design doc already answers. When one answer is obvious, **assert and confirm** ("This reads as a product dashboard, Quiet Precision direction, light + dark. Confirm or change?") instead of offering a menu.

## The five questions

1. **What is it, and who uses it where?**
   "In a sentence: what is this, who uses it, and in what situation (desk, phone on the go, a stressful moment, browsing for fun)?"
   This decides the **register**: *brand* (the page is the product: landing, marketing, portfolio, editorial) or *product* (the UI serves a task: app, dashboard, settings, tool).

2. **What should it feel like?** Offer the named directions below (pick 1, or "A with a bit of B"). Show 5–7 that fit the register, not all ten.

3. **What already exists?** Logo, brand colours, fonts, a design system (Material, Carbon, Polaris, shadcn, Tailwind theme), a current site. Existing identity wins over fresh taste.

4. **References and anti-references.** "Name 1–3 sites/apps/objects whose feel you like (and what about them), and anything it must NOT look like." Push for specifics ("Linear's density", "a museum caption"), not adjectives ("modern, clean").

5. **Theme and constraints.** Light, dark, or both? Accessibility needs beyond WCAG AA (older users, low vision, safety-critical alerts)? Audience languages / RTL? Fidelity wanted (quick sketch vs ship-ready)?

If the user says "you decide": pick, write the direction contract, and say which choices you'd most want them to sanity-check.

## Named directions (the menu)

Each is a starting point you remix, never a template to clone.

| Direction | Feels like | Typical fit | Signature moves | Risk / avoid for |
|---|---|---|---|---|
| **Quiet Precision** | calm, exact, expensive | SaaS, dev tools, fintech product UI | one neutral family + one sharp accent, tight type scale, hairline structure, generous but disciplined space | goes generic fast; needs one real distinctive move |
| **Data-Dense Pro** | capable, no-nonsense | analytics, admin, ops, trading | compact rem scale, tabular numerals, functional colour only, tables > cards, sticky context | marketing pages; first-time consumers |
| **Technical / Terminal** | engineered, keyboard-first | developer tools, infra, CLI products | mono for code/data only (not costume), dark or paper-white, command palette, dense lists | non-technical audiences: mono reads as costume |
| **Warm Human** | approachable, caring | health, education, community, services | humanist sans or soft serif, real photography of people, rounded-but-not-bubbly, plain warm copy | the cream/beige background reflex; childish rounding |
| **Calm Trust** | clear, official, reassuring | gov, health, insurance, banking | high contrast, big readable type, visible navigation, restrained colour, explicit states (GOV.UK-like) | brand campaigns that need excitement |
| **Bold Brand** | confident, loud, memorable | consumer launches, campaigns, culture | committed or drenched colour, oversized display type, art direction per section | dense product UI; trust-critical flows |
| **Editorial** | considered, literary | publications, long-form, portfolios | strong type pairing, reading measure, rules and grids, image-led | non-editorial briefs (currently over-used lane) |
| **Cinematic Immersive** | dramatic, premium | media, entertainment, high-end product launches | dark stage, large imagery/video, one orchestrated motion moment | text-heavy tasks; low-end devices |
| **Swiss / Grid** | rational, structured | agencies, architecture, events | strict grid, asymmetric layout, neo-grotesk type, flat colour blocks | warm/caring briefs |
| **Soft Tactile** | friendly depth, OS-native | consumer apps, wellness, productivity | layered surfaces, subtle materials, spring-y feedback (via the `motion` skill) | glass everywhere (contrast + "AI look") |

Notes:
- **Finer mode split (Impeccable), if useful:** brand → *Persuade* (marketing: earn the action) or *Experience* (portfolio: the artifact leads); product → *Operate* (app/dashboard: scanability beats expression); *Read* (docs: comprehension first).
- **Register first, direction second.** Product UI favours familiar, consistent patterns (Quiet Precision, Data-Dense, Calm Trust). Brand surfaces can take bigger risks (Bold Brand, Editorial, Cinematic, Swiss).
- **Remix rule:** structure from one direction + one accent idea from another ("Quiet Precision layout with Warm Human photography and copy").
- A direction is not a palette. Colour strategy, type and layout come from the direction **and** the audience.

## The direction contract (write it, ≤ 10 lines, get a yes)

```
Register: product | brand
Direction: <name> (+ <remix>)
Scene: <one sentence: who, where, light, mood>  → decides light/dark
Colour strategy: restrained | committed | full palette | drenched; hue <h> because <reason>
Type: <family/families> because <voice words>; scale ratio <r>
The one bold move: <the single memorable element>
Anti-references: <what it must not look like>
Must-haves: <a11y needs, languages, existing assets>
```

Offer to save it as `design-direction.md` (or into an existing DESIGN.md) so later sessions stay consistent. Don't create the file without a yes.
