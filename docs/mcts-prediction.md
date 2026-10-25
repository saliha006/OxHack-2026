# Separate prediction workstream

`prediction/` trains and evaluates an observed-state win-probability model, scores belief revelations and scores the opponent's root visit distribution. Search never imports or calls this model. A learned search evaluator or reranker requires its own later experiment.

## Measured public replay baseline

A bounded acquisition used the first two pages of the public [Gen 9 OU replay search](https://replay.pokemonshowdown.com/search.json?format=gen9ou), capped at 100 unique IDs. It accepted 96 rated games with six preview species per side, at least six turns and a binary winner; it rejected three unrated games and one shorter game. No game was selected using its winner or model performance. Public ladder replays do not prove that both players are human, so their source is `public_ladder`, with `human_status: unverified`.

The 2,517 observed start-of-turn states span 2026-10-25 01:45:23–03:42:01 UTC. The chronological battle split is 67 train games/1,837 turns, 14 validation games/279 turns, and 15 test games/401 turns. No battle crosses splits. The model uses fixed hyperparameters and train-only feature scaling; its Platt calibration uses only validation labels.

| Model | Test log loss | Test Brier |
|---|---:|---:|
| Constant 0.5 | 0.6931 | 0.2500 |
| Training outcome frequency | 0.6931 | 0.2500 |
| HP/alive baseline | **0.6348** | **0.2215** |
| Logistic | 0.7009 | 0.2406 |
| Validation-calibrated logistic | 0.6600 | 0.2338 |

The calibrated model **does not beat the HP baseline** on this test. It remains an experimental prediction output. Test games sharing any player or preview roster with train or validation are also reported separately: only five games/128 turns remain unseen. On that small subset, HP scores 0.6192/0.2137, raw logistic 0.5174/0.1751, and calibrated logistic 0.6369/0.2224. These are descriptive small-sample results, not evidence for replacing the baseline. Turns from the same game are correlated, and this narrow two-hour sample cannot establish performance across time or player populations.

Exact hidden teams are unavailable in spectator replays. The repeated-team control therefore uses a preview-species roster proxy, explicitly labeled in the manifest. It excludes shared rosters conservatively and does not claim hidden-set disjointness. Nine of the 15 test games share a player with earlier splits; nine share a roster. The strict unseen subset excludes either kind of overlap, including overlap with calibration data.

Committed artifacts in `evaluation/prediction-public-20261025/` include the model, all scores and reliability bins, calibration SVGs, and the frozen selection/source manifest with raw and stable log hashes. Raw replay JSON and the original search responses remain in ignored `runs/prediction-public/raw/`. The acquired turn JSONL SHA-256 is `cc5d31031dadf0ae5974772e3fc98e22b13532b685e309cc12f2b099a375f6ee`.

## Reproduce training and serve predictions

```sh
uv sync --group prediction
uv run --group prediction python -m prediction fetch-replays --output runs/prediction-repeat --manifest evaluation/prediction-public-20261025/source-manifest.json
uv run --group prediction python -m prediction train --turns runs/prediction-repeat/turns.jsonl --validation-start 2026-10-25T03:10:21+00:00 --test-start 2026-10-25T03:25:03+00:00 --source public_ladder --output runs/prediction-repeat/model
uv run python -m prediction predict --model evaluation/prediction-public-20261025/model.json --state position.json
```

The frozen manifest reuses the selected IDs and verifies each stable log hash. API view counts may change, so full response hashes document acquisition while log hashes establish reproducible battle content. A new `fetch-replays` call without `--manifest` samples the latest pages and creates a new experiment.

`position.json` can be a `BattleState`, a decision record with a `state`, or a saved search fixture with a `battle`. Serving uses the same versioned `featurize(BattleState)` function as fitting. It returns calibrated and raw probabilities and the training source. It needs no database access or NumPy; NumPy and Matplotlib are offline training dependencies.

For other datasets, provide JSONL rows with `battle_id`, `started_at`, `winner` (`p1`/`p2`) and `state` (a dict or serialized JSON). The Tiger `turns` contract has these columns. Player IDs come from `p1`/`p2` metadata or public state player names. Supply canonical complete `p1_team`/`p2_team` identities to audit exact repeated teams; otherwise the report explicitly uses roster proxies. The `--source` label must agree with source fields already in the data.

Features read only the observed state: HP/alive/status differences, boosts, hazards, screens, resource use, revealed-move counts, supported volatiles and delayed effects, turn and Trick Room. Player names, ratings, requests, future actions, winner and post-turn columns are excluded. Training preprocessing fits only train rows, and calibration receives only validation rows. Tests alter test labels and confirm that weights, preprocessing and calibration do not change.

For preserved bot-game artifacts:

```sh
uv run python -m prediction export-bot --runs runs/mcts-held-out --output runs/bot-turns.jsonl --both-perspectives
```

This uses actual raw protocol timestamps and winner mappings, full submitted team hashes from the evaluation manifest, and only observed move-decision states. Both perspectives stay in the same battle split. Missing timestamps, missing separate artifact paths and incomplete/truncated traces are rejected. A tiny bot-game train/validation/test run can test plumbing, but it is separate evidence from public replay results.

## Belief quality

```sh
uv run python -m prediction score-bot-beliefs --runs runs/mcts-held-out --priors data/set_candidates.json --output runs/belief-scores
```

This compares the exact posterior recorded **before** a new revelation against the original OU prior and a persistent hard-filter-only belief. The hard-filter baseline receives the same sequence of observed snapshots and retains hard item inferences, while disabling damage/speed replay. The target is read only from the following snapshot or final raw log, after the prediction snapshot has been saved. Decisions lacking exact posterior records are counted and excluded; sampled worlds cannot reconstruct an exact posterior.

Items, abilities and Tera types are categorical marginals. Next-new-move scores explicitly assume uniform choice among each candidate set's still-unrevealed moves, then marginalize candidate weights. That policy assumption is part of the experiment; it is not an inferred player move policy. Only the first new move in an observation interval is scored. Consumed/removed item blanks and later changes to an already revealed item are excluded from initial-item prediction.

`score-beliefs records.jsonl` also accepts independently generated pre-reveal records with `source`, `kind`, `revealed`, `known_moves`, and candidate lists named `prior`, `hard_filter`, `updated`. Candidate records contain `weight`, `moves`, `item`, `ability`, `tera_type`, and either `spread: {nature, evs}` or flat `nature`/`evs`. The scorer reserves an OTHER category and adds `alpha=1e-6` to every category before normalization. Bot, public-ladder, human-labeled and synthetic evidence are reported separately. Full-set coverage is returned only for records carrying complete `ground_truth_set`; the bot exporter currently supplies none and makes no coverage claim.

## Opponent actions

```sh
uv run python -m prediction score-actions runs/mcts-held-out/players/ACCOUNT/BATTLE.jsonl --source bot --output runs/action-scores.json
```

This joins `observation` rows to the preceding `decision_id`, translates observed moves/Tera/switches into native choice names and compares opponent visit support against uniform over the recorded native root options. Zero-visit options remain in that option set. Both predictions reserve an OTHER category; additive `alpha=1e-6` smoothing makes unsupported observations finite and their count is reported. Unknown root replies, including faint-before-acting and forced replacements, are excluded, as are decisions with no opponent prediction. Pivot follow-up switches do not replace the observed root move.

Visit support remains a search diagnostic rather than calibrated action probabilities. Public or human replay action scoring requires separately generated search predictions for those observed positions and must carry the corresponding source label; bot-game scores do not establish human action-prediction quality.

## Measured bot-game diagnostics

The preserved two-game `mcts-final-gate` produced 65 next-revelation examples across four agent perspectives, with no missing posterior snapshots and no original-prior recovery. Next-revelation log loss was 1.5131 for the original prior, 1.5022 for hard filtering, and 1.5592 for updated beliefs. Soft inference did not improve this small bot-game sample. No full-set ground truth was supplied, so coverage is not reported.

Across the MCTS side's two traces, 124 observed root replies scored 2.0970 visit-share log loss versus 2.5242 for uniform. Fifteen unknown replies and two team-preview decisions were excluded; five observed actions fell outside the recorded native option set and used the reserved OTHER probability. These are bot-only integration diagnostics with the stated smoothing, not calibrated action predictions or evidence about human players. The complete counters and engine/source provenance are saved in `evaluation/prediction-bot-gate-20261025.json`.

The bot export also produced 258 supervised rows with both perspectives, grouped into the same two battles. Two groups are insufficient for separate train/validation/test partitions; no bot-trained model is claimed from this export. The measured win-probability model above instead uses the independent bounded public replay dataset.
