# Forms, content, states, i18n: audit checks

Each row: what to check · how · typical severity. Build-side patterns live in `design-direction/references/content-and-states.md`.

## Forms
| Check | How | Sev |
|---|---|---|
| Every input has a programmatic label (`<label for>`, `aria-labelledby`) and a **visible** label | DOM / a11y tree; look at the rendered form | P0 on core flows, else P1 |
| Placeholder used as the only label or only format hint | Render; type into fields | P1 (label) / P2 (hint) |
| Placeholder/hint text contrast ≥ 4.5:1 | contrast_check | P1 |
| Errors: text (not colour-only), next to field, associated (`aria-describedby`), field marked `aria-invalid` | Submit empty + wrong data; inspect | P1 |
| Error summary on submit, links to fields, focus moved to it | Submit with errors | P2 (P1 for long forms) |
| Error wording says how to fix (not "invalid", codes, blame) | Read every message | P2 |
| Input preserved after an error / back navigation | Trigger error, go back | P1 |
| Validation timing: never while the user is still typing or on untouched empty fields. On-blur (Baymard/NN/g) and on-submit (GOV.UK) are both acceptable; once shown, an error clears as soon as the input is fixed | Type slowly, tab through | P2 |
| Correct `type`, `inputmode`, `autocomplete` tokens (WCAG 1.3.5) | Inspect; try on mobile keyboard | P1 for personal data fields |
| Paste allowed (passwords, codes); password managers work; no cognitive puzzles to log in (3.3.8) | Try paste | P1 |
| No re-entry of info already given in the flow (3.3.7) | Walk multi-step flow | P1 |
| Required/optional marked clearly and consistently | Read | P2 |
| Inputs ≥ 16 px computed font-size (iOS zoom) | Computed style | P2 |
| Multi-column layouts for unrelated fields | Visual | P2 |
| Time limits can be extended/turned off (2.2.1) | Session/OTP flows | P1 |
| Destructive action: undo or a specific confirmation; legal/financial submissions reversible, checked, or confirmed (3.3.4) | Try delete/pay | P1 |

## Copy and content
| Check | Sev |
|---|---|
| Buttons say what happens (verb + object); no "Submit / OK / Yes / Click here" | P2 |
| Link text meaningful out of context; no "read more" ×10 | P1 if many identical ambiguous links (2.4.4), else P2 |
| Terminology consistent across screens | P2 |
| Jargon/internal names exposed to users; reading level far above audience | P2 |
| Page `<title>` unique and descriptive (2.4.2) | P1 |
| Headings describe content (2.4.6); one `h1`; no skipped levels used for styling | P2 |
| Generic or fabricated marketing copy, fake proof | P3 (P1 if it misleads) |

## States
| Check | Sev |
|---|---|
| Nothing extra for < 1 s; loading indicator from ~2 s (skeleton for a page, spinner for a module); determinate progress + cancel for > 10 s | P2 |
| Async results/errors announced to screen readers (`role="status"`/`alert`, live region present before update) without stealing focus (4.1.3) | P1 |
| Empty states explain + offer an action; no "No data" during loading | P2 |
| Error states offer recovery (retry, back, contact); no raw stack traces | P1 |
| Double-submit prevented; optimistic updates roll back visibly | P2 |
| Long names / 0 / 1 / 1000 items / missing images handled | P2 (P1 if content is lost) |

## Interface details (Vercel Web Interface Guidelines)
| Check | Sev |
|---|---|
| Ellipsis character `…`, not `...`; loading labels end in `…` ("Saving…") | P3 |
| `font-variant-numeric: tabular-nums` where numbers update or are compared (tables, prices, timers) | P3 |
| `text-wrap: balance` on headings | P3 |
| URL reflects UI state (tabs, filters, pagination, open panels) so back/share/refresh work | P2 |
| `touch-action: manipulation` on controls; `overscroll-behavior: contain` in sheets/modals | P3 |
| Dark theme sets `color-scheme: dark` (native controls, scrollbars) and `<meta name="theme-color">` | P3 |

## i18n and resilience
| Check | Sev |
|---|---|
| `<html lang>` set and correct (3.1.1); `lang` on foreign-language passages (3.1.2) | P1 / P2 |
| Text expansion: +30–40% (German/Finnish) doesn't clip or overlap; no fixed-width text containers | P2 |
| RTL: `dir="rtl"` mirrors layout; physical `left/right` props replaced by logical properties; directional icons flip | P2 (P1 if an RTL locale ships) |
| Dates, numbers, currency via `Intl` / locale-aware formatting | P2 |
| Strings concatenated in code (`"You have " + n + " items"`), English-only plurals | P3 (P2 if localised) |
| CJK/emoji/accents render (UTF-8, font fallback) | P2 |
| Works offline / on slow 3G with sensible messaging (if the product needs it) | P2 |
