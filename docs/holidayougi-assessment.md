# HolidayOugi replay dataset for MCTS improvements

Yes: this is a useful source for improving what MCTS assumes about its opponent, and for evaluating observed-state predictions. Replay data does not directly train stock poke-engine MCTS or establish whether an unplayed move would have won.

## Verified source, 25 October 2026

- [Dataset card](https://huggingface.co/datasets/HolidayOugi/pokemon-showdown-replays/blob/main/README.md), revision `15a0a455dbcb7f5c07c2dd670f9252f275d4ddc8`, last updated 5 October 2026.
- Author reports 2,506,142 Gen9 OU replays, within a much larger collection spanning generations/formats. The card notes some invalid replays.
- Repository API currently lists 13 `[Gen 9] OU_part*.parquet` files, approximately 6.06 GB compressed altogether. The viewer's combined `train` split is not a scientific train/test split for this project.
- Rows expose public replay log, replay ID, format, player names, upload time, views and optional rating. Protocol logs contain moves actually used, revealed items/abilities/Tera, visible HP and the result. They do not guarantee complete hidden sets, EVs/natures, exact opposing HP/PP or the actions that were never observed.

## Reuse what the project already has

`data/pipeline/clean_battles.py` already targets `data/raw/holidayougi`, filters `gen9ou`, deduplicates replay IDs and extracts per-player ratings from logs. `data/pipeline/build_turns.py` uses the same public-state parser as the bot. The team's existing progress log reports all 2,506,142 Gen9 OU games cleaned/loaded into Tiger, with 489,840 turns extracted from 20,000 games. Those are the team's recorded results, not a new live database verification in this assessment; no credentials or database access were used here.

Start with the existing turn export described in `contracts/turns.md`, rather than downloading the whole multi-format dataset again. That contract already warns about repeated players/teams between splits and identifies an unseen subset. Our separate `prediction/` tools accept observed-state JSONL and chronological boundaries.

## Useful experiments

1. **Hidden-set inference first.** Score the original OU prior and current belief filtering against the next revealed move/item/ability/Tera on held-out recent OU games. Our bot-game pilot showed belief filtering worse than its original prior, so diagnose exclusions/recoveries before adding a more elaborate model. Learn move/set co-occurrences only with missing-field masks: a move never used in a replay is not proved absent from the set. Better guesses can then improve the worlds searched by MCTS.
2. **Opponent actions.** Learn or score moves versus switching from information available before the turn. This predicts observed player behavior, not the optimal move. Keep this experiment separate from any new weighting inside search, and compare against uniform and current visit-share predictions.
3. **Win probability.** Train the separate observed-state model on a substantially larger sample, keeping the same training/serving featurizer. Compare held-out log loss, Brier and calibration with constant and HP-only baselines. Stock native MCTS does not automatically consume a trained Python model.

Use recent Gen9 OU games from a compatible rules/metagame period, preserve rating strata, and reserve whole later battles for validation/test. Report repeated-player and team/roster overlap. Keep future revelations, eventual winner and post-turn effects out of input features. Publicly uploaded replays are a selected sample, not every ladder game.

Finally, test any resulting search change in fresh actual bot games at recorded compute budgets. Replaying a recorded action cannot reveal the result of a different action. This assessment recommends an experiment sequence; it does not claim new trained models or a new large-corpus run.

## Default decision

The user selected MCTS as the default development backend on 25 October 2026. `Agent`, demo and smoke defaults are now MCTS with eight worlds, 150 ms per world, one engine thread and a three-second decision budget. Legacy one-ply evaluation arms are pinned explicitly so historical comparisons remain meaningful. This is a user-directed product choice, not a new statistically established strength finding.
