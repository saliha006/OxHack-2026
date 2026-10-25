I want you to implement and evaluate the data-independent MCTS improvements for our Gen 9 OU Pokémon Showdown bot. Create a persistent goal for this work using create_goal (no token budget requested), after checking whether this chat already has an active goal. Do not replace an unrelated unfinished goal. The objective is to complete the six stages below, their comparisons and their live documentation, while preserving the deferred data roadmap.

Repository: https://github.com/saliha006/OxHack-2026
Local checkout: /home/kenar/Documents/ChatGPT/oxhack 2026/OxHack-2026
Implementation branch: Kenar-mcts
Frozen current-MCTS baseline: 2c02fc8daa84f047ea2bddd7d0f36f6463fff1e2

Read applicable AGENTS.md and this complete handoff first:
/home/kenar/Documents/ChatGPT/oxhack 2026/OxHack-2026/docs/mcts-improvement-handoff.md
Also read docs/mcts-improvement-plan.md, the source, progress.md and the referenced implementation/results/evaluation docs. The handoff contains the old improvement plan verbatim: preserve every requirement, caveat, deferred workstream and pinned reference. The newer execution order takes priority over its historical ordering.

Implement in this order:
1. Accurate state reconstruction (PP, counters, effects, identities and continuation requests).
2. Reliable belief updates, separating confirmed facts from uncertain inference.
3. Better leads using our actual moves/stats and current priors.
4. Search-time allocation experiments at equal effort, then bounded adaptivity if justified.
5. Narrow strategic guards justified by reproduced failures and counterexamples.
6. Optional seeded mixing among near-tied supported moves.

Before behavior changes, freeze a runnable isolated baseline and record its effective source/engine/prior hashes. Current MCTS is eight whole-team worlds ×150 ms, one thread, three-second ceiling, mean normalised visit shares and deterministic choice. The existing mcts-current-pooled harness pairing compares against one-ply, NOT the required frozen MCTS; extend the harness as needed without contaminating baseline imports. Preserve legality, successful-world retention and deadline isolation.

For EACH change, compare against the original frozen MCTS and the previous accepted incumbent, holding other behavior and compute fixed. First stage can share these comparisons. Use targeted correctness fixtures, smoke gates, then at least 60 balanced screening games over at least ten fresh reserved teams per distinct comparison. Expand promising variants to 200+ confirmation games; counts alone do not guarantee significance. Freeze teams/seeds/stopping rules before outcomes; reserve fresh confirmation matches, and report actual resource use plus wins/intervals, targeted failure metrics, rejected choices, fallbacks and latency. Existing pilot teams are regression history. Mark unavailable or incomplete studies honestly; never invent results or holdout status. Keep unsuccessful heuristics disabled and record the decision. Do not mistake a correctness improvement for a demonstrated win-rate improvement.

Keep explaining the work live in simple language, and maintain docs/mcts-improvement-log.md plus compact experiment manifests/results in evaluation/mcts-improvements/. For every change explain: what was wrong, why the fix should help, exactly what changed, how it was tested, whether it helped, its uncertainty and whether enabled. Use a documentation subagent to maintain the narrative from actual artifacts while you own implementation/evaluation. Preserve rejected experiments too. Finish with a simple cumulative comparison against the original baseline.

My teammate is preparing richer curated set data. I explicitly paused the Tiger download/training: do not restart it while doing this work. Existing dirty/untracked Tiger setup files must be preserved, not reset or silently bundled into unrelated commits. Never expose credential files. Do not depend on the forthcoming data for these six stages.

Retain the deferred roadmap in full: coherent curated sets, recent full-roster matching, team-conditioned priors, joint compatible team sampling with fallback, no future-information leakage, separate full-set/roster identity, learned OU evaluation only after baseline wins and separate battle tests, and optional parallelism/pooling/risk experiments. These deferred tasks do not block completion of this six-stage goal; resume them only when new data/scope is supplied. Reuse teammates' A6 work if present rather than duplicating it.

Work autonomously through implementation, relevant tests, controlled evaluation and documentation. Make focused commits on the implementation branch, preserve unrelated work, and follow the full handoff's evaluation/promotion rules. Do not stop after proposing another plan. Mark the persistent goal complete only when the six-stage scope is actually handled, including honest outcomes for experiments that did not help; document any external blocker and continue independent work where possible.
