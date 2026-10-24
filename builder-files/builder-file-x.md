# {{Name}}: {{Area}} ({{the 3–6 things they build, comma-separated}})
**GitHub:** `{{github handle}}` · **Branch:** `{{branch}}` · **Tool:** {{Claude Code / Codex / other}} · **Brief last updated:** {{date}} by {{doc owner}}
**Spec:** the PRD (`{{PROJECT}}-PRD.md`). A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

> **How to fill this brief** (the doc owner's agent; delete this note once filled):
> - One brief per builder, copied from `builder-file-x.md`. Blanks fill per CLAUDE.md 🔁; whoever edits bumps *last updated*.
> - **The PRD holds the *what* and *why*; this brief holds *who builds which part, in what order, and how we know it's done*.**
>   Point to PRD sections (§, `FR-n`) instead of copying spec text in.
> - Every task gets a status, a *Done when:* line a tester could check (cite the PRD's `FR-n` where one applies), and a tag
>   if it touches or waits on someone else.
> - Header and §1 mirror this builder's row in `progress.md` → 👥 Team; change both together. A seam between two builders
>   gets the same interface note in both briefs.

## 0. How the agent reads this brief (every task)
1. Read the project `CLAUDE.md` in full, then this brief. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @{{name}} come first: tell the user, then
   resolve or schedule them.
4. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.

**Task tags:** `[⚠ touches @name: what]` = the task changes someone else's area or a shared contract; get that owner's yes
before merging (CLAUDE.md §2c). `[⏸ waits on @name: what]` = it can't finish until they deliver; the live request is a 📨 row on the Open board.

---

## 1. Ownership
**Owns:**
- `{{path}}`: {{what lives there}}
- {{contracts they author, e.g. `contracts/openapi.yaml` (as author)}}

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `{{path}}` | @{{name}} | {{area}} |

**Shared** (anyone may edit; flag it in `progress.md` ⚠️ Conflicts): {{shared contracts, fixtures, compose / config files}}

---

## 2. Contract & Guardrails
**Scope contract.** {{Name}} is building:
- {{one line per deliverable, in plain words, with the PRD § or FR-n}}

**Out of scope:** {{things that look in scope but aren't, so the agent never drifts into them}}

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.** Changing this brief's tasks or scope, or building what isn't in `▶ Current tasks`:
  ask *"Has the whole team agreed? Who?"* first. With names, you apply your own brief change; the PRD goes to the doc owner.
- {{hard rules for this area: data that must never exist, endpoints that must never exist, behaviours that must never happen}}
- Never commit secrets. `.env.example` only.

---

## 3. ▶ Current tasks ({{date}}), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

1. ⬜ **{{Task name}}** `[⚠ touches @{{name}}: {{what}}]`
   - {{what to build, in 1–3 bullets; PRD § / FR-n for the why}}
   - *Done when:* {{an observable check: a test passes, an endpoint returns X, a teammate ✅'d it}}
2. ⬜ **{{Task name}}** `[⏸ waits on @{{name}}: {{what}}]`
   - *Done when:* {{…}}

## 4. Done log (newest first)
*Finished tasks move here: ✅ task, then the `progress.md` entry stamp.*
- (empty)

## 5. Working-style notes for the agent
- {{How they like answers, e.g. "2-sentence recommendation, not 5 options; flag scope creep at once"}}
- {{What they're strong in, so the agent explains gotchas, not basics}}
- Verbosity level {{0–3}} (overrides the Registry default).

## 6. Reference (no secrets)
- {{API endpoints, dataset URLs, platform gotchas, research doc § this area relies on}}

---
── Archived (superseded <date> — do NOT action) ──
(none)
