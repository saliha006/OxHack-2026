# Predictions

> **DRAFT, not team-agreed** (Derrick, 2026-10-24). Back to [decision-layer.md](decision-layer.md).

Every guess the decision layer makes about something it can't see: what it predicts, how, what data it uses, and
whether it's built. Status is as of `derrick` @ `a50936e`. For live test counts see `progress.md` → 📊 Latest.

**Status key:** ✅ built · 🟡 built in a simpler form · ⬜ planned (in the design or a decision) · 💡 new idea, **not
agreed**. Each 💡 needs the team's yes before anyone builds it (CLAUDE.md §2c).

**Where it enters the search** refers to the columns of the move-turn tree: our action → their set → their reply →
outcome → value.

---

## A. Their hidden team (belief, the "their set" column)

| # | Prediction | How | Data | Status | Next step |
|---|---|---|---|---|---|
| A1 | **Their set** (moves, item, ability, Tera type, spread) per species | Prior: a weighted list of candidate sets, top 20–50 per species | Metamon `replay_stats` joint sets, then chaos marginals with consistency rules ([data-layer §5a](data-layer.md#5a-set-candidates--priors-per-species)) | 🟡 belief runs on **hand-made** priors. The loader (feature 02) and the real prior file aren't built | Data layer produces the file (@saliha); decision layer loads it (feature 02) |
| A2 | **Rule out sets that contradict what we saw** | Hard filter, every turn | The battle log | ✅ Revealed move / item / ability / Tera; `[from] item:` lines; 2+ different moves since switching in → not Choice; a status move → not Assault Vest; no Stealth Rock damage → Boots (or Magic Guard); damaged with no heal → not Leftovers | Gaps: Choice lock seen from repeated moves; Life Orb recoil; Focus Sash |
| A3 | **Their speed**, from who moved first | Replay last turn in poke-engine with each candidate; drop it if the engine can't produce the observed order | Turn order in the log | 🟡 a pass/fail filter, not a weighting | See A5 |
| A4 | **Their attack / bulk**, from damage | Same replay, checked against the engine's damage range for both hits | HP % change in the log | 🟡 a pass/fail filter. Multi-hit moves are skipped until `BattleState` carries hit counts (parked: contract `hit_count`) | See A5 |
| A5 | **Graded likelihood** instead of pass/fail | Bayes: weight each set by how likely it makes the observed roll / order, not just whether it's possible | Same as A3–A4 | ⬜ in the design ([decision-layer §3](decision-layer.md#3-belief-set-prediction)) | Needs the damage-roll distribution from the engine |
| A6 | **Sets from their teammates** (e.g. a rain setter makes Swift Swim sets likelier) | Starting sets per opponent Pokémon from past games whose teams match theirs. Fallback: all 5 teammates must match, then one fewer at a time until at least N games match; at 0 it's A1's general priors | Replays with both teams visible (2.47M games) | ⬜ **agreed 2026-10-25** (derrick; proposed by nate) | @nate builds it after the demo and picks N. Hand-off is a function of their six at team preview: shape TBC between nate and derrick |
| A7 | **Benched Pokémon's sets** | Each benched Pokémon is fixed at its single best guess; only the active gets k = 5 sets | A1 | ✅ (a cost choice, so the search stays at k scenarios) | Revisit if switch-ins keep surprising us |
| A8 | **Behaviour hints** (they switched out of X, so they fear it) | Reweight sets or the policy from their choices | Replays | ⬜ named in decision-layer §3, no design | Probably folds into B2 |

## B. Their next action (the "their reply" column)

| # | Prediction | How | Data | Status | Next step |
|---|---|---|---|---|---|
| B1 | **Their legal options** | The sampled set's moves (revealed first), minus disabled / no-PP / Choice-locked; a Tera copy of each move if they haven't used Tera; every living benched Pokémon as a switch | A1 + the log | ✅ We can't see if they're trapped, so switches are always offered | None |
| B2 | **Which option they pick** (move, Tera or not, switch) | Policy: odds per option given the state | (state, action actually taken) pairs from high-Elo replays ([data-layer §5b](data-layer.md#5b-training-sets)) | 🟡 uniform; a move's Tera copy splits that move's share | ⬜ Stage 5 trained policy. Elo threshold not decided |
| B3 | **Who they switch in** | Part of B2's output, so no separate model | Replays: switch-ins given the matchup | 🟡 uniform across the bench | Comes free with B2 if the policy's output covers switch targets |
| B4 | **Their lead** at team preview | Lead frequency per species, ideally given their six | Replays: turn-1 actives | 💡 | Only matters if our lead pick uses it (D1) |
| B5 | **Pruning their options** | Keep the policy's top-n, never dropping the replies worst for us | B2 | ⬜ decided 2026-10-24: only after B2 is trained | None until B2 |

## C. How the turn plays out (the "outcome → value" column)

| # | Prediction | How | Data | Status | Next step |
|---|---|---|---|---|---|
| C1 | **Turn outcomes**: damage rolls, crits, accuracy, speed ties, secondary effects | poke-engine `generate_instructions` gives every outcome with its probability | Game rules (the engine) | ✅ | None |
| C2 | **How good a position is** | Stage 3: each Pokémon worth 1 alive + its HP fraction, scaled 0–1 | None | 🟡 heuristic | ⬜ Stage 5 trained win probability, same 0–1 scale |
| C3 | **Two turns ahead** | Recurse the search one more ply | Same as C1–C2 | ⬜ "later" in decision-layer §2 | Only if the turn budget allows it (needs p50/p99 timings) |

## D. Our own choices that rest on a prediction

| # | Prediction | How | Data | Status | Next step |
|---|---|---|---|---|---|
| D1 | **Best lead** | Code: the lead whose best STAB hit beats theirs by the most, averaged over their six | Showdown typechart + pokedex (static) | ✅ built; PRD → NOW confirms the type-matchup lead | Could use B4 if that's agreed |
| D2 | **Best switch-in** after a faint | Run the move-turn search as if each bench Pokémon were in, keep the best | Same as the main search | ✅ matches the 2026-10-24 decision (reuse the loop, opponent's only option `None`) | Score by post-switch value once C2 is trained |
| D3 | **Pruning our options** | Tera only on the top few moves by damage; always keep switches and one or two status moves | C1 | ⬜ decided 2026-10-24: only if p99 turn time nears the 3 s budget | Measure p50/p99 first |

## E. The player

| # | Prediction | How | Data | Status | Next step |
|---|---|---|---|---|---|
| E1 | **This player's habits** | Tilt B2 toward what this opponent usually does | Per-player replay history | 💡 weak: Metamon pseudonymises usernames, and players at the event have no history | Park unless someone finds a source |

---

## Suggested order

1. **A1, real priors.** Every column right of "our action" depends on them (A2–A8, B1, C1), and today they're hand-made.
   This needs the data layer's prior file (@saliha) plus feature 02.
2. **B2, trained opponent policy.** Replaces the uniform ⅓ that sits under every set we guess; B3 and B5 come with it.
3. **A5, graded likelihood.** Turns the existing replay check into proper weights; no new data.
4. **C2, trained value.** Biggest effect on what the leaves score, but it needs the most training data.

Not agreed, raise with the team first: B4 lead prediction, E1 player habits.
