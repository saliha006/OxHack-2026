# Coherent sets and replay revelations: change and results log

Status: implementation pushed as `740817f`; retrospective prediction and four-game integration smoke are complete; 60-game battle screening is running, 25 October 2026. This log distinguishes completed checks from planned experiments. No playing-strength improvement is established yet.

The goal is to give MCTS more plausible opponent sets. Showdown supplies coherent role templates; our existing usage prior supplies broader coverage; replay logs supply facts revealed during battles. The bot must keep several possibilities and update them as evidence appears, rather than pretending that an unrevealed item or spread is known.

## Isolation from the other MCTS chat

This work is on `Kenar-coherent-sets` in the separate `OxHack-coherent-sets` checkout. The other chat continues the data-independent handoff on `Kenar-mcts`; its working files and experiments are not changed here.

The frozen comparison anchor is **`a8613b9`**, the committed MCTS revision observed when this branch was created. It includes the state/belief work already committed by the other chat, including the fainted-Tera memory correction. New changes made by that chat after this anchor are outside this experiment. The historical `2c02fc8` baseline remains part of the older handoff; it is not silently relabelled as the current anchor.

Both arms use the same engine, MCTS settings, sampling policy, teams and game schedule in the frozen comparison. The intended treatment is the set-prior source. Any runtime compatibility changes, such as preserving IV overrides, must be recorded explicitly rather than hidden inside the data comparison. Source, prior and engine hashes in the experiment artifacts are the authority for what actually ran.

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

The candidate contract now permits optional IVs, and `decision/belief.py` preserves supplied IV overrides when loading a candidate. A record without IVs retains the historical all-31 default. Eleven initial focused importer/extractor/contract tests passed, including zero-IV serving and absent-IV compatibility checks. The initial combined decision/bot suite passed **468 tests** in `runs/coherent-evaluation/tests.txt`; that run predates added tests and the latest comparison-harness changes. The final test status and unresolved timing failures are recorded separately below.

**Artifacts:** `runs/curated-v1/bank.json`, `runs/curated-v1/priors.json` and `runs/curated-v1/manifest.json`. The source is `data/sources/gen9ou-20261025.json`, SHA-256 `898612165656b5969ef7fbecd764faf8a623039a27eaa2f912c16881b3fba087`; broad-prior SHA-256 is `47b31bf7282d6578ed44d7b28f9a63e9284eddc72882856de426f7c1bfc8c7f3`. The validator used Showdown commit `c0845f33d381402dfcb18ce324c20a94f18af075`.

**Review corrections:** identical role distributions under different names no longer gain extra curated mass. The A/A-copy/B regression verifies that duplicate role A cannot outvote distinct role B. A zero-curated-fraction mixture returns an exact deep copy of the original prior. The importer now also checks move IDs against the pinned native move snapshot before accepting them; no unsupported moves were found in this source. An offline rebuild reproduced the versioned `bank.json` and `priors.json` exactly. These changes do not alter the frozen mixture or battle treatment.

**Did it help?** Not measured yet. Better-looking templates alone do not establish better predictions or a stronger bot.

## Change 2: chronological reveal extractor

**Why:** raw replay logs contain more evidence than move names and HP. We need an explicit record of what was observed and when so evaluation cannot use future information accidentally.

**Implemented behavior:** `data/pipeline/reveal_evidence.py` extracts battle/side/Pokémon identity, event position, field, value and provenance from logs using the shared parser. It preserves a consumed/lost item identity separately from the now-empty current item and excludes possible transferred items, changed abilities and transformed identities from native-set scoring. It deduplicates repeated revelations and keeps unobserved fields unknown. Called/copied move handling follows the parser; Illusion-capable sides are excluded conservatively from native-set scoring, trading coverage for fewer incorrect labels.

**Completed checks:** focused fixtures exercise repeat observations, state strictly before a reveal, consumed items/current-empty state, Trick, called moves, transformed identities and possible Illusion. The extraction of the 200-game sample finished: **4,025 move records, 653 ability records, 1,003 item records, 510 current-item records and 272 Tera records**. Of the emitted records, **5,648** were marked eligible native-set evidence. These are extracted records, not independent complete-set labels; the scorer also excludes already-public targets and conservative protocol cases.

A new bounded read-only sample was exported by `data/pipeline/sample_replay_logs.py`: **200 complete games**, 100 from each frozen Tiger source split, selected by hashed battle identity/time with seed `coherent-v1`. All 200 selected logs matched. This is a separate bounded task, not a restart of the full turns-table download. Local artifacts are `runs/reveals/tiger-200.jsonl` and `runs/reveals/tiger-200.manifest.json`; input SHA-256 `23ff7b44ad357054d7c4fd655ef2583302ad783893a5d3d4da99847e82ff7ac9`. The transition-corrected export is `runs/reveals/evidence-200-v2.jsonl`, with summary [`extraction-v2-summary.json`](../evaluation/coherent-sets/extraction-v2-summary.json). The transition fix preserves repeated current-item loss/reacquisition timing instead of deduplicating away a real state transition. It increases item/current-item event counts while leaving the **5,648 eligible native-set targets unchanged**. The earlier `evidence-200.jsonl` export is retained as history.

A subsequent safety audit added conservative censoring after Mimic/Sketch and retained censoring of a transformed owner's history after switching out, because copied moves can remain in the parser's accumulated history. The Mimic/Sketch move itself can be native evidence; subsequent native-set targets for that owner are conservatively excluded, including otherwise valid item facts, because their conditioning state may contain copied move history. This deliberately loses coverage and also censors after a failed copy attempt. New fixtures cover these cases. No Mimic/Sketch event occurred in the 200-game sample. [`extraction-v3-summary.json`](../evaluation/coherent-sets/extraction-v3-summary.json) reports the same counts and exactly the same evidence output SHA-256 as v2, `60a471e54420e2f0b783ac13728a1e470f999e3ebcdb35dfb84942ee34290db0`. The v3 extractor hash differs as expected; the v3 scorer rerun is pending. No runtime prior/search behavior changed in this hardening.

**Remaining verification:** inspect real extracted examples and coverage, and retain focused counterexamples for protocol edge cases. Conservative exclusions mean absence from the scored evidence is not proof that a field never became knowable.

**Did it help?** The extractor provides usable time-aligned targets and passes the initial fixtures. The first prediction comparison below favors the mixture over the old prior, but filtering itself still has a problem: both arms score worse after public-fact filtering than before it. Extraction correctness and a prediction-score improvement are not win-rate results.

## Comparison plan and result status

The experiment should keep three questions separate:

1. **Correctness:** does the importer preserve the template and does the extractor preserve actual observed evidence?
2. **Prediction:** do curated-plus-usage candidates predict later revelations better than existing priors? Compare existing-only, curated-only and the mixture where supported, with declared smoothing, fallback and a stated next-revelation scoring model.
3. **Playing strength:** does the resulting MCTS win more games against the frozen current MCTS at matched requested compute, without legality, fallback or latency regressions?

The retrospective scorer, `evaluation/score_reveal_evidence.py`, reconstructs candidate beliefs from the public state strictly before each new event. This tests prefix-state revelation filtering, not the full persistent runtime damage/speed or consumed-item-history pipeline. It assumes a uniform choice among a candidate's not-yet-observed moves when scoring a new move; scores therefore mix set quality with move/reveal selection. Use whole-game development/scoring separation, and do not fit the mixture on confirmation outcomes. An unseen move or hidden spread is not a false label. A current curated snapshot evaluated on older games gives retrospective evidence; strict forward-time claims require appropriately dated source snapshots.

## First retrospective prediction result

Artifacts: initial [`reveal-diagnostic-v1.json`](../evaluation/coherent-sets/reveal-diagnostic-v1.json) and post-transition-fix [`reveal-diagnostic-v2.json`](../evaluation/coherent-sets/reveal-diagnostic-v2.json). The v2 metric tables were compared directly with v1 and are identical; conservative excluded-event counts change. The bootstrap below is now recorded in both v1 and v2. A v3 scorer rerun is pending after the additional extractor safety fixtures; no new score is asserted from that unfinished run. The frozen Tiger source test split contributes **100 games and 2,821 eligible new revelations**. No mixture tuning was performed on these scores. Lower log loss is better; coverage means positive probability before the declared floor, not exact full-set accuracy.

| Prediction variant | Test mean log loss | Target support coverage |
|---|---:|---:|
| Existing prior, before public-fact filtering | 4.0469 | 78.8% |
| 50/50 mixture, before public-fact filtering | **3.7062** | **82.0%** |
| Existing prior, after public-fact filtering | 4.5569 | 73.8% |
| 50/50 mixture, after public-fact filtering | **4.2334** | **76.6%** |

For the two filtered arms, the mixture-minus-baseline log-loss difference is **−0.3236**, with a paired whole-battle bootstrap 95% interval **[−0.4218, −0.2321]** (5,000 resamples, seed `2026102511`). This interval does not control repeated-player or repeated-roster dependence. It describes this bounded retrospective sample and scoring model; it is not a deployment-strength estimate.

The mixture improves filtered move loss from **4.9784 to 4.5982**, item loss from **4.5103 to 4.2028**, and Tera loss from **6.1402 to 5.8935**. Ability loss changes slightly in the wrong direction, **0.8705 to 0.8828**. Do not describe the result as an improvement on every field.

**Simple interpretation:** the curated mixture is a better starting set guess on this diagnostic. However, the existing public-fact filtering reduces coverage and worsens aggregate loss in both arms, so this work has **not** solved belief inference. The small candidate bank, fallback and scoring assumptions still need investigation. The current source snapshots postdate many evaluated games, so the result remains retrospective.

The v2 scoring artifact separately records exclusions: 501 current-item observations, 69 item-acquisition/restoration cases, 116 possibly changed/copied ability cases, 10 possibly transferred-item cases, 19 transformed-identity cases and 100 observations on possible-Illusion sides. These counts describe the scorer's exclusion paths, not population frequencies.

## Battle comparison: integration passed, screening running

The four-game integration smoke is frozen in [`smoke-v2-manifest.json`](../evaluation/coherent-sets/smoke-v2-manifest.json), with completed results in [`smoke-v2-results.json`](../evaluation/coherent-sets/smoke-v2-results.json) and its companion game rows. The 60-game screening is frozen in [`screening-v2-manifest.json`](../evaluation/coherent-sets/screening-v2-manifest.json), with ten validated synthetic teams under `evaluation/coherent-sets/screening-teams-v2/`. These use distinct synthetic rosters from the other chat's reserved pools; they are not an independent external competitive-team holdout.

Both arms request **8 worlds ×150 ms, one native thread, a three-second ceiling, whole-team sampling and deterministic root selection**. Later unrelated policy changes from the other chat remain excluded. The smoke passed before screening started. The original team-reservation attempt failed a trailing-whitespace content-hash check before any games; v2 is the corrected reservation. No failed-attempt game outcomes are being omitted.

The smoke finished **3 wins, 1 loss, no draws or voids** for the mixture. Across both arms, **2,728/2,728 worlds completed and were usable**, with zero fallbacks, rejected choices, failed worlds or decisions over three seconds. Candidate/baseline maximum decision latency was **1,845.83 / 1,888.37 ms**. Candidate/baseline p95 latency was **1,449.74 / 1,446.16 ms**. Candidate/baseline actual native search wall time totaled **227.73 / 223.18 seconds**; bot-process-plus-reaped-worker CPU totaled **235.07 / 230.69 seconds**. Both arms ran the same requested settings; actual measured work differs naturally.

This is an **integration gate**, not a strength result: four games give a Wilson 95% win-rate interval of approximately **30.1–95.4%**, and only a small portion of the reserved team pool was exercised. The run verifies that the new prior can play complete games under the tested deadlines.

The 60-game screening is now running in `runs/coherent-evaluation/screening-v1/`. Its partial `summary.json` is a progress artifact, not a final verdict or stopping signal. No default-prior promotion is claimed while the frozen schedule remains incomplete.

## Final test status and unresolved timing checks

The completed non-timing suite passed **451 tests in 16.34 seconds**, recorded in `runs/coherent-evaluation/non-timing-tests.txt`. That command explicitly deselected **22 subsecond timing tests**; it is not a claim that the entire 473-test suite passed. After the latest safety hardening, **18 focused importer/extractor/evaluator/contract/safety tests passed**. The expanded non-timing rerun in `runs/coherent-evaluation/non-timing-final.txt` is still in progress at this update; no expected pass count is presented as completed.

A full final attempt had five failures: one new fixture was corrected, while four existing timing checks failed. A focused rerun still had one existing timing failure, and a separate search-timing rerun had two. An unmodified `a8613b9` control also failed one same-family timing check while passing 21, in `runs/coherent-evaluation/baseline-search-timing-control.txt`. Concurrent load is a plausible contributor, but the timing flakiness remains unresolved; the baseline control does not prove every candidate failure harmless. No timing thresholds were weakened. Independent-prior-path and source-prefix-safety tests passed.

A credential-value scan reported zero matches in the committed artifacts. Raw private data and credentials remain outside Git. See [usage and reproduction commands](coherent-sets-usage.md) for exact entry points and integration cautions.

| Check | Status | Result |
|---|---|---|
| Separate branch/worktree | Complete | `Kenar-coherent-sets`, anchored at `a8613b9` |
| Importer correctness / rule validation | Initial gate passed | 556 validated variants; 2 incomplete templates rejected; review continues |
| Extractor correctness | Fixture, transition and copied-history gates passed | v3 extraction has identical output hash/counts to v2; scorer rerun pending; conservative coverage limitations remain |
| Next-revelation comparison | Initial retrospective result complete | Mixture improves aggregate loss/coverage; filtering worsens both arms; no strength claim |
| Matched-compute battle smoke | Complete | 3–1, 0 voids; 2,728/2,728 usable worlds; no tested reliability failures; integration only |
| Controlled battle screening | Running | Frozen 60-game schedule / ten synthetic teams; final verdict pending |
| Promotion decision | Pending | No default change justified yet |

For each completed run, record the source/prior/engine hashes, mixture configuration, team provenance, schedule/seed, W/L/draw/void counts, uncertainty, targeted prediction metric, completed worlds, rejected choices, fallbacks and p50/p95/p99/max latency. Keep failed experiments and void games visible. The existing handoff's screening/confirmation rules remain applicable; small smokes verify integration only.

## Decisions and next step

The current decision is to build and test the importer, mixture and extractor in isolation. Roster-conditioned weighting and joint team hypotheses remain subsequent experiments; they are not prerequisites for this milestone. Do not add a hard rule that a defensive Pokémon makes another defensive Pokémon unlikely: team roles can complement one another, and species can run different sets.

Next: complete the frozen same-MCTS/different-prior screening and record its final result, then decide whether a fresh confirmation study is justified. Keep the filtering regression and timing-test flakiness documented as unresolved findings. Do not change the default prior based on the smoke or interim scores.

References: [combined-data plan](mcts-combined-data-plan.md), [full MCTS handoff](mcts-improvement-handoff.md), [historical measured results](mcts-results.md), [Showdown set source](https://play.pokemonshowdown.com/data/sets/gen9ou.json), and [Showdown protocol](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md).
