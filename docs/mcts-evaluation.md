# MCTS evaluation

The default decision backend remains `one_ply`. The initial game comparison is an integration gate. It cannot establish a strength improvement. Visit shares in traces are **search support**, not calibrated win probabilities. Training or calibrating a prediction model is a separate experiment.

## Integration

Start the local Showdown server on port 8000, install the project with its Gen 9/Tera build settings (`uv sync`), and run from the repository root:

```sh
uv run python -m bot.smoke --backend mcts --worlds 1 --search-ms 150 --engine-threads 1 --priors data/set_candidates.json --games 2 --runs runs/mcts-smoke
uv run python -m bot.eval --runs runs/mcts-integration run --pairings mcts-current --games 2 --teams bot/teams/standin --priors data/set_candidates.json --budget 3 --shards 1 --seed 2026
uv run python -m bot.eval --runs runs/mcts-integration report
```

`mcts-current` compares one 150 ms search world against the existing one-ply agent. Adjacent games use the same team and swap sides. The same seeded team pairs are shared across the MCTS comparisons. The stand-in pool tests integration and is not declared held-out.

Each agent writes a raw `.log`, decision `.jsonl`, and decision error log in `runs/players/<account>/`; the per-game result links both agents' artifact paths. Separate directories prevent mirror-match players with the same battle tag from overwriting each other's logs. Decision records include the exact request and observed state. Compare disagreement positions using these inputs, sampled sets, visits, supported legal choices and chosen action. Setup, recovery, Protect, switches and Tera remain in the engine's search options. A native crash or timeout must preserve completed worlds and return a legal fallback before the decision deadline.

## Main comparison

Supply a held-out team pool at `bot/teams/held-out` before running the saved configuration. This directory is deliberately not populated by copying training or stand-in teams. Record how the pool was held out from model fitting and tuning alongside the results. Do not build priors from those teams; the CLI rejects that combination.

```sh
uv run python -m bot.eval --runs runs/mcts-held-out run --config evaluation/mcts-baseline.json
uv run python -m bot.eval --runs runs/mcts-held-out report
```

Explicit command-line settings override the saved config. Use a fresh output directory when input hashes, prior source, seed, engine or compute settings change. The harness rejects a resumed run with incompatible settings instead of mixing its rows.

| Pairing | Arm A | Arm B | Question |
|---|---|---|---|
| `mcts-current-pooled` | 8 worlds × 150 ms | current one-ply | Practical performance at the same 3 s decision ceiling |
| `mcts-worlds-equal-total` | 1 world × 1200 ms | 8 worlds × 150 ms | Depth versus hidden-state coverage at equal requested search time |
| `mcts-worlds-equal-per-world` | 1 world × 150 ms | 8 worlds × 150 ms | Additional hidden worlds with additional compute |
| `mcts-bench` | whole-team sampling, 8 × 150 ms | active-only sampling, 8 × 150 ms | Bench uncertainty |
| `mcts-inference` | updating beliefs, 8 × 150 ms | frozen beliefs, 8 × 150 ms | Inference during battle |
| `mcts-foulplay` | whole-team MCTS, 8 × 150 ms | existing Foul Play integration | Established search opponent |

All MCTS presets request one engine thread; native thread count is recorded separately from concurrent games. Search worlds run sequentially. Equal requested milliseconds do not imply equal completed search work: preparation, process startup, early game termination and native variation affect actual time and visits. Reports include completed/failed/usable worlds and actual native search milliseconds. The 3 s deadline includes preparation and reserves approximately 300 ms for returning a choice.

The MCTS frozen-belief arm keeps a persistent hard-filter-only belief. It preserves revealed facts and accumulated hard item inferences, and disables soft damage/speed replay by clearing the preceding simulated choice before the update. Candidate likelihood weights therefore stay at their prior values apart from hard filtering and recovery. The older `prior` and `flat` one-ply ablations retain their historical definition of freezing the entire candidate distribution; they are not the MCTS inference comparison. Evaluation shards use spawned processes because poke-env starts an event-loop thread at import, which is unsafe to inherit through fork.

Foul Play must be installed independently at `foul-play/` with its own environment and the `--team-list` / `challenge_user` CLI support. The local integration was checked against official upstream commit `8f541f80f91f960603673796559f796b10ccf0fb`. Its environment uses the same compiled `poke-engine==0.0.48` Gen 9/Tera binary as our agent (verified SHA256 `fbffd2a1c9c48eab99def9187f9030c578174a30b49d54faad159be859846ef3` during setup), plus upstream's pinned requests/websockets/dateutil dependencies.

`mcts-foulplay` starts a separate external process for each game. On even games our agent challenges Foul Play; on odd games Foul Play uses `--bot-mode challenge_user --user-to-challenge <agent>` while our player accepts. Adjacent games use the same team and Foul Play search setting, and swap challenge direction. The legacy non-MCTS Foul Play ladder retains its persistent accepting processes. Game rows record the observed side, configured budget, upstream source revision, raw external log, and deduplicated per-world iteration counts. External games are bounded and a failed opponent process surfaces as an evaluation error.

Both Foul Play search parallelism and engine threads are explicitly one. Its stock policy searches two worlds during team preview and while fewer than three opponent moves are known, and usually one thereafter. `foul_play_searches` records the actual world settings emitted by upstream and completed root iteration counts; configured milliseconds are never labelled measured search wall time. The saved settings retain the 150–260 ms **per world** band, which is a different total search budget from our 8 × 150 ms. The game record explicitly declares `compute_matched: false`. This comparison tests integration against an established search opponent; it cannot isolate strength at equal compute without a separately measured run.

## Measurements and repeatability

`eval-manifest.json` records engine/Python version, git revision, effective Python source hash, full arm settings, concurrent games, decision budget, seed, team hashes, OU prior hash and source, and the declared team role. Each game records both arms' summaries when available. Battle summaries contain the raw per-decision latencies, actual search time, fallback reasons, rejected choices and world totals. The report pools raw latencies before computing p50/p95/p99, includes win rate with Wilson and team-bootstrap 95% intervals, and reports void games separately. A single-team bootstrap interval is uninformative even if numerically narrow; use multiple held-out teams.

The game scheduler snapshots existing battle tags before dispatch. It then requires exactly one new battle per player, the terminal `.finished` state, and each agent’s summary for that same tag before writing a result or scheduling another game. Challenge-coroutine completion alone is insufficient: poke-env can return early when a reused player changes challenge direction. Overlapping new battles, an unfinished preceding game, mismatched tags, or a bounded game timeout fail the run instead of producing a stale or premature win/void result. New rows include `completion_verified: true`.

Decision records have unique `decision_id` values. The following `observation` record carries that ID and the first opponent move or voluntary switch observed afterward. Switches after a faint or forced by our move, and switches following a pivot move, are kept as `followup_actions`. If the opponent never acts at root, the root action is `null` with status `unknown`; a replacement after fainting is therefore not scored as an invented reply. These records retain the preceding opponent root visit distribution for a later, separately specified scoring experiment. Rejected choices invalidate the agent's pending belief replay so an unexecuted action cannot generate spurious damage/speed evidence.

To measure native action agreement, save a position as JSON with `request` and `battle` keys, then run:

```sh
uv run python -m bot.eval --runs runs/mcts-agreement agreement position.json --worlds 1 --search-ms 150 --engine-threads 1 --repeats 10
```

The sampler seed and beliefs reset for each repetition. The report measures the fraction of ordered pairs of runs choosing the same action and keeps the traces. Exact visit counts and choices are not asserted deterministic. The same command can benchmark two and four native threads after the one-thread integration gate.

Keep `one_ply` as default unless the held-out comparisons support a change while legality, deadline and reliability metrics remain acceptable. An inconclusive result retains both backends and reports its intervals. No main strength result or prediction-model improvement is claimed by adding this harness.
