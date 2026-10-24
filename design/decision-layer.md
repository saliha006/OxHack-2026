# Decision layer

> **DRAFT, not team-agreed.** Back to the map: [DESIGN.md](DESIGN.md).

**Job:** given a `BattleState` from the bot layer, return the `Choice` with the best expected outcome. **The next build
target is stages 3–4** (strategy with dumb models, then the belief layer).

**Design goal:** every model (belief, opponent policy, value) can be swapped without touching the loop.

---

## 1. The loop

**Flow (Derrick, 2026-10-24):** the bot gets the latest state and sends the **whole state** to the strategy layer. The
strategy layer **updates its own beliefs first**, then uses what the data layer provides to arrive at an action.
So belief lives inside the strategy layer, not in the bot layer.

```ts
state  = observe(log)                       // bot layer
sets   = sampleOppSets(state, prior, k = 5)
scores = myActions(state).map(a =>
  sum(oppPolicy(state).map(([b, pB]) =>
    sum(sets.map(([s, pS]) => pB * pS * value(simulate(state, a, b, s)))))))
send(argmax(scores))                        // bot layer
```

1. **Believe:** for each opponent Pokémon, keep weighted candidate sets and sample the top k (3–5).
2. **Evaluate:** for each of our legal actions × each likely opponent action × each sampled set, simulate, score the
   result, and weight it by the probabilities.
3. **Act:** pick the highest expected value, breaking ties toward the better worst case.

**The loop (built 2026-10-24):** `Agent(priors).choose(request, battle) -> str | None`, one Agent per battle,
in `decision/agent.py`. Wait → `None`; team preview → `team 123456`; move request → belief update → top 5 scenarios →
`build_state` → our and their actions → `simulate` → `value` → `select` → `belief.chose`; forced switch → best next turn.

## 1a. What Showdown gives the decision layer (via the bot)

Full protocol detail: [bot-layer.md §1a](bot-layer.md#1a-what-showdown-sends-us-and-what-it-takes-back).

| Need | Where it comes from | Exact or estimated? |
|---|---|---|
| **Our legal actions** | `|request|`: `active[0].moves[]` with `disabled`, plus `trapped` / `maybeTrapped`, `canTerastallize`, and `side.pokemon[]` (not fainted, not active) for switches | Exact: Showdown works out legality for us |
| Which decision it is | Request kind: team preview / move / forced switch / wait | Exact |
| Our team: HP, stats, moves, item, ability, Tera | `side.pokemon[]` | Exact (`hp/maxhp`) |
| Opponent HP | `|-damage|` / `|-heal|` / `|switch|` | **Percent only** (`/100`) |
| Opponent moves, item, ability, Tera | Log lines as they're revealed | Partial → the **belief** step |
| Opponent stats, EVs, nature, unrevealed info | Never sent | **Belief** only |
| Opponent legal actions | Never sent | Must be **inferred** from belief (their moves, Tera used?, trapped?) |
| Field, hazards, boosts, status | Log lines | Exact once parsed |
| Turn order evidence (speed) | Order of `|move|` lines in a turn | Exact order; the speed itself is inferred |

**What this means for the design:**
- **Step 4 (our actions) is cheap.** We read them from the request instead of computing them.
- **Step 5 (their actions) is not.** Their legal set depends on belief: which moves they have, whether Tera is still
  available (we saw `|-terastallize|` or not), and whether they're trapped.
- **Belief updates need events, not only a snapshot.** Speed order and damage rolls only exist in this turn's log
  lines. This is why Q7 matters.
- **The output is a string** (`move N`, `move N terastallize`, `switch N`, `team …`). Slot numbers are 1-based and
  refer to the request's order.

## 2. Components

| Component | Input → output | v1 (dumb) | Later |
|---|---|---|---|
| **Belief** | state + priors → weighted sets per opp Pokémon | Chaos priors + hard filter | + soft Bayes reweight |
| **Opp policy** | state → `[action, p][]` | Uniform over legal actions | Trained on high-Elo replays |
| **Simulate** | state + our action + opp action + sets → next state | `@pkmn/sim` / `@smogon/calc`, one turn | 1–2 turn look-ahead |
| **Value** | state → score | HP + Pokémon remaining | Trained win probability |
| **Selector** | scores → `Choice` | argmax, tie-break on worst case | 🟠 see §6 |

🟠 **The interface shapes are the next design decision** (they are the "swap without touching the loop" contract).
Once agreed, they go in `contracts/`.

## 3. Belief (set prediction)

- **Prior:** the per-species candidates + weights from the data layer ([data-layer.md §5a](data-layer.md#5a-set-candidates--priors-per-species)).
- **Hard filter:** drop candidates that contradict revealed moves / item / ability / Tera, or an implied item (Choice
  lock, Heavy-Duty Boots on hazards, no Leftovers heal).
- **Soft reweight (Bayes):** speed order vs each candidate's speed stat, damage dealt / taken vs calc ranges, behaviour
  hints.
- **Output:** top k plus the "other" bucket.

## 4. Special cases

- **Team preview:** choose the lead. Known: opp's 6 species (some formes only as `Species-*`), level, gender, whether
  each holds an item, player names / Elo, our full team. Hidden: moves, item, ability, Tera, EVs/IVs/nature, their lead.
- **Forced switch after a faint:** switches only, and the opponent doesn't act.
- **Tera:** a once-per-game modifier on a move action, so each move has a Tera and a non-Tera variant.

## 5. Cost per turn

Simulate calls per turn ≈ **our actions × opp actions × sampled sets**. With ~4 moves × 2 (Tera) + ~5 switches on each
side and k = 5, that's roughly 13 × 13 × 5 ≈ 850 calls before any pruning. How many we can afford depends on the turn
budget (§6).

## 6. Open decisions

> **🟠 DECISION: how to choose under simultaneous moves**
> - **A, pure expected value** (as in §1): simple, uses the opp policy directly · ⚠️ exploitable if the policy is wrong
> - **B, minimax / worst case:** safe against any opponent · ⚠️ too cautious; ignores what opponents actually do
> - **C, blend:** EV with a weight on the worst case, or a mixed strategy from the payoff matrix · ⚠️ one more knob to tune
>
> **Recommendation:** A for stage 3 (it's the cheapest way to get end-to-end games), keeping the full payoff matrix so
> C can be added without changing the interfaces.

> **🟠 DECISION: enumerating and pruning actions**
> - **A, enumerate everything:** no logic to get wrong · ⚠️ ~850 sims per turn
> - **B, prune opp actions to the policy's top-n:** cuts the biggest factor · ⚠️ misses surprise plays (uniform v1
>   policy makes this useless until it's trained)
> - **C, prune by calc first:** drop clearly bad moves and Tera variants using `@smogon/calc` before full sims · ⚠️ needs
>   a "clearly bad" threshold
>
> **Recommendation:** start with A and measure; add C, then B once the policy is trained.

> **🟠 DECISION: turn-time budget**
> What's the per-turn budget, and so how many sets × opp actions fit? Needs a benchmark of one `simulate` call first.
> {{budget: not decided}}

## 7. Feature checklist

> **DRAFT list, not team-agreed.** One file per feature in [decision/](decision/). Each one has its job, input/output,
> build stage, open decisions and a "done when" check. Tick a box here when its file's "done when" passes.

Stages are the build order in [DESIGN.md §4](DESIGN.md#4-build-order-by-layer).

- [x] **[State intake](decision/01-state-intake.md)**: Stage 3 (built against the `BattleState` contract; needs a real parser)
- [ ] **[Set priors (load)](decision/02-set-priors.md)**: Stage 4
- [x] **[Belief: hard filter](decision/03-belief-hard-filter.md)**: Stage 4 (built on hand-made priors)
- [x] **[Belief: soft reweight](decision/04-belief-soft-reweight.md)**: Stage 4 (built on hand-made priors)
- [x] **[Sample opponent sets](decision/05-sample-sets.md)**: Stage 4 (built on hand-made priors)
- [x] **[Our actions](decision/06-our-actions.md)**: Stage 3 (built on `derrick`, not merged)
- [x] **[Opponent actions + policy](decision/07-opp-actions.md)**: Stage 3 uniform → Stage 5 trained (uniform built on `derrick`, not merged)
- [x] **[Simulate one turn](decision/08-simulate.md)**: Stage 2 (built on `derrick`, not merged)
- [x] **[Value function](decision/09-value.md)**: Stage 3 heuristic → Stage 5 trained (heuristic built on `derrick`, not merged)
- [x] **[Action selector](decision/10-selector.md)**: Stage 3 (built on `derrick`, not merged)
- [ ] **[Special requests](decision/11-special-requests.md)** (team preview, forced switch): Stage 3
- [x] **[Turn budget + fallback](decision/12-budget-fallback.md)**: Stage 3 (built on `derrick`, not merged)
