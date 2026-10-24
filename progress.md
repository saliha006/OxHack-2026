# OxHack-2026: progress log and conflict board

The one shared doc that lives on `main`. It's where the team, and every teammate's agent, sees who shipped what, when, on
which branch, whose work it touches, and who is waiting on whom. The plan itself (`CLAUDE.md`, the PRD, the briefs) lives
on the `context` branch; this file is the history.

> **Template.** Fill `{{…}}` as the project's details arrive. Delete this note when the first real entry lands.

## How this file works (read once)
- **Newest first.** A new entry goes at the top of the Log. Stamps are `YYYY-MM-DD HH:MM` in {{timezone}}, so top to
  bottom is newest to oldest.
- **One entry per finished thing:** a feature, a fix, a deploy or infra change, a decision that changes someone's work, or
  a scope change. Not one per work-in-progress commit.
- **Write it in the same turn you push**, then commit and push `progress.md` to `main` straight away. The board is never behind.
- **Every ⚠️ conflict and 📨 need also gets a row on the Open board.** The row is removed once it's resolved, and the entry's
  Status line records who resolved it. Entries are history: never delete or reword someone else's, only annotate.
- **Merge conflict in this file?** Keep both sides, sorted newest first. Never drop an entry.
- **Volatile facts** (current commit, test counts, deploy status) live only in 📊 Latest.
- Agents: when to read and write this file is CLAUDE.md §2b; scope changes are §2c.

**Entry format** (copy it to the top of the Log):
```
### <YYYY-MM-DD HH:MM> — <feat | fix | deploy | decision | scope | docs> — <what, in plain words> — @<builder>
- **Where:** `<branch>` @ `<short sha>` · merged to `main`: yes | not yet
- **Did:** <what changed and why, 1–3 lines; numbers if you measured something>
- **Touched:** <files / modules / endpoints / contracts / infra>
- **Brief task:** <task n in builder-file-<name>.md> → ✅ done | 🟡 part | none
- **⚠️ Conflicts:** @<Name>: <what of theirs this changes or could break, and what they should do> | none
- **📨 Needs:** @<Name>: <what you need from them, and which of your tasks it blocks> | none
- **Agreed by:** @<Name>, @<Name> (decision and scope entries only)
- **Status:** open | resolved by @<Name> <YYYY-MM-DD HH:MM> (only when Conflicts or Needs isn't none)
```

---

## 📌 Open board (read on every prompt)
Everything still waiting on someone. Look for your name, or `@all`, under **To**.

| Since | From | To | Kind | What, and what to do | Entry |
|---|---|---|---|---|---|
| 2026-10-24 16:46 | @derrick | @saliha, @nate | 🔀 scope proposal | **saliha owns the bot layer and builds the log parser**, producing the `BattleState` JSON Derrick drafted (`contracts/battle-state.md` + `contracts/battle_state.py` + an example, on `derrick`). The decision layer is blocked on it for the opponent side. Next: saliha yes/no on owning it + review the shape; Nate yes/no on the ownership | 2026-10-24 16:46 |
| 2026-10-24 16:00 | @derrick | @saliha | 📨 waiting on | Publish Derrick's decision-layer docs (the publish script only lets you): `design/decision-layer.md` + new `design/decision/*.md`, on `derrick`'s working copy. Also note: decision layer is **Python** (not TS); Registry `Run · Test` = `uv run pytest --cov=decision`; feature 07 is blocked until the bot layer defines `BattleState`. Next: publish, or tell Derrick what to change | 2026-10-24 16:00 |

**Kinds:** ⚠️ conflict (my change touches your work) · 📨 waiting on (I'm blocked until you do X) · 🔀 scope proposal (needs
the whole team's yes, CLAUDE.md §2c) · ❓ question for a teammate (project-wide unknowns go in the PRD §21).

## 👥 Team
Full ownership and tasks live in each builder's brief (`builder-file-<name>.md` on `context`). Update your own **Now** cell
whenever you log an entry.

| Who | GitHub | Role | Branch | Owns (paths) | Now |
|---|---|---|---|---|---|
| {{Name}} | `{{handle}}` | {{area; extra role, e.g. doc owner, deploy owner}} | `{{branch}}` | `{{paths}}` | {{brief task n: one line}} |

**Shared** (anyone may edit; flag it in ⚠️ Conflicts): {{e.g. `contracts/*`, `fixtures/*`, compose files}}

## 🚀 Start here (new teammate, first 15 minutes)
1. Clone `https://github.com/saliha006/OxHack-2026`. Set `git config user.email` to your GitHub email (commits are credited by author) and
   `git config team.builder <your-name>` (the scripts and the Open board use it). {{Any other one-time git setup}}
2. `bash scripts/sync-context.sh` pulls `CLAUDE.md`, the PRD, your brief and the skills. After that the prompt hook
   re-syncs before every prompt. Codex: run `bash scripts/prompt-check.sh` at the start of each task (AGENTS.md).
3. Read your brief's `▶ Current tasks`, then the 📌 Open board above.
4. {{Access to the deploy target, data and secrets: where each lives. Never in git or chat}}

## 📊 Latest (volatile facts live only here)
- **As of {{YYYY-MM-DD HH:MM}}:** `main` @ `{{sha}}` · tests: {{n}} green, {{x}}% coverage · deploy: {{status, URL}}
- **On branches, not merged yet:** `derrick`: decision layer `our_actions`, `select`, `simulate`, `our_side`, `value` (59 tests, 100% coverage)

---

## Log (newest first)

### 2026-10-24 16:46 — scope — Proposal: saliha owns the bot layer and builds the log parser to Derrick's BattleState contract — @derrick
- **Where:** `derrick` @ `e98b302` · merged to `main`: not yet
- **Did:** Drafted the `BattleState` contract (what the parser hands the decision layer each turn, as JSON): both sides in the same shape, field, and last turn's events; Showdown IDs and 0–100 HP. Real example from turn 2 of replay `gen9ou-2703852247`, plus a test that keeps example and types in step.
- **Touched:** `contracts/battle-state.md`, `contracts/battle_state.py`, `contracts/examples/battle_state_turn2.json`, `tests/test_battle_state_contract.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none yet (no bot layer code exists)
- **📨 Needs:** @saliha: yes/no on owning the bot layer + building the parser; review the contract. @nate: yes/no on the ownership
- **Agreed by:** not yet (proposal)
- **Status:** open

### 2026-10-24 16:31 — feat — Decision layer: heuristic value + looser selector ties — @derrick
- **Where:** `derrick` @ `0ca12e4` · merged to `main`: not yet
- **Did:** `value(state)` scores a position 0–1 (0.5 = even): each Pokémon = alive + HP fraction, ours vs theirs. Same scale as the planned win-probability model. The selector's tie tolerance is now 1e-6, matching poke-engine's 32-bit probabilities. 59 tests, 100% coverage.
- **Touched:** `decision/value.py`, `decision/selector.py`, `tests/test_value.py`, `tests/test_selector.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none
- **📨 Needs:** none

### 2026-10-24 16:23 — feat — Decision layer: our poke-engine side from a Showdown request — @derrick
- **Where:** `derrick` @ `e6cc855` · merged to `main`: not yet
- **Did:** `our_side(request)` builds our team as a poke-engine `Side` (HP, status, stats, moves + PP, item, ability, Tera) in request order. Types and weight come from a committed snapshot of Showdown's `pokedex.json`. State is rebuilt every turn (no memory). 47 tests, 100% coverage.
- **Touched:** `decision/state.py`, `decision/data/pokedex.json` (524 KB), `tests/test_state.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): boosts, volatiles, hazards, weather and the whole opponent side must come from `BattleState`; the request doesn't carry them | none else
- **📨 Needs:** none new
- **Status:** open (the bot layer note above)

### 2026-10-24 16:13 — feat — Decision layer: one-turn simulation via poke-engine — @derrick
- **Where:** `derrick` @ `50b9a77` · merged to `main`: not yet
- **Did:** `simulate(state, ours, theirs)` returns every outcome of a turn as (probability, next state), using poke-engine (Rust, built from source with its gen9 Tera feature). Replaying turn 1 of a real gen9ou game matches the log (Kingambit 66%). 0.038 ms per call. 31 tests, 100% coverage.
- **Touched:** `decision/simulate.py`, `tests/test_simulate.py`, `pyproject.toml` (new dependency `poke-engine==0.0.48`; building it needs Rust)
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): the decision layer now works in poke-engine's `State`, so whatever `BattleState` becomes gets converted to it once per turn (feature 01, decision side) | none else
- **📨 Needs:** none new
- **Status:** open (the bot layer note above)

### 2026-10-24 16:00 — feat — Decision layer: legal actions from a request, and the action selector — @derrick
- **Where:** `derrick` @ `b27a235` · merged to `main`: not yet (`derrick` was branched from `context`, so its shared docs must come off before a merge)
- **Did:** `our_actions(request)` lists our legal moves / Tera moves / switches / leads from Showdown's raw `|request|` JSON. `select()` picks the highest expected value over opponent actions × sets, tie-break on worst case. Python + uv + pytest; 25 tests, 100% coverage.
- **Touched:** `decision/actions.py`, `decision/selector.py`, `tests/`, `pyproject.toml`, `uv.lock`, `.gitignore`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): the decision layer is Python, so the bot ↔ decision seam crosses languages if the bot is TS | none else
- **📨 Needs:** @saliha: publish the decision-layer docs, record Python + the test command (Open board row). Bot layer owner: `BattleState`, which feature 07 is blocked on
- **Status:** open

