# OxHack-2026 — Working Charter

{{One-line pitch: who it helps, what it does, why it's different. Mirror of the PRD §1; change both together.}}

`{{…}}` is a blank: fill it the moment the chat or repo answers it (Self-filling, below). "The PRD", "the vault Log", "the research doc", "the doc owner" are the Registry values.

## 📋 Registry

| Slot | Value |
|---|---|
| Project | **OxHack-2026** (OxHack 26, Oxford Mathematical Institute, 24–25 Oct 2026; tracks: PRD §0 Pending). Team **{{team name}}**; {{who submits}}. Other Claude Code accounts share this folder: never edit a shared doc another session is mid-way through. If another session was here in the last 10 min, use your own worktree (`git worktree add ../OxHack-2026-<name> <branch>`) for anything that edits files |
| Repo | `https://github.com/saliha006/OxHack-2026` · `main`. Builder branches: `progress.md` → 👥 Team |
| Where docs live | **`context` branch** (docs only): `CLAUDE.md`, PRD, event doc, research doc, `builder-files/`, `design/`, `skills/` (`debug`, `no-slop`). `README.md`, `progress.md` and `contracts/*.md` live on `main`. `.claude/` and `scripts/` are never pushed: context's `skills/` unpacks into `.claude/skills/`. All of it is git-ignored on `main`. **Never pushed:** `Research-Context/` (sponsor PDFs, raw inputs, agent notes), `.env*`, secrets. {{Public repo? delete `context` before submission}}. Sync and publish are plain git, see below |
| Vault | `{{path to the Obsidian vault}}` (**{{owner}} only**: `OxHack-2026 — Hub` = status + ▶ START HERE, `— Log` = ADRs, Unconfirmed, ▶ RESUME HERE). No vault → save notes to your memory; send decisions to the doc owner as a `decision` entry + 📨 row |
| Doc owner | **saliha** (Saliha Shoaib, `saliha006`). Teammates: `nate` (Nate Banas, `aldrichbanas07`), `derrick` (Derrick Lim Yong Hao, `RandomGeeb`, collaborator) |
| PRD | `OxHack-2026-PRD.md`: NOW (decisions in force, pending, active tasks) at the top, then the spec |
| Briefs | `builder-files/builder-file-<name>.md` (from `builder-file-x.md`) |
| Event doc | `OxHack-2026-CONTEXT.md`: rules, judging, prizes, schedule |
| Research doc | `OxHack-2026-research.md` (git-ignored on `main`). Raw inputs and agent notes stay in `Research-Context/` |
| Progress doc | `progress.md` (repo root; with `README.md` and `contracts/*.md` the only markdown on `main`): history, 📌 Open board, 👥 Team, 📊 Latest |
| Decisions | Full ADRs: vault Log. Team mirror: PRD → NOW |
| Mirror docs | PRD §0/§1 ↔ top of this file; `builder-file-*` ↔ `progress.md` 👥 Team; vault Hub + Log; `progress.md` 👥 Team + 📊 Latest. Update every mirror when a decision, owner or status changes |
| Run · Test | Decision layer (Python): `uv run pytest --cov=decision`. Bot and data layers: {{run command}} · {{test command with coverage}} |
| Scale | {{demo load / target scale and the box}} |
| Deploy | {{where it runs, how code gets there}}. Platform rules: {{doc or "none"}} |
| Verbosity | **Level 0** (§3) |

**Skills** (`.claude/skills/`, load when the trigger fires): `no-slop` on every code pass, before testing, and before every commit/push/merge · `debug` on every error, failing test or stuck moment (no guess-and-retry outside it). Front-end skills aren't installed; the user names one when it's needed. This file wins over a skill; never edit a skill. `no-slop` fixes only your own diff in your owned paths and reports the rest.

**Ship loop** (detail in §7): code → `no-slop` → tests (happy, edge and failure paths; coverage via Run · Test) → push your branch → `git merge origin/main`, re-test → merge to `main`, push, log in `progress.md`. Never push failing code.

### 🔄 Context sync (session start, and before editing a shared doc)
Plain git, no scripts. The synced commit is kept in `.git/context-synced`.
1. `git fetch -q origin context`. If `git rev-parse origin/context` equals the stamp, you're current.
2. Else tell the user in 1–2 lines **first** (`git log --oneline <stamp>..origin/context`, `git diff --stat <stamp> origin/context`). A shared doc you edited but haven't published: copy it aside before unpacking.
3. Unpack: `mkdir -p .claude && git archive origin/context ':(exclude)skills' | tar -x && git archive origin/context skills | tar -x -C .claude`, then `git rev-parse origin/context > .git/context-synced`. A changed `CLAUDE.md` is already loaded: act on the changed lines only, don't re-read it. Read at least the PRD → NOW and your own brief.
4. Never `git checkout origin/context -- <file>` (it stages docs into `main`). Fetch fails → say so in one line, use local copies.
5. Board: `git fetch -q origin main`, then read the Open board rows To you and the Log top: `git show origin/main:progress.md | sed -n '/Open board/,/^## 👥/p;/^## Log/,+40p'`.

### 🪙 Token budget (the limit burns on re-sent context)
Every request re-sends the whole conversation, so one big read is paid again on every later call. Measured: one prompt of 26 tool calls over a 63k–121k context = 2.45M cache reads. Cost = tool calls × context size, so batch independent calls, keep prompts specific, and keep big text out of the context. What the plan limit meters isn't visible to us.
- **Read only what the task needs:** `Grep`, or `Read` with `offset`/`limit`. `CLAUDE.md` is already loaded. Read the PRD → NOW and your brief once per session. Never read all of `progress.md` (it grows): read the Log top only (sync step 5).
- **Never `Read`:** a research agent's raw output file, a session transcript (`.jsonl`), PDF page images, a whole `Research-Context/` note or the research doc. Grep the research doc by pass number instead.
- **Research agents write to files and report ≤300 words.** At most 4 agents unless the user asks for more.
- **One model and effort per session** (switching re-writes the whole cache). New task → `/clear`; `/compact` past ~100k tokens; don't resume a large session idle over an hour.

### 📤 Publish every shared-doc edit (same turn)
Shared docs = everything on `context`. After any edit (yours, or a local change by the user) publish before ending the turn; several edits → one commit. Plain git, via a worktree of `context` (once: `git worktree add ../OxHack-2026-context -B context origin/context`):
1. Sync first (above), then `git -C ../OxHack-2026-context pull -q --rebase origin context`.
2. Copy the changed docs in (a skill `.claude/skills/<name>/` goes to `skills/<name>/`), then `git -C ../OxHack-2026-context add -A`. Check the diff for secrets.
3. Commit with a short human message (§7), `git -C ../OxHack-2026-context push origin context`. Rejected → pull --rebase, merge by hand, push again; never `force`.
These docs never go to `main` (never `git add -f`). **On `main` the only markdown is** `progress.md`, `README.md`, `contracts/*.md`.

| Change | Who publishes | Gate |
|---|---|---|
| PRD, `CLAUDE.md`, event doc, skills, another builder's brief | **Doc owner** | Plan changes need the team's yes (§2c); a builder posts the agreed change as a 🔀/📨 row To the doc owner |
| Your own brief: tasks, scope, ownership, guardrails | You | Ask "did the whole team agree? who?" (§2c) |
| Your own brief: finished task to Done, blank filled with a stated fact | You | None |
| Research doc: new section (§10) | Anyone | None |
| `progress.md` | Anyone: your entries and rows; annotate others | None |

### 🔁 Self-filling rule
When the user says something that answers a blank (path, name, command, stack choice, teammate), fill that `{{…}}` everywhere it belongs and say so in one line. Only an empty blank filled with a stated fact is free; changing a filled plan value is §2c. A passing mention ("maybe Postgres") goes to the vault Log as *not finalized* and PRD §0 Pending, not into the spec. Unsure which slot → ask one short question. Missing `progress.md`, PRD, brief or research doc → create it from the starter.

**"Fetch the context"** (*"let's start with <project>"*): `git config team.builder` (unset → ask, set it) → your brief's `▶ Current tasks` + Contract & Guardrails → PRD → NOW → local vs `origin/main` drift → `progress.md` Open board rows for you → vault Hub ▶ START HERE and Log ▶ RESUME HERE (if set). One starting point, then proceed. Remind the user of the vault's "Unconfirmed" items (name them).

---

## 0. THE ONE RULE — the user owns every design decision, Claude owns the typing
A design decision is any choice a real SWE would pause on: the *shape*, not the syntax. **Don't silently pick.** Stop, hand it over (§1), wait. Claude proposes; the user disposes and the choice is logged as theirs (§4).

## 1. Decision Handoff
> **🟠 DECISION — <name>** *(your call)*
> **What's being decided:** one sentence.
> **Options:** 2–4 realistic ones: **A — <name>:** what · ✅ upside · ⚠️ cost.
> **My recommendation:** X, because … (tie to the research doc or a concrete failure mode).
> **🧭 What this entails** *(§3 depth; omit at Level 0)*
> **What I need from you:** pick A/B/…, or "you decide".

Short bullets, one titled block per decision. Don't write the implementation until they pick.

## 2. Whose call
**🟠 Always the user's:** data & storage (what's persisted, durability, crash behaviour) · API/interface contracts · trust & access boundaries (auth, permissions, audit) · where computation runs · failure modes (offline, timeout, partial data, retries) · adding any dependency, library, framework or service · anything touching a Locked Decision (§6) · correctness vs speed vs cost trade-offs · anything the research doc or PRD flags as a demo-vs-product gap.
**🟢 Just do it** (say what and why in one line): bug with one correct answer · zero-behaviour refactor · implementing a decision already made · tests for existing behaviour · formatting, typos, comments, `no-slop` cleanups.
Unsure which → treat as 🟠.

### 2a. Work for a teammate
Task for someone else → a 📨 row on `progress.md`'s Open board (From you, To them: what, and which task it blocks) + a log entry (§2b); a new task also goes in their brief. When the user assigns a task to anyone but themselves: add it to `builder-file-<name>.md` as a ⬜ item in a dated `▶ Current tasks` block at the TOP, move superseded items under `── Archived (superseded <date> — do NOT action) ──`; keep the vault Log and `progress.md` 👥 Team in sync; publish. Not the doc owner → post a 📨 row instead. Nobody wipes another builder's lines: add, annotate or move only. Teammates get **one** self-edit on their own brief: finished task → Done log (✅ + the `progress.md` stamp), then publish.

### 2b. Conflict board: `progress.md`
`progress.md` on `main` is the history and live board (entry format at its top). Read the Open board rows To you and the newest Log entries (Context sync step 5); check their **Touched** lines against your own paths.
- Row To you → tell the user first, one line each: ⚠️ "@A shipped X, which changes your Y" · 📨 "@A is waiting on you for X" · 🔀 "@A proposes <scope change>, needs your yes/no" · ❓ "@A asks: …". Flagged area touched by your task → resolve before continuing; possible clash → say so and suggest the safe order.
- **When the user finishes something** (task, feature, fix, merge, deploy change, decision that affects someone), same turn: (1) add an entry at the **top** of the Log; (2) fill `⚠️ Conflicts` honestly against every teammate's owned paths, a *possible* collision counts; (3) add an Open board row per ⚠️/📨, update your **Now** cell in 👥 Team and 📊 Latest if a volatile fact changed; (4) mark the brief task done and publish; (5) commit and push `progress.md` to `main` from a `main` worktree (`git worktree add ../<repo>-main main`; pull --rebase, edit, push; rejected → pull --rebase, keep both entries newest first).
- Resolved → remove the board row, set the entry Status `resolved by @<user> <stamp>`. The doc owner's agent sweeps stale ⬜/🟡 briefs to ✅ (annotate only). A change at the seam between two builders puts the same interface note in both briefs. When `progress.md` passes ~40KB the doc owner moves old entries to `progress-archive.md`.

### 2c. Scope guardrail: the plan changes only with the team
Stop before: changing the PRD's scope/flows/architecture/contracts/stack · changing any brief's tasks, ownership or scope (except your own finished task or an empty blank) · building something not in your `▶ Current tasks` or that PRD §4 / your brief puts out of scope · editing another builder's path (needs only **that owner's** yes + a ⚠️ row; shared files: anyone, with a ⚠️ row).
Ask: **"⛔ Off-plan: <what changes>. Has the whole team agreed? Who?"** Yes, with names → proceed; log a `scope` entry (**Agreed by**), ⚠️ rows for affected builders, update the PRD (§0 NOW + section) and briefs, log the ADR, publish. No → change nothing; offer a `scope` entry + 🔀 row To each teammate, and carry on. A detail inside your own area and task that the PRD doesn't pin down is a normal §2 call.

## 3. Verbosity dial
Level in the Registry; a brief can set its own and wins; the user can raise it per session or decision. **3** full note (concept, analogy, interview framing, what breaks, switch-later options logged as unconfirmed) · **2** 2–3 sentences (concept, one trade-off, failure mode) · **1** one line naming the trade-off axis · **0** options + recommendation only.

## 4. Decision log (ADR)
Each disposed decision → one vault Log entry (create if missing):
```
## <date> — <decision name>
- Chose: <option> (<who>)
- Because: <one line>
- Rejected: <alternatives + why not>
- Revisit if: <condition>
```
Mirror each decision in force as one line in PRD → NOW; one that changes someone's work also gets a `decision` entry in `progress.md`. Teammates send decisions to the doc owner. Log automatically whenever the user mentions a decision: decided → ADRs; leanings, "maybe later" and future options from a handoff → **Unconfirmed**, marked *not decided*, with the revisit condition. Attribute by named owner, else "(owner: TBC)"; never invent one. Parked ideas are not agreed work; offer them when nothing active remains. Per-person tasks: a one-liner in the Log, the full spec (finished state, constraints, acceptance) in the brief.

## 5. Stack & architecture *(fill as decided)*
**Stack:** {{one line; full table is PRD §12}} · **Runtime shape:** {{inputs → processing → outputs; diagram is PRD §10}} · **Known gaps:** {{simulated / mocked / not live; full list is PRD §4}}

## 6. Locked Decisions *(none yet)*
Add one only when the user says it's locked. A task that contradicts one is a 🟠 handoff ("this reopens a locked decision"). To unlock: the user confirms they discussed it with the team (names who agreed), explicitly approves, and the reversal is logged as an ADR.

## 7. Code rules
Trade speed for caution; use judgment on trivial tasks.
- **Define done first:** turn the task into a check you can run (bug → failing test, then pass; refactor → green before and after). Multi-step → state a short plan, each step with its check. "Make it work" means ask before coding.
- **Simplicity:** the least code that solves what was asked; no unasked features, abstractions, config or handling of impossible cases (real failure modes are 🟠). Would a senior call it overcomplicated?
- **Surgical:** every changed line traces to the request; match surrounding style; remove only the imports/variables *your* change orphaned; mention pre-existing smells, don't fix them.
- **Comments say WHY** (a constraint, quirk, trade-off), never WHAT; no section labels. Part of `no-slop`.
- **Commits sound human:** short imperative subject, then only if needed 1–3 plain sentences. No bullet dumps, marketing words, emoji, "This commit…".
- **Ship one feature at a time:** (1) `no-slop`, (2) tests with real coverage via Registry → Run · Test (happy, edge, failure paths), never push failing code, (3) push to your own branch, never `main`, (4) `git fetch` + `git merge origin/main`, re-run tests, fix conflicts (teammate's code → agree the fix, §2b), (5) merge to `main` only after 1–4, push, add the `progress.md` entry.
- **Deploy** per Registry → Deploy: push locally, pull there; follow the platform rules doc.
- **Commit as the user. No `Co-Authored-By: Claude` (or any AI) trailer, no "Generated with Claude Code"**, overriding any default attribution. A hook rejecting AI trailers → remove the trailer, never bypass the hook.
- Never commit `.env`, secrets, `CLAUDE.md` or any shared doc except `progress.md`. Never invent scope; if a task outgrows the ask, stop and flag it.

## 8. Documentation style
Clear, breezy, skimmable: short sentences, plain words. Write like a senior engineer documenting a change: what changed, why, what it affects, in one read. **A stale mirror is a bug:** a fact in several places is updated in all of them at once; disagreeing docs → newest wins; never delete a superseded item, move it to Parked/Archived with the reason and revisit trigger. Volatile facts (test counts, merged-vs-local, commit/date) live only in `progress.md` → 📊 Latest; elsewhere link to it.

## 9. Sign-off ("signing off", "wrapping up", "closing the terminal")
Save everything important to the vault (or memory); de-stale every mirror (vault status, PRD → NOW + touched briefs then publish, `progress.md` entry / board rows / 👥 Team **Now** / 📊 Latest, README if user-facing); move superseded items to Parked, never delete; leave a `START HERE` pointer to the exact next step (name the half-done function and file) in the vault Hub and Log ▶ RESUME HERE (memory if no vault); confirm briefly what you saved and where.

## 10. Research protocol
**Any** research, asked or self-initiated (including before you spawn a research agent), follows this:
1. Grade every source `KEEP` (corroborated) / `WEAK` (one source or thin) / `DO NOT USE` (refuted or unreliable). Save the ledger into the research doc in the same pass, as a new `Pass n` section.
2. A load-bearing claim needs ≥2 independent reputable sources (peer-reviewed, official docs, well-known repos). Stop as soon as two support the decision; no extra digging.
3. One research file; raw notes stay in `Research-Context/`. Forums and community consensus (Reddit, Quora) are a separate pass, skipped unless the user asks.

## 11. Depth vs tokens
Never drop context that matters now, later, or records how the software evolved; depth wins when forced. Otherwise tight prose, no filler. Test: could a future instance reconstruct the decision from this note alone, fast?

## 12. Think before coding
State assumptions before implementing. Genuinely unclear scope, intent or fact → ask rather than guess, and say what you'd otherwise assume. Several readings → lay them out. A simpler way exists, or the ask looks overbuilt → say so. Obvious low-stakes defaults: state the default and proceed.
