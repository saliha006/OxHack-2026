# OxHack-2026: Product Requirements Document
*OxHack 26 · HRT: Best Use of Data for Predictions & Decision Making · repo: https://github.com/saliha006/OxHack-2026 · v3 · 2026-10-24*
*Links: `CLAUDE.md` (how we work) · `builder-file-<name>.md` (who builds what, in build order) · the research doc (evidence; `[P9]` = pass 9) · `contracts/` (exact interfaces)*

> **Rules for editing this PRD.** It records decisions; it doesn't make them (design choices go through CLAUDE.md §1 first). Scope, flows, architecture, contracts and stack change only with the team (CLAUDE.md §2c). One home per fact: pitch §1, cut list §4, interfaces §11, stack §12; people and tasks live in the briefs. Evidence lives in the research doc: write the claim plus a pass ref, never a DO NOT USE metric. Section numbers never change. **Clock:** all times are UTC. UK clocks go back at 02:00 BST (01:00 UTC) on Sunday, so log in UTC.

---

## 0. NOW ★ *(the part every agent reads at session start)*

**Decisions in force** (newest first; one line each, full ADR in the vault Log):
- 2026-10-24: saliha is happy to build in Rust: she installs the Rust toolchain so `poke-engine` builds on her machine (blocks every `Agent.choose` call there). No Rust hot path of our own for now [P9 D2]. (saliha)
- 2026-10-24: one project folder. `context` holds `CLAUDE.md`, this PRD, `builder-files/` and `design-decision/`; `main` holds code, `README.md` and `progress.md`. Research and the event doc stay local and are deleted per feature once it ships. (saliha)
- 2026-10-24: bot = poke-env 0.16.1 (`Player` subclass tapping raw lines, calling `Agent.choose`), format gen9ou with one fixed team + a seeded validated opponent pool, local Showdown server. Own websocket client is the fallback. Research pass 8. (saliha)
- 2026-10-24: system design choices are owned by saliha and derrick, and decision-layer choices are derrick's. The decision-layer lines below are recommendations he can override. (saliha)
- 2026-10-24: forced switch reuses the main loop with the opponent's only option `None` (double faint = normal switch-vs-switch matrix). (saliha, delegated to a reviewing agent; built by derrick)
- 2026-10-24: team preview uses Derrick's type-matchup lead (`decision/lead.py`, built and tested). (derrick)
- 2026-10-24: action pruning: v1 enumerates everything and measures p50/p99 turn time; over budget, Tera only on the top few moves by damage, always keeping switches and one or two status moves. (saliha, delegated to a reviewing agent)
- 2026-10-24: selector stays argmax-EV for v1 (built and tested); a maximin LP is a flagged option (§7.4). (saliha, delegated to a reviewing agent)
- 2026-10-24: target tracks are **HRT "Best Use of Data for Predictions & Decision Making"** (main) and **Best Handmade** (also); TIME is optional but applies to Handmade (event doc §3). (saliha)
- 2026-10-24: the doc owner is saliha; the working branch is `sali`; `.claude/`, `Research-Context/` and `.env*` never go to GitHub. (saliha)

**Pending** (not decided yet):
- **The pass 9 build plan** (two research agents + an adversarial critic, peer-reviewed and official sources, checked against the code): every brief's `▶ Current tasks` now follows it. Derrick and Nate accept each item or pick a different route (Open board rows). Proposed hand-overs to even the load (belief scoring, model figures and charts to nate; terminal stream and coach to saliha) need derrick's and nate's yes.
- Three dependencies in Derrick's `pyproject.toml`: `poke-env==0.16.1`, `scikit-learn` (brings scipy for the LP), `matplotlib`: one yes from derrick.
- Data storage: plain Parquet + DuckDB recommended over ClickHouse [P9 B4]: nate's call, with saliha and derrick.
- Learned value model replacing the HP heuristic: derrick's call (logistic first, §7.3).
- Demo story: whether the coach replay review (§7.6) is added. It's first to cut.
- Handmade piece: no plan; ask the organisers what counts (event doc §6). Elo-from-decisions: parked.

**Focus right now:** Rust toolchain + smoke battle (saliha); set candidates, then the team pool (nate); turn-time profile, belief floor, build_state on parser output (derrick).

**▶ RESUME HERE (2026-10-24 ~21:10 UTC):** briefs rewritten to the pass 9 order. Next for saliha: task 1 (Rust + `poke_engine` build, timebox 45 min), then task 3 (smoke battle). Numbers: `progress.md` → 📊 Latest.

---

## 1. One page ★

**One-liner:** a Pokémon Showdown Gen 9 OU battle agent that turns usage stats and replays into predictions (the opponent's hidden sets, the chance of winning) and uses them to choose every move, with its win rate measured against standard baseline bots.
- **Where it runs, for whom:** one laptop running a local Showdown server (the eval also shards across the team's three laptops); judges watch a live battle in the Showdown web client next to a terminal that shows what the agent believes and why it chose each move.
- **Track:** HRT Best Use of Data for Predictions & Decision Making (main); Best Handmade (also; no plan yet).

**What makes it real (and not a mock-up):**
1. A parser that reads real Showdown logs into the shared `BattleState`, tested on public gen9ou games (numbers: `progress.md` → 📊 Latest).
2. A tested decision layer (belief → simulate → value → select) that answers every request within a 3 s budget and never stalls.
3. {{Win rate vs `SimpleHeuristicsPlayer`, team-neutral, with a 95% Wilson interval: not run yet}}
4. {{Calibrated win-probability model: log loss and Brier vs baselines on held-out games played after 2026-05-19: not trained yet}}

**Novelty line:** *Unlike Foul Play (a strong poke-engine search bot with a hand-built evaluation, and win rates only its author reports) and Metamon (offline-RL transformers that act without an explicit belief or win probability), OxHack-2026 shows its predictions on every turn and proves both halves separately: the predictions on held-out games, the decisions head-to-head against a baseline.* [Pass 1 K2, K3; Pass 7]

## 2. Problem and evidence ★

- **Who:** anyone making repeated decisions under hidden information against an adaptive opponent; Showdown Gen 9 OU is a clean, public, measurable instance (open simulator, millions of public replays, monthly usage stats). [Pass 2, Pass 8]
- **How hard:** each turn is a simultaneous move with hidden opponent sets (moves, item, ability, Tera type) and random damage rolls, so the right move depends on a belief about the opponent, not just the board. [Pass 1, Pass 7]
- **Why today's fixes fail:** strong bots don't expose calibrated predictions (Foul Play uses a hand-built evaluation; Metamon has no explicit belief), and hobby win-probability trackers report no calibration metrics. [Pass 1 K1–K3, W7]
- **Why now:** Gen 9 OU has a large, recent public replay corpus (Metamon raw replays to 2026-05-19 plus newer HolidayOugi parts) and a fast Rust simulator (`poke-engine`) with Gen 9 support. [Pass 2, P9 B4, P9 D2]
- **Prior art:** Foul Play, Metamon, PokéChamp (ICML 2025), the PokeAgent Challenge (NeurIPS 2025). [Pass 1 K1–K3]

**Claims we never make:** ⚠️ never claim a ladder Elo or "beats humans" (no ladder games are played) · never quote Foul Play's GXE figures as fact (self-reported only) · never say the LP or MCTS arms improve win rate unless our own A/B shows it with an interval · never say the live battle view works without internet (the local client redirects to `psim.us`) · never report win probabilities as calibrated without the held-out reliability check.

## 3. Users and decisions ★

| Actor | Context | Gets | Decision it supports |
|---|---|---|---|
| HRT judge | 4–5 minutes at our table, quant background | Live battle + terminal readout; eval table; calibration chart | "Is the prediction honest, and does the decision beat a baseline?" |
| The agent (in battle) | One request at a time, 3 s budget | Belief over opponent sets, value per option | Which move, switch or Tera to play |
| The team | Overnight eval runs, model training | `runs/*.jsonl` traces, eval tables, data card | Which arm to keep (value model, LP, MCTS), what to cut |
| Showdown player (stretch) | Reviewing a finished game | Coach review: per-turn regret, decisive turns | Which of their turns lost the game |

## 4. Scope ★

| Layer | What's in it, and why |
|---|---|
| **Real / live** | Battles on a local Showdown server; set priors from Smogon chaos stats; training data from real public replays; teams from Metamon's replay-derived team sets |
| **Simulated** (labelled on screen) | Opponents are poke-env baseline bots, not ladder players: the public ladder needs a registered bot |
| **Stretch / next step** | Maximin LP selector (flagged), poke-engine MCTS arm (only if the agent is under ~85% vs SimpleHeuristics), coach replay review, scenario diversity in belief, a fitted opponent action model |
| **Cut** | Public ladder run; browser side panel; ladder snapshot scheduler (one `curl` only); ClickHouse; our own Rust hot path; voice and LLM coaching text; TypeScript runtime |

**Demo-vs-product gap:** a registered bot account under Smogon's bot policy for ladder play; opponents that adapt; more than one of our teams; a client that runs offline. CLAUDE.md §2 treats anything in this list as a 🟠 decision.

## 5. User flows ★

**Flow A: live demo (the demo flow)**
1. saliha runs `bot/demo.py` → the bot logs in to the local server and starts a battle vs `SimpleHeuristicsPlayer` → prints the battle URL.
2. The judge watches in the Showdown web client (needs internet) → the terminal streams each turn: chosen move, top 3 options with value, win probability, top sets per opponent Pokémon.
3. The game ends → the terminal prints the result; `runs/<battle-id>.jsonl` holds the full trace.
4. saliha shows the three charts: win-rate bars with intervals, this game's win-probability curve, the reliability diagram.
- **Unhappy path (no Wi-Fi):** play the recorded battle video and replay the terminal stream from the saved `runs/*.jsonl`.

**Flow B: evaluation run**
1. `bot/eval.py` starts N shard processes per laptop, each with its own account and one `Agent` per battle.
2. Each game appends a result line to `runs/eval-<arm>-<machine>.jsonl`; a killed run resumes from the file.
3. The merge step computes win rates with Wilson 95% intervals and a cluster bootstrap by team → the table goes to `progress.md` → 📊 Latest.

**Flow C: training the win-probability model**
1. Replays (Metamon raw shards, HolidayOugi part 13) → `states_from_log` → (state, winner) pairs in Parquet, split by battle, time and player.
2. Fit the baseline ladder, then the model → calibrate on the validation split → report log loss, Brier and the reliability diagram on the post-2026-05-19 test split.

## 6. Functional requirements ★

| ID | Requirement | MVP / stretch | Flow |
|---|---|---|---|
| FR-1 | The bot connects to the local server and plays a full gen9ou game unattended | MVP | A, B |
| FR-2 | The parser turns every protocol line into the contract's `BattleState`, skipping unknown lines without crashing | MVP (built) | A, C |
| FR-3 | `Agent.choose` returns a legal choice for every request within its deadline, falling back to the first legal option on any error | MVP (built) | A, B |
| FR-4 | Every fallback is counted per game; a smoke run fails if the fallback rate is above a few percent | MVP | B |
| FR-5 | The bot writes one trace line per request (choice, top 3 options, win probability, top opponent sets, think time) | MVP | A |
| FR-6 | Belief loads real set candidates from the data layer's file and never zeroes a set outright (floored weight) | MVP | A |
| FR-7 | The eval harness reports win rate with a 95% Wilson interval and a cluster bootstrap by team, team-neutral vs `SimpleHeuristicsPlayer` | MVP | B |
| FR-8 | The eval resumes from its results file after a crash, and shards merge across machines | MVP | B |
| FR-9 | The win-probability model reports log loss, Brier and a reliability diagram vs the constant and HP baselines on held-out games | MVP | C |
| FR-10 | One command regenerates the three demo charts from `runs/` | MVP | A |
| FR-11 | The data card lists every dataset, size, date range, split and licence note, each traced to a query or file | MVP | A |
| FR-12 | The maximin LP selector runs behind a flag, default off, with offline exploitability numbers | stretch | B |
| FR-13 | The coach review reports per-turn regret with an interval on a finished game | stretch | — |

## 7. Core logic

### 7.1 Turn loop (decision layer, built)
- **In:** raw `|request|` JSON + `BattleState` · **Out:** a choice string (`"move 2"`, `"switch 4"`, `"team 123456"`) or `None` on a wait.
- **Rule:** belief → sample 5 opponent scenarios → `build_state` → both sides' legal actions → `poke-engine` one-turn `simulate` → value each outcome → selector. A 3 s deadline returns the best-so-far; any error plays the first legal option.
- **Why:** the learned value and the LP plug in here; poke-engine's own search hard-wires its Rust evaluation, so it can't use either without a Rust fork [P9 D2].

### 7.2 Belief over opponent sets
- **In:** set candidates per species (chaos stats 1825, 2026-09) + revealed moves/item/ability/Tera + replayed turns · **Out:** weighted sets per opponent slot.
- **Rule:** hard filter on reveals, soft reweight by replaying each turn in poke-engine; a set that can't explain a turn drops to a small floor (proposed 0.02–0.05), not zero.
- **Why:** same shape as Foul Play; the floor keeps a rounding miss or an unlisted set from wiping out the belief [P9 D1]. Scored by next-reveal log loss vs the prior, on held-out reveals and on our eval games where we know the true set (not on pool teams: they come from the same stats, so it's circular) [P9 critique].

### 7.3 Win-probability model (proposed; derrick's call)
- **In:** public-information features from `BattleState` (HP, alive count, status, boosts, hazards, Tera used, turn) · **Out:** P(we win).
- **Rule:** baselines first (constant, HP heuristic; rating-only offline only, since the local server has no ratings), then logistic regression, then `HistGradientBoostingClassifier` with monotone constraints if time allows; Platt or isotonic calibration picked by validation log loss; split by battle, time and player; bootstrap intervals by battle.
- **Why:** a calibrated, held-out, baselined prediction is the half of the HRT story that stands without the agent [P9 D3, critique]. Shipping logistic only is a pass.

### 7.4 Selector
- **Rule:** argmax expected value over opponent actions × scenarios, tie-break on worst case (built). Flagged option: a maximin mixed strategy from `scipy.optimize.linprog` (HiGHS) after iterated dominance deletion, default off [P9 D4].
- **Why:** against fixed poke-env baselines the LP can't beat argmax-EV; its value is bounded exploitability, shown offline [P9 critique].

### 7.5 Evaluation statistics
- **Rule:** headline = team-neutral head-to-head vs `SimpleHeuristicsPlayer` (both sides get the same pool team, 5 games per team over 60 teams = 300 games); Wilson 95% interval plus a cluster bootstrap by team. At 100 games a true 60% win rate is detected only about half the time, so the headline leg gets 300 [P9 B3].

### 7.6 Coach review (stretch, first to cut)
- **Rule:** regret per turn = value of the best action minus value of the played action, on the expected next state, in win-probability points. Reviews the **baseline's** turns in our eval games (our own bot's regret is zero by construction) [P9 critique].

## 8. AI, models and agent

| # | Model / component | Framework | Runs where | Trained on | Metric (vs baseline) |
|---|---|---|---|---|---|
| M1 | Baseline value: alive count + HP fraction | Python | in-process | none | reference for M2/M3 |
| M2 | Win-probability model, logistic | scikit-learn (pending OK) | trained offline, served in-process | ≤100k gen9ou games' (state, winner) pairs | log loss, Brier, reliability vs M1 and constant |
| M3 | Win-probability model, gradient boosting (if time) | scikit-learn | same | same | same, vs M2 |
| M4 | Belief over opponent sets | Python + poke-engine | in-process | chaos stats priors | next-reveal log loss vs prior and vs hard-filter-only |
| M5 | Opponent action policy | uniform (built) | in-process | none | a fitted policy is stretch, unowned |

- **Decisions a script can't make:** which move to play given a belief over hidden sets (the trace logs top options and scores); how much to trust each candidate set after a turn (logged as top sets per slot).
- **Agent loop:** per Showdown request · memory: one `Agent` per battle (belief, last choice), lost on restart, which is fine since a battle can't resume · on a failed turn: first legal option, counted as a fallback.
- **Anti-wrapper test:** there is no LLM; every decision is search over a simulator with a probabilistic belief and a value function.
- **Human in the loop:** none during battles.

## 9. Data ★

**Sources**
| Role | Dataset / feed | Span / latency | Licence / access | Status |
|---|---|---|---|---|
| train / validate | Metamon raw replays (`jakegrigsby/metamon-raw-replays`), 5–8 shards | to 2026-05-19, cap ~100k games | pseudonymised; check card | KEEP [P9 B4] |
| test | `HolidayOugi/pokemon-showdown-replays`, part 13 (games after 2026-05-19) | recent | no licence stated | KEEP [P9 B4] |
| priors | Smogon chaos stats `gen9ou-1825`, 2026-09 | monthly | public | KEEP |
| teams | `jakegrigsby/metamon-teams`: `hl_05_26/gen9ou` (pool), `competitive/gen9ou` (our team) | static | check card | KEEP [P9 B2] |
| live | Local Showdown server battles | per turn | ours | KEEP |
| snapshot | Showdown gen9ou ladder top 500, one `curl` | once | public | parked use |

**Entities** (what we store)
| Entity | Key fields | Written by | Read by | Sensitivity | Retention |
|---|---|---|---|---|---|
| Battle log + decision trace | turn, `BattleState`, choice, top options, win probability, think time, fallback flag | bot | eval, charts, coach | internal | local `runs/`, through the demo |
| Eval results | arm, machine, game index, teams, winner, turns, fallbacks | eval harness | merge, charts | internal | local `runs/` |
| Set candidates | per species: weighted sets + an "other" bucket | data layer | decision layer | public (derived) | rebuilt per stats month |
| Team pool | 60 seeded packed gen9ou teams + manifest | data layer | eval | public | kept with its seed |
| Training pairs | battle id, time, player, features, winner, split | data layer | value model | public (derived) | Parquet, local, never committed |

## 10. System architecture ★

```
OFFLINE (data layer)                              ONLINE, per request (each laptop)
chaos stats ─► set candidates ─────────────────────────┐
metamon teams ─► 60-team pool + our team ──► eval      │
replays ─► states_from_log ─► (state, winner) Parquet ─► value model (logistic → HGB)
                                                       ▼
Showdown server ─log lines─► Parser ─► BattleState ─► Agent.choose() ─► choice ─► server
   (web client needs internet)   └─► runs/*.jsonl trace ─► eval merge · terminal stream · charts
eval: N shard processes per laptop (cores − 2), one blocking Agent per battle, results jsonl, merged across 3 laptops
```

| Component | Job | Runs on | Talks to | Budget (CPU / RAM) | Area |
|---|---|---|---|---|---|
| Showdown server | Runs battles; judges watch in the web client | Local, Node ≥ 22.18 | Bot | 1 core | platform |
| Bot layer | Connection, parser, trace, eval harness, demo | Local, Python; shard processes | Server, decision layer | 1 core per shard | backend |
| Decision layer | Belief → simulate → value → select | In-process with each shard | Bot, set candidates, value model | ≤3 s per turn live; eval think budget 1.0 s proposed | ML |
| Data layer | Set candidates, team pool, training pairs, charts, data card | Offline | Files for the other two | ≤100k games in Parquet | ML / data |

**Contracts:** `contracts/battle-state.md`, `contracts/set-candidates.md` (on `main`), `agent.choose(request, battle_state) -> str | None`, and the trace line (§11). Frozen by {{time}}.

## 11. Interfaces ★

| Method · path / event | Purpose | Consumer | Auth | Key fields in → out |
|---|---|---|---|---|
| `Agent(priors).choose(request, battle_state)` | One decision per request | bot | in-process | request dict + `BattleState` → choice string or `None` |
| `Parser(us).feed(line)` · `.snapshot()` | Live log → state | bot, decision | in-process | protocol line → `BattleState` per request |
| `states_from_log(log_lines, us)` | Saved replay → states | data layer | in-process | log lines → one `BattleState` per turn |
| `data/set_candidates.json` (proposed path) | Priors for belief | decision layer | file | species → weighted sets, per `contracts/set-candidates.md` |
| `agent.last_trace` (proposed) | What the agent considered | bot trace writer | in-process | top 3 options + scores, win probability, top sets per slot |
| `runs/<battle-id>.jsonl` | Decision trace, one line per request | eval, charts, demo, coach | file | §9 trace fields |
| `runs/eval-<arm>-<machine>.jsonl` | One line per eval game | merge, charts | file | §9 eval fields |
| `ws://localhost:8000/showdown/websocket` | Showdown protocol | bot (poke-env) | `--no-security`, no account | protocol lines ↔ `/choose …` |

## 12. Tech stack ★

| Layer | Choice | Why (vs alternative) | Gotcha |
|---|---|---|---|
| Decision layer | Python, `poke-engine` 0.0.48, `uv`, `pytest --cov` | Built and merged on `main` | Builds from source: needs a Rust toolchain. Legality comes from the request, not the engine |
| Bot layer | Python, poke-env 0.16.1 (pending OK) | Only option with baseline bots + concurrent battles | #973 swallows parse errors; #246 forced-switch ordering; add `/choose ` ourselves; shard processes, not a per-turn process pool (the `Agent` keeps per-battle state) [P9 critique] |
| Game server | Pokémon Showdown, local, `--no-security` | No account, no rate limits | The web client redirects to `psim.us`, so watching needs internet; `generate-team gen9ou` throws locally [P9 B2, B5] |
| Models | scikit-learn (+ scipy for the LP), pending OK | Logistic and HGB train in minutes; scipy's HiGHS solves the LP | Batch leaf states into one `predict` call |
| Data storage | Parquet + DuckDB (recommended, nate's call) | No server to run; ClickHouse is overkill for ≤100k games | Never commit data files |
| Charts | matplotlib (pending OK), pre-rendered PNGs | Nothing to serve during the demo | — |
| Design direction | Terminal readout (plain ANSI) + Showdown client | No front-end build in the time left | — |

## 13. Non-functional requirements ★

| Quality | Target | How we check |
|---|---|---|
| Live turn latency | ≤3 s per decision, never a timeout loss | trace think time; eval p50 / p99 |
| Eval turn latency | 1.0 s think budget (proposed; stated on the data card) | eval p99 |
| Reliability | 0 stalls; fallback rate ≤ a few percent of turns | fallback counter per game (FR-4) |
| Eval size | ≥300 games on the headline leg; ~1,200 planned in total | merged eval file |
| Resource limits | one laptop: cores − 2 shards; eval sharded across 3 laptops | `nproc`, run logs |
| Restart | a killed eval loses only the battles in flight | kill test on the harness |
| Privacy / retention | public pseudonymised replays only; nothing personal stored | data card |

## 14. Security and trust ★

| Role | Can | Can't |
|---|---|---|
| Our bot accounts | Play on the local server | Touch the public server (needs bot registration under Smogon's policy) |
| Teammates | Push code to their branch, docs to `context` via the doc owner | Commit data files, secrets or shared docs to `main` |

| Threat | Mitigation |
|---|---|
| Hammering Showdown's public APIs | No scraping: test set comes from HolidayOugi; one ladder `curl` only |
| Licence misuse | Data card records each dataset's licence; no redistribution of raw data |
| Leaked credentials | No accounts needed locally; any future password goes in `.env`, never in git |

- **Hard rules:** no public-server play without a registered bot account; no data files or `.env` in git; `Research-Context/` never pushed.

## 15. Failure modes ★

| Failure | Detected by | System behaviour | User sees |
|---|---|---|---|
| `poke-engine` won't build (no Rust) | `uv sync` fails | 45-min timebox, then Docker or Derrick's Mac | nothing at the demo |
| Decision error or over the deadline | `Agent.choose` catches it; `decision` logger | first legal option, else `default`; counted as a fallback | the battle goes on |
| Fallback rate high (silent weak bot) | fallback counter per game | smoke run fails; investigate before eval | nothing |
| Malformed protocol line | parser warning | skips the line, keeps the state | nothing |
| Invalid choice | `|error|[Invalid choice]` | resend the first legal option, then `default` | nothing |
| poke-env swallows an error and hangs (#973) | per-battle watchdog | forfeit that battle, record it, carry on | eval continues |
| Socket drop or crash mid-eval | missing result lines | resume from the results file; no reconnect logic | eval continues |
| No Wi-Fi at the demo | client won't load | hotspot, then the recorded video + terminal replay from `runs/` | the recorded battle |
| Training data late | Nate's 01:00 UTC extract missing | train on the 20k extract; ship logistic | smaller test set, said honestly |
| UK clock change at 02:00 BST | timestamps jump | log everything in UTC | nothing |

## 16. Sponsor / platform fit

- **HRT (Predictions & Decision Making):** prediction = calibrated win probability + belief over hidden sets, scored on held-out games; decision = search over a simulator that uses both, proven head-to-head vs a baseline with intervals · proof: §17 tables and the live trace.
- **Best Handmade:** n/a until a piece is planned (§0 Pending).

## 17. Evaluation and success ★

| Question | Evidence | Target |
|---|---|---|
| Does the agent beat the baseline? | Team-neutral head-to-head vs `SimpleHeuristicsPlayer`, 300 games (60 pool teams × 5), Wilson 95% + cluster bootstrap by team; plus MaxBasePower 150, Random 60, fixed-team + mirror 200 | lower bound above 50% vs SimpleHeuristics |
| Are its win probabilities honest? | Log loss, Brier and a reliability diagram on games after 2026-05-19, split by battle, time and player; bootstrap by battle | better than the HP heuristic and the constant |
| Is the belief better than the prior? | Next-reveal log loss vs the prior and vs hard-filter-only, on held-out reveals and on our eval games (true sets known) | below the prior |
| Does the learned value change decisions? | Ablation: heuristic vs learned value, same seeds, 300 games | reported either way, with its interval |
| Is the agent safe to run? | Fallback rate, p50 / p99 think time, stalls | §13 targets |

| Judging criterion | Where we prove it (§ / demo beat) |
|---|---|
| Use of data for predictions | §7.2, §7.3, row 2–3 above · demo beat 3 |
| Use of data for decision making | §7.1, §7.4, row 1 above · demo beats 2 and 4 |
| Rigour and honesty | splits, intervals, the "claims we never make" list (§2) · demo beat 5 |

**Definition of done (MVP):** one command starts a live gen9ou battle on the local server in which the agent plays every turn through the decision layer with no stalls; the team-neutral eval table vs `SimpleHeuristicsPlayer` exists with intervals; the win-probability model (logistic at least) has its held-out calibration report.

## 18. Demo script ★ *(4 minutes; one row per beat)*

| Time | Beat | Live / recorded | Fallback |
|---|---|---|---|
| 0:00 | **Hook:** "Every turn, this agent guesses what's hidden in the opponent's team and how likely it is to win, then picks the move that's best under that guess." | live | — |
| 0:30 | Live battle vs SimpleHeuristics; terminal shows choice, top 3, win probability, top opponent sets | live (needs internet) | recorded video + terminal replay |
| 1:45 | Prediction proof: reliability diagram + log loss vs baselines on held-out games | PNG | — |
| 2:30 | Decision proof: win-rate bars with intervals, team-neutral | PNG | — |
| 3:15 | Data card + **honest limits** (baseline opponents, one format, no ladder Elo) + next steps | slide / PNG | — |

## 19. Milestones and cut order ★ *(UTC; Sat 21:00 UTC = 22:00 BST)*

| When (UTC) | Milestone (done means…) |
|---|---|
| Sat 21:45 | Rust toolchain decided (build works, or fallback chosen) |
| Sun 00:30 | First real game: bot + `Agent.choose` on the local server |
| Sun 01:00 | 20k-game training extract to derrick; set candidates + team pool ready |
| Sun 04:00 | Smoke eval vs Random / MaxBasePower; full training extract; recorded demo battle |
| Sun 06:00 | Win-probability model frozen |
| Sun 07:00 | Final eval starts on all three laptops (code frozen by 08:00) |
| Sun 10:00 | Feature freeze; charts and data card final |
| Sun before 12:00 | **Submit** on Devpost with the GitHub link |

**Cut order (first → last):** 1. coach review · 2. MCTS arm · 3. LP A/B (keep offline exploitability) · 4. mirror leg · 5. MaxBasePower leg size · 6. gradient boosting (ship logistic) · 7. the second chart
**Never cut:** bot working with fallback and logging; head-to-head vs SimpleHeuristics with Wilson; a calibrated, held-out, baselined prediction (logistic at least); the belief floor; the recorded demo video; the honest-limits close.

## 20. Risks ★

| Risk | Likelihood | Impact | Mitigation | Trigger to act |
|---|---|---|---|---|
| No Rust toolchain on saliha's machine blocks every `Agent.choose` there | H | H | Install first; Docker or Derrick's Mac as fallback | not building by 21:45 UTC |
| Set candidates late, so no real priors | M | H | Nate does them first; hand-made priors stay as a stand-in | not on `main` by 01:00 UTC |
| Eval compute exceeds one laptop | H | M | 1.0 s eval budget, shard across 3 laptops, explicit game budget | p50 turn time > 1 s |
| Derrick overloaded (~13 h of work) | H | M | Proposed hand-overs to nate and saliha | any task slips past its UTC milestone |
| One-ply agent already beats SimpleHeuristics by a wide margin, so no decision gain shows | M | L | Tell it as "prediction is good AND the decision beats the baseline" | headline > ~90% |
| Venue Wi-Fi down for the live client | M | M | Hotspot; recorded video | client won't load at setup |

## 21. Open questions ★

- [ ] The real Devpost deadline and what the form requires: owner saliha, needed by Sun 09:00 UTC (event doc §6)
- [ ] Can one project win HRT and Best Handmade? How is HRT judged, and by whom? Owner saliha, needed by Sun 09:00 UTC
- [ ] Are datasets prepared before 12:00 Saturday allowed? Owner saliha, needed before training
- [ ] Does poke-engine release the GIL (thread vs process shards)? Owner saliha, needed before the eval harness [P9 B1 gap]
- [ ] Does the browser cache serve the Showdown client offline? Owner saliha, needed before the recorded demo [P9 B5 gap]

## 22. Glossary
| Term | Meaning |
|---|---|
| Gen 9 OU | Showdown's main singles format for the current generation |
| Set | One Pokémon's hidden build: moves, item, ability, nature/EVs, Tera type |
| Chaos stats | Smogon's monthly usage JSON per format and rating cut-off (we use 1825) |
| Belief | Weights over each opponent Pokémon's possible sets, updated by what's revealed |
| Request | The JSON Showdown sends when we must act; it lists our legal options |
| Wilson interval | A confidence interval for a win rate that behaves well at small samples |
| Team-neutral | Both sides play the same team, so the win rate measures the agent, not the team |
| Fallback | The agent's safe answer (first legal option) after an error or timeout |
| Regret | Value of the best action minus value of the action played |

---

## Appendix *(agents can stop reading here)*

### A. Judge / user Q&A
| Likely question | Short answer (point to the §) |
|---|---|
| Isn't the win rate just your team being strong? | The headline is team-neutral: both sides play the same pool team (§7.5) |
| How do you know the probabilities are calibrated? | Held-out games after 2026-05-19, reliability diagram, log loss vs baselines (§17) |
| Why not reinforcement learning? | Not in 25 hours; search over a simulator plus a learned value is testable now (§7.1) |
| Why not use the strongest existing bot? | We'd learn nothing and couldn't show predictions; our point is the measured prediction + decision loop (§1) |
| What doesn't it do? | No ladder play, baseline opponents only, one format (§4) |

### B. Key sources
Full list: the research doc. For judges: PokéChamp (ICML 2025), Metamon (RLC 2025), the PokeAgent Challenge (NeurIPS 2025), `poke-engine`, poke-env.

### C. Version history *(the reasons live in the vault Log ADRs)*
- v3 2026-10-24: every section filled; pass 9 build plan (research + critique) behind the briefs.
- v2 2026-10-24: bot on poke-env, gen9ou, local server; decision-layer recommendations.
