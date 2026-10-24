# Action selector

> Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick`, not merged.

**Job:** combine the scores and pick one choice.

| | |
|---|---|
| **Input** | `scores[our action][opp action][opp set]` + opponent action probabilities + set probabilities |
| **Output** | One `Action` |
| **Build stage** | Stage 3 |
| **Owner** | Derrick |
| **Code** | `decision/selector.py` · tests `tests/test_selector.py` |

## Interface
```python
def select(scores, set_probs, opp_probs) -> Action
# scores[our action][opp set][opp action] = value; opp_probs[set][opp action] = p(action | set)
# EV = Σ p(set) · Σ p(action | set) · value  (expected_value() is public for the loop)
```

## Decisions (Derrick, 2026-10-24)
1. **Rule:** highest expected value, `Σ p(opp action) · p(set) · value`. Ties go to the better worst case.
2. **Input:** the full 3-D table, so the worst case covers both the worst opponent action and the worst set.
3. **Final tie:** the first action in `scores` order (that is, `our_actions` order). Deterministic, so runs repeat.

4. **Opponent odds per set** (Derrick, 2026-10-24): their options differ by set (Choice lock, Taunt, Struggle), so
   `opp_probs` is given per set rather than once for all sets.

## Rules (one right answer)
- The worst case only counts outcomes with probability > 0.
- Ties use `math.isclose(rel_tol=1e-6, abs_tol=1e-6)`: poke-engine's probabilities are 32-bit, and values are on 09's 0–1 scale.
- An empty table raises `ValueError`. It can't happen in play, since `select` is never called on a wait request.

## Later (not decided)
- A blend `(1-w)·EV + w·worst`, or a mixed strategy. The table is already the full payoff matrix, so adding one won't change the interface.

## Done when
- [x] Picks the argmax on hand-built score tables
- [x] Keeps the full payoff table so a blend can be added later
