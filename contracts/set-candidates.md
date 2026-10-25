# SetCandidates contract

> **DRAFT v0**, defined by Derrick (decision layer), 2026-10-24. To be built by the data layer (@nate); not yet agreed.

**What it is:** one JSON file listing, per species, the likely full sets an opponent might run, with prior weights,
plus trimmed usage shares. The decision layer's belief loads it once at startup.

- **Types:** [`set_candidates.py`](set_candidates.py) (TypedDicts; field comments are the spec).
- **Example:** [`examples/set_candidates_example.json`](examples/set_candidates_example.json). Its `usage` blocks are
  real (2026-09 chaos, 1825, top 5 each); its `sets` and their weights are **illustrative only**.
- **Check:** `uv run pytest tests/test_set_candidates_contract.py`.

## How the decision layer uses it
| Part | Used by | For |
|---|---|---|
| `sets` | Belief prior (02), hard filter (03), reweight (04), sampling (05) | The starting guesses and their weights |
| `usage` | Hard filter fallback (03) | Rebuilding sets when every candidate contradicts what's revealed |

## What Derrick decided the contents should be (feature 02 doc)
- **Source:** Smogon chaos stats, `gen9ou`, **1825** band, month **2026-09** (record it in `source`).
- **Sets are combined from the chaos counts:** moves, item, ability, Tera type and spread, weighted by the product of
  their shares (treated as independent). Up to **30 per species**, highest first, weights renormalised to 1. No "other" set.
- **Consistency rules:** a Choice item or Assault Vest ⇒ no status moves; only moves the species can learn.
- **No teammate correlations** in v1.

## Conventions
- **Names are Showdown IDs** (`gholdengo`, `makeitrain`, `choicescarf`), formes as their own species (`samurotthisui`).
- **EVs are `[hp, atk, def, spa, spd, spe]`**, as in chaos spreads (`Timid:0/0/0/252/4/252` → `timid`, `[0,0,0,252,4,252]`).
- **IVs aren't in chaos data,** so the decision layer assumes 31 in every stat.
- **Move shares sum to about 4** (each set has 4 moves); every other `usage` category sums to about 1.

## Still open
- 🟠 Nate's yes on building it to this shape, and where the file lives (proposed: `data/set_candidates.json`).
- 🟠 How sets are combined beyond "product of shares" (e.g. how many moves/items/spreads are tried per species).

## Optional coherent-template extension (Kenar-coherent-sets)

`CandidateSet.ivs` may supply six IVs in the same stat order, each 0–31. Existing
files without it retain all-31 behavior. This preserves source overrides such as
zero Attack; values describe sampled hypotheses, not observed opponent stats.
The importer validates all concrete variants against the pinned local Gen9 OU
TeamValidator. Choice items may legally have status moves (for example Trick);
the current builder already permits them. The earlier draft consistency line
above is historical and must not be used to reject those sets.

`data/curated-v1/priors.json` is an **opt-in** 50/50 coherent-template/broad-usage
experiment. It preserves the existing `usage` fallback and source structure.
Its separate manifest records template provenance, assumed completions and
mixture weights; neither these weights nor source role counts are measured joint
set frequencies. Duplicated role distributions are coalesced before weighting.
The normal `data/set_candidates.json` and default bot invocation are unchanged.
