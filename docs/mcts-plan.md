Implement MCTS as an alternative decision backend, keeping the current agent available for comparison. The first version should use stock `poke-engine`, the existing belief updates and real OU priors. Add learned evaluation and more sophisticated opponent modelling only after measuring that version.

The first milestone is a legal, deadline-safe OU MCTS agent with results against the existing agent. A calibrated win-probability model can be developed separately for the prediction deliverable.

**1. Stabilise the existing inputs**

Inspect the current branch, `progress.md`, beliefs and installed engine before making changes. Confirm which failures reported in the notes remain unresolved.

Check and fix:

- Missing-species and forme lookups, including battle-only formes.
- `calculate_damage` results containing only one value.
- Empty collections reaching `max()` or normalisation.
- `_rebuild()` rejecting status moves on Choice sets: Choice Scarf + Trick is valid; Assault Vest prevents selecting status moves.
- Candidate rebuilding losing revealed moves, items, abilities or Tera information.

Use a small likelihood floor for noisy damage and speed evidence so an imperfect observation cannot collapse the distribution. Confirmed revelations remain hard constraints; the floor must not restore sets that contradict them.

If no candidate survives, use an explicit recovery path that preserves known facts and records why recovery was needed.

Validate and reuse the real OU priors. Verify that the installed `poke-engine==0.0.48` build supports Gen 9 and Terastallization.

**Acceptance:** existing tests pass; focused fixtures cover these failures; a short smoke run reports fallback frequency and reasons.

**2. Verify the essential state adapter before comparing search strength**

MCTS needs a state that remains meaningful over future turns. Check the fields that determine immediate legal actions first:

| Area | Required behaviour |
|---|---|
| Moves | Carry disabled moves, remaining PP and Choice/Encore restrictions correctly |
| Switching | Represent forced replacement, trapping and active-slot order correctly |
| Terastallization | Preserve transformed Pokémon and whether each side has spent its resource |
| Revealed information | Keep known moves, items, abilities and relevant effects consistent with observations |

Verify the installed engine’s action encoding and forced-switch behaviour directly.

Keep team preview on `pick_lead()`. Replace the current hypothetical-next-turn forced-switch workaround only after the engine’s replacement search is verified.

**Acceptance:** known states produce legal actions, including used Tera, Choice lock and forced replacement; reordered team slots map to the correct Pokémon.

**3. Add a small MCTS wrapper and backend flag**

Create `decision/search.py`, responsible for:

- Calling the installed engine’s MCTS interface.
- Converting native results into ordinary Python records.
- Returning our root action visits and, where available, the opponent’s root visits.
- Recording elapsed time, total visits and failure information.
- Handling an unsuccessful world without discarding successful worlds.

Keep `Agent.choose(request, battle)` unchanged. Add a backend option such as `one_ply` or `mcts`, retaining the current implementation as the comparison arm.

Account for the installed binding’s native panic behaviour as well as ordinary Python exceptions. Process isolation should also contain native crashes.

Initially allow MCTS to consider every action the engine represents as legal. Do not remove setup, recovery, Protect or switches because the one-turn evaluator gives them a poor score.

**Acceptance:** one known engine state produces a result that maps to a legal Showdown action; failures produce structured diagnostics.

**4. Add worker deadlines and traces before running games**

Use one persistent worker process, searching worlds sequentially. The parent must remain able to enforce the deadline and return a choice if native search stalls.

Return each completed world’s result immediately so replacing a stalled worker does not lose earlier results.

Starting settings:

| Setting | Initial value |
|---|---|
| Worlds | 1 during integration; 8 for the first pooled version |
| Search per world | 150 ms |
| Engine threads | 1 initially; benchmark 2–4 afterward |
| Overall decision budget | Planned 3 seconds, confirmed against the caller |
| Time reserved for returning a choice | Approximately 300 ms |
| Final randomisation | Disabled |
| Learned reranker | Disabled |

These are tuning defaults, not performance claims. More engine threads may increase search work within a world; do not assume they divide sequential wall time by the thread count.

Start the deadline before state preparation. Stop scheduling worlds when insufficient time remains.

Prepare a cheap legal fallback before search. Use completed results when available. If none are usable, return the fallback. Only invoke the existing evaluator as a fallback when sufficient time remains and it is covered by the same deadline.

Populate `last_trace` with:

- Backend, configuration and sampled worlds.
- Requested, completed, failed and usable world counts.
- Our visits, opponent visits and pooled support.
- State preparation, search and total decision timings.
- Chosen action, mapping failures and fallback reasons.

Link the opponent action observed afterward to the preceding decision. Record unobserved actions as unknown—for example, when the opponent faints before acting.

**Acceptance:** a deliberately stalled worker cannot prevent a choice from being returned; successful worlds survive partial failures; traces connect decisions with subsequent observations.

**5. Run an early integration comparison**

Once single-world search is legal and deadline-safe, run a small comparison against the current agent using matched teams, balanced sides and recorded compute settings.

Use this run to find integration failures and large regressions. Inspect positions where the agents disagree, especially setup, recovery, switching and Tera decisions.

This is an integration gate, not sufficient evidence of a strength improvement. If MCTS performs poorly, investigate state conversion, action mapping and failures before adding complexity.

**Acceptance:** games complete, choices are legal, deadlines hold, and disagreements can be explained from traces.

**6. Sample hidden sets across the whole team**

Add `Belief.sample_worlds(n, rng)` alongside the existing `scenarios()` method.

For each world:

- Keep all six species fixed to team preview.
- Sample each Pokémon’s complete set using its current candidate weights.
- Apply revealed moves, items, abilities and Tera information.
- Retain existing damage and speed evidence updates.
- Record the sampled configurations for debugging.

Start with independent sampling between Pokémon. Sampling all six addresses bench uncertainty; conditioning a Pokémon’s set on its teammates is a separate improvement.

Because worlds are sampled according to their probabilities, give each sampled occurrence equal weight during aggregation. Do not multiply by its prior probability again.

If explicitly enumerated scenarios are used instead, combine them using their scenario weights. Keep these two aggregation modes distinct.

**Acceptance:** sampling respects revelations, approximates candidate frequencies, reproduces worlds with the same seed and does not mutate beliefs.

**7. Pool results and select a legal action**

Create `decision/search_policy.py`.

For each successful sampled world, normalise our root visits:

\[
p_w(a)=\frac{N_w(a)}{\sum_b N_w(b)}
\]

Average these distributions across usable worlds. This prevents a world receiving more influence simply because its search completed more iterations.

Then:

- Translate engine choices into existing `Action` objects.
- Intersect them with `our_actions(request)`.
- Renormalise surviving scores.
- Choose the highest-scoring action with a stable tie-break.

Ignore unusable results while recording their failure reasons. Record when filtering leaves no supported legal action.

Call the aggregated output **search support**. Visit shares are not calibrated win probabilities.

Retain the opponent’s root distribution for later evaluation. Do not use it to introduce a separate opponent-weighting mechanism into the first version.

**Acceptance:** mapping checks cover switches, reordered teams, Tera, Struggle, rejected options, zero-visit results and partial search failures. Pooling checks distinguish sampled worlds from weighted enumerated scenarios.

**8. Complete the adapter audit**

Before the main strength evaluation, extend coverage to effects that change future turns:

- Relevant status and volatile-effect counters.
- Wish and Future Sight.
- Weather, terrain, screens and other supported durations.
- Substitute and other partially observed state.

Preserve known information and explicitly represent estimates. Exact opponent PP, remaining durations and Substitute HP may be uncertain; record the approximation.

Document the remaining limitations so evaluation failures can be interpreted.

**Acceptance:** focused replay fixtures cover delayed attacks, persistent effects and uncertain observations without silently treating estimates as facts.

**9. Evaluate before making MCTS the default**

Extend `bot/eval.py` with:

| Comparison | What it tests |
|---|---|
| MCTS versus current agent | Whether the new backend improves practical performance |
| One versus eight worlds, equal total search time | How to divide compute between depth and hidden-state coverage |
| One versus eight worlds, equal time per world | Effect of additional worlds with additional compute |
| Active-only versus whole-team sampling | Value of representing bench uncertainty |
| Frozen versus updated beliefs | Value of inference during battle |
| MCTS versus Foul Play | Performance against an established search opponent |

Use held-out teams, balanced sides and matched practical compute budgets. Record engine version, world count, per-world budget, threads and concurrent games.

Track win rate with confidence intervals, rejected choices, fallbacks, failed worlds and p50/p95/p99 decision latency. Report actual search time and completed worlds alongside requested settings.

Use deterministic checks for sampling and pooling. For native MCTS, measure action agreement across repeated positions rather than requiring identical visit counts or choices.

Keep the default backend behind a flag until the larger comparison supports switching. If results are inconclusive, retain both and report the uncertainty.

**Acceptance:** a reproducible evaluation configuration, results with intervals, latency and reliability measurements, and a documented default-backend decision.

**10. Develop prediction outputs separately**

If the prediction prize remains a target, add a separate workstream:

- **Win probability:** train a simple model over observed `BattleState` features, using the same featurizer during training and serving. Evaluate against constant and HP-only baselines using log loss, Brier score and calibration plots.
- **Belief quality:** measure next-reveal log loss against the original OU prior and a hard-filter-only baseline. Report full-set coverage only where ground truth is available.
- **Opponent actions:** score MCTS opponent visit shares against uniform using observed replies. Specify smoothing for zero probabilities and distinguish bot-game results from human-replay results.

Use held-out battles, time-based splits and controls for repeated players or teams. Fit calibration only on validation data.

The win-probability model initially supplies predictions and display output. Adding it to search requires a separate experiment.

**Delivery order:** belief fixes and traces → essential adapter checks → single-world MCTS with worker deadlines → small integration comparison → whole-team sampling and pooling → remaining adapter coverage → full comparative evaluation.

**Deferred experiments:** teammate-conditioned priors, learned search evaluation, Python beam search, parallel worlds, mixed strategies and additional opponent models. Each should have its own measured comparison after the baseline is established.