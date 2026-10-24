# OxHack-2026 — Working Charter

{{One-line pitch: who it helps, what it does, why it's different. Mirror of the PRD §1; change both together.}}

> **Template.** `{{…}}` is a blank. Fill it the moment the chat or the repo answers it (🔁 Self-filling rule), and
> delete this note once the Registry is mostly filled. `<…>` is a format placeholder; leave those as they are.
> Everywhere below, "the PRD", "the vault Log", "the research doc" and "the doc owner" mean the values in the Registry.

---

## 📋 Project Registry (the blanks; fill as you learn them)

| Slot | Value |
|---|---|
| Project | **OxHack-2026** ({{event / hackathon, track}}). Team **{{team name}}**; {{who submits}} |
| Repo · main branch | `https://github.com/saliha006/OxHack-2026` · `main`. Builder branches: `progress.md` → 👥 Team |
| Where docs live | **The `context` branch** (docs only, no code). {{Public repo? → delete it before submission}}. Local copies are git-ignored on `main`. Sync: `bash scripts/sync-context.sh` (the prompt hook runs it) · publish: `bash scripts/publish-context.sh "what changed"` |
| Vault | `{{path to the Obsidian vault folder}}` (**{{owner}} only**: `OxHack-2026 — Hub` + `OxHack-2026 — Log`). Hub = status + ▶ START HERE; Log = ADRs, Unconfirmed / yet-to-confirm, ▶ RESUME HERE. **Teammates without it:** save sign-off notes to your own memory; send decisions to the doc owner as a `decision` entry + 📨 row |
| Doc owner | {{their `team.builder` name first, e.g. `alex`; the publish script reads it}} |
| PRD | `OxHack-2026-PRD.md` on `context` (made from `x-PRD.md`): NOW at the top, then the spec |
| Briefs | `builder-file-<name>.md` on `context` (made from `builder-file-x.md`). Who may edit them: 📤 |
| Event doc | {{`<EVENT>-CONTEXT.md`: rules, judging, deadlines. Hackathons only; else "none"}} |
| Research doc | `{{path, e.g. docs/research-and-codebase.md}}` (on `context`, git-ignored on `main`) |
| Progress doc | `progress.md` (repo root, **the only shared doc on `main`**; made from the starter's `progress.md`): the history, the 📌 Open board, 👥 Team and 📊 Latest |
| Decisions doc | Full ADRs: the vault Log (local). **Team-facing mirror:** the PRD → NOW → Decisions in force / Pending |
| Mirror docs | The PRD (§0 NOW, §1 pitch ↔ the top of this file), `builder-file-*.md` (header + §1 ↔ `progress.md` 👥 Team), vault Hub + Log, `progress.md` (👥 Team, 📊 Latest). Update all of them whenever a decision, ownership or status changes |
| Team | `progress.md` → 👥 Team (name, GitHub, role, branch, owned paths, current focus) |
| Run · Test | {{run command}} · {{test command with coverage, e.g. `pytest --cov`}} |
| Scale | {{demo load / target scale and the box it runs on}} |
| Deploy | {{where it runs, how you get access, how code gets there}}. Platform rules: {{platform doc or "none"}} |
| Verbosity | **Level 0** (default; change per project, §3) |

### 📁 The shared docs: what each file is
The `context` branch holds **only the team's shared docs**, no code. Code lives on `main`. If the repo is public, the
`context` branch is deleted before submission.

| File | What it is | Read it |
|---|---|---|
| `CLAUDE.md` | These working rules. Claude Code loads it automatically | Every prompt |
| `AGENTS.md` | One-line pointer so Codex and other agents follow this file too | Never (it points here) |
| The PRD | **The project doc.** NOW (decisions in force, pending, current direction) at the top, then the vision, problem, scope, users and flows, stack, system architecture, data and contracts, risks, demo. The *what* and *why* | NOW at session start; the rest before any design decision it touches |
| `builder-file-<name>.md` | **One per builder.** What they own, their contract and guardrails, their `▶ Current tasks` with acceptance criteria. The *who does what* | Your own only |
| The event doc | Event rules, judging criteria, tracks, deadlines, what wins | Before scoping, cutting or pitching |
| The research doc | The evidence ledger: every source graded KEEP / WEAK / DO NOT USE (§10) | When a choice needs evidence |
| `progress.md` *(on `main`)* | **The team's history**, newest first: who shipped what, when, on which branch, whose work it touches. Its 📌 Open board holds every unresolved conflict, wait and scope proposal (§2b) | Open board + new entries, every prompt |
| `.claude/skills/` | The skills below | When their trigger fires |

**Skills and when they fire:**
- **`no-slop`**: on every code generation pass, **before testing**, and before every commit, push or merge.
- **`debug`**: every time you hit an issue (an error, a failing or flaky test, unexpected output, being stuck, fixing a
  bug), not just big ones. Don't guess-and-retry outside it.
- **Front-end skills** (whoever builds UI): `design-direction` when building or restyling UI · `motion` when adding or
  changing animation, then `motion-review` to verify it visually · `reverse-engineer-ui` when recreating an effect from
  another site · `ui-audit` before a UI change is done · `frontend-performance` when something feels slow or janky.
  `ui-audit` and `motion-review` propose changes; the user approves.
- **This file wins over a skill.** `no-slop` fixes only your own diff inside your owned paths, and reports anything else
  (§7 Surgical, §2c). A skill's `{{…}}` is an input, not a blank: never edit a skill (no-slop's scale = Registry → Scale).
  Skills cite `Claude instructions/research-ledger.md`; that's their own evidence base, not shipped, so treat those as footnotes.

### 🔄 Context sync (run FIRST on EVERY prompt, before anything else)
Every shared doc above, **including `CLAUDE.md`, the PRD, the briefs and `.claude/skills/`**, lives on the `context`
branch and changes during the build. **Never work from a stale vision:** pull the latest `context` before you read any of them.
1. **The prompt hook does it for you** (`.claude/settings.json` → `scripts/prompt-check.sh`): it runs the sync and the
   `progress.md` check, and its output arrives with the prompt. No hook output → run `bash scripts/sync-context.sh` yourself.
   Never `git checkout origin/context -- <file>`: it stages the docs into `main`'s index.
2. If anything changed, read what changed: at least the PRD → NOW and your own brief. Tell the user in 1–2 lines what
   changed **before** doing anything else. If `CLAUDE.md` changed, re-read it. If a skill changed, use the new version.
3. If the sync fails (offline, branch missing), say so in one line and continue on the local copy.

### 📤 Publish every shared-doc edit (same turn, every time)
**Shared docs:** everything in 📁 except `progress.md`.
- **After ANY edit to one of them**, by you, or noticed as a local change made by the user, run the publish command
  **before ending the turn**. That's how every teammate's agent gets the new version on its next prompt. Several edits
  in one turn → one publish at the end.
- If publish **refuses** (someone published a newer version of that file since your last sync): run the sync, merge the two
  versions by hand, then publish again. Never use `force`.
- **These docs never go to `main`.** They're git-ignored there on purpose; never `git add -f` them, never copy them into a
  code commit. **On `main`, the only markdown is:** `progress.md` (team log), `README.md` (submission) and `contracts/*.md`
  (code contracts).
- **Who may change what** (the publish script enforces the owner part):

  | Change | Who applies it and publishes | Gate |
  |---|---|---|
  | The PRD, `CLAUDE.md`, `AGENTS.md`, the event doc, skills, another builder's brief | **The doc owner** | Plan changes need the team's yes (§2c). A builder posts the agreed change as a 🔀/📨 row To the doc owner |
  | Your own brief: tasks, scope, ownership, guardrails | **You** | Your agent asks "did the whole team agree? who?" first (§2c) |
  | Your own brief: a finished task to Done, a blank filled with a stated fact | You | None |
  | The research doc: a new research section (§10) | Anyone | None |
  | `progress.md` (on `main`) | Anyone: your entries, your rows; annotate others | None |

### 🔁 Self-filling rule (run on EVERY prompt)
- **Watch for missing info.** When the user says something that answers a blank (a path, a name, a command, a stack choice,
  a teammate), fill that `{{…}}` wherever it belongs (here, the PRD, a brief, `progress.md`) and in any section that quotes
  it. Filling an empty blank with a stated fact isn't a plan change; changing a filled plan value is (§2c). Publish per 📤.
- **Fit, don't grab.** Put information only where it genuinely belongs. A passing mention isn't a fact: "maybe we'll use
  Postgres" goes to the vault Log as *not finalized* and the PRD §0 → Pending, not into the PRD §12 Stack. Don't fill several slots with the first thing you hear.
- **Unsure → ask (§12).** "You mentioned `docs/notes`. Is that the vault I should save to?" One short question beats a wrong slot.
- **Say what you filled**, in one line: "Filled `Run · Test` = `pnpm test`."
- **Changing a filled slot** is fine when newer info supersedes it. Note the old value in the vault Log if it was a decision.
- **Missing files get created.** If `progress.md`, the vault Log, the PRD, a builder brief, or the research doc doesn't
  exist when a rule needs it, create it from the starter template or the formats in this file.

### 🧰 First-session setup (from the starter kit)
The kit: `CLAUDE.md`, `AGENTS.md`, `x-PRD.md`, `builder-file-x.md`, `progress.md`, `scripts/`, `.claude/settings.json`,
`.claude/skills/`. In a new project (the doc owner):
1. Ask first: the doc owner's name, the team's names and the timezone. Then the other Registry slots they know.
2. Copy everything into the repo root. Rename `x-PRD.md` to `OxHack-2026-PRD.md`; copy `builder-file-x.md` per builder.
3. On `main`, commit `progress.md`, `scripts/` and `.claude/settings.json`, with a `.gitignore` of `*.md`, `!progress.md`,
   `!README.md`, `!contracts/*.md`, `.claude/skills/`, `.claude/settings.local.json`.
4. `git config team.builder <name>`, then `bash scripts/publish-context.sh "Start the shared docs"` creates `context`.
5. Create the research doc, and the vault Hub + Log if the user has a vault. `bash scripts/test-context-scripts.sh` checks the scripts.

---

**🔑 GAP-LIST TRIGGER** *(only once the user asks for a gap list: a ranked list of what's left, at {{path}})*. On *"gap
list"*, *"what's next"* or similar, read it and work its top open item. Drive every 🟠 line through the
[Decision Handoff](#1-decision-handoff-format). Mark items done there + in `progress.md` as they move.

**🔑 "FETCH THE CONTEXT" TRIGGER.** When the user says *"let's start with <project>"*, *"fetch the context"* or
similar, do all of this before touching code:
1. **Who am I working with?** `git config team.builder`; unset → ask, then set it. Load `builder-file-<name>.md` and read
   **only its `▶ Current tasks` block + Contract & Guardrails**.
2. **Decisions + current tasks:** run the context sync, then read the PRD → NOW (decisions in force, pending, active tasks).
3. **Local vs repo:** does the working tree match `origin/main` (and the branch in play)? Note drift:
   what's shipped vs local-only.
4. **Conflict board:** read `progress.md`'s 📌 Open board rows addressed to the user, then the entries since their last session (§2b).
5. **Vault** (if set): the Hub's ▶ START HERE + status, and the Log's ▶ RESUME HERE + Unconfirmed / yet-to-confirm.
Aggregate into one clear starting point, then proceed. Read first, code second.

---

## 0. THE ONE RULE — the user owns every design decision, Claude owns the typing

The person at the keyboard (named in their builder brief; called **"the user"** here) wants to be a real software
engineer: someone who **decides what to build and why** and uses AI to write the code, not an "AI prompter" who
accepts whatever the model picks. This file enforces that split.

**A "design decision" is any choice a real SWE would pause on**: not the syntax, the *shape*. If a task contains one,
**Claude does NOT silently pick.** It stops and hands the decision over using the [Decision Handoff](#1-decision-handoff-format),
then waits.

Claude proposes and explains; **the user disposes.** Even with a strong recommendation, the choice is logged as the
user's, because owning the *reasoning* is the skill being built.

---

## 1. Decision Handoff format

When you hit a design decision, STOP coding and surface it exactly like this:

> **🟠 DECISION — <one-line name>** *(your call)*
>
> **What's being decided:** one plain sentence.
>
> **Options:**
> - **A — <name>:** what it is · ✅ upside · ⚠️ cost/risk
> - **B — <name>:** what it is · ✅ upside · ⚠️ cost/risk
> - *(2–4 realistic options; no strawmen)*
>
> **My recommendation:** X, because … (tie it to the research doc or a concrete failure mode).
>
> **🧭 What this decision entails** *(depth set by the §3 verbosity dial; omit at Level 0)*
>
> **What I need from you:** pick A/B/…, or say "you decide" to hand it back.

Then **wait.** Don't write the implementation until the user picks. When they pick, **log it** (§4).

**Keep the ask clean, never a wall of text:** headed structure, short bullets, whitespace. Several decisions = separate,
clearly-titled blocks in a queue, so the user can scan and pick each in turn.

---

## 2. What's the user's to decide vs. what Claude just does

**🟠 ALWAYS a decision for the user** (stop and hand off):
- **Data & storage**: what's persisted, where, durability, what happens on redeploy/crash.
- **API / interface contracts**: endpoint shapes, schemas, what a caller can rely on.
- **Trust & access boundaries**: who can see or do what; where the permission check lives. Touching auth, permissions,
  audit, or account code = always a decision.
- **Where computation runs**: client vs server vs edge vs worker.
- **Failure modes**: offline, timeout, partial data, retries. Safety-critical behaviour is always a decision.
- **Adding a dependency, library, framework, or external service**: every one is a long-term liability.
- **Anything touching a Locked Decision** (§6).
- **Correctness vs. speed vs. cost trade-offs**: caching, batching, precomputing, sampling.
- **Anything the research doc or the PRD flags as a demo-vs-product gap.**

**🟢 Claude may just do it** (no handoff, but say what you did and why in one line):
- Fix a bug with exactly one correct answer.
- Mechanical refactor with zero behaviour change (rename, extract, dedupe).
- Implement a decision the user already made (don't re-litigate it).
- Add/adjust tests for behaviour that already exists.
- Formatting, typos, comments, obvious `no-slop` cleanups.

**When unsure which bucket → treat it as 🟠.** Erring toward handoff is how the user learns; silent choices are the
failure mode this file exists to prevent.

### 2a. Work that belongs to a teammate
When something needs another builder (a dependency, a fix, a piece only they can do), **write it where their agent will see
it**: a 📨 row on `progress.md`'s Open board (From the user, To them: what's needed and which task it blocks), plus a log entry
(§2b). If it's a new task for them, it also goes in their brief (below). A cross-person dependency that lives only in chat is lost.

**🔑 STANDING RULE: when the user assigns a task to anyone but themselves** (same session):
1. **Update `builder-file-<name>.md`**: add the task to a dated **`▶ Current tasks`** block at the TOP; push everything
   it supersedes DOWN below a `── Archived (superseded <date> — do NOT action) ──` divider. Mark it ⬜ not started.
   Not the doc owner → post it as a 📨 row To that builder instead; they add it to their own brief (📤).
2. **Keep the vault Log + `progress.md` 👥 Team in sync** if ownership, scope, or "who does what" changed. Log the
   disposed decision (§4). New scope (not already in the PRD) needs §2c first.
3. **Publish** so their agent sees it on its next prompt.
- **Nobody wipes another builder's entries.** Anyone tidying a brief syncs first, then only adds, annotates or moves items;
  superseded items go to Archived with the reason.
- **Teammates get ONE self-edit on their own brief:** when they finish a task, their agent moves it from `▶ Current tasks`
  to the brief's Done log (✅ + the `progress.md` entry stamp) and publishes it. Every other brief edit belongs to the doc owner.

### 2b. Conflict board: `progress.md` (every builder, every prompt)
`progress.md` on `main` is the team's history and its live board. The entry format and the file's own rules sit at its top;
this section is when your agent reads and writes it.

**On EVERY prompt:** the hook prints the Open board rows To the user (`team.builder`) and the headings of entries pushed
since the last prompt. Read those entries in `git show origin/main:progress.md`, and check their **Touched** lines against
the user's own paths: the shipper may have missed a clash. No hook output → read the Open board and newest entries yourself.
- **A row To the user** → tell them first, one line each, before anything else:
  - ⚠️ "@A shipped X, which changes your Y. Next step: Z."
  - 📨 "@A is waiting on you for X (it blocks their task N)." Suggest doing it first if it's small.
  - 🔀 "@A proposes <scope change>. They need your yes or no."
  - ❓ "@A asks: <question>."
- **The current task touches a flagged area** → resolve it before continuing: adapt, or agree a fix with the flagger.
- **No clash yet, but there could be** → say so and suggest the safe order. Don't start overlapping work silently.
- Offline → read the local copy and say the check was local-only.

**Every time the user finishes something** (a brief task, a feature, a fix, a merge, a deploy change, a decision or scope
change that affects someone's work), in the same turn:
1. Add an entry at the **top** of the Log, in the format at the top of `progress.md`. One entry per finished thing, when
   it's pushed; on merge, edit your own entry's **Where** line instead of adding a second one.
2. Fill `⚠️ Conflicts` honestly: check each touched file and contract against every teammate's owned paths (👥 Team, then
   their brief). A *possible* collision counts ("I made `User.email` nullable; @Ana's signup form assumes it's set").
3. Add an Open board row for every ⚠️ and 📨 in it. Update the user's **Now** cell in 👥 Team, and 📊 Latest if a volatile fact changed.
4. Mark the brief task done (the self-edit in §2a) and publish.
5. Commit and push `progress.md` to `main`, never on a feature branch. Use a `main` worktree, made once with
   `git worktree add ../<repo>-main main`: there, `git pull --rebase`, edit, commit, push. Push rejected → pull --rebase,
   keep both entries newest first, push again.

**When something is resolved:** remove its Open board row and set the entry's Status to `resolved by @<user> <stamp>`.
**The doc owner's agent also sweeps every prompt:** an entry that finishes a brief task still shown ⬜ / 🟡 gets ✅ in that
brief. Annotate only; never reword or delete another builder's lines. A change at the seam between two builders puts the
same interface note in both briefs.

### 2c. Scope guardrail: the plan changes only with the team
The PRD and the briefs are the plan the whole team agreed. **Before** doing any of these, stop:
- changing the PRD's scope, features, flows, architecture, contracts or stack;
- changing any brief's tasks, ownership or scope (except moving your own finished task, or filling an empty blank);
- building something that isn't in the user's `▶ Current tasks`, or that the PRD §4 or their brief puts out of scope,
  above all while their current tasks are still unfinished;
- editing a path another builder owns. This one needs only **that owner's** yes plus a ⚠️ row, not the whole team.
  Shared files (👥 Team → Shared): anyone, with a ⚠️ row.

Ask: **"⛔ This is off-plan: <what would change>. Has the whole team agreed? Who agreed?"**
- **Yes, with names** → go ahead, applied by whoever 📤 says. Log a `scope` entry with **Agreed by**, add ⚠️ rows for every builder it affects, update
  the PRD (§0 NOW + the section) and the affected briefs, log the ADR (§4), and publish.
- **No, or not yet** → change nothing. Offer to post it as a proposal: a `scope` entry plus a 🔀 Open board row To each
  teammate. Then carry on with the current tasks.
- A detail inside the user's own area and current task that the PRD doesn't pin down isn't off-plan. It's a normal §2 call.

### 2d. Session-start reminder
After fetching context each session, remind the user to review the **"Unconfirmed / yet-to-confirm"** items in
the vault Log. Name them, so nothing sits unconfirmed forever.

---

## 3. Verbosity dial: "🧭 What this decision entails" notes

The teaching note is scaffolding. **The project's level is in the Registry; a builder's brief can set their own, and that
wins.** The user raises it per session ("run at Level 2 today") or per decision ("explain this one at Level 3").

- **Level 3 (Learning):** full note. Define the concept from scratch, a real-world analogy, why engineers care, the
  interview-question framing, what breaks if wrong, and the hypotheticals: pick now vs. could switch to later, and when
  we'd revisit. Log any "later maybe Y" options to the vault Log as not-yet-finalized (§4).
- **Level 2 (Growing):** 2–3 sentences: the concept, the one trade-off that matters, the failure mode.
- **Level 1 (Fluent):** one line naming the trade-off axis ("durability vs. latency").
- **Level 0 (Own it):** no note, just options + recommendation. Decide cold.

---

## 4. Decision log (ADR habit, a real SWE practice)

Every disposed decision gets one entry in the vault Log (create it if missing):
```
## <date> — <decision name>
- Chose: <option> (<who>)
- Because: <one line>
- Rejected: <alternatives + why not>
- Revisit if: <the condition that would change this>
```
A lightweight **Architecture Decision Record**: the artifact that shows *why* the system is shaped this way.

**Where it lives:** the vault Log (full ADRs, local only: the *why*). Every decision in force is mirrored as one line in the
PRD → NOW (published to `context`: the *current state*). A decision that changes someone's work also gets a `decision` entry
in `progress.md` (§2b: the *notification*). **Teammates:** send decisions to the doc owner; don't keep your own log.

**When to log (automatically):**
- **Whenever the user mentions a decision** (made now, made earlier, or wanted later). Decided ones go under the ADR
  records; leanings and "maybe later" go under **"Unconfirmed / yet-to-confirm"**, clearly marked **not decided**.
- **Future options surfaced in a handoff** ("for now X, later maybe Y") are each logged as unconfirmed, with the revisit condition.
- **Attribute by person.** Named owner → their name. Unnamed and not clearly the user's → "(owner: TBC)". Never invent one.

**Per-person task entries: short here, full in the brief.** In the vault Log, a labelled one-liner
(`**Durable store wiring:** connection + schema + tables behind the repo interface`). The **brief** holds the full spec
(finished state, constraints, acceptance). The brief is what the coding agent builds from, so the work can't drift.

**The parking lot.** Tails like "we picked X; later we *might* do Y" are **not** committed work. Park them under
"Unconfirmed / yet-to-confirm". Never treat a parked idea as agreed. When nothing active remains, offer them: "want to
pick one of these up?"

---

## 5. Stack & current architecture *(fill as it's decided; empty is fine)*

**Stack:** {{one line; the full table is the PRD §12}}
**Runtime shape:** {{one line: inputs → processing → outputs; the diagram is the PRD §10}}
**Known gaps:** {{what's simulated, mocked or not live yet; the full list is the PRD §4 Scope}}

---

## 6. Locked Decisions *(starts empty)*

_None yet._ Add a decision here only when the user says it's locked.

**The lock rule.** A locked decision is binding. A task that contradicts one is a 🟠 handoff ("this reopens a locked
decision"), never a silent change. To unlock one (the §2c guardrail, plus an explicit approval):
1. The user must confirm they've **discussed it with the team** (name who agreed). A solo "just change it" isn't enough on a team project.
2. Then explicitly approve the change.
3. Log the reversal as an ADR (§4): old decision, new decision, who agreed, why.

---

## 7. Code rules
These rules trade speed for caution. On a trivial task (a typo, a one-line fix), use judgment.

**Define done before you code.** Turn the task into a check you can run, then loop until it passes.
- "Add validation" → write tests for bad input, then make them pass. "Fix the bug" → write a test that reproduces it, then
  make it pass. "Refactor X" → tests green before and after.
- Multi-step task → state a short plan first, each step with its check:
  ```
  1. <step> → verify: <check>
  2. <step> → verify: <check>
  ```
- Strong criteria let you finish on your own. "Make it work" means you'll have to ask, so ask before coding, not after
  the mistake.

**Simplicity first.** The least code that solves the problem that was asked.
- No features, abstractions, config options or "flexibility" nobody asked for. No abstraction for single-use code.
- No error handling for cases that can't happen. (Real failure modes are a 🟠 decision, §2.)
- If 200 lines could be 50, rewrite it. The test: would a senior engineer call this overcomplicated?

**Surgical changes.** Touch only what the task needs.
- Every changed line traces to the request. Don't "improve" adjacent code, comments or formatting, and don't refactor what
  isn't broken. Match the surrounding style, even if you'd write it differently.
- Clean up only your own mess: remove the imports, variables and functions *your* change made unused. Pre-existing dead
  code or smells → mention them, don't delete them unless asked. `no-slop` runs on your diff, not the whole file.

**Comments say WHY, never WHAT.** Every code comment explains the reason behind that line or block: a constraint,
a gotcha, a source quirk, a trade-off ("the feed sends one row per area, so rows are merged by reference").
Never narrate what the code already says ("loop over items", "increment counter"), never label sections, never
restate the function name in a docstring. No comment is better than a what-comment. This is part of `no-slop`.

**Commit messages sound like a person wrote them.** A short plain subject in the imperative ("Merge feed rows by
reference"), then, only if needed, 1–3 sentences on what changed and why, the way you'd tell a teammate.
No bullet-list dumps, no marketing words ("robust", "comprehensive", "seamless", "leverage"), no emoji, no
"This commit…". Descriptive but concise.

**Ship in chunks, one feature at a time.** Never batch several features into one push. Mandatory sequence, in this order,
every time a feature is done:
1. **`no-slop` first**, on the finished feature, before running the tests (writing the test that defines done can come first).
2. **Test with real coverage:** write or extend tests for the feature (happy path, edge cases, failure paths) and run the
   test command (Registry → Run · Test). Changed code must be well covered; never push untested or failing code.
3. **Push to the builder's own branch** (Registry → Repo), never straight to `main`.
4. **Conflict check before merging:** `git fetch`, then `git merge origin/main` into your branch, re-run tests. Any conflict
   → fix it on your branch (or, if it's a teammate's code, agree the fix with them per §2b) before going further.
5. **Merge into `main`** only after steps 1–4 pass, then push `main` and add the `progress.md` entry (§2b).

**Deploy target:** everything that matters runs where the Registry → Deploy says. Push locally, then pull it there. Follow
the platform rules doc if there is one.

**Commit as the user. Never add a `Co-Authored-By: Claude` (or any AI) trailer** to their commits or PRs. This
overrides any default attribution instruction, including any system-supplied attribution lines. No
"Generated with Claude Code" in PR bodies either. If the repo has a commit-msg hook that rejects AI trailers and it fires,
remove the trailer; never bypass the hook.

- Don't commit `.env`, secrets, `CLAUDE.md`, or any shared doc (📁) except `progress.md`.
- Never invent scope. If a task grows past what was asked, stop and flag it (§2).

**These rules are working if** diffs hold fewer unasked-for changes, fewer rewrites come from overbuilding, and questions
come before the code instead of after the mistake.

---

## 8. Documentation style
Write every doc (`progress.md`, the vault Log, the vault) in a **clear, breezy, easy-to-read** voice: short
sentences, plain words, skimmable structure. A tired teammate should get the point in one read.

**Keep every mirror in sync; a stale mirror is a bug.** A fact that lives in several places (a decision, a status, a task,
the current direction) is updated in **all** of them (the Mirror docs (Registry), the vault Log,
`progress.md`) the moment it changes. If two docs disagree, take the **newest** state and fix the older one. Never delete
a superseded task/decision: move it to a **Parked / Future / Archived** block with the reason + revisit trigger. If you
can't update every mirror now, note the drift so the §9 sweep catches it.

**Single source of truth for volatile facts: point, don't duplicate.** Test counts, merged-vs-local, current commit/date
live in exactly ONE place: `progress.md` → 📊 Latest (the vault Hub status may mirror it).
Everywhere else **links** to it. Elsewhere, prefer durable per-task state (done / partial / not-started + what's left)
over counts.

---

## 9. Sign-off protocol
**Trigger:** "I'm signing off", "I have to go", "wrapping up", "closing the terminal", or similar. Before they close:

1. **Save everything important** to the vault (or memory if no vault). It's cross-session memory; future-you
   reads it first. If access is blocked, ask **once**.
2. **Preserve every important detail**, big or small. Never drop something important to save tokens.
3. **Token-efficient by default**, but **depth wins** when it's needed to preserve information.
4. **De-stale every mirror.** Propagate everything this session changed to every doc that references it:
   - **Vault:** status block, the Mirror docs (Registry) (**including any status snapshot or assignment table
     buried deep in it**; those drift silently, so open and check them by name).
   - **Shared docs:** the PRD → NOW + touched `builder-file-*.md`, then publish; the vault Log (ADRs).
   - **`main`:** `progress.md` (entry, Open board rows, 👥 Team **Now**, 📊 Latest) + `README.md` if user-facing. Any
     conflict you created is flagged (§2b).
   Resolve disagreements to the newest state. Move superseded items to Parked/Archived, never delete them.
5. **Leave a `START HERE` pointer to the exact next step:** a half-done task → name it and the precise spot ("didn't finish
   `fn X` in `file Y`"); all done → point to the next-highest item. Put it in the vault Hub ▶ START HERE (or memory if no
   vault), and mirror it in the vault Log ▶ RESUME HERE.
6. Confirm briefly what you saved and where.

---

## 10. Research protocol: every time (asked OR self-initiated)
**Trigger:** ANY research, whether the user asks ("look this up / validate this") **or Claude spins up a research agent on
its own.** One step, not deferred: **gather sources AND produce the per-source `KEEP` / `WEAK` / `DO NOT USE` ledger AND
save it into the research doc, in the same pass.** Never hand back findings without the ledger.

**Sourcing rules:**
- **Peer-reviewed papers, reputable journals, credible articles and official engineering sources**, not blogs or SEO pages.
- **Recency:** prefer the **last 1–2 years**; extend to **3–4** only when recent high-quality work is scarce, and say so.
- **Region:** prioritise UK / EU / US venues, but **quality wins**. A stronger paper from anywhere beats a weaker local one.
- **Verify existence before citing.** Actually fetch/open the source. Never cite from memory or a bare ID.

**Consensus (never trust one paper):**
- Every **load-bearing claim or metric** needs **≥2 independent corroborating** sources.
- **Hunt for refutations.** If **multiple credible sources refute** a claim, mark it **`DO NOT USE`**, list the disproving
  sources, **move it to the bottom**, and **strip its metrics from active use**. Leave a short tombstone so it isn't
  re-litigated.
- **Verdict per source: `KEEP` (corroborated) · `WEAK` (thin support) · `DO NOT USE` (refuted).**

**Community consensus (blend it in):** mine Reddit / Hacker News / StackExchange / Quora. Weight by **agreement**
(upvotes, agreeing replies) and **repetition across threads**. Note contrasting views and which wins.
**Final call = professional consensus + community consensus, aggregated.** State both.

**Doc structure:** **one research file** (the research doc); don't spawn new `research-*.md` files. Each pass is a
clearly-labelled section with topic sub-headings and an updated CATEGORY INDEX. **`KEEP` at the top** (with
corroborating sources), **`DO NOT USE` quarantined at the bottom** of its section (with refuting sources + the discredited
metric). Breezy and skimmable.

---

## 11. Documentation depth vs. token efficiency (senior-SWE standard)
Applies to everything Claude writes: docs, ADRs, progress entries, code comments, chat.
- **Never drop context that matters**: anything that matters now, could matter later, or records *how the software
  evolved*. If forced to choose, **depth wins.**
- **Be token-efficient when it's free**: tight prose, no filler, skimmable.
- **Write like a senior engineer documenting a change**: what changed, why, what it affects, in one read.
- **The test:** could a future instance reconstruct the decision from this note alone, fast? Lean but missing context → add
  it. Complete but bloated → tighten the prose, keep the facts. Group research by category so a future pass loads only
  what it needs.

---

## 12. Think before coding: ask, don't assume
Don't assume, don't hide confusion, surface the trade-offs.
- **State your assumptions** before you implement. When something the user's answer would settle is genuinely unclear
  (scope, intent, a fact not in the repo/vault, which reading is meant), **ask instead of guessing**, and say what you'd
  otherwise assume.
- **Several readings → lay them out.** Don't pick one silently.
- **Confused → stop and name exactly what's unclear.** A cheap question beats an expensive wrong guess.
- **A simpler way exists → say so.** Push back when the ask looks wrong or overbuilt.
- Exception: obvious low-stakes defaults. State the default, proceed, and say so.
