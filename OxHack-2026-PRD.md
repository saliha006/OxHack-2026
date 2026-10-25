> **Status, 2026-10-25 ~10:00 UTC.** This PRD (v4) describes `main` as built at `abf0e19`: Kenar's MCTS decision layer (merged 07:01, PR #1), the live bot with its battle-chat stream, the eval harness with Foul Play levels, the data pipeline and Tiger tables, and the offline `prediction/` package. [CURRENT-STATUS.md](CURRENT-STATUS.md) is the 06:30 cross-branch audit, kept for its evidence pins; where it disagrees about `main`, this PRD wins. Volatile numbers (test counts, merged win rates) live only in `progress.md` → 📊 Latest.

# OxHack-2026: Product Requirements Document
*OxHack 26 · HRT: Best Use of Data for Predictions & Decision Making · repo: https://github.com/saliha006/OxHack-2026 · v4 · 2026-10-25*
*Links: `CLAUDE.md` (how we work) · `builder-files/builder-file-<name>.md` (who builds what) · `design-decision/` (design notes; the per-feature decision docs are historical) · `contracts/` (exact interfaces) · `DATA-CONTEXT.md` (datasets and splits)*

> **Rules for editing this PRD.** It records decisions; it doesn't make them (design choices go through CLAUDE.md §1 first). Scope, flows, architecture, contracts and stack change only with the team (CLAUDE.md §2c). One home per fact: pitch §1, cut list §4, interfaces §11, stack §12; people and tasks live in the briefs. Evidence lives in the research doc: write the claim plus a pass ref, never a DO NOT USE metric. Section numbers never change. **Clock:** all times are UTC.

---

## 0. NOW ★ *(the part every agent reads at session start)*

**Decisions in force** (newest first; one line each, full ADR in the vault Log):
- 2026-10-25 ~09:00: demo games kept short (35 turns or less where possible) by **pinning the demo team from eval data**, not by changing the model or using a weaker opponent (option A). Candidate so far: `bot/teams/standin/team_6.txt`. (saliha)
- 2026-10-25 08:45: this laptop's fphard eval resumed across an opt-in-only code change by moving the old manifest aside (`runs/eval-manifest-7ec059b.json`); the `mcts8`, `mcts8joint` and `fphard` arm configs were checked identical. (saliha)
- 2026-10-25 08:20: **demo-flag rule:** a candidate flag (`--priors data/set_candidates_joint.json`, `--engine-threads 4`, `--tera-min-wins 2`) turns on only if its arm beats `mcts8` head to head with a Wilson 95% lower bound above 50%; otherwise the demo keeps today's bot. (saliha)
- 2026-10-25 07:01: **decision layer = Kenar's MCTS on `main`** (PR #1): 8 belief-sampled worlds × 150 ms of native poke-engine MCTS, 1 engine thread, `reliable` belief, type-matchup lead. `one_ply` stays as a comparator; coherent priors stay opt-in. Derrick's backtest CLI, `choose_public` and the 1825-cutoff proposal are withdrawn; `derrick` is kept as an archive. (whole team; `progress.md` 2026-10-25 06:41)
- 2026-10-25 03:00: data storage = Parquet + DuckDB for the offline pipeline, Postgres ("Tiger", `oxhack-data`) for the shared tables; read-only logins for teammates. (nate)
- 2026-10-25: team-conditioned set priors (A6): yes, built by nate after the demo; the fallback lowers the teammate match from 5 to 0 until N games match (N: nate's call); belief reads it at team preview as a function of the opponent's six. (derrick, proposed by nate)
- 2026-10-25: belief floors contradicted sets: a set that fails the speed/damage replay keeps 3% of its weight (`FLOOR = 0.03`); reveals stay a hard zero, with a recovery chain when nothing fits. (derrick)
- 2026-10-24: Elo ladder = option B: our bots + random-move mixes at uneven rates + Foul Play at uneven search-time bands on top; blind schedule; Bradley-Terry Elo (Random = 1000). Internal ladder Elo only, never a Showdown Elo. (saliha)
- 2026-10-24: eval mix = B+ (same-team matches with alternating sides; headline vs SimpleHeuristics; ablations), built in `bot/eval.py`. (saliha)
- 2026-10-24: dependencies are added by whoever needs them, with a ⚠️ row to derrick (`pyproject.toml` is his). (saliha)
- 2026-10-24: saliha builds `poke-engine` from source (Rust toolchain); no Rust hot path of our own [P9 D2]. (saliha)
- 2026-10-24: one project folder. `context` holds `CLAUDE.md`, this PRD, `builder-files/`, `design-decision/` and the status docs; `main` holds code, `README.md`, `progress.md` and `contracts/`. Research and the event doc stay local. (saliha)
- 2026-10-24: bot = poke-env 0.16.1 (`Player` subclass feeding raw lines to our parser, calling `Agent.choose`), format gen9ou, local Showdown server. (saliha)
- 2026-10-24: system design choices are owned by saliha and derrick; decision-layer choices are derrick's (Kenar's MCTS was adopted by the whole team, 2026-10-25). (saliha)
- 2026-10-24: forced switch reuses the main loop; team preview uses Derrick's type-matchup lead (`decision/lead.py`). (derrick)
- 2026-10-24: target tracks are **HRT "Best Use of Data for Predictions & Decision Making"** (main) and **Best Handmade** (also). (saliha)
- 2026-10-24: the doc owner is saliha; her working branch is `sali`; `.claude/`, `Research-Context/` and `.env*` never go to GitHub. (saliha)
- *Superseded as defaults by the MCTS decision (2026-10-25 07:01), still true of the `one_ply` comparator:* argmax-EV selector with worst-case tie-break; action pruning plan; 5-scenario belief sampling.

**Pending** (not decided yet):
- **Demo flags and the pinned demo team:** decided from the 09:45 eval merge, saliha's yes. Evidence so far: Nate's slice has `mcts8t4` (4 engine threads) beating `mcts8` 11/14 (Wilson 52.4–92.4%), which passes the rule only barely; `team_6.txt` leads on win rate, game length and guess accuracy across every source (small samples).
- **Ownership of `decision/` between derrick and kenar:** both have worked in it; the split is TBC with both (the 👥 Team table still lists derrick).
- **Learned win probability in search:** `prediction/` exists but its logistic model is worse than the HP heuristic on held-out games, and search doesn't call it. Owner TBC (kenar or derrick).
- **`Kenar-coherent-v2`** (conservative coherent priors, panels unfinished): stays off `main` until after the demo.
- **Declare `duckdb` and `pyarrow`** in `pyproject.toml`: the offline pipeline imports them but they're undeclared. No effect on the bot; after the demo (owner TBC: data layer, with a ⚠️ row to derrick).
- **Handmade piece:** no plan.
- **Parked (kept for the record, not being pursued):** pass 10 decision plan (superseded by MCTS on `main`); pass 9 build plan; maximin LP selector; coach review; **backtesting frontend** (removed from Pending 2026-10-25 at derrick's request; the backtest CLI is archived on `derrick`).

**Focus right now:** demo freeze **10:30 UTC** (no code after it); submission **12:00 UTC**. 10:30–12:00 is docs only: README, `progress.md`, Devpost.

**▶ RESUME HERE (2026-10-25 ~10:00 UTC):** merge every machine's `runs/eval/*.jsonl` → `uv run python -m bot.eval report` → pick demo flags + pinned team by the rule above (saliha's yes) → verify battle chat → rehearse twice by 10:20 → freeze 10:30 → README + `progress.md` + submit.

---

## 1. One page ★

**One-liner:** a Pokémon Showdown Gen 9 OU battle agent that turns usage stats and replays into predictions (the opponent's hidden sets, the chance of winning) and uses them to choose every move, with its win rate measured against standard baseline bots.
- **Where it runs, for whom:** one laptop running a local Showdown server (the eval also shards across the team's laptops). Judges watch a live battle in the Showdown web client; every decision appears in the battle chat and, in more detail, in the terminal.
- **Track:** HRT Best Use of Data for Predictions & Decision Making (main); Best Handmade (also; no plan yet).

**What makes it real (and not a mock-up):**
1. A parser that reads real Showdown protocol into the shared `BattleState`, tested on public gen9ou games, and reused offline (`states_from_log`) so training data and live play see the same state.
2. A search-based decision layer: each turn it samples 8 complete opponent teams ("worlds") from its belief over hidden sets, runs 150 ms of poke-engine MCTS in each, pools the results and plays the best legal action, inside a 3 s budget, in a supervised worker process that can't stall the battle. Fallbacks are counted per game.
3. An eval harness that measures play, not teams: same team on both sides, sides swapped, Wilson 95% intervals plus a team bootstrap, merged across machines, against SimpleHeuristics and Foul Play at ladder strength (results: `progress.md` → 📊 Latest).
4. Predictions measured honestly: a calibrated logistic win-probability model and next-reveal scoring of the belief, both on held-out public games. Neither beats its simple baseline yet, and we say so.

**Novelty line:** *Unlike Foul Play (a strong poke-engine search bot that shows nothing of its reasoning) and Metamon (offline-RL transformers that act without an explicit belief), OxHack-2026 shows on every turn what it's weighing and what it guesses about the opponent's hidden sets, and measures its predictions and its decisions separately, with intervals.* [Pass 1 K2, K3; Pass 7]

## 2. Problem and evidence ★

- **Who:** anyone making repeated decisions under hidden information against an adaptive opponent; Showdown Gen 9 OU is a clean, public, measurable instance (open simulator, millions of public replays, monthly usage stats). [Pass 2, Pass 8]
- **How hard:** each turn is a simultaneous move with hidden opponent sets (moves, item, ability, Tera type) and random damage rolls, so the right move depends on a belief about the opponent, not just the board. [Pass 1, Pass 7]
- **Why today's fixes fail:** strong bots don't expose their beliefs or calibrated predictions (Foul Play uses a hand-built evaluation; Metamon has no explicit belief), and hobby win-probability trackers report no calibration metrics. [Pass 1 K1–K3, W7]
- **Why now:** Gen 9 OU has a large public replay corpus (2.5M battles loaded into Tiger) and a fast Rust simulator with MCTS (`poke-engine`) and Gen 9 support. [Pass 2, P9 B4, P9 D2]
- **Prior art:** Foul Play, Metamon, PokéChamp (ICML 2025), the PokeAgent Challenge (NeurIPS 2025). [Pass 1 K1–K3]

**Claims we never make:** ⚠️ never claim a ladder Elo or "beats humans" (no ladder games are played) · never quote Foul Play's GXE figures as fact (self-reported only) · never say a flag (joint priors, threads, Tera gate) improves win rate unless our own head-to-head shows it with an interval · never call MCTS visit shares ("Weighing" percentages) win probabilities: they aren't calibrated · never say the win-probability model beats the HP heuristic (it doesn't yet) · never say the live battle view works without internet (the local client loads assets from pokemonshowdown.com) · never present the best of 10 teams' win rate as the bot's overall win rate.

## 3. Users and decisions ★

| Actor | Context | Gets | Decision it supports |
|---|---|---|---|
| HRT judge | 4–5 minutes at our table, quant background | Live battle with a chat line per decision; terminal readout; eval table with intervals; prediction metrics | "Are the predictions honest, and do the decisions beat a baseline?" |
| The agent (in battle) | One request at a time, 3 s budget | Belief over opponent sets, 8 sampled worlds, pooled MCTS support | Which move, switch or Tera to play |
| The team | Eval runs on several laptops | `runs/*.jsonl` traces, `runs/eval/*.jsonl`, the merged report | Which flags and team the demo uses; what to cut |

## 4. Scope ★

| Layer | What's in it, and why |
|---|---|
| **Real / live** | Battles on a local Showdown server; set priors from Smogon chaos stats (gen9ou-1825, 2026-09); 2.5M public replays (HolidayOugi) in Tiger; Foul Play as a strong opponent in the eval |
| **Simulated** (said on screen) | Opponents are bots (SimpleHeuristics in the demo, Foul Play and our own variants in the eval), not ladder players: the public ladder needs a registered bot |
| **Built, opt-in** | `one_ply` backend; joint priors (`data/set_candidates_joint.json`); coherent/curated priors (`data/curated-v1/`); 4 engine threads; Tera gate; near-tie mixing; moves/stats lead; `prediction/` models; `evaluation/` and `analysis/` diagnostics |
| **Next step (after the demo)** | Team-conditioned priors (A6, nate); `Kenar-coherent-v2`; a learned value that beats the HP heuristic; adaptive world allocation; more teams and opponents |
| **Cut** | Public ladder run; maximin LP selector; coach review; backtesting frontend; browser side panel (replaced by battle-chat lines); ClickHouse; our own Rust hot path; LLM coaching text; voice |

**Demo-vs-product gap:** a registered bot account under Smogon's bot policy for ladder play; adaptive human opponents; a client that runs offline; battle chat on a public server (ours relies on a local, uncommitted patch to `pokemon-showdown/server/chat.ts` that lets guests chat under `--no-security`). CLAUDE.md §2 treats anything in this list as a 🟠 decision.

## 5. User flows ★

**Flow A: live demo**
1. The local server runs (`node pokemon-showdown start --no-security` in `pokemon-showdown/`, with the chat patch).
2. `$env:PYTHONUTF8=1; uv run python -m bot.demo live [flags]` (PowerShell) logs in "oxhack demo" and "oxhack rival" (SimpleHeuristics by default), both with the same team, and prints `Watch it live: http://localhost:8000/battle-gen9ou-NNN`.
3. The viewer opens that room (or types `/join battle-gen9ou-NNN` in the Lobby). Each decision appears as a battle-chat line from "oxhack demo"; the terminal shows the same block: `Weighing` (pooled MCTS support for our options), `Expects them` (support for the opponent's replies), `Guessing their <Pokémon>: <item> (n/8 worlds) · Tera <type>`.
4. The game ends → `Game over: won in N turns · fallbacks · think p50/p99`. One battle per run; `runs/<battle>.log`, `.jsonl` and `.decision.log` hold the full record.
- **Unhappy path (no Wi-Fi):** `uv run python -m bot.demo replay runs/<battle>.jsonl` replays the terminal stream offline.

**Flow B: evaluation run**
1. `uv run python -m bot.eval run --pairings <names> --games N --seed S --machine <name> --shards K` plays a seeded, shuffled schedule of unplayed games across K processes; Foul Play opponents run from a `foul-play/` checkout with its own venv.
2. Each finished game appends one line to `runs/eval/<machine>-<shard>.jsonl`; a rerun skips finished games. `runs/eval-manifest.json` fingerprints the code, priors, teams and arms, and refuses to mix a changed configuration into the same folder.
3. Copy every machine's files into `runs/eval/`, then `uv run python -m bot.eval report`: win rate, Wilson 95%, team bootstrap, fallback rate, think-time p99, Bradley-Terry Elo.

**Flow C: data and prediction (offline)**
1. HolidayOugi replays → `data/pipeline/clean_battles.py` (DuckDB) → `build_turns.py` (Parquet, states from the live parser) → `load_tiger.py` (Postgres `battles`, `battle_logs`, `turns`; spec in `contracts/turns.md`).
2. Chaos stats → `build_set_candidates.py` → `data/set_candidates.json` (the default priors). Optional: `joint_sets.py` → `set_candidates_joint.json`; `import_curated_sets.py` → `data/curated-v1/`.
3. `python -m prediction train | predict | score-beliefs | score-actions | …` fits and scores the win-probability model and the belief on held-out games; figures land in `evaluation/prediction-public-20261025/`.

## 6. Functional requirements ★

| ID | Requirement | Status | Flow |
|---|---|---|---|
| FR-1 | The bot connects to the local server and plays a full gen9ou game unattended | built | A, B |
| FR-2 | The parser turns every protocol line into the contract's `BattleState`, skipping unknown lines without crashing | built | A, C |
| FR-3 | `Agent.choose` returns a legal choice for every request within its budget, falling back to the first legal option (then `default`) on any error | built | A, B |
| FR-4 | Fallbacks are counted per game; the smoke run fails above 5% (`bot.smoke --max-fallback`) | built | B |
| FR-5 | One trace line per request: choice, think time, fallback flag, `BattleState`, MCTS support and sampled worlds | built (no win probability: visit shares instead) | A |
| FR-6 | Belief loads real set candidates and never zeroes a set on a failed replay (floor 0.03) | built | A |
| FR-7 | The eval reports win rate with a Wilson 95% interval and a team bootstrap, team-neutral | built | B |
| FR-8 | The eval resumes from its results file, merges across machines, and refuses mixed configurations | built | B |
| FR-9 | The win-probability model reports log loss, Brier and a reliability diagram vs the HP heuristic on held-out games | built (model doesn't beat the baseline yet) | C |
| FR-10 | One command regenerates the eval charts from `runs/` | not built (prediction SVGs exist) | A |
| FR-11 | A data card lists every dataset, size, date range, split and licence note | partial (`DATA-CONTEXT.md`, `data-artifact-inventory.json`) | — |
| FR-12 | Each decision is posted to the battle chat so viewers in the browser see the reasoning | built (needs the local chat patch) | A |
| FR-13 | The eval can play Foul Play at fixed search-time levels (fplow/fpmid/fphigh/fphard) | built | B |
| FR-14 | Maximin LP selector; coach review | cut | — |

## 7. Core logic

### 7.1 Turn loop (decision layer, `backend="mcts"`, default)
- **In:** raw `|request|` JSON + `BattleState` · **Out:** a choice string (`"move 2"`, `"switch 4"`, `"team 123456"`, a `-tera` move) or `None` on a wait.
- **Rule:** team preview → the type-matchup lead, no search. Otherwise a persistent spawned worker process (`decision/search.py`) keeps the belief: update on the new turn → sample 8 whole-team worlds → for each world `build_state` and `poke_engine.monte_carlo_tree_search(150 ms, threads)`, streamed back as each finishes; worlds that would pass the deadline aren't started. `pool_results` (`decision/search_policy.py`) normalises each world's root visits, weights worlds equally, maps them to the request's legal actions (ambiguous names are rejected) and takes the argmax with request-order tie-break. A 3 s budget with a return reserve of `min(0.3, 0.1 × budget)`; an error plays the first legal option; a stalled worker is killed and replaced.
- **Opt-in, after pooling:** Tera gate (`tera_min_wins`: Tera only when it tops at least that many worlds outright; Laplace's rule) and seeded near-tie mixing (`mix_root`).
- **Why:** this is the Foul Play wiring (one MCTS per sampled world, visit shares summed) [P9 D2]. Native search uses poke-engine's hand-written evaluation, so a learned value can't plug in without a Rust fork; the process boundary makes the deadline enforceable.
- **Comparator `backend="one_ply"`:** top-k sets for the opponent's active Pokémon (bench at its most likely set), uniform opponent reply, one simulated turn, HP/alive value, argmax-EV with worst-case tie-break. Used by the older eval arms (`full`, `prior`, `flat`, `k1`).

### 7.2 Belief over opponent sets
- **In:** set candidates per species (`data/set_candidates.json`: chaos stats gen9ou-1825, 2026-09; up to 30 sets per species, weights sum to 1, usage block) + revealed moves/item/ability/Tera + replayed turns · **Out:** weighted sets per opponent slot, and sampled worlds.
- **Rule:** forme aliases resolve to a prior entry (missing → rebuilt from usage). Hard filter on reveals and item rules (boots / not-boots, not Assault Vest, not Choice, not Leftovers); if nothing survives: rebuild → relax inferred rules → reconstruct from revealed facts. Soft reweight by replaying the last turn in poke-engine (move order, damage range); a set that can't explain it keeps `FLOOR = 0.03` of its weight. Modes: `legacy`, `revelations` (hard reveals only), `reliable` (default: skips unstable intervals, forced moves, item changes and suppression). Worlds draw each slot independently (no teammate correlation yet; A6 is the fix).
- **Why:** the floor keeps a rounding miss or an unlisted set from wiping out the belief [P9 D1]. Measured: next-reveal log loss favours the prior over the updated belief so far, so updating is not yet shown to help (§17).

### 7.3 Win-probability model (`prediction/`, offline, not used by search)
- **In:** public-state features from `BattleState` (side differences, turn, Trick Room) · **Out:** P(we win).
- **Rule:** logistic regression with Platt calibration; chronological splits grouped by battle, with player/team-overlap "unseen" controls; log loss, Brier and reliability vs the HP heuristic. CLI `python -m prediction`.
- **Status:** on the public study the calibrated logistic model is worse than the HP heuristic on the test split (log loss 0.6600 vs 0.6348). Search never calls it. Shipping it into search needs a model that beats the heuristic first.

### 7.4 Selector
- **Rule:** MCTS: pooled visit shares, argmax (§7.1). `one_ply`: argmax-EV with worst-case tie-break. The maximin LP is cut.

### 7.5 Evaluation statistics (`bot/eval.py`)
- **Rule:** every game puts the same team on both sides; adjacent games share a team and swap challenge direction, so it measures play, not teams. Wilson 95% plus a team bootstrap; internal Bradley-Terry Elo only.
- **MCTS pairings (measure today's bot):** `mcts-headline` (`mcts8` vs SimpleHeuristics, the demo matchup); vs Foul Play `fphard` (parallelism 4, 900–1100 ms per decision, about ladder strength): `mcts-foulplay-hard`, `mcts-joint-foulplay-hard`, `mcts-threads-foulplay-hard`, `mcts-deeper-foulplay-hard`; head to head vs `mcts8`: `mcts-joint`, `mcts-threads`, `mcts-tera-gate`, `mcts-mix`, `mcts-deeper`.
- **Legacy pairings** (`headline`, `full~*`, ablations, the Foul Play ladder): measure the **one-ply** bot, not the demo bot.
- **Arms:** `mcts8` (default), `mcts8joint` (joint priors), `mcts8t4` (4 engine threads), `mcts8tera` (Tera gate, 2 wins), `mcts8mix` (near-tie mixing), `mcts4x300` (4 worlds × 300 ms).
- **Demo-flag rule:** §0.

### 7.6 Coach review
- Cut; not built.

## 8. AI, models and agent

| # | Model / component | Framework | Runs where | Trained on | Metric (vs baseline) |
|---|---|---|---|---|---|
| M1 | Native MCTS evaluation | poke-engine (Rust, hand-written) | in the search worker | none | win rate head to head (§17) |
| M2 | Belief over opponent sets | Python + poke-engine replay | in the search worker | chaos-stats priors | next-reveal log loss vs the prior |
| M3 | HP/alive value | Python | `one_ply` backend; prediction baseline | none | reference for M4 |
| M4 | Win-probability model, logistic + Platt | numpy (`prediction/`) | offline only | public replays (chronological split) | log loss, Brier, reliability vs M3 |
| M5 | Opponent model | inside MCTS (each world searches both sides); uniform in `one_ply` | in-process | none | "Expects them" support is a bot-only diagnostic, not a calibrated prediction |

- **Agent loop:** per Showdown request · one `Agent` per battle, its belief kept in the worker process, lost on restart (a battle can't resume) · on a failed turn: first legal option, counted as a fallback.
- **Anti-wrapper test:** there is no LLM; every decision is search over a simulator with a probabilistic belief.
- **Human in the loop:** none during battles.

## 9. Data ★

**Sources**
| Role | Dataset / feed | Span / size | Licence / access | Status |
|---|---|---|---|---|
| replays | `HolidayOugi/pokemon-showdown-replays` → Tiger `battles`, `battle_logs` | 2,506,142 battles | no licence stated; read-only logins | loaded (`progress.md` 03:00) |
| training / test turns | Tiger `turns` (`contracts/turns.md`) | 489,840 turns from 20,000 games: 15k train (from 2025-01-01) / 5k test (from 2026-05-19) | derived | built; test split is **not** player/team-disjoint (see `DATA-CONTEXT.md`) |
| priors (default) | Smogon chaos stats `gen9ou-1825`, 2026-09 → `data/set_candidates.json` | 243 species + 78 forme aliases, ≤30 sets each | public | built |
| priors (opt-in) | Showdown's gen9ou sets snapshot (`data/sources/`, 2026-10-25) → `data/curated-v1/`; Foul Play's observed complete sets → `data/set_candidates_joint.json` (75/25 blend) | static | public | built, opt-in |
| teams | `bot/teams/standin/` (10 gen9ou teams; the demo picks one at random unless `--teams` pins one) | static | ours | in use |
| live | local Showdown battles | per turn | ours | in use |

**Entities** (what we store)
| Entity | Key fields | Written by | Read by | Sensitivity | Retention |
|---|---|---|---|---|---|
| Battle record | `runs/<battle>.log` (raw protocol), `.jsonl` (one line per request), `.decision.log` | bot | demo replay, analysis | internal | local `runs/`, git-ignored |
| Eval results | pairing, game, arms, team, side, winner, turns, compute settings, fallbacks, think times | eval harness | `report` | internal | local `runs/eval/`, git-ignored |
| Eval manifest | engine version, source hash, priors hash, team hashes, seed, arms | eval harness | eval harness | internal | `runs/eval-manifest.json` |
| Set candidates | per species: weighted sets + usage block | data layer | decision layer | public (derived) | committed, rebuilt per stats month |
| Tiger tables | `battles`, `battle_logs`, `turns` | data layer | prediction, analysis | public (derived) | Postgres service, never committed |

## 10. System architecture ★

```
OFFLINE (data/, prediction/, evaluation/)                ONLINE, per request (one laptop)
chaos stats ─► build_set_candidates ─► data/set_candidates.json ──────────┐ priors
Foul Play observed sets ─► joint_sets ─► set_candidates_joint.json (opt-in)│
replays ─► clean_battles (DuckDB) ─► build_turns (Parquet) ─► Tiger (Postgres)
                                    └─► prediction/ (logistic win prob; NOT used by search)
                                                                           ▼
Showdown server ─protocol─► AgentPlayer (poke-env) ─► Parser ─► BattleState + request
  ▲   (web client needs internet;                            │
  │    battle chat needs the local patch)                     ▼
  │                                  Agent.choose ─► search worker process:
  │                                     belief update ─► 8 sampled worlds ─► poke-engine MCTS × 150 ms each
  │                                     ◄─ pooled visit shares ─► legal action (+ opt-in Tera gate / mixing)
  └──────── choice ◄─────────────────────┘
            │ on_decision ─► terminal block + one battle-chat line
            └─► runs/<battle>.log · .jsonl · .decision.log
EVAL: bot/eval.py shards (seeded schedule) per machine ─► runs/eval/<machine>-<shard>.jsonl ─► report (merged)
      opponents: SimpleHeuristics, our arms, Foul Play (external checkout, own venv) at fplow…fphard
```

| Component | Job | Runs on | Talks to | Budget | Area |
|---|---|---|---|---|---|
| Showdown server | Runs battles; viewers watch in the web client | Local, Node ≥ 22.18, `--no-security` | Bot, browser | 1 core | platform |
| Bot layer (`bot/`) | Connection, parser, trace, demo, eval harness | Local Python process per shard | Server, decision layer | 1 core per shard | saliha |
| Decision layer (`decision/`) | Belief → worlds → MCTS → pooled choice | Worker process per `Agent` | Bot, set candidates | ≤3 s per turn (8 × 150 ms search) | kenar / derrick |
| Data layer (`data/`) | Priors, Tiger tables, turns | Offline | Files + Postgres | — | nate (curated-v1 + reveal evidence: kenar; joint priors: saliha) |
| Prediction + diagnostics (`prediction/`, `evaluation/`, `analysis/`) | Win-probability model, belief and search studies | Offline | Tiger, `runs/` | — | kenar |

**Contracts:** `contracts/battle-state.md` (+ `battle_state.py`), `contracts/set-candidates.md` (+ `set_candidates.py`), `contracts/turns.md`, `agent.choose(request, battle_state)`, and the trace line (§11).

## 11. Interfaces ★

| Method · path / event | Purpose | Consumer | Auth | Key fields in → out |
|---|---|---|---|---|
| `Agent(priors, budget=3.0, backend="mcts", mcts_worlds=8, search_ms=150, engine_threads=1, belief_mode="reliable", lead_policy="types", mix_root=False, tera_min_wins=0, seed=2026, …).choose(request, battle_state)` | One decision per request | bot | in-process (+ worker process) | request dict + `BattleState` → choice string or `None` |
| `agent.last_trace` | What the agent considered | bot trace writer, demo | in-process | worlds, own/opponent support, sampled worlds, fallback reason, timings |
| `Parser(us).feed(line)` · `.snapshot()` · `states_from_log(lines, us)` | Protocol → state, live and offline | bot, data, prediction | in-process | protocol line → `BattleState` |
| `data/set_candidates.json` (+ `_joint`, `curated-v1/priors.json`) | Priors for belief | decision layer | file | species → weighted sets, per `contracts/set-candidates.md` |
| `runs/<battle>.jsonl` · `.log` · `.decision.log` | Trace, raw protocol, decision log | demo replay, analysis | file | one line per request |
| `runs/eval/<machine>-<shard>.jsonl` · `runs/eval-manifest.json` | One line per eval game; config fingerprint | `bot.eval report` | file | §9 eval fields |
| `python -m bot.demo live | replay` · `python -m bot.eval run | report | agreement` · `python -m bot.smoke` | Demo, eval, smoke | people | CLI | flags in §5 |
| `python -m prediction train | predict | export-bot | fetch-replays | score-bot-beliefs | score-beliefs | score-actions` | Offline prediction studies | kenar, nate | CLI | Tiger / replays → metrics, figures |
| Tiger `battles`, `battle_logs`, `turns` | Shared replay and training tables | data, prediction | read-only Postgres login (`.env`) | `contracts/turns.md` |
| `ws://localhost:8000/showdown/websocket` · battle chat | Showdown protocol; one chat line per decision | bot (poke-env), viewers | `--no-security`, guest names; chat via local patch | protocol lines ↔ `/choose …`; `|c|☆oxhack demo|…` |

## 12. Tech stack ★

| Layer | Choice | Why (vs alternative) | Gotcha |
|---|---|---|---|
| Language, tooling | Python + `uv`, `pytest --cov` | One toolchain for every layer | On Windows set `PYTHONUTF8=1` (PowerShell: `$env:PYTHONUTF8=1`); the full bot suite under `--cov` hangs on Windows, so run its test files one by one; `testpaths` covers `tests/` only |
| Decision layer | `poke-engine==0.0.48` (native MCTS, Tera feature) in a spawned worker process | Fast Rust search with Gen 9 support; the process boundary enforces the deadline | Builds from source: needs a Rust toolchain. Legality comes from the request, not the engine |
| Bot layer | `poke-env==0.16.1` | Baseline bots + concurrent battles out of the box | Parse errors can be swallowed (#973): the player retries with the first legal option, then `default` |
| Game server | Pokémon Showdown, local, `--no-security` | No account, no rate limits | The client needs internet for assets; battle chat for guests needs our local patch to `server/chat.ts` (revert: `git -C pokemon-showdown checkout server/chat.ts`), active after a restart |
| Strong opponent | Foul Play, external `foul-play/` checkout with its own venv | Ladder-strength reference opponent | Leftover processes after a killed eval: kill the tree |
| Offline data | DuckDB + Parquet (pyarrow); Postgres "Tiger" via `psycopg` (`tiger` group) | No server for the local pipeline; one shared database for the team | `duckdb` and `pyarrow` are imported but not declared in `pyproject.toml` (§0 Pending) |
| Prediction | numpy + matplotlib + requests (`prediction` group) | Logistic + Platt fit in seconds; no scikit-learn needed | Separate from search |
| Node scripts | `data/pipeline/validate_curated.cjs`, `evaluation/mcts_improvements/simulator.cjs`, `docs/validate-mcts-heldout.cjs` | Use Showdown's own validator/simulator | Need a built local `pokemon-showdown/` (Node ≥ 22.18) |
| Presentation | Terminal readout + Showdown battle chat | No front-end build in the time we had | — |

## 13. Non-functional requirements ★

| Quality | Target | How we check |
|---|---|---|
| Live turn latency | ≤3 s per decision, never a timeout loss | trace think time; demo summary p50 / p99 |
| Reliability | 0 stalls; fallback rate ≤5% (smoke gate) | fallback counter per game |
| Fairness of comparisons | same team both sides, sides swapped; one config per results folder | eval schedule; manifest guard |
| Resource limits | one game per core for 1-thread arms; the 4-thread arm only fair with the cores to itself | `--shards`; eval notes |
| Restart | a killed eval loses only the games in flight | rerun skips finished games |
| Privacy / retention | public pseudonymised replays only; nothing personal stored; data never committed | `DATA-CONTEXT.md` |

## 14. Security and trust ★

| Role | Can | Can't |
|---|---|---|
| Our bot accounts ("oxhack demo", "oxhack rival", eval names) | Play and chat on the local server | Touch the public server (needs bot registration under Smogon's policy) |
| Teammates | Push code to their branch; read Tiger with read-only logins; docs to `context` via the doc owner | Commit data files, secrets or shared docs to `main` |

| Threat | Mitigation |
|---|---|
| Hammering Showdown's public APIs | No scraping: replays come from HolidayOugi; one sets snapshot only |
| Licence misuse | Licence notes per dataset in `DATA-CONTEXT.md`; no redistribution of raw data |
| Leaked credentials | Tiger logins live in `.env`, never in git |
| The chat patch reaching a real server | It's local and uncommitted; only meaningful under `--no-security` |

- **Hard rules:** no public-server play without a registered bot account; no data files or `.env` in git; `Research-Context/` never pushed.

## 15. Failure modes ★

| Failure | Detected by | System behaviour | User sees |
|---|---|---|---|
| `poke-engine` won't build (no Rust) | `uv sync` fails | install Rust; nothing runs `Agent.choose` until it builds | nothing at the demo |
| Decision error or deadline overrun | `Agent.choose`; worker supervision | first legal option, else `default`; stalled worker killed and replaced; counted as a fallback | the battle goes on |
| Bookkeeping message to the worker times out (50 ms) | `decision` warning "chosen action retained" | the move is still played; that turn's replay bookkeeping is not recorded | nothing |
| Invalid choice | `|error|[Invalid choice]` | resend the first legal option, then `default` | nothing |
| Eval inputs changed mid-run | manifest guard | refuses to resume; use a new `--runs` folder or move the manifest aside after checking the arms | an error line |
| Socket drop or crash mid-eval | missing result lines | rerun skips finished games | eval continues |
| "must be registered to chat" | battle log | the server isn't running the chat patch: restart it | no chat lines in the browser |
| Browser stays on the Lobby | — | each battle has its own room; `/join battle-gen9ou-NNN` | the Lobby |
| No Wi-Fi at the demo | client won't load | hotspot, then `bot.demo replay` of a saved trace | the replayed stream |
| Demo shares the laptop with an eval | slower think times | both bots get less search; flag those eval games | slightly slower turns |

## 16. Sponsor / platform fit

- **HRT (Predictions & Decision Making):** prediction = an explicit belief over hidden sets shown on every turn (and scored on held-out reveals) plus a calibrated win-probability model scored on held-out games; decision = MCTS over belief-sampled worlds, measured head to head against SimpleHeuristics and Foul Play with intervals. Honest negatives (model below baseline, belief not yet beating the prior) are part of the pitch.
- **Best Handmade:** n/a until a piece is planned (§0 Pending).

## 17. Evaluation and success ★

| Question | Evidence | Target / status |
|---|---|---|
| Does the agent beat the demo opponent? | `mcts-headline`: `mcts8` vs SimpleHeuristics, same team, Wilson 95% + team bootstrap | lower bound above 50%; numbers in 📊 Latest |
| How does it do against a strong bot? | `mcts-foulplay-hard` (+ the joint and threads arms) vs Foul Play `fphard` | reported either way; research estimate 25–40% |
| Do the opt-in flags help? | head to head vs `mcts8`: `mcts-joint`, `mcts-threads`, `mcts-tera-gate`, `mcts-mix`, `mcts-deeper` | a flag ships only with a Wilson lower bound above 50% (§0) |
| Are the win probabilities honest? | `prediction/`: log loss, Brier, reliability on a chronological held-out split | better than the HP heuristic (not yet: 0.6600 vs 0.6348) |
| Is the belief better than the prior? | next-reveal log loss vs the prior and vs hard-filter-only | below the prior (not yet: prior 2.71 vs posterior 3.08 in the pilot) |
| Is the agent safe to run? | fallback rate, think p50 / p99, stalls | §13 targets |

| Judging criterion | Where we prove it (§ / demo beat) |
|---|---|
| Use of data for predictions | §7.2, §7.3, rows 4–5 above · demo beats 2 and 4 |
| Use of data for decision making | §7.1, §7.5, rows 1–3 above · demo beats 2 and 3 |
| Rigour and honesty | same-team design, intervals, manifest guard, the "claims we never make" list (§2) · demo beat 5 |

**Definition of done (MVP):** one command starts a live gen9ou battle on the local server in which the agent plays every turn through MCTS with no stalls and posts each decision to the battle chat; the team-neutral eval table vs SimpleHeuristics and Foul Play exists with intervals; the prediction metrics are reported against their baselines.

## 18. Demo script ★ *(4 minutes; one row per beat)*

| Time | Beat | Live / recorded | Fallback |
|---|---|---|---|
| 0:00 | **Hook:** "Every turn, this agent guesses what's hidden in the opponent's team, searches 8 versions of the game that fit its guess, and picks the move that works best across them." | live | — |
| 0:30 | Live battle vs SimpleHeuristics; the chat shows Weighing / Expects them / Guessing per turn | live (needs internet) | `bot.demo replay` of a saved trace |
| 1:45 | Decision proof: win rate vs SimpleHeuristics and vs Foul Play `fphard`, with Wilson intervals, same team on both sides | table | — |
| 2:30 | Prediction proof, honestly: guess accuracy, belief scoring and the win-probability model vs their baselines | table / SVG | — |
| 3:15 | **Honest limits** (bot opponents, one format, no ladder Elo, prediction not yet above baseline) + next steps (A6 team-conditioned priors) | slide | — |

## 19. Milestones and cut order ★ *(UTC)*

| When (UTC) | Milestone (done means…) |
|---|---|
| Sat 21:47 | First real game: bot + `Agent.choose` on the local server (one-ply) |
| Sun 03:00 | Real priors on `main`; Tiger tables loaded (nate) |
| Sun 07:01 | Kenar's MCTS merged to `main` (PR #1) and made the default |
| Sun 08:20–09:45 | MCTS eval slices on four laptops |
| Sun 10:30 | **Demo freeze**: no code changes after this |
| Sun 10:30–12:00 | Docs only: README, `progress.md`, Devpost |
| Sun before 12:00 | **Submit** on Devpost with the GitHub link |

**Cut order (first → last):** 1. any flag without evidence · 2. the pinned team (fall back to random) · 3. battle chat (the terminal still shows everything) · 4. live battle (replay a saved trace)
**Never cut:** the bot playing with fallback and logging; the same-team eval with Wilson intervals; the honest-limits close.

## 20. Risks ★

| Risk | Likelihood | Impact | Mitigation | Trigger to act |
|---|---|---|---|---|
| Venue Wi-Fi down for the live client | M | M | Hotspot; `bot.demo replay` | client won't load at setup |
| A flag looks good on a small sample by luck | M | M | Wilson lower-bound rule; report the interval, not the point | lower bound near 50% |
| The pinned team flatters the demo | M | L | Say it's pinned; report the all-teams win rate | — |
| Server restarted without the chat patch | L | M | Patch stays in the local checkout; check for "must be registered" | no chat lines |
| Demo and eval on one laptop slow both | M | L | Don't run evals during the demo | think p99 above 2.5 s |

## 21. Open questions ★

- [ ] The Devpost form's requirements: owner saliha, needed before 12:00 UTC
- [ ] Can one project win HRT and Best Handmade? Owner saliha
- [ ] Does the browser cache serve the Showdown client offline? Owner saliha [P9 B5 gap]
- [ ] Who owns `decision/` now, derrick or kenar? Owners: both

## 22. Glossary
| Term | Meaning |
|---|---|
| Gen 9 OU | Showdown's main singles format for the current generation |
| Set | One Pokémon's hidden build: moves, item, ability, nature/EVs, Tera type |
| Chaos stats | Smogon's monthly usage JSON per format and rating cut-off (we use 1825) |
| Belief | Weights over each opponent Pokémon's possible sets, updated by what's revealed |
| World | One complete guess of the opponent's six sets, sampled from the belief |
| Visit share | The fraction of MCTS visits an action got at the root; our "Weighing" percentages. Not a win probability |
| Request | The JSON Showdown sends when we must act; it lists our legal options |
| Arm / pairing | A bot configuration (`mcts8`, `mcts8joint`, …) / a matchup of two arms in the eval |
| fphard | Foul Play with 4 parallel searches at 900–1100 ms per decision, about ladder strength |
| Wilson interval | A confidence interval for a win rate that behaves well at small samples |
| Team-neutral | Both sides play the same team, so the win rate measures the agent, not the team |
| Fallback | The agent's safe answer (first legal option) after an error or timeout |

---

## Appendix *(agents can stop reading here)*

### A. Judge / user Q&A
| Likely question | Short answer (point to the §) |
|---|---|
| Isn't the win rate just your team being strong? | Both sides always play the same team (§7.5) |
| Are those percentages win probabilities? | No: they're MCTS visit shares pooled over 8 worlds; the calibrated model is separate and offline (§7.3) |
| How good is it against a strong bot? | Measured vs Foul Play at ladder strength, with intervals (§17) |
| Why not reinforcement learning? | Not in 25 hours; search over a simulator with an explicit belief is testable now (§7.1) |
| What doesn't it do? | No ladder play, bot opponents only, one format, prediction not yet above baseline (§4) |

### B. Key sources and credits
Full list: the research doc. For judges: PokéChamp (ICML 2025), Metamon (RLC 2025), the PokeAgent Challenge (NeurIPS 2025), `poke-engine`, poke-env. Ideas adapted from **Foul Play** (`pmariglia/foul-play`: one MCTS per sampled world, observed complete sets) and **Laplace** (more engine threads per world; the Tera gate).

### C. Version history *(the reasons live in the vault Log ADRs)*
- v4 2026-10-25: rewritten to describe `main` as built: MCTS decision layer, battle chat, MCTS eval pairings and Foul Play levels, data pipeline + Tiger, `prediction/`; Derrick's board request applied; superseded plans parked.
- v3 2026-10-24: every section filled; pass 9 build plan (research + critique) behind the briefs.
- v2 2026-10-24: bot on poke-env, gen9ou, local server; decision-layer recommendations.
