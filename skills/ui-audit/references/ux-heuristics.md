# UX heuristics, cognitive load, personas

Use for the "is it usable and clear" half of the audit. Score honestly; most shipped interfaces land 20–32/40.

## Nielsen's 10 heuristics — score 0–4 each

| # | Heuristic | Look for | 0 → 4 |
|---|---|---|---|
| 1 | Visibility of system status | Loading/progress, save confirmation, current location, inline validation | No feedback → every action confirms |
| 2 | Match the real world | User's words, not internal jargon; natural order; familiar icons | Jargon → user's language throughout |
| 3 | User control & freedom | Undo, cancel, back, clear filters, escape multi-step flows | Trapped → undo/cancel everywhere |
| 4 | Consistency & standards | Same term/action/look means the same thing; platform conventions | Stitched-together → one system |
| 5 | Error prevention | Constraints, good defaults, confirm only irreversible actions, autosave | No guardrails → hard to err |
| 6 | Recognition over recall | Visible options, labelled icons, recent items, no cross-screen memory load | Memorise paths → all discoverable |
| 7 | Flexibility & efficiency | Shortcuts, bulk actions, sensible defaults that experts can skip | One rigid path → accelerators |
| 8 | Aesthetic & minimalist | Every element earns its place; clear hierarchy; no decorative noise | Everything competes → focused |
| 9 | Recover from errors | Plain-language cause + fix, near the field, input preserved | Codes/blank → pinpoints + preserves |
| 10 | Help & documentation | Contextual help at decision points, task-oriented, findable | None → right help at the right moment |

Bands: 36–40 excellent · 28–35 good · 20–27 needs work · 12–19 poor · 0–11 critical. Report the table, then convert each low score into concrete proposals.

## Cognitive load checks
- **One primary action per view.** Count competing primary-styled buttons; more than one is a finding.
- **Chunking.** Long forms and settings are grouped under headings; related items are adjacent (proximity), unrelated ones separated.
- **No memory bridges.** Info needed on step 3 is visible on step 3, not only on step 1.
- **Plain language.** Domain terms defined inline; instructions before the field, not after.
- **Progressive disclosure** for advanced options; but never hide what most users need.
- **Choice count is a smell, not a law.** Long option lists aren't wrong by themselves (choice-overload effects are small and context-dependent in meta-analyses); flag them when there's no grouping, default, search or recommended option.
- **Interruptions.** Modals, toasts and auto-advancing carousels that steal attention mid-task are findings. Time limits need a way to extend (WCAG 2.2.1).
- **Consistent help** (WCAG 3.2.6): help/contact mechanisms in the same relative place on every page that has them.

## Persona walkthroughs (pick 2–3 that fit)

Walk the primary task as each persona and report what broke, by element name.

| Persona | Tests | Red flags |
|---|---|---|
| **Keyboard + screen-reader user** | Whole flow with Tab/Shift-Tab/Enter/Space/Esc/arrows; heading & landmark nav; announcements | Click-only controls, invisible focus, unlabeled buttons, colour-only status, silent async updates |
| **First-timer** | Is the first action obvious in 5 seconds? Labels literal? | Icon-only nav, jargon, no help, no success confirmation |
| **Power user** | Core task speed, shortcuts, bulk actions, skippable onboarding | Forced tours, unskippable animation, one-at-a-time where batch is natural |
| **Distracted mobile user** | One thumb, interruptions, slow network | Primary actions out of thumb reach, state lost on tab switch, tiny targets, heavy pages |
| **Stress tester** | 0 / 1 / 1000 items, very long names, emoji/RTL, double-submit, refresh mid-flow | Silent failures, data loss on refresh, overflow, raw error dumps |
| **Older / low-vision user** | 200% zoom, larger default text, high contrast | Fixed px text, light grey text, small targets, hover-only info |

Only derive extra project-specific personas from real audience info the user gave; never invent audience facts.
