# Accessibility checklist: WCAG 2.2 AA (+ notable AAA)

Target: **WCAG 2.2 AA** (= ISO/IEC 40500:2025). Legal context, if the user asks: the EU Accessibility Act has applied since 28 Jun 2025 via EN 301 549 (V3.2.1 = WCAG 2.1 AA; V4.1.1 = WCAG 2.2 AA, published Sep 2026, pending Official Journal citation). US ADA Title II requires WCAG 2.1 AA by 26 Apr 2027 (large public entities) / 26 Apr 2028 (smaller). Auditing to 2.2 AA covers all of these. Don't give legal advice; state the standard tested.

Most common real-world failures (WebAIM Million 2026, home pages): low-contrast text 83.9%, missing alt 53.1%, missing form labels 51.0%, empty links 46.3%, empty buttons 30.6%, missing `lang` 13.5%. Check these first. Pages with ARIA averaged *more* errors (correlation, not cause: bad ARIA is common).

Legend: SC · level · how to test · default severity (see `proposal-format.md`).

## Perceivable
| SC | Check | Test | Sev |
|---|---|---|---|
| 1.1.1 A | Meaningful images have alt that conveys the information; decorative `alt=""`; icon buttons named; complex charts have a text equivalent | DOM/a11y tree; turn images off | P0 if it blocks a task, else P1 |
| 1.2.x A/AA | Video captions; audio transcript; audio description for essential visual-only info | Play media | P1 |
| 1.3.1 A | Structure is in markup: headings, lists, tables with `<th>`, labels, landmarks, fieldset/legend for groups | a11y tree, heading list | P1 |
| 1.3.2 A / 2.4.3 A | Reading and focus order match visual order (watch CSS `order`, absolute positioning, `row-reverse`) | Tab + screen reader | P1 |
| 1.3.4 AA | Works in portrait and landscape | Rotate | P2 |
| 1.3.5 AA | Personal-data inputs have correct `autocomplete` tokens | Inspect | P1 |
| 1.4.1 A | Colour isn't the only cue (errors, status, required, links in text need underline or 3:1 vs text + another cue) | Greyscale screenshot | P1 (P0 for safety alerts) |
| 1.4.3 AA | Text ≥ 4.5:1; large text (≥ 24 px, or ≥ 18.66 px bold) ≥ 3:1; includes placeholders, text over images, every theme/state | `scripts/contrast_check.py`, detector | P1 (P0 < 3:1 on core body text) |
| 1.4.4 AA | Text resizes to 200% with no loss (no `vw`-only type, no `user-scalable=no` / `maximum-scale=1`) | Browser zoom / text-only zoom | P1 |
| 1.4.10 AA | Reflow at 320 CSS px (= 1280 at 400%): no two-dimensional scrolling except data tables, maps, code | Resize to 320 px | P1 (P0 if content is lost) |
| 1.4.11 AA | UI component boundaries, states, focus indicators and meaningful graphics ≥ 3:1 vs adjacent colours | contrast_check on borders/icons/chart marks | P1 |
| 1.4.12 AA | Survives line-height 1.5, paragraph 2×, letter 0.12em, word 0.16em without clipping | Inject the text-spacing bookmarklet / CSS | P2 |
| 1.4.13 AA | Hover/focus popups: dismissible (Esc), hoverable, persistent | Hover tooltips/menus | P2 |
| 1.4.6 AAA | 7:1 text (worth it for long reading, older or low-vision audiences, safety alerts) | — | P3 advisory |

## Operable
| SC | Check | Test | Sev |
|---|---|---|---|
| 2.1.1 A / 2.1.2 A | Everything works by keyboard; no traps; custom widgets follow ARIA APG keyboard patterns (arrows in tabs/menus/radios, Esc closes) | Keyboard only | P0 |
| 2.1.4 A | Single-key shortcuts can be turned off/remapped or only work on focus | Try shortcuts | P2 |
| 2.2.1 A | Time limits adjustable/extendable (≥ 20 s warning) | Session/OTP flows | P1 |
| 2.2.2 A | Auto-moving/scrolling/blinking content > 5 s can be paused; auto-updating content can be paused (no 5 s exception) | Carousels, marquees, tickers | P0 if no control on a carousel/marquee, else P1 |
| 2.3.1 A | Nothing flashes > 3×/s | Inspect animation | P0 |
| 2.3.3 AAA | Interaction-triggered motion can be disabled: honour `prefers-reduced-motion` (replace scale/pan/parallax with fade or none) | Emulate reduced motion in devtools | P1 for large/vestibular motion (practical baseline even though AAA), else P2 |
| 2.4.1 A | Skip link or landmarks to bypass repeated blocks | Tab from page top | P2 |
| 2.4.2 A | Unique, descriptive `<title>` (SPA: updates on route change) | Inspect | P1 |
| 2.4.4 A | Link purpose clear from text or context | Links list in screen reader | P2 |
| 2.4.6 AA | Headings and labels describe their content | Read | P2 |
| 2.4.7 AA | Visible focus on every focusable element | Tab | P0 if missing site-wide, else P1 |
| **2.4.11 AA** (new) | Focused element not **entirely** hidden by sticky headers/footers, cookie bars, chat widgets | Tab with sticky UI present; fix with `scroll-padding` | P1 |
| 2.4.13 AAA (new) | Focus indicator ≥ 2 px perimeter-equivalent and ≥ 3:1 change (inset rings need ~3 px; dashed ~4 px) | Measure | P3 advisory; recommend as the target |
| 2.5.1–2.5.4 A | Multi-point/path gestures have single-pointer alternatives; actions fire on up-event; visible label text is in the accessible name; motion-actuated features have UI alternatives | Try | P1 |
| **2.5.7 AA** (new) | Dragging (sliders, sortable lists, maps, kanban) has a single-pointer alternative (buttons, inputs) | Try without dragging | P1 |
| **2.5.8 AA** (new) | Targets ≥ 24×24 CSS px, **or** a 24 px circle centred on each small target doesn't overlap another target/circle. Exempt: inline text links, equivalent control elsewhere, browser-default controls, essential | Measure bounding boxes | P1 |
| 2.5.5 AAA | 44×44 px; recommend for primary and touch actions (Apple 44 pt, Material 48 dp, ~1 cm research floor) | — | P3 advisory |

## Understandable
| SC | Check | Test | Sev |
|---|---|---|---|
| 3.1.1 A / 3.1.2 AA | `<html lang>` valid BCP 47; `lang` on passages in other languages | Inspect | P1 / P2 |
| 3.2.1 A / 3.2.2 A | Focus or input doesn't trigger unexpected context changes (auto-submit, auto-navigate on select) | Try | P1 |
| 3.2.3 AA / 3.2.4 AA | Navigation and identically-functioning components consistent across pages | Compare pages | P2 |
| **3.2.6 A** (new) | Help mechanisms (contact, chat, FAQ link) in the same relative order on every page that has them | Compare pages | P2 |
| 3.3.1 A / 3.3.3 AA | Errors identified in text and with a suggested fix | Submit bad data | P1 |
| 3.3.2 A | Labels or instructions for inputs (formats, required) | Read form | P1 |
| 3.3.4 AA | Legal/financial/data-deleting submissions: reversible, checked, or confirmed | Try | P1 |
| **3.3.7 A** (new) | Info already entered in the same process is auto-filled or selectable (except security/essential) | Walk multi-step flows | P1 |
| **3.3.8 AA** (new) | No cognitive function test to log in (memorising, transcribing, puzzles) unless an alternative or mechanism exists; **blocking paste or password managers fails** | Try paste, password manager | P1 |
| 3.3.9 AAA | Same, without object-recognition / personal-content exceptions | — | P3 advisory |

## Robust
| SC | Check | Test | Sev |
|---|---|---|---|
| 4.1.2 A | Every control has name, role, state/value exposed (`aria-expanded`, `aria-pressed`, `aria-checked`, `aria-current`); no empty links/buttons; no `aria-hidden`/`role="presentation"` on focusable elements | a11y tree, axe | P0 on primary controls, else P1 |
| 4.1.3 AA | Status messages announced without moving focus: live region present (empty) in the DOM *before* the update, not `display:none`; polite by default; ≤ ~2 regions; no interactive controls inside transient toasts | Screen reader | P1 |
| (4.1.1 Parsing) | Removed in 2.2 as obsolete. Don't report HTML validation errors as WCAG failures (they may still be bugs) | — | — |

## Semantics: native first
- `<button>` for actions, `<a href>` for navigation, `<label>`, `<fieldset>/<legend>`, `<dialog>` (with `showModal()`), `<details>`, `popover`. A `role` adds **no** keyboard behaviour: `div role="button"` needs tabindex, Enter **and** Space handling. Flag it (P1) and propose the native element.
- "No ARIA is better than bad ARIA." Don't add `aria-label` that contradicts visible text (2.5.3), redundant roles, or `aria-live` on large regions.
- Modals: focus moves in, is contained (`showModal()` or `inert` on the background), Esc closes, focus returns to the trigger, background not reachable by screen reader.
- Focus styling: use `:focus-visible`; prefer `outline` (survives Windows forced-colours mode; `box-shadow` alone disappears there). `outline: none` with no replacement fails (F78).

## Motion, vestibular, flashing
What reduced motion should do (replace travel with fades, keep feedback, the no-motion-first pattern, the global-reset backstop) is owned by `motion/references/accessibility.md`; audit against it and grade with the rows above. Motion quality itself → `motion-review`.
- A global `*` duration reset used as the *whole* strategy: P3 "prefer per-component handling" (P2 if it breaks something, e.g. kills meaningful fades).
- Motion as the only feedback (a state change shown only by animation, no colour/icon/label cue): P1 if it carries status, else P2.
- Also respect `prefers-contrast: more`, `prefers-reduced-transparency`, `forced-colors: active` (test in Windows High Contrast). Shadow-only rings and edges vanish there: keep a `1px solid transparent` border under them.

## Myths: never assert these
- "WCAG requires 16 px minimum font." False: no minimum size; 1.4.4 requires 200% resize.
- "An overlay/accessibility widget makes the site compliant." False (Overlay Fact Sheet; FTC order vs accessiBe 2025). If an overlay is present, report it as a risk, not a fix.
- "Lighthouse 100 / zero axe errors = accessible." False: automated rules cover a minority-to-half of issues.
- "Max 7 nav items (Miller's 7±2)." Miller studied recall; menus are recognition. Not a rule.
- "APCA is the WCAG 3 standard." False: removed from the draft in 2023; WCAG 3 contrast method undecided. Use APCA only as an advisory extra.
