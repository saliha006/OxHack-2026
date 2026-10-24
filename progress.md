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
| 2026-10-24 20:36 | @saliha | @derrick | ⚠️ conflict | The parser is on `main`: `from bot.parser import Parser, states_from_log`. `Parser(us).feed(line)` per protocol line, `.snapshot()` per request. Unblocks your task 3 (build_state on a parser-made BattleState) | 2026-10-24 20:36 |
| 2026-10-24 20:36 | @saliha | @nate | ⚠️ conflict | The parser is on `main`: `states_from_log(log_lines, us)` gives one `BattleState` per turn of a saved replay, for your (state, winner) pairs | 2026-10-24 20:36 |
| 2026-10-24 20:15 | @saliha | @derrick | 📨 waiting on | New tasks 6–9 in your brief (trace, turn-time profile, win-probability model, maximin LP); the model and LP are your calls. The bot will need `poke-env==0.16.1` in your `pyproject.toml`: OK to add? | 2026-10-24 20:15 |
| 2026-10-24 20:15 | @saliha | @nate | 📨 waiting on | New tasks 6–8 in your brief: seeded gen9ou team pool (~60 validated teams), eval and demo charts, data card. Training states should come from saliha's parser | 2026-10-24 20:15 |
| 2026-10-24 19:16 | @saliha | @all | ⚠️ conflict | `scripts/` and every skill except `debug` and `no-slop` are gone from `context`. Keep your local copies (they stay git-ignored); `sync`/`publish` won't update from `context` any more | 2026-10-24 19:16 |
| 2026-10-24 18:14 | @derrick | @nate | ⚠️ conflict | `contracts/set-candidates.md` (on `derrick`) defines the set file your data layer would build for belief: 30 weighted sets per species + trimmed usage, chaos 1825 / 2026-09. Next: yes/no on the shape and on `data/set_candidates.json` as its path | 2026-10-24 18:14 |

**Kinds:** ⚠️ conflict (my change touches your work) · 📨 waiting on (I'm blocked until you do X) · 🔀 scope proposal (needs
the whole team's yes, CLAUDE.md §2c) · ❓ question for a teammate (project-wide unknowns go in the PRD §21).

## 👥 Team
Full ownership and tasks live in each builder's brief (`builder-file-<name>.md` on `context`). Update your own **Now** cell
whenever you log an entry.

| Who | GitHub | Role | Branch | Owns (paths) | Now |
|---|---|---|---|---|---|
| Saliha | `saliha006` | Bot layer; doc owner | `sali` | `bot/` {{paths tbd}} | brief task 1: decide the bot skeleton (poke-env / local server / format) |
| Nate | `aldrichbanas07` | Data layer | {{nate's branch}} | `data/` {{paths tbd}} | brief task 1: start the ladder snapshotter |
| Derrick | `RandomGeeb` | Decision layer | `derrick` | `decision/`, `tests/`, `contracts/battle_state.py` | feature 11 built on `derrick`; tasks 3–4 wait on the parser and set candidates |

**Shared** (anyone may edit; flag it in ⚠️ Conflicts): {{e.g. `contracts/*`, `fixtures/*`, compose files}}

## 🚀 Start here (new teammate, first 15 minutes)
1. Clone `https://github.com/saliha006/OxHack-2026`. Set `git config user.email` to your GitHub email (commits are credited by author) and
   `git config team.builder <your-name>` (the scripts and the Open board use it). {{Any other one-time git setup}}
2. `bash scripts/sync-context.sh` pulls `CLAUDE.md`, the PRD, your brief and the skills. After that the prompt hook
   re-syncs before every prompt. Codex: run `bash scripts/prompt-check.sh` at the start of each task (AGENTS.md).
3. Read your brief's `▶ Current tasks`, then the 📌 Open board above.
4. {{Access to the deploy target, data and secrets: where each lives. Never in git or chat}}

## 📊 Latest (volatile facts live only here)
- **As of 2026-10-24 20:36:** `main` @ `c25be7e` · tests: decision 140 green, 100% coverage (`uv run pytest --cov=decision`); bot 25 green, 100% coverage (`uv run pytest bot/tests --cov=bot`) · deploy: none yet
- **On branches, not merged yet:** @derrick `derrick` @ `a50936e`: feature 11 (type-matchup lead), 144 tests green, 100% coverage

---

## Log (newest first)

### 2026-10-24 20:36 — feat — Bot layer: log parser to BattleState — @saliha
- **Where:** `sali` @ `c25be7e` · merged to `main`: yes (fast-forward)
- **Did:** `bot/parser.py` turns Showdown protocol lines into the contract's `BattleState`. It's pure, so live battles and saved replays use the same code. Replay `gen9ou-2703852247` turn 2 equals `contracts/examples/battle_state_turn2.json`; 20 recent public gen9ou games (383–457 turns) parse with no skipped line. 25 tests, 100% coverage on `bot/`.
- **Touched:** `bot/__init__.py`, `bot/parser.py`, `bot/tests/test_parser.py`, `bot/tests/fixtures/gen9ou-2703852247.log`
- **Brief task:** saliha task 3 ✅
- **⚠️ Conflicts:** @derrick, @nate: new shared entry point (Open board rows). No contract field changed meaning
- **📨 Needs:** none
- **Status:** open (the notes to @derrick, @nate)

### 2026-10-24 20:15 — decision — Bot runs on poke-env, gen9ou, local server; all three briefs get the demo plan — @saliha
- **Where:** `context` @ `538549d` · merged to `main`: n/a (docs branch)
- **Did:** Picked poke-env 0.16.1 (a `Player` subclass tapping raw lines and calling `Agent.choose`) on gen9ou with one fixed team and a seeded opponent pool, on a local Showdown server (research pass 8). Briefs now cover a working demo: parser, wiring, decision trace, eval harness vs poke-env's three baselines, demo mode. The PRD's architecture and stack are filled from what's built. saliha and derrick own design choices; decision-layer ones are derrick's.
- **Touched:** `context`: PRD, `CLAUDE.md`, research doc, all three briefs, `design/DESIGN.md`, `design/bot-layer.md`
- **Brief task:** saliha task 1 ✅
- **⚠️ Conflicts:** @derrick: the bot adds `poke-env` to `pyproject.toml` (yours). @nate: new tasks in your brief
- **📨 Needs:** @derrick: OK on the dependency, and your calls on tasks 8–9. @nate: read tasks 6–8
- **Status:** open

### 2026-10-24 19:26 — feat — Decision layer: lead picked by type matchup at team preview — @derrick
- **Where:** `derrick` @ `a50936e` · merged to `main`: not yet
- **Did:** Feature 11. At preview each of our six is scored on STAB type matchups against the opponent's six (log₂ of our best multiplier minus theirs, immunity floored at ×0.25); best leads, back five keep order. Forced switches keep the main-loop scoring. Type chart snapshot at `decision/data/typechart.json`. 144 tests, 100% coverage.
- **Decided:** lead = type-matchup rule (C), forced switch = reuse the main loop (A), both by @derrick. Revisit the lead if it loses turn 1 often in real games; the switch if the value model upgrade is cut.
- **Touched:** `decision/lead.py`, `decision/agent.py`, `decision/actions.py` (comment), `decision/data/typechart.json`, `tests/test_lead.py`, `tests/test_agent.py`
- **Brief task:** none listed (feature 11 is in the brief's scope contract); Done log line written locally, not published
- **⚠️ Conflicts:** none: preview still answers `team ……` through `Agent.choose`, so the bot's interface is unchanged
- **📨 Needs:** @saliha: publish the feature 11 docs + brief line, mirror the decisions in PRD → NOW, and look at the publish script refusing non-owners since the trim (Open board row)
- **Status:** open (the row to @saliha)

### 2026-10-24 19:16 — docs — Context branch trimmed; Derrick's feature 12 docs published — @saliha
- **Where:** `context` @ `54086aa` · merged to `main`: n/a (docs branch); `.gitignore` on `main`
- **Did:** Published `design/decision/12-budget-fallback.md` and the §7 tick from `derrick`, which closes both of Derrick's publish rows. Removed the duplicate `.claude/`, `scripts/` and every skill except `debug` and `no-slop` from `context`. `main`'s `.gitignore` now also ignores `.claude/`, `scripts/`, `builder-files/`, `design/`, `skills/` and `Research-Context/`.
- **Touched:** `context` branch, `.gitignore`
- **Brief task:** none
- **⚠️ Conflicts:** @all: `scripts/` is no longer on `context`, so a fresh clone can't bootstrap the sync hook from it
- **📨 Needs:** none
- **Status:** open (the note to @all)

### 2026-10-24 18:50 — feat — Decision layer: 3 s turn budget and a fallback that never stalls — @derrick
- **Where:** `derrick` @ `a57313e` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `Agent.choose()` always answers: a 3 s budget (most likely scenarios first, best-so-far when time's up), and any error is logged with the turn and replaced by the first legal option, or `default` if even that fails. 140 tests, 100% coverage.
- **Touched:** `decision/agent.py`, `tests/test_agent.py`
- **Brief task:** none new
- **⚠️ Conflicts:** @saliha: `choose()` never raises now; decision errors appear on the `decision` logger, so the bot should send its logs somewhere visible. It can also return `"default"`
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:40 — feat — Decision layer: the turn loop runs end to end — @derrick
- **Where:** `derrick` @ `640216c` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `Agent(priors).choose(request, battle)` turns a Showdown request + BattleState into a choice string, running belief → 5 scenarios → build_state → both sides' actions → simulate → value → select. Selector now takes the opponent's odds per set. Team preview and forced switches have stand-ins until feature 11. A full move decision takes well under a second in tests. 135 tests, 100% coverage.
- **Touched:** `decision/agent.py`, `decision/selector.py`, `tests/test_agent.py`, `tests/test_selector.py`
- **Brief task:** none new (the core loop is task 1, already ✅; belief task 4 still 🟡)
- **⚠️ Conflicts:** @saliha: the bot's whole hook into the decision layer is one call per request: `agent.choose(request_dict, battle_state) -> "move 2" | "switch 4" | "team 123456" | None` (None on a wait), with one `Agent(priors)` per battle
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:32 — docs — BattleState contract: last_move reset and Event.source spellings written in — @derrick
- **Where:** `derrick` @ `eb56c61` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Answered saliha's 18:30 ask: `contracts/battle-state.md` + `battle_state.py` now say `last_move` resets to null when that side switches, and list the exact `Event.source` strings belief matches. No field changed meaning.
- **Touched:** `contracts/battle-state.md`, `contracts/battle_state.py`
- **Brief task:** none
- **⚠️ Conflicts:** none (writes down what saliha already agreed)
- **📨 Needs:** @saliha: publish the newer 03-05 + decision-layer.md (Open board row)
- **Status:** open → publish asks resolved by @saliha 2026-10-24 19:16 (`context` @ `54086aa`)

### 2026-10-24 18:29 — feat — Decision layer: soft reweight by replaying each turn in poke-engine — @derrick
- **Where:** `derrick` @ `7fb50c3` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Belief now replays last turn per candidate set (the loop calls `belief.chose(request, action)` after choosing) and drops sets the engine can't square with the observed move order or damage (both ways, crits included, ±1 for rounding). Speed ties, flinches, U-turn pivots and KOs handled; switches, one-sided turns and multi-hit moves give no evidence. 126 tests, 100% coverage.
- **Touched:** `decision/belief.py`, `decision/simulate.py` (`engine_move` now public), `tests/test_reweight.py`
- **Brief task:** 4 → 🟡 part (all belief logic built on hand-made priors; the real set file and the "beats uniform log loss" check wait on @nate's data)
- **⚠️ Conflicts:** @saliha: belief reads event order within `last_turn` (move → damage) and each damage event's `crit`; `hit_count` is parked in the contract for multi-hit moves
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

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
- **Where:** `derrick` @ `7ca09bb` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `Belief(priors, battle)` keeps each opponent slot's set weights for the battle. `update()` filters on revealed moves/item/ability/Tera and four implied-item rules (Choice, Assault Vest, Leftovers, Boots), rebuilding from usage when nothing fits. `scenarios(k=5)` gives the active's top 5 with the bench at its best guess. Soft reweight (04) is next. 113 tests, 100% coverage.
- **Touched:** `decision/belief.py`, `tests/test_belief.py`
- **Brief task:** 4 → 🟡 part (logic on hand-made priors; real set file waits on @nate)
- **⚠️ Conflicts:** @saliha: the rules read `Event.source` values `"stealthrock"` and `"item:<id>"` exactly as the contract's examples spell them
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:14 — decision — Derrick drafts the SetCandidates contract; belief logic starts ahead of the merge — @derrick
- **Where:** `derrick` @ `f9744ee` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
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
- **Where:** `derrick` @ `bd84938` (code) · docs handed off at `9c98381` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** When Choice lock / Encore / Taunt leave the opponent no usable move, `build_state` gives it Struggle (poke-engine only runs it from the move list). Fixed a crash: poke-engine panics on any Encored side unless `last_used_move` is set, which the adapter now does. Found: poke-engine's gen9 Struggle is a Normal-type move with no recoil (real one is typeless, ¼ recoil). 96 tests, 100% coverage.
- **Touched:** `decision/adapter.py`, `decision/opponent.py`, `tests/test_opponent.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none
- **📨 Needs:** @saliha: publish the decision-layer docs from `origin/derrick` (Open board row). The publish script only lets the doc owner publish them
- **Status:** open

### 2026-10-24 17:41 — feat — Decision layer: opponent options + uniform policy — @derrick
- **Where:** `derrick` @ `82e0eb6` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
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
- **Where:** `derrick` @ `a104fb4` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `build_state(request, battle_state, sets)` builds the whole turn state: our team from the request, the opponent + field from `BattleState`, hidden opponent details from one guessed set per slot (nature + EVs → stats). Revealed info beats the guess. Tested on the contract's turn-2 example. 81 tests, 100% coverage.
- **Touched:** `decision/adapter.py`, `decision/sets.py`, `tests/test_adapter.py`, `tests/test_sets.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none (reads `contracts/battle_state.py`; the parser that fills it is the open 🔀 proposal to @saliha)
- **📨 Needs:** none new

### 2026-10-24 16:46 — scope — Proposal: saliha owns the bot layer and builds the log parser to Derrick's BattleState contract — @derrick
- **Where:** `derrick` @ `e98b302` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Drafted the `BattleState` contract (what the parser hands the decision layer each turn, as JSON): both sides in the same shape, field, and last turn's events; Showdown IDs and 0–100 HP. Real example from turn 2 of replay `gen9ou-2703852247`, plus a test that keeps example and types in step.
- **Touched:** `contracts/battle-state.md`, `contracts/battle_state.py`, `contracts/examples/battle_state_turn2.json`, `tests/test_battle_state_contract.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none yet (no bot layer code exists)
- **📨 Needs:** @saliha: yes/no on owning the bot layer + building the parser; review the contract. @nate: yes/no on the ownership
- **Agreed by:** not yet (proposal)
- **Status:** open

### 2026-10-24 16:31 — feat — Decision layer: heuristic value + looser selector ties — @derrick
- **Where:** `derrick` @ `0ca12e4` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `value(state)` scores a position 0–1 (0.5 = even): each Pokémon = alive + HP fraction, ours vs theirs. Same scale as the planned win-probability model. The selector's tie tolerance is now 1e-6, matching poke-engine's 32-bit probabilities. 59 tests, 100% coverage.
- **Touched:** `decision/value.py`, `decision/selector.py`, `tests/test_value.py`, `tests/test_selector.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none
- **📨 Needs:** none

### 2026-10-24 16:23 — feat — Decision layer: our poke-engine side from a Showdown request — @derrick
- **Where:** `derrick` @ `e6cc855` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `our_side(request)` builds our team as a poke-engine `Side` (HP, status, stats, moves + PP, item, ability, Tera) in request order. Types and weight come from a committed snapshot of Showdown's `pokedex.json`. State is rebuilt every turn (no memory). 47 tests, 100% coverage.
- **Touched:** `decision/state.py`, `decision/data/pokedex.json` (524 KB), `tests/test_state.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): boosts, volatiles, hazards, weather and the whole opponent side must come from `BattleState`; the request doesn't carry them | none else
- **📨 Needs:** none new
- **Status:** open (the bot layer note above)

### 2026-10-24 16:13 — feat — Decision layer: one-turn simulation via poke-engine — @derrick
- **Where:** `derrick` @ `50b9a77` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `simulate(state, ours, theirs)` returns every outcome of a turn as (probability, next state), using poke-engine (Rust, built from source with its gen9 Tera feature). Replaying turn 1 of a real gen9ou game matches the log (Kingambit 66%). 0.038 ms per call. 31 tests, 100% coverage.
- **Touched:** `decision/simulate.py`, `tests/test_simulate.py`, `pyproject.toml` (new dependency `poke-engine==0.0.48`; building it needs Rust)
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): the decision layer now works in poke-engine's `State`, so whatever `BattleState` becomes gets converted to it once per turn (feature 01, decision side) | none else
- **📨 Needs:** none new
- **Status:** open (the bot layer note above)

### 2026-10-24 16:00 — feat — Decision layer: legal actions from a request, and the action selector — @derrick
- **Where:** `derrick` @ `b27a235` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate) (`derrick` was branched from `context`, so its shared docs must come off before a merge)
- **Did:** `our_actions(request)` lists our legal moves / Tera moves / switches / leads from Showdown's raw `|request|` JSON. `select()` picks the highest expected value over opponent actions × sets, tie-break on worst case. Python + uv + pytest; 25 tests, 100% coverage.
- **Touched:** `decision/actions.py`, `decision/selector.py`, `tests/`, `pyproject.toml`, `uv.lock`, `.gitignore`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): the decision layer is Python, so the bot ↔ decision seam crosses languages if the bot is TS | none else
- **📨 Needs:** @saliha: publish the decision-layer docs, record Python + the test command (Open board row). Bot layer owner: `BattleState`, which feature 07 is blocked on
- **Status:** open

