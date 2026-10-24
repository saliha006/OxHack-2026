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

**Kinds:** ⚠️ conflict (my change touches your work) · 📨 waiting on (I'm blocked until you do X) · 🔀 scope proposal (needs
the whole team's yes, CLAUDE.md §2c) · ❓ question for a teammate (project-wide unknowns go in the PRD §21).

## 👥 Team
Full ownership and tasks live in each builder's brief (`builder-file-<name>.md` on `context`). Update your own **Now** cell
whenever you log an entry.

| Who | GitHub | Role | Branch | Owns (paths) | Now |
|---|---|---|---|---|---|
| Saliha | `saliha006` | Bot layer; doc owner | `sali` | `bot/` {{paths tbd}} | brief task 1: decide the bot skeleton (poke-env / local server / format) |
| Nate | `aldrichbanas07` | Data layer | {{nate's branch}} | `data/` {{paths tbd}} | brief task 1: start the ladder snapshotter |
| Derrick | `RandomGeeb` | Decision layer | `derrick` | `decision/`, `tests/`, `contracts/battle_state.py` | brief task 2: merge `derrick` to `main` (code only) |

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
- **On branches, not merged yet:** `derrick`: decision layer `our_actions`, `select`, `simulate`, `our_side`, `value`, `build_state`, `opp_actions`, `Belief` (113 tests, 100% coverage)

---

## Log (newest first)

### 2026-10-24 18:30 — decision — Bot layer is saliha's; `last_move` resets on switch; Derrick's notes 02-05 published — @saliha
- **Where:** `context` @ `cb32fd0` (docs only) · merged to `main`: n/a
- **Did:** (1) saliha owns the bot layer and the log parser; as doc owner saliha waived a separate yes from Nate (the bot layer meets the data layer only through `BattleState`), Nate is informed and can object here. (2) Answer to Derrick's ⚠️: yes, the parser resets `sides[*].last_move` to null when that side switches; Derrick please spell it out in `contracts/battle-state.md`. (3) The parser will emit `Event.source` exactly as the contract examples spell it (`"stealthrock"`, `"item:<id>"`). (4) Published `design/decision/02..05-*.md` from `derrick` @ `e4cef23`; the earlier 12 docs were already out.
- **Touched:** `design/decision/02-05`, `builder-file-saliha.md`, PRD NOW
- **Brief task:** saliha tasks 1-5 unchanged; the Nate wait tag removed from task 3
- **⚠️ Conflicts:** none
- **📨 Needs:** @derrick: add the `last_move` rule to the contract. @nate: review `contracts/set-candidates.md` (Derrick's 18:14 entry). The user picks the (a)-(e) build choices and the bot skeleton on the main account
- **Agreed by:** saliha, derrick (proposer); nate informed
- **Status:** resolved by @saliha 2026-10-24 18:30 (the 🔀, ⚠️ and 📨 rows above are cleared)

### 2026-10-24 18:17 — feat — Decision layer: belief (hard filter + sampling) on hand-made priors — @derrick
- **Where:** `derrick` @ `7ca09bb` · merged to `main`: not yet
- **Did:** `Belief(priors, battle)` keeps each opponent slot's set weights for the battle. `update()` filters on revealed moves/item/ability/Tera and four implied-item rules (Choice, Assault Vest, Leftovers, Boots), rebuilding from usage when nothing fits. `scenarios(k=5)` gives the active's top 5 with the bench at its best guess. Soft reweight (04) is next. 113 tests, 100% coverage.
- **Touched:** `decision/belief.py`, `tests/test_belief.py`
- **Brief task:** 4 → 🟡 part (logic on hand-made priors; real set file waits on @nate)
- **⚠️ Conflicts:** @saliha: the rules read `Event.source` values `"stealthrock"` and `"item:<id>"` exactly as the contract's examples spell them
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:14 — decision — Derrick drafts the SetCandidates contract; belief logic starts ahead of the merge — @derrick
- **Where:** `derrick` @ `f9744ee` · merged to `main`: not yet
- **Did:** Drafted the per-species set file the data layer builds and the decision layer's belief loads (`contracts/set-candidates.md`, `contracts/set_candidates.py`, example with real 2026-09 1825 usage). Derrick's contents decisions: chaos 1825 / 2026-09, sets combined from usage shares, 30 per species, no teammate data, no "other" set. Starting brief task 4's belief logic (hard filter, reweight, sampling) on hand-made sets before task 2 (the merge).
- **Touched:** `contracts/set-candidates.md`, `contracts/set_candidates.py`, `contracts/examples/set_candidates_example.json`, `tests/test_set_candidates_contract.py`
- **Brief task:** 4 in builder-file-derrick.md → 🟡 part (logic only; the set file is @nate's)
- **⚠️ Conflicts:** @nate: this defines the shape of your set-candidates output (`data/`), please review before building it
- **📨 Needs:** @nate: yes/no on the contract and the file path (proposed `data/set_candidates.json`). @saliha: publish the 02-05 decision notes from `origin/derrick` (`design/decision/02..05-*.md`)
- **Status:** open

### 2026-10-24 18:00 — docs — Research merged, builder briefs filled, Derrick's docs published — @saliha
- **Where:** `context` @ `1163870` (docs only) · merged to `main`: n/a
- **Did:** Merged six research passes into `OxHack-2026-research.md` (READ THIS FIRST at the top). Published Derrick's 12 decision-layer feature docs and his research section 7. Filled `builder-file-saliha/nate/derrick.md` from the template and 👥 Team below. CLAUDE.md halved; research protocol is now the `research-protocol` skill; Read guard + active-session warning added to the prompt hook.
- **Touched:** `OxHack-2026-research.md`, `design/decision*`, `builder-files/*`, `CLAUDE.md`, `scripts/prompt-check.sh`
- **Brief task:** briefs created for all three builders
- **⚠️ Conflicts:** none. Each builder should read their brief once and fix the "Open blanks" list in it
- **📨 Needs:** @nate: yes/no on saliha owning the bot layer, your branch name and `data/` paths; run `bash scripts/prompt-check.sh --install-guard` once. @derrick: same install
- **Status:** open

### 2026-10-24 17:51 — feat — Decision layer: Struggle, and Encore no longer crashes the engine — @derrick
- **Where:** `derrick` @ `bd84938` (code) · docs handed off at `9c98381` · merged to `main`: not yet
- **Did:** When Choice lock / Encore / Taunt leave the opponent no usable move, `build_state` gives it Struggle (poke-engine only runs it from the move list). Fixed a crash: poke-engine panics on any Encored side unless `last_used_move` is set, which the adapter now does. Found: poke-engine's gen9 Struggle is a Normal-type move with no recoil (real one is typeless, ¼ recoil). 96 tests, 100% coverage.
- **Touched:** `decision/adapter.py`, `decision/opponent.py`, `tests/test_opponent.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none
- **📨 Needs:** @saliha: publish the decision-layer docs from `origin/derrick` (Open board row). The publish script only lets the doc owner publish them
- **Status:** open

### 2026-10-24 17:41 — feat — Decision layer: opponent options + uniform policy — @derrick
- **Where:** `derrick` @ `82e0eb6` · merged to `main`: not yet
- **Did:** `opp_actions(state, battle)` lists the opponent's moves, Tera moves (while unused) and switches; Choice lock, Encore and Taunt limit them. `uniform_policy()` gives each move/switch an equal share, split with its Tera copy. Adds a `moves.json` snapshot for move categories. 92 tests, 100% coverage.
- **Touched:** `decision/opponent.py`, `decision/data/moves.json`, `tests/test_opponent.py`, `tests/turn2.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** @saliha: relies on `BattleState.sides[*].last_move` being reset when the active Pokémon switches out (Choice lock / Encore)
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 17:20 — decision — saliha accepts the bot layer + log parser; waiting on Nate — @saliha
- **Where:** PRD §0 NOW (published to `context`) · merged to `main`: n/a (docs only)
- **Did:** Answered Derrick's 🔀 proposal: saliha owns the bot layer and builds the parser that fills the `BattleState` contract. Not agreed yet: Nate's yes (§2c). Research for the data, decision and bot layers is running; notes land in the research doc.
- **Touched:** none in code
- **Brief task:** none
- **⚠️ Conflicts:** none
- **📨 Needs:** @nate: yes/no on saliha owning the bot layer. @derrick: push `design/decision/*.md` to `context` (not there yet; `design/decision-layer.md` is)
- **Agreed by:** saliha, derrick (proposer); nate pending
- **Status:** open

### 2026-10-24 17:05 — feat — Decision layer: full poke-engine state from a request + BattleState — @derrick
- **Where:** `derrick` @ `a104fb4` · merged to `main`: not yet
- **Did:** `build_state(request, battle_state, sets)` builds the whole turn state: our team from the request, the opponent + field from `BattleState`, hidden opponent details from one guessed set per slot (nature + EVs → stats). Revealed info beats the guess. Tested on the contract's turn-2 example. 81 tests, 100% coverage.
- **Touched:** `decision/adapter.py`, `decision/sets.py`, `tests/test_adapter.py`, `tests/test_sets.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none (reads `contracts/battle_state.py`; the parser that fills it is the open 🔀 proposal to @saliha)
- **📨 Needs:** none new

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

