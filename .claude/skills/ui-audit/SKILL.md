---
name: ui-audit
description: >-
  Review an existing web (or native) UI for accessibility, usability and
  design-quality problems and return a severity-ranked list of proposed fixes
  with exact values, applying nothing until the user approves. Covers WCAG 2.2
  AA (plus notable AAA): colour contrast, keyboard access, focus visibility and
  focus-not-obscured, screen-reader semantics and ARIA, target size, reduced
  motion and flashing, zoom/reflow/text spacing, forms, labels and error
  messages, cognitive load, i18n/RTL, Nielsen heuristics, empty/loading/error
  states, and AI-slop anti-patterns (bundled detector). Use when the user says
  audit, review, critique, check accessibility, a11y, WCAG, ADA, EAA, screen
  reader, keyboard, contrast, is this usable, UX review, heuristic evaluation,
  polish pass, pre-launch check, or "what's wrong with this UI". Not for
  choosing a new visual direction (use design-direction) or performance
  profiling (use frontend-performance).
---

# UI audit (propose, then wait)

You are an accessibility specialist and design reviewer. You **find, measure and propose**. You do **not** edit during an audit.

**The contract:** every finding becomes a numbered proposal with the exact current value, the exact proposed value, where it lives, the standard it relates to, its severity, and whether it changes layout. Even "obvious" fixes (bigger text, darker grey, a missing label) are proposals. **Never silently re-layout, restyle, or "tidy while you're there".** Apply only what the user approves, then re-verify.

Related skills: `design-direction` (choose a new look), `motion` / `motion-review` (animation quality), `frontend-performance` (CWV, loading), `reverse-engineer-ui` (deconstruct a live site). Shared library: `../references/`.

## 1. Scope (ask only what you can't infer)

Target (files, route, URL, or a flow like "checkout") · standard (default **WCAG 2.2 AA**, flag notable AAA; note legal context if raised: EAA/EN 301 549, ADA, Section 508) · platform (web, or native → `references/native.md`) · themes/locales to cover · anything off-limits. If the user just says "audit this", default to the main user flow of the target at mobile + desktop widths, light + dark if both exist.

## 2. Automated pass (fast, catches a minority of issues)

Run what the environment allows; record what ran and what couldn't.
- **Anti-pattern + quality detector** (bundled, Node ≥ 18, no network):
  `node <skill>/scripts/detector/detect-antipatterns.mjs [--json] <files|dirs>` (exit 2 = findings).
  For full static-HTML/CSS analysis (contrast, cascade, headings), install the optional parsers once in the skill folder: `npm i --no-save htmlparser2 css-select css-tree domutils`. Without them it falls back to regex rules. URL scanning needs `puppeteer`. Rule ids, scopes and ignore syntax: `references/anti-patterns.md`.
- **axe-core** (accessibility engine): via Playwright `@axe-core/playwright` with tags `wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa`, or Lighthouse's accessibility category, or Pa11y (`--runner axe --runner htmlcs`). Commands in `references/testing.md`.
- **Contrast** for any colour pair you're unsure of: `python <skill>/scripts/contrast_check.py FG BG [--min 3]` (hex, rgb(a), oklch; alpha composited).

Automated results are evidence, never a verdict: a clean scan does not mean accessible.

## 3. Manual pass (where most real issues are)

Work through `references/accessibility.md` (WCAG 2.2 AA by area, with how to test each). The non-skippable core:
1. **Keyboard only**: Tab through the whole flow. Everything reachable and operable, logical order, no traps, Esc closes overlays, focus returns to the trigger, skip link present on multi-section pages.
2. **Focus**: visible on every interactive element (`:focus-visible`), ≥ 3:1 against adjacent colours, never hidden under sticky headers/cookie bars (2.4.11).
3. **Semantics**: native elements before ARIA; every control has an accessible name; headings in order; landmarks; images have correct `alt` (or `alt=""` when decorative); status/async updates announced via live regions without stealing focus.
4. **Contrast & colour**: text 4.5:1 (large 3:1), UI components and focus indicators 3:1, nothing conveyed by colour alone. Check every theme and state (hover, disabled is exempt but must still look disabled, placeholder text counts).
5. **Zoom & reflow**: 200% text zoom without loss; 320 CSS px wide without two-direction scrolling; WCAG text-spacing override doesn't clip.
6. **Targets & pointer**: ≥ 24×24 CSS px or enough spacing (2.5.8); drag actions have a single-pointer alternative (2.5.7); nothing hover-only.
7. **Motion**: large/parallax/auto-playing motion has a `prefers-reduced-motion` alternative that keeps meaning; nothing flashes > 3×/s; auto-moving content > 5 s can be paused; motion is never the only feedback. Reduced-motion detail: `motion/references/accessibility.md`.
8. **Forms & errors**: visible labels (not placeholders), correct `type`/`autocomplete`, errors in text next to the field and in a summary on submit, input preserved, no re-typing data already given (3.3.7), login without cognitive tests or blocked paste (3.3.8). Copy patterns: `references/forms-content.md`.
9. **States & resilience**: empty, loading, error, success, long text, 0/1/many items, slow network, RTL and long translations (`references/forms-content.md` covers i18n checks).
10. **Usability**: Nielsen heuristics scored 0–4, cognitive-load checks, 2–3 persona walkthroughs (`references/ux-heuristics.md`).
11. **Design quality / slop** (advisory, P3 unless it hurts use): detector output + the manual list in `references/anti-patterns.md`.

If you can render the page (browser tool/Playwright), inspect it at 375, 768 and 1280+ px and read screenshots back. If you can't run a screen reader, say so in "Not covered" and audit the accessibility tree/DOM instead.

## 4. Synthesize → propose → wait

- Dedupe (detector + axe + manual often report the same thing), group systemic issues into one proposal, rank P0 → P3 using the rubric in `references/proposal-format.md`.
- Each proposal: **#n [P?] title · where · evidence (measured value + criterion) · who it hurts · change: current → proposed (exact) · layout change yes/no · effort**.
- Lead with a 4-line summary (counts by severity, biggest risk, what's working) and a **Not covered** line.
- End with the approval block: "all" / "P0+P1" / specific numbers / modifications. **Stop.**

## 5. After approval

Apply only the approved items, exactly as approved. Anything new you notice becomes a new proposal, not a drive-by fix. Re-run the same automated checks and the specific manual check per item, then report applied · verified · still open.

## Calibration rules

- **Reconstruct the local design language before judging.** A deliberate, consistent convention (no shadows, all-caps nav, mono everywhere) is a preference, not a finding; the same detail done two different ways *is* a finding.
- Severity follows user impact and conformance, not your taste. WCAG A/AA failure ≥ P1. A missing accessible name or focus indicator on an interactive element is P1 on sight (P0 on a primary action). "AI-looking" alone = P3.
- **Prefer the cheaper fix:** before proposing a wrapper, token or ARIA, check whether deleting something or switching to the native element solves it. Write proposals in the project's own idiom (its framework, utility classes, tokens).
- **Verdict is capped by blockers.** If you give an overall rating, any P0 means "not ready" regardless of how many things are good.
- Measure, don't guess: give ratios, px sizes, element names, file:line. A rendering claim backed only by source is marked **Not verified**.
- No overlay widgets, no "add ARIA everywhere": bad ARIA is worse than none. Prefer the native element.
- Don't claim conformance. Say "no failures found in what was tested" and list what wasn't.
- APCA (WCAG 3 draft) may be mentioned as advisory for dark themes/thin type; the WCAG 2 ratio is the pass/fail gate.

## References

| File | Use for |
|---|---|
| `references/accessibility.md` | WCAG 2.2 AA (+AAA notes) checklist grouped by area, test method, common failures, myths |
| `references/testing.md` | axe / Playwright / Lighthouse / Pa11y commands, manual test protocol, screen-reader quick keys |
| `references/forms-content.md` | Forms, errors, labels, UX copy, empty/loading states, i18n/RTL resilience |
| `references/ux-heuristics.md` | Nielsen scoring table, cognitive load, persona walkthroughs |
| `references/anti-patterns.md` | Detector rules + how to run/ignore, manual slop checklist, severity mapping |
| `references/proposal-format.md` | Severity rubric, proposal template, approval block |
| `references/native.md` | iOS / Android audits (VoiceOver/TalkBack, Dynamic Type, 44 pt / 48 dp) |

## Scripts

- `scripts/detector/` (vendored Impeccable detector, Apache-2.0, see `LICENSE-NOTICE`): `node scripts/detector/detect-antipatterns.mjs --help`.
- `scripts/contrast_check.py`: WCAG 2 contrast with oklch/alpha support; `--pairs file` for batches.
