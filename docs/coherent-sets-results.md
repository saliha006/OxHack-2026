# Coherent sets and replay revelations: change and results log

Status: importer/extractor implemented and the first retrospective prediction comparison is complete; battle evaluation is in progress, 25 October 2026. This log distinguishes completed checks from planned experiments. There is no playing-strength result for the new prior mixture yet.

The goal is to give MCTS more plausible opponent sets. Showdown supplies coherent role templates; our existing usage prior supplies broader coverage; replay logs supply facts revealed during battles. The bot must keep several possibilities and update them as evidence appears, rather than pretending that an unrevealed item or spread is known.

## Isolation from the other MCTS chat

This work is on `Kenar-coherent-sets` in the separate `OxHack-coherent-sets` checkout. The other chat continues the data-independent handoff on `Kenar-mcts`; its working files and experiments are not changed here.

The frozen comparison anchor is **`a8613b9`**, the committed MCTS revision observed when this branch was created. It includes the state/belief work already committed by the other chat, including the fainted-Tera memory correction. New changes made by that chat after this anchor are outside this experiment. The historical `2c02fc8` baseline remains part of the older handoff; it is not silently relabelled as the current anchor.

Both arms should use the same engine, MCTS settings, sampling policy, teams and game schedule. The intended treatment is the set-prior source. Any runtime compatibility changes, such as preserving IV overrides, must be recorded explicitly rather than hidden inside the data comparison. Source, prior and engine hashes in the experiment artifacts are the authority for what actually ran.

## What each source contributes

| Source | Purpose | Important limit |
|---|---|---|
| Showdown `gen9ou.json` templates | Keep moves, item, ability, nature, spread and Tera choices together within a plausible role | Templates are neither complete historical teams nor measured role probabilities |
| Existing `data/set_candidates.json` | Supply broad usage-based candidates, weighting information and fallback coverage | Combining separate usage marginals can produce combinations that were never observed together |
| Tiger replay logs / turn states | Supply observed moves and item, ability or Tera revelations with their timing | Unused moves, unactivated items and exact EVs/IVs remain unknown |

The prior source audit inspected 203 named `dex` roles across 108 species in the Showdown endpoint. Its `stats` section supplies an additional displayed usage set for 75 species, with substantial overlap and no Tera field in those entries. These are source-content counts, not importer acceptance counts. The importer must report accepted/rejected records separately.

The Tiger audit inspected 20 games, all with matching raw logs. It confirmed useful item/ability/Tera events exist, but it was a small, ordered descriptive sample. It does not establish population coverage. The earlier full-table download remains stopped; a bounded development export, if used for this task, must be recorded separately.

## Change 1: coherent template importer and prior mixture

**Why:** our existing candidate builder constructs full records from separate move/item/ability/spread/Tera frequencies. A named role template preserves more of the relationship between those fields—for example, a particular item and spread accompanying a particular four-move role.

**Implemented behavior:** `data/pipeline/import_curated_sets.py` imports template records, retains source/provenance information and IV overrides, validates concrete variants with `data/pipeline/validate_curated.cjs`, deduplicates final complete candidates, and builds an explicit prior mixture. Unknown Tera fields in supplemental usage templates are completed from declared usage choices and remain marked as assumptions. No template is treated as exhaustive or as the real opponent's known set.

**Completed checks:** the initial bank contains **556 validated concrete variants**. Two supplemental usage templates, Infernape and Chandelure, were rejected because there was no Tera fallback for their incomplete records; the pinned Showdown validation reported no invalid variants among the remaining records. The generated mixture augments **160 species/form aliases**. Where curated support exists, it assigns **50% curated / 50% broad-prior mass**; unsupported species retain the old prior. `dex` roles take precedence over overlapping displayed `stats` sets.

Equal role mass and equal alternative mass within a role are declared heuristics, not learned frequencies. The 50/50 value is an initial experimental setting, not a tuned optimum. The existing live default prior file is unchanged.

The candidate contract now permits optional IVs, and `decision/belief.py` preserves supplied IV overrides when loading a candidate. A record without IVs retains the historical all-31 default. Eleven focused importer/extractor/contract tests passed, including zero-IV serving and absent-IV compatibility checks. The combined decision/bot suite passed **468 tests** in `runs/coherent-evaluation/tests.txt`; that run predates the latest comparison-harness edit, so it does not validate that subsequent edit.

**Artifacts:** `runs/curated-v1/bank.json`, `runs/curated-v1/priors.json` and `runs/curated-v1/manifest.json`. The source is `data/sources/gen9ou-20261025.json`, SHA-256 `898612165656b5969ef7fbecd764faf8a623039a27eaa2f912c16881b3fba087`; broad-prior SHA-256 is `47b31bf7282d6578ed44d7b28f9a63e9284eddc72882856de426f7c1bfc8c7f3`. The validator used Showdown commit `c0845f33d381402dfcb18ce324c20a94f18af075`.

**Review correction:** identical role distributions under different names no longer gain extra curated mass. The new A/A-copy/B regression verifies that duplicate role A cannot outvote distinct role B. A zero-curated-fraction mixture now returns an exact deep copy of the original prior. Ten focused importer/extractor tests passed after these corrections, and the already generated 50/50 mixture was confirmed unchanged.

**Did it help?** Not measured yet. Better-looking templates alone do not establish better predictions or a stronger bot.

## Change 2: chronological reveal extractor

**Why:** raw replay logs contain more evidence than move names and HP. We need an explicit record of what was observed and when so evaluation cannot use future information accidentally.

**Implemented behavior:** `data/pipeline/reveal_evidence.py` extracts battle/side/Pokémon identity, event position, field, value and provenance from logs using the shared parser. It preserves a consumed/lost item identity separately from the now-empty current item and excludes possible transferred items, changed abilities and transformed identities from native-set scoring. It deduplicates repeated revelations and keeps unobserved fields unknown. Called/copied move handling follows the parser; Illusion-capable sides are excluded conservatively from native-set scoring, trading coverage for fewer incorrect labels.

**Completed checks:** focused fixtures exercise repeat observations, state strictly before a reveal, consumed items/current-empty state, Trick, called moves, transformed identities and possible Illusion. The extraction of the 200-game sample finished: **4,025 move records, 653 ability records, 995 item records, 496 current-item records and 272 Tera records**. Of the emitted records, **5,648** were marked eligible native-set evidence. These are extracted records, not independent complete-set labels; the scorer also excludes already-public targets and conservative protocol cases.

A new bounded read-only sample was exported by `data/pipeline/sample_replay_logs.py`: **200 complete games**, 100 from each frozen Tiger source split, selected by hashed battle identity/time with seed `coherent-v1`. All 200 selected logs matched. This is a separate bounded task, not a restart of the full turns-table download. Local artifacts are `runs/reveals/tiger-200.jsonl` and `runs/reveals/tiger-200.manifest.json`; input SHA-256 `23ff7b44ad357054d7c4fd655ef2583302ad783893a5d3d4da99847e82ff7ac9`. The evidence export is `runs/reveals/evidence-200.jsonl`. This 200-game extraction is the source of the record counts above.

**Remaining verification:** inspect real extracted examples and coverage, and retain focused counterexamples for protocol edge cases. Conservative exclusions mean absence from the scored evidence is not proof that a field never became knowable.

**Did it help?** The extractor provides usable time-aligned targets and passes the initial fixtures. The first prediction comparison below favors the mixture over the old prior, but filtering itself still has a problem: both arms score worse after public-fact filtering than before it. Extraction correctness and a prediction-score improvement are not win-rate results.

## Comparison plan and result status

The experiment should keep three questions separate:

1. **Correctness:** does the importer preserve the template and does the extractor preserve actual observed evidence?
2. **Prediction:** do curated-plus-usage candidates predict later revelations better than existing priors? Compare existing-only, curated-only and the mixture where supported, with declared smoothing, fallback and a stated next-revelation scoring model.
3. **Playing strength:** does the resulting MCTS win more games against the frozen current MCTS at matched requested compute, without legality, fallback or latency regressions?

The retrospective scorer, `evaluation/score_reveal_evidence.py`, reconstructs candidate beliefs from the public state strictly before each new event. This tests prefix-state revelation filtering, not the full persistent runtime damage/speed or consumed-item-history pipeline. It assumes a uniform choice among a candidate's not-yet-observed moves when scoring a new move; scores therefore mix set quality with move/reveal selection. Use whole-game development/scoring separation, and do not fit the mixture on confirmation outcomes. An unseen move or hidden spread is not a false label. A current curated snapshot evaluated on older games gives retrospective evidence; strict forward-time claims require appropriately dated source snapshots.

## First retrospective prediction result

Artifact: [`evaluation/coherent-sets/reveal-diagnostic-v1.json`](../evaluation/coherent-sets/reveal-diagnostic-v1.json). The frozen Tiger source test split contributes **100 games and 2,821 eligible new revelations**. No mixture tuning was performed on these scores. Lower log loss is better; coverage means positive probability before the declared floor, not exact full-set accuracy.

| Prediction variant | Test mean log loss | Target support coverage |
|---|---:|---:|
| Existing prior, before public-fact filtering | 4.0469 | 78.8% |
| 50/50 mixture, before public-fact filtering | **3.7062** | **82.0%** |
| Existing prior, after public-fact filtering | 4.5569 | 73.8% |
| 50/50 mixture, after public-fact filtering | **4.2334** | **76.6%** |

For the two filtered arms, the mixture-minus-baseline log-loss difference is **−0.3236**, with a paired whole-battle bootstrap 95% interval **[−0.4218, −0.2321]** (5,000 resamples, seed `2026102511`). This interval does not control repeated-player or repeated-roster dependence. It describes this bounded retrospective sample and scoring model; it is not a deployment-strength estimate.

The mixture improves filtered move loss from **4.9784 to 4.5982**, item loss from **4.5103 to 4.2028**, and Tera loss from **6.1402 to 5.8935**. Ability loss changes slightly in the wrong direction, **0.8705 to 0.8828**. Do not describe the result as an improvement on every field.

**Simple interpretation:** the curated mixture is a better starting set guess on this diagnostic. However, the existing public-fact filtering reduces coverage and worsens aggregate loss in both arms, so this work has **not** solved belief inference. The small candidate bank, fallback and scoring assumptions still need investigation. The current source snapshots postdate many evaluated games, so the result remains retrospective.

The scoring artifact separately records exclusions: 487 current-item observations, 68 item-acquisition/restoration cases, 116 possibly changed/copied ability cases, 3 possibly transferred-item cases, 19 transformed-identity cases and 100 observations on possible-Illusion sides. These counts describe the scorer's exclusion paths, not population frequencies.

## Battle comparison: frozen, running, no result yet

The four-game integration smoke is frozen in [`smoke-v2-manifest.json`](../evaluation/coherent-sets/smoke-v2-manifest.json). The planned 60-game screening is frozen in [`screening-v2-manifest.json`](../evaluation/coherent-sets/screening-v2-manifest.json), with ten validated synthetic teams under `evaluation/coherent-sets/screening-teams-v2/`. These use distinct synthetic rosters from the other chat's reserved pools; they are not an independent external competitive-team holdout.

Both arms request **8 worlds ×150 ms, one native thread, a three-second ceiling, whole-team sampling and deterministic root selection**. Later unrelated policy changes from the other chat remain excluded. The smoke must pass before screening starts. The original team-reservation attempt failed a trailing-whitespace content-hash check before any games; v2 is the corrected reservation. No failed-attempt game outcomes are being omitted.

No battle-strength result or default-prior promotion is claimed while the smoke is running and screening has not started.

| Check | Status | Result |
|---|---|---|
| Separate branch/worktree | Complete | `Kenar-coherent-sets`, anchored at `a8613b9` |
| Importer correctness / rule validation | Initial gate passed | 556 validated variants; 2 incomplete templates rejected; review continues |
| Extractor correctness | Initial fixture gate passed | Focused fixtures passed; real-export coverage review pending |
| Next-revelation comparison | Initial retrospective result complete | Mixture improves aggregate loss/coverage; filtering worsens both arms; no strength claim |
| Matched-compute battle smoke | Running | Four planned games; no result claimed yet |
| Controlled battle screening | Frozen, not started | 60 games / ten synthetic teams after smoke gate |
| Promotion decision | Pending | No default change justified yet |

For each completed run, record the source/prior/engine hashes, mixture configuration, team provenance, schedule/seed, W/L/draw/void counts, uncertainty, targeted prediction metric, completed worlds, rejected choices, fallbacks and p50/p95/p99/max latency. Keep failed experiments and void games visible. The existing handoff's screening/confirmation rules remain applicable; small smokes verify integration only.

## Decisions and next step

The current decision is to build and test the importer, mixture and extractor in isolation. Roster-conditioned weighting and joint team hypotheses remain subsequent experiments; they are not prerequisites for this milestone. Do not add a hard rule that a defensive Pokémon makes another defensive Pokémon unlikely: team roles can complement one another, and species can run different sets.

Next: finish the frozen battle smoke, then run the same-MCTS/different-prior screening if the gate passes. Keep the filtering regression as a documented unresolved finding. Replace pending result entries only from actual artifacts.

References: [combined-data plan](mcts-combined-data-plan.md), [full MCTS handoff](mcts-improvement-handoff.md), [historical measured results](mcts-results.md), [Showdown set source](https://play.pokemonshowdown.com/data/sets/gen9ou.json), and [Showdown protocol](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md).
