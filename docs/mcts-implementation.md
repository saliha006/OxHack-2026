# MCTS implementation and operating limits

`Agent(priors)` uses MCTS by default following the user's 25 October decision. Use `Agent(priors, backend="one_ply")` for the retained legacy comparison. The default searches eight independently sampled full-team worlds, 150 ms native search per world, one engine thread, and a three-second decision ceiling. `Agent.choose(request, battle)` is unchanged. Team preview still uses `pick_lead`; replacement requests use verified native replacement search.

Team preview defaults to the historical type scorer (`lead_policy="types"`). The
experimental `lead_policy="moves_stats"` uses supplied own moves/stats and public
opposing priors with traced, fixed heuristic weights. It approximates opening
damage, speed/priority, fragility and hazard/pivot/Taunt utility; it omits weather,
terrain, secondary effects, future switches and preview Tera. An explicit
`fixed_lead` option supports team-builder-intent tests. The optional policy remains
off by default until its separate game comparisons justify promotion.

`decision/search.py` wraps stock `poke-engine==0.0.48`, converts root visits/scores to Python records, and runs one persistent spawned worker per battle. Belief construction/update (including native evidence replay), state conversion and sequential native searches all execute in the child. The parent prepares its first legal fallback before search and starts its wall-clock deadline before preparation. It stops the worker at 2.7 seconds for a three-second budget, reserving 300 ms for mapping/return. Smaller budgets reserve ten percent. No one-ply evaluator is called on the MCTS failure path.

Each completed world is streamed immediately. Ordinary exceptions and PyO3 `PanicException` become structured world failures; OS-level native exit is contained by the process boundary. A stalled worker is terminated and, if necessary, killed with short bounded joins. Successful earlier worlds remain eligible. The next decision starts a replacement worker and explicitly records loss of accumulated soft inference; confirmed revelations are reapplied from its snapshot. A readiness handshake keeps the multi-megabyte prior payload out of the synchronous spawn bootstrap.

`decision/search_policy.py` normalises each usable world's root visits before pooling. Each sampled occurrence has equal mass, even if its draw probability or native iteration count differs. An explicit enumeration mode uses scenario weights instead. Engine names map to the request's move/party slots, then intersect with `our_actions(request)`. Surviving support is renormalised and the request's stable action order breaks ties. Unsupported/ambiguous choices and zero visits are diagnostic failures. The output is search support, with no calibration claim. Opponent visit distributions are retained separately; they do not reweight our search.

`mix_root=False` preserves that deterministic default. Optional MCTS-only
`mix_root=True` uses `decision/root_mixing.py` to sample a sufficiently mature,
supported near-tied pair of legal non-Tera moves. Switch/Tera winners, diffuse
roots and inadequate or failed mapping evidence retain the deterministic choice.
Its persistent `mix_seed` RNG is separate from world sampling. `root_mixing`
traces retain eligibility/decline reasons, probabilities, draw, seed and
original/final action; worker replay records the final action. This heuristic is
off pending controlled evaluation, with no equilibrium or exploitation-resistance
claim. Fixed gates and verification are in the [staged record](mcts-improvement-log.md).

`last_trace` contains requested, scheduled, completed, interrupted, failed and usable world counts; full sampled set records; native our/opponent root visits; pooled support; preparation, native search, worker wall and total timings; worker history reset; chosen action; mappings, recovery reasons and state approximations. Requested settings alone are not actual compute measurements. Battle logs retain exact requests and link decisions to subsequent observed root replies; forced replacements/pivot followups are separate and missing root actions remain unknown. Rejected choices invalidate the planned action used by next-turn belief replay.

Belief hard revelations are never restored by the noisy evidence likelihood floor. Missing/empty priors, incompatible inferred rules and failed native replay use explicit recovery paths. The missing-species emergency set preserves known details and otherwise uses neutral DEX estimates and a recorded Tackle placeholder; it is not presented as a real OU set. Real priors cover 321 species/aliases from September 2026 OU at 1825 cutoff. Whole-team sampling remains independent between teammates.

The staged reliability change makes `Agent` use `belief_mode="reliable"` by
default. It separates direct revelations from guarded item deductions and soft
damage/speed replay, with explicit removal, skip and recovery diagnostics.
Called/forced moves, incomplete intervals and item/ability changes do not become
unsupported hard evidence. `belief_mode="legacy"` retains the earlier inference
rules; `belief_mode="revelations"` keeps direct facts only. Direct `Belief`
construction retains its legacy default for ablation. The likelihood floor
remains 0.03. This default is a correctness decision on reproduced defects;
the [staged record](mcts-improvement-log.md) tracks separate game comparisons and
does not claim an established strength gain.

The frozen-belief MCTS ablation keeps the same persistent hard filtering and inferred item rules but disables soft damage/speed replay. This isolates the value of those noisy likelihood updates. Neither learned evaluation nor opponent visit weighting is added to search. See the adapter audit for remaining native mechanics, hidden PP and duration limitations, and the evaluation document for measured results and reproducible configurations.

The prediction workstream is separate: its model supplies observed-state predictions and evaluation output. Loading a learned model into MCTS search remains a separate experiment requiring its own measured comparison.
