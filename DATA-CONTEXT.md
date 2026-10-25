# Data, contracts, training and test context

Snapshot: 25 October 2026. Branch pins/defaults/results: [CURRENT-STATUS.md](CURRENT-STATUS.md). Machine-readable path/size/SHA-256 inventory: [data-artifact-inventory.json](data-artifact-inventory.json). This records available artifacts, not a claim that every file trained a model. Raw datasets remain in their existing storage.

## Sources and actual use

| Source/artifact | Use and status |
|---|---|
| HolidayOugi replay Parquet → `data/clean/battles/` | Historical gen9ou corpus; `data/pipeline/clean_battles.py`, DuckDB/Parquet cleaning; upstream URL is recorded in the pipeline/progress source. Tiger-recorded 2,506,142 games/logs. |
| Tiger/Postgres `battles` | Player IDs, pre-game Elo, six-species preview rosters/leads, outcome and timestamps. Roster identity is not complete hidden-set identity. |
| Tiger `battle_logs` | Raw protocol logs; reveals are partial observations, not exact complete sets/EVs/IVs. Recorded raw-log size 9.2 GB. |
| Tiger `turns` | 489,840 public start-of-turn states / 20,000 games; actions/outcomes are labels. Existing training resource; no completed Tiger-trained model established. |
| September 2026 Smogon gen9ou-1825 chaos marginals | Runtime `data/set_candidates.json`: 574,541 source battles, 321 species/form aliases, up to 30 candidates/species. Marginal combinations are not observed joint sets. All-ratings rebuild was tested separately; default file remains 1825. |
| Public Showdown replay API, latest gen9ou | Completed small prediction study: 100 requested, 96 accepted, 2,517 turns; chronological 67 train /14 validation /15 test battles. Full IDs, URLs and source/log hashes in `evaluation/prediction-public-20261025/source-manifest.json`. Not verified human-only. |
| Showdown OU role templates / pinned pkmn/smogon source | Coherent-prior branch: 556 variants, 160 augmented aliases, two incomplete templates rejected; 50/50 template/usage mixture; optional IV support. Opt-in after 25–35 battle screening. |
| Synthetic teams + local bot battles | Original MCTS pilot, frozen improvement schedules and coherent-prior screens. Evaluation manifests carry arms, seeds, teams and compute. Familiar component sets are not independent external-set holdouts. |
| Foul Play | Optional external comparison bot; original pilot compute unmatched. No human ladder Elo claim. |

## Tiger schema, contracts and splits

Exact main-branch prose snapshots: [BattleState](contracts/battle-state.md), [set candidates](contracts/set-candidates.md), [turns](contracts/turns.md). Executable interfaces remain `contracts/battle_state.py`, `contracts/set_candidates.py`, `decision/sets.py` and branch-specific tests. The set-contract prose is older than implementation: Choice items may have status moves; only Assault Vest forbids them. Coherent-sets extends candidates with optional IVs.

Tiger keys: `battles(id, started_at)`, `battle_logs(id, started_at)`, `turns(battle_id, turn, started_at)`. Join using ID **and timestamp** for correctness and monthly chunk pruning. No credentials or database endpoint values are included here. Read-only access uses private `TIMESCALE_SERVICE_URL`; no queries in `Agent.choose`.

The turns contract specifies 99 columns: identity/time/split/winner/Elo; public active HP/status, alive/HP totals, boosts/Tera/hazards/screens; twelve preview slots' species/HP/status; field; actions, first mover, crit/faints/Tera; full JSONB state. State precedes each turn. Forced faint replacements have no separate row; choices hidden by a knockout are censored. Player names, final outcomes and post-turn actions must not leak into serving features.

Frozen table: train 15,000 games /361,437 turns from 2025-01-01 through 2026-05-18; test 5,000 /128,403 from 2026-05-19 through 2026-10-05. Freeze excludes starts at/after 2026-10-24 11:00 UTC. Rated, known Elo both sides, six-plus turns, binary winner, seed 2026. Source table has no validation split. Test overlap: 43% players, 38% exact species rosters; 1,909 test games share neither. Report full and strict subsets separately. Raw cleaning additionally reserves smogtours IDs as eval; that does not make this turns sample a three-way split.

Local Tiger tooling (`data/tiger.py`, `prediction/tiger.py`, `docs/tiger-setup.md`) provides streaming read-only export with JSONL, battle metadata and hashed manifest; compact feature preparation and logistic/calibration training. Proposed validation cutoff 2026-03-01 within source train; scaling/coefficients train-only, calibration validation-only. Expected local outputs: `runs/tiger/turns.jsonl`, `turns.battles.json`, `turns.manifest.json`, `features/`, `model/{model,metrics}.json`. Tooling exists locally; full export/training remained paused. Do not infer completion from commands/docs. This refresh did not connect to Tiger or restart training.

## Completed training and tests

Small public model: `prediction/` shared observed-state features and `WinModel`; `evaluation/prediction-public-20261025/{model,metrics,source-manifest}.json`. Calibrated logistic test loss/Brier 0.6600/0.2338 versus HP 0.6348/0.2215; strict unseen subset five games/128 turns. Search does not call this model.

Belief/action diagnostics: `evaluation/prediction-bot-pilot-{beliefs,actions}-20261025.json`, local `evaluation/mcts-improvements/stage2-original-belief-scoring-results.json`, coherent branch reveal reports. Later revelations are scoring targets only; filtering currently worsens the recorded next-reveal losses. No exact-spread/full-set accuracy claim.

Battle studies: `evaluation/mcts-pilot-20261025/`, `evaluation/mcts-gate-20261025/`, `evaluation/mcts-improvements/`, coherent branch `evaluation/coherent-sets/`. Manifests define planned runs; result files and completed summaries establish observed results. See current-status for scores and uncertainty. Inventory includes local summary hashes without publishing raw logs. Do not label a planned confirmation/panel as completed.

Derrick backtest uses fixed Tiger trajectories and reconstructed own sets to compare recorded actions, not train a counterfactual win model. Recorded 200-game sample: 125 eligible, 29.9% action agreement; separate all-ratings-prior trial 195 eligible, 31.5%. [Backtest details](design-decision/backtesting.md).

## Provenance limits and next work

Current templates/September usage applied to older replay games make those studies retrospective even with chronological battle splits. Logs, turns and source replay exports can be the same battle: deduplicate identity/timestamp. Unrevealed fields remain unknown. Independent set holdouts, roster-conditioned A6/joint hypotheses and a demonstrated learned search value remain gaps. Opponent-model and fact-filtering diagnostics and one-team specialization were active in other chats at snapshot time; no finished result is implied.
