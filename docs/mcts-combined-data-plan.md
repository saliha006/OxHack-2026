# Combining OU set templates, usage priors and partially observed replays

Status: source audit and proposed integration, 25 October 2026. No runtime bot behavior changed by this audit. This supplements the original MCTS improvement plan and its handoff; it does not replace their requirements, evaluation contract or frozen baseline. Independent MCTS work in the other chat can continue.

## What was actually checked

A read-only Tiger audit sampled the first 20 turn-1 battle IDs in database order and joined `battle_logs` on both ID and timestamp. All 20 had logs. This is descriptive, not a representative coverage estimate. Aggregate results are in ignored `runs/data-source-audit/tiger-sample-audit.json`.

`turns` has start-of-turn JSON states with species, HP, revealed moves, item, ability and Tera fields, plus boosts, hazards, status, field effects and action/outcome targets. Item/ability/Tera values are often unknown. At turn 1 in this sample, 7 of 240 Pokémon had an ability recorded and 2 an item; absence means unknown, not no ability/item. None of these fields is a ground-truth EV/IV spread.

Raw logs contain structured protocol events, not only natural-language chat: moves, damage/healing with source tags, `-item`, `-enditem`, `-ability`, `-terastallize`, status, hazards, weather and other effects. Observed counts in these 20 logs included 628 move events, 13 item events, 65 end-item events, 38 ability events and 28 Tera events. These are event counts, not unique owners or estimated population frequencies. Reparse sequentially using the current shared parser when a feature needs events not retained in the old turns snapshot; do not assume parsing is automatically complete/correct.

The live Showdown file https://play.pokemonshowdown.com/data/sets/gen9ou.json was fetched and inspected. Snapshot stored locally under ignored `runs/data-source-audit/gen9ou.json`:

- `dex`: 108 species, 203 named role templates. Each has moves, item, ability, nature, EVs and Tera type; 48 specify IV overrides.
- `stats`: 75 species with one displayed usage set each, with moves/item/ability/nature/EVs; these entries lack a Tera field. There are 65 species shared with `dex`.
- Neither section supplies a probability for each complete template. Do not mistake the name `stats` for counts or treat one displayed set as the only legal set. Do not assign duplicated entries extra mass.
- The current `pkmn/smogon` source also exposes alternative move slots/items/natures/Tera choices; it is a separate snapshot, not asserted identical to the user's Showdown endpoint. If imported later, preserve alternatives rather than flattening unrelated variants indiscriminately.

Existing `data/set_candidates.json` contains 321 species/form aliases; its source metadata is September 2026, cutoff 1825, 574,541 battles. The current builder combines marginal move/item/ability/spread/Tera usage into at most 30 candidate records per species. That gives broad coverage and weights, but does not establish that the combined fields occurred together in a real set.

## Give each source a distinct job

| Source | Use | Do not claim |
|---|---|---|
| Showdown `dex` templates | Coherent candidate moves + item + ability + spread + Tera for each role | Real full-team exports, exhaustive coverage or true role frequencies |
| Showdown `stats` templates | Additional plausible per-species candidates where useful | Full joint distributions or complete Tera knowledge |
| Existing usage marginals | Initial frequency clues and a broad fallback | Independently combined fields are jointly observed sets |
| Tiger `battles` rosters | All six species, roster retrieval, teammate context | Complete hidden moves/items/EVs |
| Tiger `turns` | Time-aligned public states, actions and outcomes | Private requests/full set labels |
| Tiger `battle_logs` | Richer observed evidence with reveal timing | Unused moves, unactivated items or exact spreads are known |

Turns, logs and any HolidayOugi replay exports for the same battle are different views of one observation. Join by battle identity/timestamp and deduplicate; concatenating them as independent games double-counts evidence.

## Proposed implementation order

### 1. Import and validate coherent set templates

Build a separate offline importer and versioned set-bank artifact. Keep species/form normalization, role label, source URL/date/hash, template ID and component provenance. Validate against the pinned Gen9 OU engine/rules rather than assuming every external record is currently usable. Explicitly handle missing values and source variants.

Preserve nature/EV relationships and IV overrides such as zero Attack; the runtime `PokemonSet` supports IVs, but the current candidate-file contract only expresses nature/EVs. Extend the contract/import path intentionally rather than silently losing IV overrides. Missing Tera in the `stats` section remains unknown and is completed by a declared fallback distribution when a simulation needs a concrete value. Defaulted IVs in a template are source conventions, not observations about the real opponent.

Combine curated templates with the existing broad usage prior behind a flag. Deduplicate identical complete candidates and avoid counting shared source evidence twice. Pick/tune a mixture on development data, retaining a nonzero fallback. Curated-only, existing-only and mixture are separate ablations.

### 2. Extract observed evidence, not fabricated full labels

On a bounded local development slice, parse logs into `(battle, side, Pokémon identity, turn/event offset, field, value, provenance)` records. Keep roster identity stable across nicknames/form changes. Record direct reveals separately from inferences. Preserve original held item, consumed/lost/transferred item and current item as different facts where needed. Account for copied/called moves, Transform and ability changes before treating an event as a native-set constraint.

A move not used is unknown. An item not activated is unknown. Lack of Leftovers recovery is not automatically a hard exclusion. Percentage HP and damage/order observations may bound some spreads under assumptions; they do not uniquely reveal exact EVs/IVs/nature. Keep them as soft evidence, if validated.

Keep final revealed information for scoring later revelations, but supply only the history prefix available at prediction time to the bot. Outcome/action columns are not pre-turn features. First audit extraction coverage/errors on hand-checked games before a bulk export. The previous full Tiger download remains stopped; any new large job should be a deliberately scoped integration task, not an accidental restart of the old training run.

### 3. Run a per-Pokémon posterior first

At preview, maintain several compatible templates for each of the six known species. Begin with source/usage weights; update when moves/items/abilities/Tera become observable. A confirmed native move eliminates templates that cannot contain it, except where the event itself reflects a called/copied move. A known held item constrains the correct item state/time, not necessarily the original item after Trick.

Process each observation once, or recompute from a fixed prior plus the unique history; do not repeatedly multiply the same revelation every turn. Prefer broad compatible fallback when the template bank misses the actual set. Report support/recovery and preserve confirmed facts through recovery. Do not output a single guessed exact spread as certain.

Our current bot already has per-species candidates, revelation filtering, damage/speed inference and whole-team world sampling. The main new piece is the coherent template source; reuse the existing belief interface and the other chat's reliability fixes instead of adding a competing belief engine.

### 4. Learn roster-conditioned weights conservatively

Fit initial teammate-conditioned adjustments from training rosters and partial revelations. Frequent full-roster matches can help; back off to five/four-species overlap, teammate evidence and finally species priors when support is sparse. Reuse Nate's A6 if available.

These are incomplete labels. Match compatible templates or fit a latent-template model using partial evidence, with smoothing and an explicit unmatched component; do not mark a compatible template or inferred EV spread as ground truth. Move and item reveals are selection-biased: popular moves are used more, some items reveal reliably, and others rarely reveal. Naive counts of revealed items are not true held-item frequencies. Initially use these signals as weak, tested reweighting and report sensitivity to missingness.

Do not hard-code “one defensive Pokémon makes a second defensive Pokémon unlikely.” Team roles can be complementary or redundant, and one species can run multiple roles. Estimate any role relationship from evidence, retain uncertainty, and compare roster-conditioned predictions against species-only predictions on unseen rosters. Species co-occurrence alone does not identify the six actual sets.

### 5. Add joint team hypotheses only after the marginal model works

Jointly sample candidate roles/sets for all six Pokémon to represent supported correlations. Partial replay evidence can weakly constrain those hypotheses; it cannot recover a database of exact complete teams without additional information. Complete public team exports remain useful if they become available. Never label independently sampled sets as a historically observed team.

Each MCTS world receives one plausible complete hypothesis. Concrete completion of unknown fields is a sampled assumption and should be traced. No database calls or large scans during `Agent.choose`. Preserve equal per-sampled-world mass and existing deadline supervision; do not multiply a sampled world's prior weight a second time.

## Evaluate before promoting

1. Extraction correctness: manually check reveal owner/timing, native vs called move, and lost/transferred items. Report missingness/coverage; no exact-spread accuracy claims without known spreads.
2. Set prediction: on whole held-out battles, predict the next *new* revealed move/item/ability/Tera using only earlier events. Compare current prior/belief, curated-only, mixture and roster conditioning separately. Report coverage, smoothed loss, posterior recovery and a clearly stated model for which move is used/revealed. Repeated moves are not repeated independent set revelations.
3. Team conditioning: separate familiar-roster and unseen-player/roster subsets. Train/tune only on earlier games; deduplicate across raw logs/turns/source exports. Do not use final test logs to build role weights.
4. Source-time caveat: a current curated snapshot or September 2026 usage prior was not available during many historical 2025/early-2026 games. Such experiments are retrospective; strict forward-time claims need source snapshots available before the evaluated games. Record this limitation rather than hiding it behind a chronological battle split.
5. Battle strength: compare each enabled change against frozen current MCTS and the accepted incumbent at matched compute, using the full handoff's game schedule, reliability metrics and documentation rules. Better set prediction is useful evidence, not proof of higher win rate.

## Immediate recommendation

Proceed with the coherent set importer and evidence-extraction audit; complete real-world set labels are not a prerequisite. First milestone: curated + broad-prior candidates updated from actual revelations, with extraction/next-reveal tests and isolated battle comparisons. Add learned roster correlations afterward. Keep the data-independent MCTS improvements in the other chat isolated from this prior experiment, with an explicit candidate/engine/source hash for every comparison.

References: [Showdown sets](https://play.pokemonshowdown.com/data/sets/gen9ou.json), [Showdown protocol](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md), `contracts/turns.md`, `data/pipeline/build_turns.py`, `data/pipeline/build_set_candidates.py`, `decision/belief.py`, `decision/sets.py`, and `docs/mcts-improvement-handoff.md` (including the original plan).
