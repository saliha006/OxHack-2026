# Proposal format + severity rubric

The audit output is a **proposal list**, not a changelog. Nothing in it has been applied.

## Severity rubric (assign exactly one)

| Level | Meaning | Typical examples |
|---|---|---|
| **P0 Blocker** | A user group cannot complete a core task, or a safety/legal-critical failure on a primary flow. | Keyboard trap; form can't be submitted by keyboard; unlabeled primary button for screen readers; critical alert conveyed by colour only; body text < 3:1 on a core flow; content lost at 320 px width. |
| **P1 Major** | WCAG 2.2 A/AA failure, or a usability issue most users will hit. | Normal text 3–4.49:1; no visible focus; targets < 24×24 px without spacing; errors not tied to fields; large motion with no reduced-motion path; missing empty/error state on a primary view. |
| **P2 Minor** | Real, but with a workaround or a narrow reach. | Inconsistent terms; placeholder as the only format hint; truncation with no way to read the full text; heading level skip on a secondary page. |
| **P3 Polish / advisory** | No measurable user impact: taste, consistency, "AI-slop" tells, AAA-only gaps. | Overused font; side-stripe card borders; gradient text; uniform spacing. |

Tie-breakers: fails a WCAG A/AA criterion → at least P1. Would a user contact support about it → at least P1. Detector `slop` findings are **P3** unless they also cause an accessibility or comprehension failure (then grade by that failure).

## Output skeleton

```markdown
# UI audit: <target> (<date>)
Scope: <files/URL/flows> · Standard: WCAG 2.2 AA (+ notable AAA) · Platform: <web|ios|android>
Method: <automated tools actually run> + <manual checks actually done>
Not covered: <e.g. no screen reader available; dark theme not inspected; no real device>

## Summary
- P0: n · P1: n · P2: n · P3: n
- Biggest risk: <one sentence>
- Keep: <2–3 specific strengths>

## Proposals (nothing applied yet)

### #3 [P1] Body text contrast too low on cards
- Where: `src/components/Card.css:14` (`.card p`)
- Evidence: `#9a9a9a` on `#ffffff` = 2.85:1, needs 4.5:1 (WCAG 1.4.3)
- Who it hurts: low-vision users; anyone on a phone outdoors
- Change: `color: #9a9a9a` → `color: #595959` (7.0:1), or use token `--color-ink-muted`
- Layout change: no · Visual change: text darker · Effort: XS
```

Rules for every proposal:
- **Exact values**, current → proposed (colour, px/rem, attribute, string). "Increase contrast" is not a proposal; `#9a9a9a → #595959 (7.0:1)` is.
- **Location**: file:line or selector, or URL + element description.
- **Standard**: WCAG SC number, heuristic, or rule id; advisory items say "advisory".
- **Layout flag**: say whether the change moves, resizes, or reflows anything. A re-layout is always its own proposal, never folded into a "small fix".
- **Group systemic issues**: "replace 14 hard-coded greys with tokens" (instances listed) beats 14 proposals.
- **Offer the alternative** when there's a real design choice (darken the text *or* lighten the background).

## Approval block (end every audit with this)

```
Reply with what to apply: "all" · "P0+P1" · numbers ("1, 3, 5") · or "3 but use <value>".
Nothing changes until you choose. After applying I'll re-run the same checks and show before/after.
```

## After approval
1. Apply **only** the approved numbers, exactly as written (or as the user modified them).
2. No drive-by edits. Anything new you notice becomes a new proposal.
3. Re-run the automated checks plus the specific manual check for each fixed item.
4. Report: applied (diff summary) · verified (how) · still open.
