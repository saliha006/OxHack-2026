# Coherent prior revision: diagnosis, change and results

Status: diagnosis, frozen-extractor replication, independent probability audit and fresh replay prediction test completed; primary battle screening running and secondary reliability retry pending. This revision now lives in `/home/kenar/Documents/ChatGPT/oxhack 2026/OxHack-coherent-v2` on **`Kenar-coherent-v2`**. The earlier coherent-set checkout and its separate observed-fact-filtering chat remain untouched. Its live `native_facts` / `original_set_before` extractor edits are excluded here. The original data-independent MCTS chat remains separate too.

## Starting evidence

The first optional 50/50 coherent-template/usage mixture improved the retrospective next-revelation diagnostic, but it did not improve the screened battle result:

| Measurement | Existing prior | First mixture |
|---|---:|---:|
| Test revelation log loss after public-fact filtering | 4.5569 | **4.2334** |
| Target support coverage | 73.8% | **76.6%** |
| Head-to-head wins, matched requested MCTS compute | **35** | 25 |
| Screened games | 60 | 60 |
| Runtime fallbacks / rejected actions / failed worlds | 0 / 0 / 0 | 0 / 0 / 0 |

The mixture scored 41.7% wins, Wilson 95% interval 30.1–54.3%, with a sparse candidate-team bootstrap interval of 25–60%. That does not support promotion; it also does not establish general harm across the ladder. Full first-study evidence remains in [the original results log](coherent-sets-results.md) and [`screening-v2-results.json`](../evaluation/coherent-sets/screening-v2-results.json). The positive four-game smoke was an integration gate and is not substituted for the completed 60-game comparison.

Both old and mixed priors scored worse after public-fact filtering than before it. That is a diagnostic problem to investigate, not evidence that all revealed information should be ignored. The scorer's assumed next-new-move distribution, incomplete candidate support, recovery behavior and source weighting need to be separated.

## What the diagnosis establishes

Evidence: [`v2-diagnosis-predictions.json`](../evaluation/coherent-sets/v2-diagnosis-predictions.json) and [`v2-diagnosis-battles.json`](../evaluation/coherent-sets/v2-diagnosis-battles.json). The prediction analysis used **100 training games / 2,827 targets**, excluding the previously inspected test half from tuning.

**The prediction target is incomplete for battle decisions.** About 70% of its targets are moves; it has no true EV, IV or nature labels. Better coverage of a later revealed move does not validate the speed or bulk MCTS assumes when choosing a move. The audit of actual known evaluation teams also found better active move recall mass for v1, **0.8238 versus 0.7968**, so it would be wrong to say the deployed mixture simply guessed moves worse overall. Those averages are conditional on different visited positions and game lengths; they are not a matched counterfactual decision test.

**The first mixture overtrusted a few templates.** Equal role weights and a 50% curated component redistributed at least 25% of exact-EV probability mass for **119 of 160 species/form aliases**, and at least 40% for 57. These alias counts are not independent Pokémon. Exact-tuple variation can count small, combat-minor four-EV swaps, so this is a drift warning rather than proof of combat harm. One exact Kingambit template went from zero mass to 50%; nearby zero-HP/max-Speed spreads already existed in the baseline. Kingambit's effective set count fell **18.65 → 3.80** and its expected distinct hypotheses among eight draws fell **6.71 → 4.65**, despite increasing from 30 to 31 candidate records. More records did not mean more useful search diversity.

For Gholdengo, Air Balloon mass rose **29.7% → 52.4%**, while the raw usage marginal was about 22.4%. The data supports that item as plausible; equal template counting did not justify such strong probability. Some dangerous alternatives were diluted: Hydrapple's Draco Meteor mass fell **0.771 → 0.386**, and Garganacl's Protect mass **0.904 → 0.618**. These are concrete threat-coverage changes, not proof that either change caused a particular loss.

**The filtering diagnostic has its own failure modes.** On training data, the first mixture's public-fact filter changed 136 prior-supported targets to zero support. Its small compatible bank can retain some hypotheses while excluding future truth, and fallback cannot represent every legal continuation. In 29 targets with a known current item after a possible transfer, posterior loss was 7.116 versus prior loss 3.416; current held item is not always original role identity. That small subgroup does not explain the entire forecast gap or the battle result. The runtime belief implementation remains fixed in this prior experiment; the other chat's filtering changes are a separate treatment.

**What is not established:** no single causal explanation of the 25–35 result is proven. The evidence supports objective mismatch, overly concentrated role weighting and diluted threat tails as mechanisms worth controlling. The finite battle interval still includes an even match. Private evaluation sets are used only for post-game diagnosis, never for fitting the prior or as live bot inputs.

## Development and evaluation separation

The first 60-game screening is now development history. It can reveal failure mechanisms, but replaying it cannot become new confirmation. The original 100-game Tiger test sample also remains previously inspected evidence. Candidate selection and probability tuning must use training/development material rather than optimize those earlier test scores.

A new reservation is complete at `evaluation/coherent-sets/v2-screening-teams/`. It contains ten new six-species roster combinations, using familiar regression component sets and existing legal weather components. These are **synthetic teams with known components**, not an independent external competitive-team holdout. The planner verified disjointness against **222 previously known rosters**, including stand-in teams and explicit roster metadata from this branch and the other chat's known reservation pools at reservation time. All ten new teams passed the pinned Gen9 OU validator with zero errors. It never reads outcomes to select teams. Later other-chat reservations can change, so the recorded exclusion snapshot defines the exact claim.

The reserved files are excluded from mixture fitting and candidate selection. A 60-game schedule uses four-game blocks balancing simulator side and both bot/team assignments, seed `2026102521`, six appearances for every team in each bot role. The team/schedule reservation is **not** a frozen source/prior experiment manifest; source/engine/prior identities are frozen separately after the selected artifact is ready. Moving the reservation to this worktree rewrote only its file paths: all ten team-content hashes and the reserved schedule stayed unchanged. The `isolation_transfer` record preserves the earlier manifest SHA-256. Protocol options are recorded in [`v2-experiment-plan.json`](../evaluation/coherent-sets/v2-experiment-plan.json). Three reservation integrity tests passed before games started. The revised prior was then frozen before fresh prediction evaluation and both battle panels.

Two source/prior-frozen comparisons use the same selected candidate:

1. Revised mixture versus the same frozen `a8613b9` current-MCTS baseline, at eight whole-team worlds ×150 ms, one native thread and a three-second ceiling. Its 60-game panel uses **three concurrent games**, in [`vs-broad-screening-manifest.json`](../evaluation/coherent-sets/v2/vs-broad-screening-manifest.json), and has started after its smoke gate.
2. Revised mixture versus the first 50/50 mixture, another **60 games** on the same balanced fresh team/matchup schedule. Its original three-concurrent-game screening plan was **superseded without being run** after a smoke reliability failure; the replacement [`vs-v1-screening-v2-manifest.json`](../evaluation/coherent-sets/v2/vs-v1-screening-v2-manifest.json) uses **two concurrent games**. A serial smoke retry must pass before that panel starts. Each comparison has its own frozen manifest, run directory and resource report. Sharing the schedule creates useful pairing but does not make the two comparisons independent statistical samples.

Every run must retain source/engine/prior/team hashes, seeds, actual CPU/search time, complete game outcomes including voids, world completion, failures, recovery and latency. Keep no-op/error fallback behavior and the native deadline unchanged. Do not combine the other chat's later lead/allocation/guard/mixing work into the prior comparison.

## Revised candidate: conservative weighting selected, battle result pending

The selected development configuration is `25-075`: usage-weighted curated roles, a **25% maximum curated share**, and a **7.5 percentage-point maximum marginal shift** across move inclusion, item, Tera, nature and decision-relevant EV bins. The reported mean effective curated share is about **12.22%**, rather than 50%. Source coherent sets and broad fallback remain available; the restriction limits how far uncertain templates can pull the prior. The selected artifact is `data/curated-v2/priors.json`, SHA-256 **`211d30993b4dbc346dc0bea52901d7fb4ebca6b23301fa748e776c8948516ed8`**. Complete source/engine/prior identities are recorded separately in each frozen study manifest.

Selection used four globally declared configurations on the **training half only**. The selected candidate's training posterior loss was **4.09334**, versus **4.05813** for the first mixture and **4.37846** for broad priors; target support was **77.856%**, equal to v1. The choice deliberately accepts a small prediction-loss tradeoff for more conservative prior changes. It does not claim to optimize the hidden battle objective from those forecasts. The previous test half was not checked or tuned in this selection. Selection evidence is in `evaluation/coherent-sets/v2-train-selection-plan.json` and its results artifact. Replication against the frozen **`50d9a43` extractor** completed in [`v2-train-selection-replication.json`](../evaluation/coherent-sets/v2-train-selection-replication.json): all recorded metrics matched exactly and the same `25-075` candidate was selected. The previously inspected test half was not used to reselect or retune it. The separate filtering chat's live `native_facts` / `original_set_before` changes were excluded; frozen extractor SHA-256 is `46e5ad3306e64985f38c60a3894761a440250388ac7de77a59a6221198519afe`.

Fresh smoke outcomes now exist, but neither 60-game panel has a final strength result. The existing default prior stays unchanged.

## Independent probability and position checks

[`marginal-audit.json`](../evaluation/coherent-sets/v2/marginal-audit.json) checks the assembled prior rather than trusting only its producer metadata. Across **321 species/form aliases**, the maximum absolute shift in audited features is **0.075** for the revised prior, versus **0.5** for v1; zero species exceed the revised bound beyond numerical tolerance. Mean effective set count is **15.12** for broad priors, **9.47** for v1 and **15.02** for the revised prior. This verifies the intended probability/diversity control. It does not establish that the broad marginals themselves are ground truth or that restoring diversity improves play.

The public-position diagnostic in [`position-diagnostic.json`](../evaluation/coherent-sets/v2/position-diagnostic.json) ran **nine native calls / 72 usable worlds**. All nine pooled choices remained **Pyro Ball**, including worlds whose sampled opponent sets were faster because of Choice Scarf. The revised probabilities changed without changing this action. This is not a replay of historical persistent beliefs, an oracle or a counterfactual game result, and it does not prove that the revision fixes the historical knockout. It is evidence against a simplistic story that correcting this assumption automatically corrects the move.

## Fresh held-out revelation result

[`fresh-prediction-results.json`](../evaluation/coherent-sets/v2/fresh-prediction-results.json) evaluates **100 new source-test games / 2,892 targets**, with **zero battle-identity overlap** with the original 200-game sample. The newly fetched source-training half was left unused. Candidate parameters were frozen before these scores and were not retuned afterward. Scoring uses the frozen legacy extractor and prefix-filter diagnostic, so it excludes the other chat's new native-fact scoring changes.

| Prior | Fresh posterior mean log loss | Target support |
|---|---:|---:|
| Broad baseline | 4.274805 | 75.8990% |
| First 50/50 mixture | **3.889368** | **79.0802%** |
| Revised conservative mixture | 3.919504 | 79.0456% |

The revision-minus-v1 difference is **+0.030136**, whole-battle bootstrap 95% interval **[+0.011686, +0.050111]**: the revision is slightly worse on this forecast metric. Versus broad priors it remains better, difference **−0.355301**, interval **[−0.454645, −0.259330]**. These retrospective, partial-label scores do not validate hidden spreads, and the bootstrap does not control repeated-player/roster dependence. The conservative revision has retained most of the prediction benefit while limiting prior drift; whether that tradeoff improves battles remains an empirical question.

## Battle gates and operational backoff

The broad-baseline smoke completed **3–1**, with no fallback, rejected action, failed world or decision beyond three seconds, in [`vs-broad-smoke-results.json`](../evaluation/coherent-sets/v2/vs-broad-smoke-results.json). Actual completed worlds were **955/960 requested** for the candidate and **958/968** for the baseline: requested work is not reported as fully completed work. The successful reliability gate allowed the 60-game primary study to start. Its partial wins are progress only, not a promotion result.

The initial v1 smoke completed **1–3**, and its old-mixture B arm had **one first-decision worker-deadline fallback and one failed world**. Maximum observed decision time was about **2,732 ms**; no server rejection or decision beyond three seconds occurred. That failed reliability run is preserved in [`vs-v1-smoke-results.json`](../evaluation/coherent-sets/v2/vs-v1-smoke-results.json), rather than omitted or replaced by a better-looking record.

The implementer froze a **serial smoke retry**, [`vs-v1-smoke-serial-manifest.json`](../evaluation/coherent-sets/v2/vs-v1-smoke-serial-manifest.json), and lowered the **unrun secondary screening** from concurrency three to two. The candidate, prior files, native search time, thread count and decision budget did not change. The manifest records operational startup backoff as the reason; it is not a score-driven policy retune. The serial retry is **in progress**, so no pass is assumed and the secondary 60-game study remains gated.

One shared-host snapshot showed load average **19.22 on 16 logical CPUs**, about **12/14 GiB RAM used** and **8 GiB swap used**, with other chats evaluating concurrently. That is relevant context for startup failures, not proof of their sole cause. Within each panel both arms request the same compute and actual worlds, CPU/search time and latency must be reported. The different panel concurrency is an explicit cross-panel caveat; do not label results across the two panels as identical actual resource conditions.

## Tests and promotion status

The pretrial full suite completed **493 passed, two existing subsecond timing tests failed**, in `runs/coherent-v2/pretrial-tests.txt`. The focused revision gate passed **25 tests**, and the position diagnostic tests passed **two**. These are separate runs, not an all-green full suite. No legacy timing threshold was weakened. The old study's 478-pass/one-failure result stays historical and is not substituted for current test evidence.

No final battle result or promotion is claimed yet. Both complete 60-game comparisons, their resource/reliability outcomes and the secondary smoke retry will be recorded here. Better forecasts alone cannot justify promotion, and the revised forecasts are in fact slightly worse than v1. Keep the default prior unchanged while those outcomes remain incomplete.
