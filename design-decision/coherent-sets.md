# Coherent set priors and public replay evidence

Verified 25 October 2026 against `Kenar-coherent-sets` at
[`50d9a43`](https://github.com/saliha006/OxHack-2026/commit/50d9a4362da5946918bd0a52d6689e582d16e46f).
See [current status](../CURRENT-STATUS.md) for the branch matrix and integration state.

**Decision: keep the 50/50 coherent-template mixture opt-in.** It improved the
retrospective revelation diagnostic but finished **25–35** against the frozen
MCTS baseline. The normal prior remains `data/set_candidates.json`; the optional
mixture is selected explicitly with `--priors data/curated-v1/priors.json`.

## Implemented

- `data/pipeline/import_curated_sets.py` imports pinned Showdown OU role templates,
  validates concrete variants, preserves optional IV overrides and combines
  curated support with the existing usage prior. The versioned bank contains
  **556 validated variants**, augmenting **160 species/form aliases**. Two
  incomplete templates were rejected because no Tera fallback was available.
- Curated and broad support each receive 50% mass where curated support exists;
  unsupported species retain their old prior. Equal role/alternative weights are
  declared heuristics, not measured joint-set frequencies. Duplicate identical
  role distributions and alternatives do not gain extra probability mass.
- The candidate contract and `decision/belief.py` accept optional six-stat IVs.
  Existing candidates without IVs retain the all-31 behavior. Sampled spreads
  remain hypotheses about hidden sets.
- `data/pipeline/reveal_evidence.py` extracts timed public move, item, ability and
  Tera evidence. It separates consumed/lost items from the current empty item
  slot, and conservatively excludes possible transfers, copied moves/abilities,
  transformed identities and possible Illusion identities from native-set labels.
- `data/pipeline/sample_replay_logs.py` supplies a bounded read-only Tiger sample;
  `evaluation/score_reveal_evidence.py` predicts each eligible revelation from
  the public state strictly before that event. This does not add database access
  or a second belief engine to live play.
- The comparison runner supports independent frozen prior files with `--b-priors`.

## Completed evidence

The bounded sample contains 200 games; its test half has **100 games and 2,821
eligible new revelations**. No mixture tuning used these scores. The diagnostic
assumes a uniform choice among each candidate's unseen moves and reconstructs
revelation-only filtering; it does not test persistent runtime damage/speed
inference or exact hidden-set accuracy. The source snapshots postdate many games,
so this is retrospective evidence.

| Test metric | Existing prior | 50/50 mixture |
|---|---:|---:|
| Mean log loss before public-fact filtering | 4.0469 | 3.7062 |
| Support coverage before filtering | 78.8% | 82.0% |
| Mean log loss after public-fact filtering | 4.5569 | 4.2334 |
| Support coverage after filtering | 73.8% | 76.6% |

Lower loss is better. Filtering worsens both arms, and ability loss slightly
worsens with the mixture; this has not solved belief inference.

The planned **60/60-game** battle screening completed with **25 wins, 35 losses,
zero draws and zero voids**. Candidate win rate was **41.7%**, Wilson 95% interval
**30.1–54.3%**; the result does not establish a stronger bot or general harm.
Both arms used eight whole-team worlds ×150 ms, one native thread, a three-second
budget and deterministic root selection. All **43,712 requested worlds** completed
and were usable, with zero fallbacks, rejected choices, failed worlds or decisions
over three seconds. Candidate p50/p95/max latency was **1,382.95 / 1,464.79 /
2,057.77 ms**.

The comparison freezes MCTS at **`a8613b9`**; subsequent `Kenar-mcts` policy changes
are outside this experiment. The treatment includes the prior and its IV-preserving
loader compatibility. Ten synthetic rosters reuse familiar regression component
sets: they are **not an independent external competitive-team holdout**. Shared
teams, sparse clusters and stochastic native search limit generalization.

The final recorded full test attempt was **478 passed, 1 failed**. The same
0.6-second worker scheduling assertion reproduced in the untouched `a8613b9`
control; it remains unresolved. The focused data/compatibility gate passed 22 tests.
These are recorded experiment results, not a new test run of the context branch.

## Integration and remaining work

This implementation is available on `Kenar-coherent-sets`; it is not merged into
`main` or the active MCTS branch. Reconcile optional-IV and independent-prior
runner changes with that branch, then rerun relevant checks and comparisons on
the combined engine before attributing an interaction gain. The 25–35 screen does
not justify a promotion confirmation of this exact mixture.

Investigate filtering and role weights using development evidence before proposing
a new prior experiment. **Roster-conditioned A6 priors remain pending**: the
approved teammate-match fallback design is not implemented by this importer.
No learned role probabilities or joint-team hypothesis model was added.

## Source and artifacts

All links below are pinned to the audited source revision:

- [Implementation, results and limitations](https://github.com/saliha006/OxHack-2026/blob/50d9a4362da5946918bd0a52d6689e582d16e46f/docs/coherent-sets-results.md)
- [Usage and reproduction commands](https://github.com/saliha006/OxHack-2026/blob/50d9a4362da5946918bd0a52d6689e582d16e46f/docs/coherent-sets-usage.md)
- [Experiment index](https://github.com/saliha006/OxHack-2026/blob/50d9a4362da5946918bd0a52d6689e582d16e46f/evaluation/coherent-sets/index.json)
- [60-game screening results](https://github.com/saliha006/OxHack-2026/blob/50d9a4362da5946918bd0a52d6689e582d16e46f/evaluation/coherent-sets/screening-v2-results.json)
- [Retrospective revelation diagnostic](https://github.com/saliha006/OxHack-2026/blob/50d9a4362da5946918bd0a52d6689e582d16e46f/evaluation/coherent-sets/reveal-diagnostic-v3.json)
- [Recorded test gates](https://github.com/saliha006/OxHack-2026/blob/50d9a4362da5946918bd0a52d6689e582d16e46f/evaluation/coherent-sets/test-gates.json)

The generated bank/prior/manifest live in `data/curated-v1/`; public result summaries
live in `evaluation/coherent-sets/`. Raw private replay logs and credentials remain
outside Git.
