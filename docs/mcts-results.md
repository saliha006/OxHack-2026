# Measured MCTS baseline and prediction results

> **25 October user decision:** MCTS is now the default development backend (8 worlds, 150 ms/world, one thread). The evaluation arms explicitly retain one-ply for fair comparisons. Earlier default recommendations and measurements below are historical; the promotion is a user choice, not a new strength result.

The default backend remains **`one_ply`**. The alternative backend is legal and deadline-contained in the tested cases, but this small comparison does not establish greater playing strength. The learned prediction model also remains experimental and is not used by search.

## Source and protocol

The clean two-game integration gate and 24-game pilot ran from an immutable copy of commit `46885bd`, effective Python source SHA256 `f182c3b0e26228d90e25ff94f011e1aa94d1124e98abe6fd0f95556d075a2692`. The copy prevents ongoing documentation and review work from changing running workers. Gen9/Tera `poke-engine==0.0.48`, one engine thread, 150 ms per world, a three-second decision ceiling and four concurrent pilot games were recorded. Actual native time and completed worlds were measured separately from these requested settings.

Each comparison has four games: two unchanged, reserved offense/bulky-offense teams, each played on both sides. This is a bounded pilot. The larger saved configuration uses all four reserved teams and is **not reported as completed**. The teams were reserved before these runs, but may overlap the public battles underlying aggregate Smogon priors. They now form evaluation/regression history; a confirmatory study should reserve fresh teams.

Foul Play was upstream commit `8f541f80f91f960603673796559f796b10ccf0fb`, with the same native engine binary, one thread and one search process. Its four games were balanced across p1/p2. Its variable one/two-world policy and 150–260 ms per-world band differ from our eight-world total budget. Those games verify external-opponent integration, with **unmatched compute** explicitly recorded; they cannot isolate strength at equal compute.

## Games

| Comparison, first arm's result | Record | Win rate | Wilson 95% interval |
|---|---:|---:|---:|
| Single-world MCTS vs existing agent, early gate | 1–1 | 50% | 9.5–90.5% |
| Eight-world MCTS vs existing agent | 3–1 | 75% | 30.1–95.4% |
| One × 1200 ms vs eight × 150 ms | 2–2 | 50% | 15.0–85.0% |
| One × 150 ms vs eight × 150 ms | 1–3 | 25% | 4.6–69.9% |
| Whole-team vs active-only sampling | 3–1 | 75% | 30.1–95.4% |
| Updating vs hard-filter-only beliefs | 2–2 | 50% | 15.0–85.0% |
| Eight-world MCTS vs Foul Play | 2–2 | 50% | 15.0–85.0% |

There were no void pilot games. Team-bootstrap intervals are included in the JSON report, but two team clusters provide very little information. Same-team mirrored games and multiple turns are dependent; the table is not a population-strength estimate. The HP-based one-ply agent uses less actual compute than MCTS despite sharing its decision ceiling.

Across both Agent perspectives, the pilot made **1,288 MCTS decision calls**, including 40 previews. All **7,863 requested native worlds completed and were usable**. There were zero observed fallbacks, rejected choices, failed worlds or decisions over three seconds. For the eight-world arm, pooled p50/p95/p99 decision latency was **1,367 / 1,436 / 1,979 ms**; its maximum was 2,049 ms. Across every MCTS arm the maximum was 2,054 ms. These are practical shared-desktop observations; a 22.4-second position-analysis run overlapped the pilot, as recorded in the environment note.

Native search results are stochastic. On one fixed position, five repetitions at each of one, two and four threads all chose Swords Dance with no fallback. Median native visits rose from 18,000 to 34,000 to 57,000, while median native search time was 165, 174 and 196 ms. More threads increased work per world and did not divide sequential wall time. This is one-position throughput/agreement evidence, not a strength result; the default remains one thread.

## Failure containment and final hardening

Fixtures cover stalled preparation/search, process exit, partial framed replies, blocked initialization/job writes, interrupted-world retention and worker replacement. Independent review also identified the final notification that records the selected action for next-turn belief replay. That notification and retry invalidation now use bounded writes; the worker already retains its request, so only the compact action is sent. Failed preparation is never recorded as replay evidence. A bookkeeping failure preserves the legal selected action, retires the worker when needed and records lost history.

That transport/trace hardening happened after the frozen pilot and does not change search selection. A subsequent real eight-world smoke game won in 52 turns: **424/424 worlds usable**, zero fallbacks, rejected choices or bookkeeping errors, and maximum decision latency 1,977 ms. It verifies final integration, not a strength improvement. The final combined suite passed 402 tests with one credential-dependent Tiger integration check skipped; the mixed Agent/external-opponent scoring fix subsequently passed all 20 focused prediction tests.

## Predictions and belief quality

The independent prediction experiment acquired the first 100 public ladder replays from a frozen two-page selection. Ninety-six met the predefined rated, completed, six-plus-turn criteria, giving 2,517 observed turns. Whole battles were split chronologically into 67 train, 14 validation and 15 test games. Preprocessing used training only; Platt calibration used validation only. Public replay metadata does not prove the participants were human.

On the 15-game test split, calibrated logistic regression had log loss/Brier **0.6600 / 0.2338**, while the HP baseline had **0.6348 / 0.2215**. The simpler baseline performed better. The strict unseen-player/roster subset has only five games and uses preview-roster proxies for unknown complete sets. These limits preclude a calibrated-model improvement claim.

The pilot's 611 next-revelation examples gave loss **2.7074** for the original prior, **3.0745** for hard filtering, and **3.0773** for the recorded posterior. The inference variants did not improve this metric. These examples pool several experimental arms; they are diagnostic bot-game evidence, and the assumed next-new-move distribution is explicitly uniform within each candidate's remaining moves. No full-set coverage claim is made without supplied ground truth.

For 927 observed bot replies, opponent visit-share loss was **2.8223**, versus uniform **3.5420**. The scorer excluded 350 unknown replies, 44 previews and 80 decisions without a prediction, and applied declared smoothing to 107 replies outside the native root options. This is a diagnostic likelihood score; visit shares remain uncalibrated. It does not establish human-opponent prediction quality.

## Reproduce and inspect

- [Pilot configuration](../evaluation/mcts-pilot.json), [full study configuration](../evaluation/mcts-baseline.json), [hardware/source settings](../evaluation/mcts-environment.json).
- [Pilot summary](../evaluation/mcts-pilot-20261025/summary.json), [all game rows](../evaluation/mcts-pilot-20261025/games.jsonl), [both-perspective reliability](../evaluation/mcts-pilot-20261025/reliability-by-arm.json), [clean gate](../evaluation/mcts-gate-20261025/eval-summary.json).
- [Final-code smoke](../evaluation/mcts-hardened-smoke-20261025.json), [thread measurements](../evaluation/mcts-thread-benchmark-20261025.json), [same-position inputs/results](../evaluation/mcts-position-comparison.json).
- [Prediction model/data split/calibration](../evaluation/prediction-public-20261025/metrics.json), [belief scores](../evaluation/prediction-bot-pilot-beliefs-20261025.json), [opponent action scores](../evaluation/prediction-bot-pilot-actions-20261025.json).

Use `uv run python -m bot.eval --runs <new-output-folder> run --config evaluation/mcts-pilot.json` against a local Showdown server, followed by the `report` subcommand. Regenerate pooled reliability with `uv run python -m evaluation.summarize_pilot --games evaluation/mcts-pilot-20261025/games.jsonl`. Saved raw protocol/decision traces remain in the local ignored `runs/` folders; their paths are retained in game rows. [The evaluation guide](mcts-evaluation.md) and [prediction guide](mcts-prediction.md) give full setup and scoring commands.

Earlier runs that exposed duplicate trace paths, premature challenge completion, seed-reused account reconnections or source mutation were retained locally for debugging and excluded from these results. No default backend promotion, learned search evaluator, teammate-conditioned prior or separate opponent weighting was introduced.
