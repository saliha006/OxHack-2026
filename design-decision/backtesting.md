# Replay backtesting

Verified 25 October 2026 against `derrick` at `9f86111365ecefb510408dcfdf03aea925def085`. [Branch inventory](../CURRENT-STATUS.md). Main records this work in progress but does not contain `backtest/`.

## Implemented flow

1. `uv run --group data --env-file .env python -m backtest.tiger` copies read-only Tiger rows verbatim to ignored `runs/tiger/turns.jsonl`, using a server cursor and atomic destination replacement. Psycopg is an optional data dependency on this branch. Credentials remain local.
2. `uv run python -m backtest.engine` samples recorded test games (default 200, seed 2026), prepares our guessed sets and calls `Agent.choose_public(battle, our_sets)` at each public-state snapshot. No fabricated live request is needed; default think budget is three seconds.
3. It compares choices with recorded p1 moves/switches, optionally including Tera, and streams JSONL plus a summary to `runs/backtest/`. Games with species absent from priors are skipped/counted. Strategy errors are recorded per turn and the run continues.

Our full-game revealed moves/Tera reconstruct player-known own-set information; items/abilities come from the current snapshot. Unrevealed own details are guesses. `choose_public` is a separate API; the live choose contract is unchanged and public-path errors can propagate to the recorder.

## Interpretation and results

This is action agreement on fixed trajectories, not counterfactual wins, player-skill calibration or a forward-only hidden-set inference benchmark. There is **no dashboard/frontend**; the recorded 04:15 decision chose a CLI backend.

Main progress records 125/200 games played, 75 skipped; 29.9% agreement over 3,003 scorable turns (game-bootstrap 95% 27.6–32.4%), 21.4% including Tera. Attack agreement 38%; switch agreement 3%; strategy switched 4% vs recorded players 24%. Latency p50/p99/max 163/475/954 ms. One NaN-selector error among 3,310 turns. These are recorded results, not rerun here.

A local same-month all-ratings prior rebuild allowed 195/200 games, with 31.5% agreement (95% 29.6–33.5%). The committed prior is still 1825; Nate's agreement/rebuild remained open. Coverage and NaN handling remain follow-ups.

Sources: [engine](https://github.com/saliha006/OxHack-2026/blob/9f86111365ecefb510408dcfdf03aea925def085/backtest/engine.py), [Tiger dump](https://github.com/saliha006/OxHack-2026/blob/9f86111365ecefb510408dcfdf03aea925def085/backtest/tiger.py), [public API](https://github.com/saliha006/OxHack-2026/blob/9f86111365ecefb510408dcfdf03aea925def085/decision/agent.py), [recorded decisions/results](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/progress.md).
