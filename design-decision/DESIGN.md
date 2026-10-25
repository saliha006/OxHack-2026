# Gen 9 OU battle agent: implemented architecture

Source audit: 25 October 2026. [CURRENT-STATUS.md](../CURRENT-STATUS.md) pins branch heads, defaults, measured results and local-only boundaries. This replaces the early three-layer draft; unimplemented research proposals remain proposals.

| Layer/workstream | Implemented responsibility | Source/status |
|---|---|---|
| [Bot](bot-layer.md) | Showdown connection, public-state parser, live choices, traces, demo, evaluation | bot/, main and code branches |
| [Data](data-layer.md) | HolidayOugi cleaning, Parquet/DuckDB, Tiger tables, marginal priors | data/pipeline/, main/data branches |
| [Decision](decision-layer.md) | Belief, reconstruction, legal actions, simulation/search, choice | One-ply on main/Derrick; MCTS default on Kenar-mcts |
| [Prediction](predictions.md) | Observed-state win model; belief/root-action scoring | prediction/, Kenar-mcts; separate from search |
| [Replay backtest](backtesting.md) | Tiger JSONL → request-free choices → recorded-action agreement | backtest/, Derrick only; CLI/no frontend |
| [Coherent priors](coherent-sets.md) | Validated role/usage mixture, IV-aware candidates, reveal and battle screening | Kenar-coherent-sets; opt-in after 25–35 screening |

## Data flow

```text
Historical replays → Parquet/DuckDB → Tiger + parser-produced turns
Chaos statistics → weighted candidate JSON ──────────────┐
                                                        ↓
Showdown ↔ poke-env player → Parser → BattleState + request → Agent → legal choice
                                                          ├ main: one-ply EV/HP
                                                          └ Kenar: native MCTS/worlds
Traces + recorded turns → offline prediction/diagnostics/evaluation reports
```

Online search reads offline candidate artifacts, not Tiger on every turn. No ClickHouse deployment is implemented. Native MCTS has no learned value plugged in.

## Implemented seams

| Seam | Actual interface | Caveat |
|---|---|---|
| Bot → decision | Agent(priors).choose(request, battle_state) → str or None | Branch-specific backends/defaults; wait returns None |
| Parser → consumers | Parser(us).feed(line), snapshot(), states_from_log(log_lines, us) | Replay snapshots lack private requests/hidden sets |
| Data → belief | SetCandidates.load(path), data/set_candidates.json | Implementation/tests are ahead of stale set-contract prose |
| Decision → trace | agent.last_trace on MCTS; bot JSONL state/choice/timing/fallback | Native root support is not calibrated P(win); branch schemas differ |
| Tiger → offline | contracts/turns.md; joins on id and started_at | Actions/post-turn/winner are labels, not serving features |
| Replay → decision | Derrick choose_public(battle, our_sets) | Branch-only, fixed-trajectory action agreement |

## Completed and remaining

Parser, simulator, live handling, legacy strategy, real priors and ingestion are built. MCTS/prediction exist on Kenar branches; integration into main is not implied. No general strength gain has been established by the small studies. Roster-conditioned priors, learned search evaluation, adaptive allocation, maximin LP and coach review remain unimplemented or unverified. The old stage-3/4 TODOs and TypeScript simulator plan no longer describe the code.
