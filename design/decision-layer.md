# Decision layer

> **DRAFT, not team-agreed.** Back to the map: [DESIGN.md](DESIGN.md).

**Job:** given a `BattleState` from the bot layer, return the `Choice` with the best expected outcome. **The next build
target is stages 3–4** (strategy with dumb models, then the belief layer).

**Design goal:** every model (belief, opponent policy, value) can be swapped without touching the loop.

---

## 1. The loop

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
