# Coherent sets and public replay evidence

This branch adds an optional coherent-template prior and an offline replay-reveal extractor. It keeps `data/set_candidates.json` as the normal default. Read [measured results](coherent-sets-results.md) before deciding whether to enable the mixture.

## Build the prior

The committed source snapshot and generated bank are versioned. No network/database access occurs during a battle.

```sh
uv sync --group prediction --group tiger
uv run python -m data.pipeline.import_curated_sets \
  --source data/sources/gen9ou-20261025.json \
  --priors data/set_candidates.json \
  --simulator /path/to/pokemon-showdown \
  --fraction 0.5 --output runs/curated-rebuild
```

Output `bank.json` keeps role/source IDs, concrete legal variants, IV overrides, unknown fields and completion assumptions. `priors.json` mixes curated and broad usage mass. `manifest.json` records source/prior/validator hashes, component attribution and rejected records. Use a fresh output directory; existing experiments are not overwritten. `data/curated-v1/` contains the initial built experiment for direct inspection/use.

Curated roles receive equal mass, with equal mass across alternatives within each distinct role distribution. Duplicate identical role distributions are coalesced. These are explicit heuristics, not real complete-set usage probabilities. Dex roles take precedence over the displayed `stats` set when both exist for a species. Stats-only entries missing Tera are completed from existing usage options and marked as assumptions. Missing fallback prevents import rather than inventing a known Tera value. Only supported species/aliases change; the existing `usage` block remains the recovery fallback. `--fraction 0` reproduces the input prior exactly, including order and metadata; a fraction of one is rejected to preserve broad support.

To try the versioned mixture in a live smoke or normal demo, supply the existing prior-path option:

```sh
uv run python -m bot.smoke --backend mcts --worlds 8 --search-ms 150 \
  --engine-threads 1 --priors data/curated-v1/priors.json \
  --games 2 --runs runs/coherent-live-smoke
```

This requires the usual local Showdown server setup. Existing belief updates consume these candidate sets; no second online belief engine was introduced. The only decision-code compatibility change is reading optional six-stat IV overrides; old candidate files still use all-31 IVs. Sampled IVs/spreads are hypotheses, not facts about an opponent.

## Extract observed evidence

Inputs are JSONL battle records with `battle_id`, `started_at`, `split` and `log`. Use public protocol logs; source games must stay distinct from training/confirmation teams. Keep private files outside Git.

```sh
uv run python -m data.pipeline.reveal_evidence \
  --logs runs/reveals/tiger-200.jsonl --output runs/reveals/evidence-new.jsonl
```

The extractor emits field/value, side/slot/species, turn and event offset, evidence scope and eligibility, exclusions and log hash. It records each distinct observation once. It separates lost/consumed item identity from the now-empty current item slot. Called moves are excluded by the shared parser; transferred/restored items, changed/copied abilities and transformed identities are conservatively ineligible for original-set labels. Sides with possible Illusion are excluded conservatively because earlier public identity may be disguised. This loses coverage deliberately; no claim of exhaustive mechanic handling is made.

No unused move, unactivated item, exact EV/IV/nature or unknown Tera becomes a fabricated ground-truth label. This tool exports evidence; it does not train new role weights or silently change the live parser/decision policy.

## Optional bounded Tiger sample

The full turns download remains stopped. This reader requests only selected logs plus metadata. Credentials remain in a private ignored env file; they are never shell-sourced or printed. SQL sessions are TLS/read-only and joins use ID plus timestamp.

```sh
uv run --group tiger python -m data.pipeline.sample_replay_logs \
  --env-file /path/to/private.env --per-split 100 --seed coherent-v1 \
  --output runs/reveals/new-sample.jsonl
```

The sample reader refuses more than 1,000 games per split. Manifest selection hashes document what was read. Raw usernames/logs stay ignored locally; the two views of a battle are never counted as separate games. Read-only connectivity reuses `data/tiger.py`; its full-export subcommand is not needed for this experiment.

## Score predictions

```sh
uv run python -m evaluation.score_reveal_evidence \
  --logs runs/reveals/tiger-200.jsonl \
  --baseline data/set_candidates.json --mixture data/curated-v1/priors.json \
  --output runs/reveals/new-scores.json
```

For each first eligible revelation, the scorer uses the public state strictly before that event. It compares raw priors and revelation-only filtering reconstructed from that prefix. It does not replay persistent damage/speed inference or retained historical item evidence. Move likelihood assumes a uniform choice among a candidate's not-yet-seen moves. Therefore this is a set-support diagnostic, not a calibrated action policy or full-set accuracy benchmark.

The 200-game source sample is fixed; its test half contains 100 games. The mixture fraction was fixed before these results, with no score-driven tuning. Current curated/usage sources postdate some replay games, so the study is retrospective. A chronological battle split alone does not establish forward-time performance. Future trained weights require separate development/validation/test boundaries, deduplication and player/roster overlap controls.

## Compare battle behavior

The isolated runner now accepts `--b-priors`: both prior paths/hashes are frozen independently. The candidate is based on `a8613b9`; comparison B is an immutable complete snapshot of that commit. Both use eight whole-team worlds ×150 ms, one native thread, three-second ceiling, reliable beliefs and type-only preview. Other-chat lead/allocation/guard/mixing experiments are not mixed into these results.

`evaluation/coherent-sets/*manifest.json` freezes actual source, engine, prior and simulator identities, team hashes, seeds, settings and stopping rules. `screening-v2-manifest.json` uses four-game blocks balancing sides and bot/team assignments, 60 games and ten synthetic rosters. Known component sets are reused, so these teams are not an independent external set holdout. Files under `runs/coherent-evaluation/` preserve raw traces, requests and logs; compact summaries are published beside the manifest.

The runner validates source/engine/prior/simulator hashes before resuming. Paths in a frozen local manifest are machine-specific. On another machine, rebuild the immutable baseline and freeze a new manifest with its local paths; do not rewrite a historical manifest and call it the same run. Keep failed/censored games and resource measurements in the report. Promote based on the complete evaluation contract, not on a few wins or prediction loss alone.

## Coexistence and integration

Implementation checkout: `OxHack-coherent-sets`, branch `Kenar-coherent-sets`. The original `OxHack-2026` checkout remains owned by the active data-independent MCTS chat. No changes were made there and no cross-chat message was sent. Merge/cherry-pick only after reviewing its current accepted changes; reconcile the optional IV line and evaluator `b_priors` support if the same files evolved. Re-run correctness and compute-matched comparisons on the combined accepted engine before attributing an interaction gain. Separate effects of priors and policy changes remain explicit.
