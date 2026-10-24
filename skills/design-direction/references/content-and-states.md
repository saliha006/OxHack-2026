# Content, states and forms (building them right)

The review-side checklist for the same topics is `ui-audit/references/forms-content.md`. Evidence: `Claude instructions/research-ledger.md` §3 design + audit → "UX writing & forms".

## Copy is part of the design
- **Specific beats impressive.** Replace "Unlock the power of…", "seamless", "elevate", "revolutionize", "next-generation" with the concrete thing a competitor couldn't claim. No invented numbers, logos or testimonials.
- **Plain language:** common short words, sentences under ~25 words, about a reading age of 9 (that means *simple words*, not childish tone). Define unavoidable jargon inline.
- **Sentence case** in UI (buttons, headings, labels). Consistent terms: pick "Sign in" or "Log in", "Delete" or "Remove", and never vary them.
- **Buttons** = verb + object, saying exactly what happens: "Save changes", "Send invite", "Delete 3 files". Not "Submit", "OK", "Yes/No", "Click here". The resulting toast echoes it ("Changes saved").
- **Links** make sense out of context ("Download the 2026 price list (PDF, 2 MB)").
- **Alt text** states the information, not the picture ("Sales rose 40% in Q4"); decorative images get `alt=""`.

## States to design (every data view, every control)
| State | Build it as |
|---|---|
| Default / hover / focus-visible / active / disabled | All five, consistent across the product. Focus is never removed without a visible replacement. |
| **Loading** | < 1 s: show nothing. ~2–10 s: spinner for one module, skeleton for a full page. > 10 s: determinate progress + estimate + cancel. Don't claim skeletons are "faster"; evidence is mixed. |
| **Empty** | Say what will be here and why it's empty, plus one primary action ("No invoices yet. Create your first invoice"). Separate first-use, no-results (suggest clearing filters) and no-permission empties. Never show "No data" while still loading. |
| **Error** | What happened + how to fix it, in plain words, next to the source, input preserved, retry where it makes sense. Icon + text, not colour alone. |
| **Success** | Confirm what happened and what happens next; brief. |
| **Edge content** | 0 / 1 / many items, very long names, missing images, slow network, offline. |

## Error messages (formula)
- Field errors reuse the label's words and say how to fix it: "Enter your email address", "Enter an email address in the correct format, like name@example.com", "Date of birth must be in the past".
- Avoid "invalid", "error occurred", "oops", "please/sorry" padding, error codes, and blaming ("You entered…").
- No jokes in routine errors. Tone can be warm, never cute, when the user is stuck.
- On submit: an error summary at the top linking to each field, plus inline messages. Never clear what the user typed.

## Forms
- **One column.** Only tightly related short fields share a row (postcode + city, expiry + CVC).
- **Visible label above every field.** Placeholders are not labels (they vanish, look pre-filled, often fail contrast). Hints go in persistent text under the label.
- Ask fewer things. Then mark fields: long forms mark both required (`*` explained) and "(optional)"; short or one-question-per-page forms mark only "(optional)".
- Correct `type` / `inputmode` / standard `autocomplete` tokens (`email`, `tel`, `name`, `street-address`, `postal-code`, `one-time-code`, `new-password`, `current-password`, `cc-number`, `bday-day`…). Never blanket `autocomplete="off"`. Don't block paste (passwords, codes).
- **Validate on blur** (or when the input reaches a fixed length) or **on submit** (GOV.UK's choice: kinder to slow typists). Never while the user is still typing, never on empty untouched fields. Once an error shows, re-check on input and clear it the moment it's valid.
- Memorable dates (birthdays): three fields Day / Month / Year. Date pickers only for near-term scheduling, always with a typed fallback.
- Don't ask for information already given in the same flow (WCAG 3.3.7). Logins: allow paste and password managers; no puzzles (3.3.8).
- Destructive actions: prefer **undo**; confirm only irreversible or costly actions, naming the object and consequence with specific buttons ("Delete project" / "Keep project").

## Onboarding
- Goal: first real value fast, not a tour of features. Teach in context (empty states, inline hints) over upfront carousels.
- Every tour skippable and replayable; don't repeat it once dismissed; don't block the UI.
- Ask only what's needed to start; collect the rest later.

## Internationalisation-ready by default
- Leave room for +30–40% text length; no fixed-width buttons or labels. Use CSS logical properties (`margin-inline-start`, `padding-inline`) so RTL works with `dir="rtl"`.
- `lang` on `<html>` (and on inline passages in other languages). Format dates, numbers and currency with `Intl.*`. Full sentences as single translatable strings; use plural-aware i18n functions, not `count + 's'`.
