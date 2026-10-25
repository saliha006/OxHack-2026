> **Superseded for `main`, 2026-10-25 ~10:00 UTC.** Since this 06:30 audit, Kenar's MCTS was merged to `main` (PR #1, 07:01) and is the default; `main` also now has `prediction/`, `evaluation/`, `analysis/`, the battle-chat demo stream, MCTS eval pairings with Foul Play `fphard`, joint priors, a 4-thread arm and an opt-in Tera gate. The rows below that say "main … no MCTS" are historical. How `main` works today: [the PRD (v4)](OxHack-2026-PRD.md). The branch pins, measurements and limits below remain the evidence record.

# Current implementation across branches

Source audit refreshed **2026-10-25T06:30:34.334294+00:00** (branch heads re-fetched; earlier measured results retained). This is a snapshot, not a live monitor. It refreshes context from source and saved artifacts without merging implementation branches or declaring team approval for experiments. Start here, then read [DATA-CONTEXT.md](DATA-CONTEXT.md) for datasets, contracts and training/test provenance, and the relevant design doc.

## Branch inventory and publication boundary

All eight GitHub branches were enumerated through the connected account and fetched. The full commit IDs pin the source inspected; branch names may advance. Context started at `17814b5055ee3967b27dfc03dadcdc48d4a87470` and contains documentation only.

| Branch | Inspected commit | What is actually there |
|---|---|---|
| main | bbb95d60fb57a01497aae370d8ca922c275bb79d | Live bot/parser/evaluation/demo, legacy one-ply decision engine, marginal priors, data pipeline and turns contract. No MCTS, prediction package or backtest package. |
| sali | 25f7afa1b58718a85b332a6059302cfc1d8432ab | Bot/decision source matches main; lacks subsequent data pipeline and progress updates. |
| derrick | 9f86111365ecefb510408dcfdf03aea925def085 | One-ply engine plus Tiger dump, request-free public-state choices and replay-backtest CLI; five unique commits since common main ancestor. No frontend. |
| nate-data | e6700d3a14e4c364eb0b34cfb7d9e31713234b2d | Data source/contracts match main; later differences are progress history. |
| Data-stuff-(Nate) | 6c5bf4b9f8b32fbea55547562ab5e29238414da9 | Older branch still exists remotely despite the recorded rename. Pipeline matches main; lacks turns contract and later progress updates. |
| Kenar-mcts on GitHub | 2c02fc8daa84f047ea2bddd7d0f36f6463fff1e2 | Default MCTS, isolated native workers, whole-team sampling, prediction/evaluation tools and original pilot. |
| Kenar-mcts local | 09ae92eb88f96541c2d443322e0b4f87509a89da | **13 unpushed commits**: state/belief/Tera fixes, immutable comparisons, optional lead/mixing policies, later evidence. Also separate uncommitted work. Not all available from GitHub. |
| Kenar-coherent-sets | 50d9a4362da5946918bd0a52d6689e582d16e46f | Published template/usage mixture, IV support, reveal diagnostics and complete 60-game screening; opt-in. Excludes later MCTS changes. |

Pinned roots: [main](https://github.com/saliha006/OxHack-2026/tree/bbb95d60fb57a01497aae370d8ca922c275bb79d), [sali](https://github.com/saliha006/OxHack-2026/tree/25f7afa1b58718a85b332a6059302cfc1d8432ab), [derrick](https://github.com/saliha006/OxHack-2026/tree/9f86111365ecefb510408dcfdf03aea925def085), [nate-data](https://github.com/saliha006/OxHack-2026/tree/e6700d3a14e4c364eb0b34cfb7d9e31713234b2d), [old Nate](https://github.com/saliha006/OxHack-2026/tree/6c5bf4b9f8b32fbea55547562ab5e29238414da9), [published MCTS](https://github.com/saliha006/OxHack-2026/tree/2c02fc8daa84f047ea2bddd7d0f36f6463fff1e2), [coherent sets](https://github.com/saliha006/OxHack-2026/tree/50d9a4362da5946918bd0a52d6689e582d16e46f). The local MCTS SHA is intentionally not presented as published.

## Runtime and defaults

**Main:** `Agent(priors, k=5, budget=3.0)` combines deterministic belief scenarios, uniform opponent replies, one-turn poke-engine simulation and expected HP/alive value. Type-matchup preview leads, forced switches, belief floors and fallback exist. Parser, live poke-env player, raw/JSONL/decision logs, demo, resumable/sharded evaluation, ablations, optional Foul Play processes and internal Bradley–Terry reports are implemented. Harness support does not prove its full proposed ladder or 300-game headline completed.

**Published MCTS:** MCTS is already the default on Kenar-mcts; `one_ply` remains a comparator. Per-world native visit shares are normalised before averaging and mapped to legal request actions. A process boundary supervises deadlines and preserves completed worlds. Native evaluation is hand-written; visit shares/support are **not calibrated win probabilities**.

**Local MCTS:** eight whole-team worlds ×150 ms, one native thread, three-second ceiling, `belief_mode="reliable"`, `lead_policy="types"`, `mix_root=False`. State/PP/history, guarded inference and retention of used Tera after its user faints are enabled correctness fixes. `moves_stats` lead and seeded near-tie mixing exist but stay off. Fixed 4×300/12×100 allocations have development studies/frozen schedules; no adaptive allocator. The switch-cycle guard was rejected before runtime integration. No stock persistent-tree continuation API is used.

Sources: `decision/{agent,adapter,state,belief,search,search_worker,lead,root_mixing}.py` and `bot/{player,parser,eval,demo}.py`; some files exist only at the newer local revision. See [decision](design-decision/decision-layer.md), [predictions](design-decision/predictions.md), [bot](design-decision/bot-layer.md).

## Data and Tiger

- Committed `data/set_candidates.json` uses **September 2026 gen9ou-1825 marginals**, not joint observed sets: reported 243 species +78 aliases, up to 30 candidates/species. Choice items can keep status moves such as Trick; only Assault Vest bars them. No explicit other-set bucket or roster-conditioned A6 service in v1.
- Main implements HolidayOugi replay cleaning → local Parquet/DuckDB → Tiger/Postgres. Source-recorded counts: **2,506,142 battles/logs**, **489,840 turns/20,000 games**: train 15,000 games/361,437 turns; test 5,000/128,403. These are extraction records, **not a fresh database query**.
- Turns use the live parser and include all 12 species/HP/status entries, public state, recorded actions and winner. Post-turn/action/winner fields are labels/diagnostics, not prediction features. Tiger joins require ID **and** `started_at`.
- Train from 2025-01-01; test from 2026-05-19; freeze 2026-10-24 11:00 UTC. No validation split in this extract. Test player overlap **43%**, exact-team overlap **38%**; only **1,909** test games share neither. Do not call the whole split player/team-disjoint. Recorded HP baseline log loss/Brier **0.6407/0.2246**; opponent switch share **19.2%** of acted turns.
- Removing the 1825 cutoff was locally tested/requested; Nate's agreement/rebuild remained pending. The committed file is **not** cutoff 0.
- Kenar's Tiger exporter/training plumbing is uncommitted; downloading/training remain explicitly **paused**. No completed Tiger-trained model is claimed. This refresh did not access Tiger or restart work.

Sources: main `data/pipeline/`, `contracts/turns.md`, `progress.md`; [data layer](design-decision/data-layer.md). Plain main `uv sync` does not install every optional pipeline dependency; consult branch-specific setup.

## Replay backtest: Derrick only

`backtest/tiger.py` copies read-only rows verbatim to JSONL. `backtest/engine.py` calls `choose_public(battle, our_sets)` on recorded states and compares with p1. Full-game own moves/Tera reconstruct player-known own sets; items/abilities stay time-specific. This is **action agreement**, not changed battle trajectories, win rate or a calibrated expertise score. It is a **CLI with no frontend**, absent from main/Kenar branches inspected.

Recorded first run: **125/200 games played**, 75 skipped; **29.9%** agreement over 3,003 scorable turns, game-bootstrap 95% **27.6–32.4%**; **21.4%** including Tera. Latency p50/p99/max **163/475/954 ms**; one NaN-selector error among 3,310 turns. Local all-ratings priors allowed **195/200** games, agreement **31.5%** (95% **29.6–33.5%**). These runs were not repeated here. See [backtesting](design-decision/backtesting.md).

## MCTS measurements and their limits

| Experiment | Observed result | Interpretation/publication |
|---|---|---|
| Original pilot | 24 games/six pairings; MCTS vs one-ply **3–1**; vs Foul Play **2–2** | Published; four-game comparisons, very uncertain; Foul Play compute unmatched. |
| Pilot reliability | 1,288 MCTS calls; **7,863/7,863 usable worlds**; no observed fallback/rejection/>3s decision; eight-world p50/p95/p99 **1367/1436/1979 ms** | Reliability on those configurations/games. |
| State fixes vs original | **35–25/60**, Wilson **45.7–69.9%** | Locally committed; inconclusive, predates Tera repair. |
| Reliable belief vs original | **35–25/60**, same interval | Locally committed; strength unproven, predates Tera repair. |
| Reliable belief vs Stage 1 | **27–33/60**, Wilson **33.1–57.5%** | New ignored local raw summary only; complete, no draws/voids. |
| Corrected Tera cumulative bot vs original | **32–28/60**, Wilson **40.9–65.4%** | New ignored local raw summary only; complete, no draws/voids. |
| Stage 6 mixing smoke | Two six-turn-censored voids; **192/192 worlds**; zero fallback/server rejection/mapping discard | Untracked; **zero mixing-eligible/sampled/changed positions**. Transport only. |

All four 60-game intervals include parity. Roster combinations reuse familiar component sets, not independent external-set holdouts. Historical Stage 1/2 screens balance sides and aggregate exposure but do not swap both bot/team assignments within every exact matchup; later plans use four-game blocks. No completed summaries establish the later Stage 3/4 screens, Tera-vs-incumbent, full confirmations or final cumulative comparison. Plans/manifests are not completed games.

Published sources: `evaluation/mcts-pilot-20261025/{summary.json,reliability-by-arm.json}`, `docs/mcts-results.md`. Local committed: `evaluation/mcts-improvements/{stage1-screening-results.json,stage2-original-screening-results.json,strategic-guard-decision.json,allocation-development-v2-results.json}`, `docs/mcts-improvement-log.md`. Latest recorded MCTS full suite **495 passed**; not rerun during this audit.

New raw summaries: `runs/mcts-improvements/stage2-incumbent-screening-v1/summary.json`, SHA256 `30fb6663d10e48565f76b3fc152090f8eac26b739254e73acfffb8f87d3538fc` (modified 06:14:17 UTC); `runs/mcts-improvements/tera-followup-original-screening-v1/summary.json`, SHA256 `c852b33ac3e60cdf8a5f29ce49a9b7ad1d3462a9b37139a801ac7a6c540e32c4` (06:17:27 UTC). These artifacts remain local. Untracked `evaluation/mcts-improvements/stage6-smoke-results.json` SHA256 `ff693b1a547f2d5a8d27c44efde60b1088662cd7f1d91db51ca4a3a8c1470884` records the smoke only.

## Prediction is separate from search

MCTS-branch `prediction/` public study: **96 games/2,517 turns**, chronological battle split **67 train/14 validation/15 test**. Calibrated logistic test log loss/Brier **0.6600/0.2338**, worse than HP **0.6348/0.2215**. Strict unseen subset is only five games/128 turns; roster proxies are not hidden-set identities and human-only provenance is unverified. **Search never calls this model.**

Published pilot next-reveal loss: prior **2.7074**, hard filter **3.0745**, posterior **3.0773**; no predictive gain. Opponent-action visit-share loss **2.8223** vs uniform **3.5420** is a bot-only diagnostic, not calibrated human action prediction. Untracked Stage 2-original diagnostic (791 reveals) also favors the prior: **2.318296** vs revelations **2.857000**, legacy-hard **2.965288**, reliable-hard **2.935730**, reliable-soft **2.980440**. No full-set accuracy claim.

Sources: `docs/mcts-prediction.md`, `evaluation/prediction-public-20261025/{metrics.json,source-manifest.json,model.json}`, `evaluation/prediction-bot-pilot-{beliefs,actions}-20261025.json`; local `evaluation/mcts-improvements/stage2-original-belief-scoring-results.json`, SHA256 `c057de6e26245c19fe647ac21706f1f1ab46b6d26692ebf4ff4112883ceb06ea`.

## Coherent priors: published, opt-in

Kenar-coherent-sets imports pinned validated Showdown role templates and mixes them **50/50** with usage candidates, preserving optional IVs. **556 variants**, **160 augmented species/form aliases**, two incomplete templates rejected. Equal role/alternative mass is heuristic, not learned joint frequency or roster-conditioned A6.

Retrospective 100-game/2,821-reveal diagnostic: unfiltered loss **4.0469 → 3.7062**; filtered **4.5569 → 4.2334**; support **73.8% → 76.6%**. Filtering worsens both arms; ability loss slightly worsens. Complete screening: **25W–35L**, no draws/voids, Wilson **30.1–54.3%**, **43,712/43,712 usable worlds**, zero fallback/rejection/failed world/>3s decision. Ten synthetic rosters are not an external-set holdout. Engine/belief anchor **a8613b9** excludes later MCTS changes; treatment includes IV compatibility.

Recorded decision: **keep opt-in; default remains `data/set_candidates.json`**. No playing-strength gain or expansion of this exact mixture to 200-game confirmation is justified. Recorded test gates: focused **22 passed**; full attempt **478 passed/1 failed**, same scheduling fixture also failing on untouched baseline. Do not call the full suite green. [Design and pinned evidence](design-decision/coherent-sets.md).

## Actual gaps and stale records

Remaining: roster-conditioned A6/joint-team priors; independent competitive-set holdouts; controlled later-stage/confirmation/panel results; better demonstrated prediction and separately evaluated search integration; Derrick replay missing-species/NaN follow-ups; branch integration decisions. Kenar Tiger training stays paused. Maximin LP, adaptive allocation, coach review and backtest frontend are not established implemented features.

Main README remains provisional Momentum text. Main progress has stale latest/team/startup rows alongside newer backtest/data entries. Main set-contract prose still says draft and wrongly prohibits Choice status moves. MCTS results retain historical one-ply-default wording; its index says Stage 5/6 pending and now-complete local screens running. This refresh corrects interpretation in context; it does not edit other branches or close teammate-owned board items. Earlier milestones/research recommendations are historical, not current task assignments or proof of completed runs.

Re-fetch and inspect source before future implementation claims. The local checkout and evaluation jobs are actively changing; do not promote an observed implementation into team agreement or a plan into a result.
