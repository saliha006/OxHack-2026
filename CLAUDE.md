> **Current-status correction — 25 October 2026 (~10:00 UTC).** How `main` works today: the PRD (v4). Kenar's MCTS is the decision layer on `main` (PR #1, 07:01). Datasets and splits: DATA-CONTEXT.md; the 06:30 cross-branch audit and its evidence pins: CURRENT-STATUS.md. Kenar works on Kenar-mcts and Kenar-coherent-sets; role is MCTS/search, prediction and set-prior experiments (brief: `builder-file-kenar.md`). Data storage is Parquet/DuckDB plus Tiger/Postgres. Earlier startup/team/status and task-order text below is historical where superseded.

# OxHack-2026 — Working Charter

A Pokémon Showdown Gen 9 OU battle agent that turns usage stats and replays into predictions (the opponent's hidden sets, the chance of winning) and uses them to choose every move, with its win rate measured against standard baseline bots. *(Mirror of PRD §1; change both together.)*

`{{…}}` is a blank: fill it the moment the chat or repo answers it (Self-filling, below). "The PRD", "the vault Log", "the research doc", "the doc owner" are the Registry values.

## 📋 Registry

| Slot | Value |
|---|---|
| Project | **OxHack-2026** (OxHack 26, Oxford Mathematical Institute, 24–25 Oct 2026; tracks: PRD §0 Pending). Team **{{team name}}**; {{who submits}} |
| Team | **saliha** (Saliha Shoaib, `saliha006`): bot layer, **doc owner**, branch `sali` · **derrick** (Derrick Lim Yong Hao, `RandomGeeb`, collaborator): decision layer, branch `derrick` · **nate** (Nate Banas, `aldrichbanas07`): data layer · **kenar** (Kenar Narayaka, `kxnar`): search + prediction (the MCTS decision layer on `main`, belief and set-prior experiments, `prediction/`), branches `Kenar-mcts`, `Kenar-coherent-sets`; `decision/` ownership with derrick TBC. Owned paths and **Now**: `progress.md` → 👥 Team |
| Repo | `https://github.com/saliha006/OxHack-2026` · `main` |
| Where docs live | One folder. **`context` branch** (docs only): `CLAUDE.md`, the PRD, `builder-files/`, `design-decision/`. **`main`**: code, `README.md`, `progress.md`, `contracts/*.md`. **Local only, never pushed unless the user says so:** `Research-Context/` (event doc, research doc, sponsor PDFs, notes), `.claude/` (skills `no-slop`, `debug`, set up per machine), `pokemon-showdown/` (the local server), `runs/`, `.env*`, secrets. All of it is git-ignored on `main`. {{Public repo? delete `context` before submission}}. Sync and publish are plain git, below |
| Vault | `{{path to the Obsidian vault}}` (**{{owner}} only**: `OxHack-2026 — Hub` = status + ▶ START HERE, `— Log` = ADRs, Unconfirmed, ▶ RESUME HERE). No vault → save notes to your memory; send decisions to the doc owner as a `decision` entry + 📨 row |
| PRD | `OxHack-2026-PRD.md`: NOW (decisions in force, pending, active tasks) at the top, then the spec |
| Briefs | `builder-files/builder-file-<name>.md`: `derrick`, `kenar`, `nate`, `saliha` |
| Event doc | `Research-Context/OxHack-2026-CONTEXT.md` (local only): rules, judging, prizes, schedule |
| Research doc | `Research-Context/OxHack-2026-research.md` (local only). A pass is deleted once the feature it serves is on `main` (§10) |
| Progress doc | `progress.md` (repo root; with `README.md` and `contracts/*.md` the only markdown on `main`): history, 📌 Open board, 👥 Team, 📊 Latest |
| Decisions | Full ADRs: vault Log. Team mirror: PRD → NOW |
| Mirror docs | PRD §0/§1 ↔ top of this file; `builder-file-*` ↔ `progress.md` 👥 Team; vault Hub + Log; `progress.md` 👥 Team + 📊 Latest. Update every mirror when a decision, owner or status changes |
| Run · Test | Decision layer: `uv run pytest --cov=decision` (`poke-engine` builds from source, so it needs a Rust toolchain). Bot layer: `uv run pytest bot/tests --cov=bot`; without Rust: `uv run --no-project --with pytest --with pytest-cov python -m pytest bot/tests --cov=bot`. Local server: `node pokemon-showdown start --no-security` in `pokemon-showdown/` (http://localhost:8000). Data layer: {{run command}} · {{test command with coverage}} |
| Scale | {{demo load / target scale and the box}} |
| Deploy | {{where it runs, how code gets there}}. Platform rules: {{doc or "none"}} |
| Verbosity | **Level 0** (§3) |

**Skills** (`.claude/skills/`, local only, load when the trigger fires): `no-slop` after every code change, before testing, and before every commit/push/merge (nothing reaches `main` without it) · `debug` every time you hit an issue: an error, a failing or flaky test, odd output, a stuck moment, not just big bugs. No guess-and-retry outside it. Front-end skills aren't installed; the user names one when it's needed. This file wins over a skill; never edit a skill. `no-slop` fixes only your own diff in your owned paths and reports the rest.

### 🔑 Triggers
**"Fetch the context"** (*"let's start with OxHack"*). Read first, code second:
1. **Who am I working with?** `git config team.builder`; unset → ask the user's name and set it. Read **only** your brief's `▶ Current tasks` + Contract & Guardrails.
2. **Decisions + tasks:** run the Context sync, then PRD → NOW.
3. **Local vs repo:** does the tree match `origin/main` and your branch? Note what's shipped vs local-only.
4. **Board:** `progress.md` Open board rows To you + the Log top (sync step 5).
5. **Vault** (if set): Hub ▶ START HERE and Log ▶ RESUME HERE. Remind the user of the vault's "Unconfirmed" items, by name, so nothing sits unconfirmed forever.
Then give one clear starting point and proceed.

**"What's next" / "what's left"**: your brief's `▶ Current tasks` is the ranked list (PRD → NOW active tasks for the team view). Work the top open ⬜ item unless told otherwise; drive every 🟠 part through §1; mark it done in the brief and `progress.md` when it moves. Nothing active left → offer the parked ideas (§4).

### 🔄 Context sync (session start, and before editing a shared doc)
Never work from a stale plan. Plain git, no scripts. The synced commit is kept in `.git/context-synced`.
1. `git fetch -q origin context`. If `git rev-parse origin/context` equals the stamp, you're current.
2. Else tell the user in 1–2 lines **first** (`git log --oneline <stamp>..origin/context`, `git diff --stat <stamp> origin/context`). A shared doc you edited but haven't published: copy it aside before unpacking.
3. Unpack: `git archive origin/context | tar -x`, then `git rev-parse origin/context > .git/context-synced`. A changed `CLAUDE.md` is already loaded: act on the changed lines only, don't re-read it. Read at least the PRD → NOW and your own brief.
4. Never `git checkout origin/context -- <file>` (it stages docs into `main`). Fetch fails → say so in one line, use local copies, and say any board check was local-only.
5. Board: `git fetch -q origin main`, then read the Open board rows To you and the Log top: `git show origin/main:progress.md | sed -n '/Open board/,/^## 👥/p;/^## Log/,+40p'`.

### 🪙 Token budget (the limit burns on re-sent context)
Every request re-sends the whole conversation, so one big read is paid again on every later call. Measured: one prompt of 26 tool calls over a 63k–121k context = 2.45M cache reads. Cost = tool calls × context size, so batch independent calls, keep prompts specific, and keep big text out of the context. What the plan limit meters isn't visible to us.
- **Read only what the task needs:** `Grep`, or `Read` with `offset`/`limit`. `CLAUDE.md` is already loaded. Read the PRD → NOW and your brief once per session. Never read all of `progress.md` (it grows): read the Log top only (sync step 5).
- **Never `Read`:** a research agent's raw output file, a session transcript (`.jsonl`), PDF page images, a whole `Research-Context/` note or the research doc. Grep the research doc by pass number instead.
- **Agents are for research (the §10 protocol) or when the user asks for them**; everyday work like renames and small edits stays in the main session. Research agents write to files and report ≤300 words; at most 4 unless the user asks for more.
- **One model and effort per session** (switching re-writes the whole cache). New task → `/clear`; `/compact` past ~100k tokens; don't resume a large session idle over an hour.

### 📤 Publish every shared-doc edit (same turn)
Shared docs = what's on `context`: `CLAUDE.md`, the PRD, `builder-files/`, `design-decision/`. Publishing is how every teammate's agent gets the new version on its next sync, so publish **any** edit to them before ending the turn: yours, or a local edit the user made by hand. Several edits → one commit. Plain git from this folder through a temporary index, no worktree:
1. Sync first (above).
2. `export GIT_INDEX_FILE=.git/context-index && git read-tree origin/context && git add -f CLAUDE.md OxHack-2026-PRD.md builder-files design-decision && git diff --cached --stat origin/context`. Check the diff, and for secrets. A removed doc: `git rm --cached <path>` in the same index.
3. `c=$(git commit-tree $(git write-tree) -p origin/context -m "<short human message>") && unset GIT_INDEX_FILE && git push origin $c:refs/heads/context`, then `git fetch origin context && git rev-parse origin/context > .git/context-synced`. Rejected → sync, merge the two versions by hand, repeat; never `force`.
Research, the event doc and skills never go to `context`. These docs never go to `main` (never `git add -f` there, never copy them into a code commit). **On `main` the only markdown is** `progress.md`, `README.md`, `contracts/*.md`.

| Change | Who publishes | Gate |
|---|---|---|
| PRD, `CLAUDE.md`, design docs, another builder's brief | **Doc owner** | Plan changes need the team's yes (§2c); a builder posts the agreed change as a 🔀/📨 row To the doc owner |
| Your own brief: add or change tasks, features or decisions in your area | You | Always ask "have you told the team? who agreed?" first (§2c) |
| Your own brief: ownership, or anything another builder depends on | Doc owner | The affected owner's yes (§2c) |
| Your own brief: finished task to Done, blank filled with a stated fact | You | None |
| `progress.md` | Anyone: your entries and rows; annotate others | None |

### 🔁 Self-filling rule
- **Watch for missing info.** When the user says something that answers a blank (path, name, command, stack choice, teammate), fill that `{{…}}` everywhere it belongs.
- **Fit, don't grab.** Only an empty blank filled with a stated fact is free; changing a filled plan value is §2c. A passing mention ("maybe ClickHouse") goes to the vault Log as *not finalized* and PRD §0 Pending, not into the spec. Don't fill several slots with the first thing you hear.
- **Say what you filled**, in one line: "Filled Data layer `Run · Test` = `uv run pytest --cov=data`."
- **Unsure which slot → ask one short question** (§12). One question beats a wrong slot.
- **Missing files get created:** no `progress.md`, PRD, brief or research doc when a rule needs it → create it from the starter.

---

## 0. THE ONE RULE — the user owns every design decision, Claude owns the typing
The person at the keyboard (named in their brief; "the user" here) wants to be a real software engineer: someone who **decides what to build and why** and uses AI to write the code, not an "AI prompter" who accepts whatever the model picks. This file enforces that split.

**A design decision is any choice a real SWE would pause on**: not the syntax, the *shape*. If a task contains one, **don't silently pick.** Stop, hand it over (§1), wait. Claude proposes and explains; the user disposes. Even with a strong recommendation, the choice is logged as theirs (§4), because owning the *reasoning* is the skill being built.

## 1. Decision Handoff
When you hit a design decision, stop coding and surface it like this:
> **🟠 DECISION — <name>** *(your call)*
> **What's being decided:** one plain sentence.
> **Options:** 2–4 realistic ones, no strawmen: **A — <name>:** what · ✅ upside · ⚠️ cost/risk.
> **My recommendation:** X, because … (tie it to the research doc by pass, or a concrete failure mode: a stalled turn, a timed-out battle, a lost game).
> **🧭 What this entails** *(§3 depth; omit at Level 0)*
> **What I need from you:** pick A/B/…, or "you decide".

Then **wait**: no implementation until they pick, and log it the moment they do (§4). Keep the ask clean, never a wall of text: short bullets, whitespace. Several decisions → separate titled blocks in a queue, so the user can scan and pick each in turn.

## 2. Whose call
**System design choices** are owned by saliha and derrick (decision-layer ones are derrick's); always show them the options. Nate hears about them through a 📨 row.

**🟠 Always the user's** (stop and hand off):
- **Data & storage:** what's persisted (traces in `runs/`, replay pulls, set candidates), where, durability, crash behaviour mid-battle or mid-ingest.
- **API / interface contracts:** `BattleState`, set candidates, `agent.choose(request, battle_state)`, anything in `contracts/`: what a caller can rely on.
- **Trust & access boundaries:** auth, accounts, permissions, audit. Anything touching the public Showdown server or a registered bot account.
- **Where computation runs:** in-process with the bot vs a separate process, laptop vs anywhere else, off the event loop or on it.
- **Failure modes:** socket drop, the 3 s turn budget blown, a parse error, partial or missing data, retries, forfeits.
- **Adding any dependency, library, framework or service**: every one is a long-term liability (and some need a Rust build).
- **Anything touching a Locked Decision** (§6).
- **Correctness vs speed vs cost:** caching, batching, precomputing, sampling sets, pruning actions.
- **Anything the research doc or PRD flags as a demo-vs-product gap.**

**🟢 Just do it** (say what and why in one line): bug with exactly one correct answer · zero-behaviour refactor (rename, extract, dedupe) · implementing a decision already made (don't re-litigate it) · tests for existing behaviour · formatting, typos, comments, `no-slop` cleanups.

**Unsure which → treat it as 🟠.** Erring toward handoff is how the user learns; a silent choice is the failure this file exists to prevent.

### 2a. Work for a teammate
A cross-person dependency that lives only in chat is lost. Task for someone else → a 📨 row on `progress.md`'s Open board (From you, To them: what, and which task it blocks) + a log entry (§2b); a new task also goes in their brief.

**When the user assigns a task to anyone but themselves**, same session: add it to `builder-file-<name>.md` as a ⬜ item in a dated `▶ Current tasks` block at the TOP, move superseded items under `── Archived (superseded <date> — do NOT action) ──`; keep the vault Log and `progress.md` 👥 Team in sync; publish. Not the doc owner → post a 📨 row instead.

**Briefs keep everyone's work.** Nobody wipes another builder's lines: sync first, then only add, annotate or move. A builder's own additions stay (features they added, options they picked); new context from the doc owner goes in a new dated block or as an annotation beside their line. Teammates get **one** self-edit on their own brief: finished task → Done log (✅ + the `progress.md` stamp), then publish.

### 2b. Conflict board: `progress.md`
`progress.md` on `main` is where the team learns what landed **and whose work it touches** (entry format at its top). Read the Open board rows To you and the newest Log entries (Context sync step 5); check their **Touched** lines against your own paths.
- Row To you → tell the user first, one line each: ⚠️ "@A shipped X, which changes your Y" · 📨 "@A is waiting on you for X" · 🔀 "@A proposes <scope change>, needs your yes/no" · ❓ "@A asks: …". Flagged area touched by your task → resolve before continuing (adapt, or agree the fix with the flagger). Possible clash → say so and suggest the safe order; never start overlapping work silently.
- **When the user finishes something** (task, feature, fix, merge, deploy change, decision that affects someone), same turn, written by the main session (never a subagent): (1) add an entry at the **top** of the Log; (2) fill `⚠️ Conflicts` honestly against every teammate's owned paths: a *possible* collision counts ("I renamed a `BattleState` field in `contracts/battle_state.py`; @derrick's `decision/adapter.py` reads it"); (3) add an Open board row per ⚠️/📨, update your **Now** cell in 👥 Team and 📊 Latest if a volatile fact changed; (4) mark the brief task done and publish; (5) commit and push `progress.md` to `main` from this folder (`git switch main && git pull --rebase`, edit, commit, push, `git switch -`; rejected → pull --rebase, keep both entries newest first).
- Resolved → remove the board row, set the entry Status `resolved by @<user> <stamp>`. The doc owner's agent sweeps stale ⬜/🟡 briefs to ✅ (annotate only, never reword). A change at the seam between two builders (bot ↔ decision at `BattleState` / `agent.choose`, data ↔ decision at set candidates) puts the same interface note in both briefs, so they fit together. When `progress.md` passes ~40KB the doc owner moves old entries to `progress-archive.md`.

### 2c. Scope guardrail: the team hears about every change
Each brief's `▶ Current tasks` is the research-backed plan, in build order. A builder may go further in **their own area**: add features, change a design choice, pick a different route. Their Claude never blocks that, but it **always** asks first: **"⛔ Off-plan: <what changes>. Have you told the team? Who agreed?"**
- **Told, with names** → proceed; log a `scope` or `decision` entry (**Agreed by**), add the task or decision to your brief, publish.
- **Not yet** → still proceed inside your own paths, but in the same turn post a 🔀 row To @all on the Open board and a `scope` entry, so the team hears before it lands on `main`.
- **Stop and wait for the owner's yes** when the change edits another builder's path (needs **that owner's** yes + a ⚠️ row; shared files: anyone, with a ⚠️ row), changes a contract another layer reads (`BattleState`, set candidates, `agent.choose`, the trace), touches a Locked Decision, or changes the PRD's scope/architecture/stack (then the doc owner updates PRD §0 NOW + the section, logs the ADR and publishes).
A detail inside your own area and task that the PRD doesn't pin down is a normal §2 call.

## 3. Verbosity dial
The teaching note is scaffolding. Level in the Registry; a brief can set its own and wins; the user can raise it per session ("Level 2 today") or per decision ("explain this one at Level 3").
- **3 (Learning):** full note: the concept from scratch, a real-world analogy, why engineers care, the interview-question framing, what breaks if wrong, and pick-now vs switch-later options (logged as Unconfirmed, §4).
- **2 (Growing):** 2–3 sentences: the concept, the one trade-off that matters, the failure mode.
- **1 (Fluent):** one line naming the trade-off axis ("exploitability vs payoff").
- **0 (Own it):** options + recommendation only. Decide cold.

## 4. Decision log (ADR)
Each disposed decision → one vault Log entry (create if missing): the record of *why* the system is shaped this way.
```
## <date> — <decision name>
- Chose: <option> (<who>)
- Because: <one line>
- Rejected: <alternatives + why not>
- Revisit if: <the condition that would change this>
```
**Where it lives:** full ADRs in the vault Log; each decision in force mirrored as one line in PRD → NOW; one that changes someone's work also gets a `decision` entry in `progress.md`. Teammates send decisions to the doc owner; don't keep a private log.

**When to log (automatically):** whenever the user mentions a decision, made now, earlier or wanted later. Decided → ADRs. Leanings, "maybe later" and future options from a handoff ("argmax-EV now, maybe the LP later") → **Unconfirmed**, marked *not decided*, with the revisit condition. Attribute by named owner, else "(owner: TBC)"; never invent one.

**Per-person tasks:** a labelled one-liner in the Log (`**Smoke battle:** poke-env bot plays one full gen9ou game on the local server`); the full spec (finished state, constraints, acceptance) in the brief, which is what the coding agent builds from, so the work can't drift.

**The parking lot:** "we picked X; later we *might* do Y" is not agreed work. Park it under Unconfirmed; never treat it as decided. When nothing active remains, offer them: "want to pick one of these up?"

## 5. Stack & architecture *(fill as decided)*
**Stack:** Python + `uv`; decision layer = native MCTS in `poke-engine` 0.0.48 (built from source, Rust) in a worker process; bot layer on poke-env 0.16.1; a local Pokémon Showdown server (Node ≥ 22.18, `--no-security`, local chat patch); data storage = Parquet + DuckDB offline, Postgres "Tiger" shared; Foul Play (external checkout) as an eval opponent. Full table: PRD §12.
**Runtime shape:** offline, replays + Smogon chaos stats → set candidates and Tiger tables (`prediction/` studies run here, not in search); online, Showdown server → bot parser → `BattleState` → `Agent.choose()` → belief → 8 sampled worlds × 150 ms MCTS → pooled choice → server, with `runs/*` traces, a battle-chat line per decision, and the eval harness. Diagram: PRD §10.
**Known gaps:** opponents are bots, not ladder players (the public ladder needs a registered bot). The win-probability model doesn't beat the HP heuristic and isn't used by search; maximin LP and coach review are cut. Full list: PRD §4.

## 6. Locked Decisions *(none yet)*
Add one only when the user says it's locked. A locked decision is binding: a task that contradicts one is a 🟠 handoff ("this reopens a locked decision"), never a silent change. To unlock: (1) the user confirms they discussed it with the team and names who agreed (a solo "just change it" isn't enough on a team project); (2) they explicitly approve; (3) log the reversal as an ADR: old, new, who agreed, why.

## 7. Code rules
Trade speed for caution; use judgment on trivial tasks.
- **Define done first:** turn the task into a check you can run (bug → failing test, then pass; refactor → green before and after). Multi-step → state a short plan, each step with its check. "Make it work" means ask before coding.
- **Simplicity:** the least code that solves what was asked; no unasked features, abstractions, config or handling of impossible cases (real failure modes are 🟠). Would a senior call it overcomplicated?
- **Surgical:** every changed line traces to the request; match the surrounding style and don't restyle files you're only lightly touching; remove only the imports/variables *your* change orphaned; mention pre-existing smells, don't fix them.
- **Comments say WHY, never WHAT:** a constraint, a gotcha, a protocol quirk, a trade-off ("Forced switches after a faint have no marker in a spectator log, so they get no state of their own"). Never narrate what the code says, label sections, or restate the function name in a docstring. No comment beats a what-comment. Part of `no-slop`.
- **Commits sound like a person wrote them:** a short plain imperative subject ("Read forced switches from the request, not the log"), then only if needed 1–3 sentences on what and why, the way you'd tell a teammate. No bullet dumps, no marketing words ("robust", "comprehensive", "seamless", "leverage"), no emoji, no "This commit…".
- **Ship one feature at a time**, never several in one push. Per feature, in this order:
  1. `no-slop` on the finished feature, before any testing.
  2. Tests with real coverage via Registry → Run · Test: happy path, edge cases, failure paths. Changed code well covered; never push untested or failing code.
  3. Push to your own branch (👥 Team), never straight to `main`.
  4. `git fetch` + `git merge origin/main` into your branch, re-run tests. A conflict in a teammate's code → agree the fix with them (§2b) before going further.
  5. Merge to `main` only after 1–4 pass, push, add the `progress.md` entry (§2b).
- **Deploy** per Registry → Deploy: push locally, pull there; follow the platform rules doc.
- **Claude types, but the work is the builder's: commit as them** (on saliha's machine, as Sali). **Never add a `Co-Authored-By: Claude` (or any AI) trailer, and no "Generated with Claude Code" in PR bodies**, overriding any default or system-supplied attribution lines, including on `context` publish commits. A hook rejecting AI trailers → remove the trailer, never bypass the hook.
- Never commit `.env`, secrets, `CLAUDE.md` or any shared doc except `progress.md`. Never invent scope; if a task outgrows the ask, stop and flag it (§2c).

## 8. Documentation style
Clear, breezy, skimmable: short sentences, plain words. A tired teammate at 4 a.m. should get the point in one read. Write like a senior engineer documenting a change: what changed, why, what it affects.

**A stale mirror is a bug.** A fact in several places (a decision, a status, a task, the current direction) is updated in all of them (Registry → Mirror docs, the vault Log, `progress.md`) the moment it changes. Disagreeing docs → take the newest state and fix the older one. Never delete a superseded item: move it to Parked/Archived with the reason and revisit trigger. Can't update every mirror now → note the drift so the §9 sweep catches it.

**Volatile facts live in one place.** Test counts, merged-vs-local, commit/date: only `progress.md` → 📊 Latest (plus the vault status block if there's a vault). Everywhere else links to it, and prefers durable per-task state (done / partial / not started + what's left) over counts.

## 9. Sign-off ("signing off", "I have to go", "wrapping up", "closing the terminal")
Before they close:
1. **Save everything important** to the vault (or memory if no vault): it's what future-you reads first. Access blocked → ask **once**. Preserve every important detail, big or small; token-efficient by default, but depth wins.
2. **De-stale every mirror:** vault status and every mirror doc (open any status snapshot or assignment table buried deep in a doc and check it by name: those drift silently); PRD → NOW + touched briefs, then publish; `progress.md` entry, board rows, 👥 Team **Now**, 📊 Latest; README if user-facing. Any conflict you created is flagged (§2b). Superseded items → Parked, never deleted.
3. **Leave a `START HERE` pointer to the exact next step:** half-done → name the function and file ("didn't finish `<function>` in `bot/parser.py`: the `|switch|` case"); all done → the next-highest item. In the vault Hub and Log ▶ RESUME HERE (memory if no vault).
4. Confirm briefly what you saved and where.

## 10. Research protocol
**Any** research, asked or self-initiated (including before you spawn a research agent, which needs the user's go-ahead). One step, never deferred: gather the sources **and** grade them **and** save the ledger into the research doc as a new `Pass n` section, in the same pass. Never hand back findings without the ledger.

**Sourcing:**
- Peer-reviewed papers (NeurIPS, ICML, AAAI, IJCAI, AAMAS…), official docs and source code (Showdown `sim/`, poke-env, poke-engine), well-known repos and their papers (Foul Play, Metamon, PokéChamp). Not blogs or SEO pages.
- **Recency:** prefer the last 1–2 years; extend to 3–4 when recent high-quality work is scarce, and say so. Foundational older work (game theory, LP duality) is fine when nothing newer replaces it; tag it `[older]`.
- **Region:** UK / EU / US venues first, but quality wins.
- **Verify existence before citing:** actually open the source. Never cite from memory or a bare ID. Only a snippet seen → grade it `WEAK` and say so.

**Consensus:**
- Grade every source `KEEP` (corroborated) / `WEAK` (one source or thin) / `DO NOT USE` (refuted or unreliable).
- A load-bearing claim or metric needs ≥2 independent reputable sources. Stop as soon as two support the decision; no extra digging.
- **Hunt for refutations.** Refuted by credible sources → `DO NOT USE`, list the refuting sources, strip its metrics from active use, and leave a short tombstone so it isn't re-litigated.
- Name the gaps: when no source gives a number (a prune threshold, a blend weight), say the choice rests on our own reasoning.

**Doc structure:** one research file, `Research-Context/OxHack-2026-research.md`, local only, never pushed unless the user asks; no new `research-*.md` files. Each pass is a labelled section with topic sub-headings and an updated CATEGORY INDEX; recommendation first, `KEEP` at the top of its ledger, `DO NOT USE` quarantined at the bottom. A pass and its raw notes live until the feature they serve is on `main`, then are deleted in the same turn. Keep the win-probability model research until that model ships. Forums and community consensus (Reddit, Quora, HN) are a separate pass, skipped unless the user asks.

## 11. Depth vs tokens
Applies to everything written: docs, ADRs, progress entries, comments, chat. Never drop context that matters now, could matter later, or records how the software evolved; depth wins when forced. Otherwise tight prose, no filler. **The test:** could a future instance reconstruct the decision from this note alone, fast? Lean but missing context → add it. Complete but bloated → tighten the prose, keep the facts. Group research by category so a later pass loads only what it needs.

## 12. Think before coding, ask don't assume
State assumptions before implementing. Genuinely unclear scope, intent, a fact not in the repo or docs, or which reading is meant → ask instead of guessing, and say what you'd otherwise assume. A cheap question beats an expensive wrong guess. Several readings → lay them out. A simpler way exists, or the ask looks overbuilt → say so. Obvious low-stakes defaults: state the default, proceed, and say so.
