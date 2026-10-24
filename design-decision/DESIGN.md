# Gen 9 OU battle agent: design overview

> **DRAFT, not team-agreed.** The three-layer split is still Pending in the PRD → §0 NOW (owner saliha; needs Nate and
> Derrick, CLAUDE.md §2c). Nothing here is a decision until it shows up in PRD → NOW → Decisions in force.

A decision-making agent that plays Pokémon Showdown **Gen 9 OU** (`gen9ou`). Each turn it reads the battle log, works out
what the opponent probably has and will do, simulates the options, and picks the move with the best expected outcome.

This file is the map. Each layer has its own doc:

| Layer | Doc | Owns | Question it answers |
|---|---|---|---|
| **Data** | [data-layer.md](data-layer.md) | Sources, ingestion, storage, offline priors, training sets | "What has happened in past games, and who played them?" |
| **Decision** | [decision-layer.md](decision-layer.md) | Belief, opponent policy, simulate, value, action selector | "Given this state, what should we do?" |
| **Bot** | [bot-layer.md](bot-layer.md) | Showdown connection, log parsing, state, sending choices | "What is the state right now, and how do we act on it?" |

---

## 1. How the layers fit

```
             OFFLINE                                   ONLINE (per turn)
 ┌─────────────────────────────┐        ┌──────────────────────────────────────────┐
 │ DATA LAYER                  │        │ BOT LAYER                                │
 │ replays · ladder · chaos    │        │ Showdown socket → log lines → observe()  │
 │   → ClickHouse              │        │            │                 ▲           │
 │   → set candidates + priors ├──┐     │      BattleState          Choice         │
 │   → training sets ─┐        │  │     └────────────┼─────────────────┼───────────┘
 └────────────────────┼────────┘  │                  ▼                 │
                      ▼           │     ┌──────────────────────────────┴───────────┐
           Python training        └────►│ DECISION LAYER                           │
           (opp policy, value) ────────►│ belief → oppPolicy → simulate → value    │
             exported models            │        → action selector                 │
                                        └──────────────────────────────────────────┘
```

- **Data → Decision** happens offline, through artifacts: set candidates + prior weights per species, and the trained
  model files. The decision layer never queries ClickHouse in the middle of a turn.
- **Bot ↔ Decision** happens online, through two types: `BattleState` in, `Choice` out. That seam lets each side be
  built and tested on its own (replay a log into the decision layer; drive the bot with a random chooser).

## 2. Seams (the contracts between layers)

Exact shapes go in `contracts/` once agreed. For now these are just their names and who produces them.

| Seam | Producer → consumer | What crosses | Status |
|---|---|---|---|
| `BattleState` | Bot → Decision | Actives, HP %, status, boosts, field, hazards, revealed info, request type | Drafted: `contracts/battle-state.md` |
| `Choice` | Decision → Bot | `move N`, `move N terastallize`, `switch N`, team order | `agent.choose()` returns it as a string |
| Set candidates + priors | Data → Decision | Per species: top 20–50 sets with weights, plus an "other" bucket from marginals | Drafted: `contracts/set-candidates.md` |
| Model artifacts | Python training → Decision | Opponent policy, value model | 🟠 export format not decided |
| Battle rows | Ingestion → ClickHouse | `battles` keyed on replay id; `players` from ladder snapshots | 🟠 schema not decided |

## 3. Stack (as proposed)

- **Python** throughout. The decision layer runs on `poke-engine` 0.0.48 (built, on `main`); it replaced the earlier TypeScript `@pkmn/sim` idea.
- **Bot framework:** poke-env 0.16.1 on gen9ou, local server (decided 2026-10-24, research pass 8).
- **Storage:** 🟠 pending (ClickHouse vs lighter files).

The stack's home is PRD §12.

## 4. Build order (by layer)

| Stage | What | Layer | Done when |
|---|---|---|---|
| 1 | Log parser + state representation | Bot | Plays against a local Showdown server |
| 2 | Simulator wrapper over `@pkmn/sim` / `@smogon/calc` for one-turn outcomes | Decision | Given state + both actions + a set, returns the next state |
| 3 | Strategy layer with dumb models: uniform opp policy, HP-based value | Decision | Plays legal games end to end |
| 4 | Belief layer: chaos priors + hard filter, then soft reweight | Decision (+ Data for priors) | Candidate sets narrow as info is revealed |
| 5 | Trained opponent policy, then value model | Data → Decision | Beats the stage-3 bot over N games ({{N}}) |

**Next up: stages 3–4.** The open questions are in [decision-layer.md §6](decision-layer.md#6-open-decisions).

## 5. Scope for v1

- **Learned:** opponent action distribution; state value / win probability.
- **Computed, not learned:** hidden sets (lookup + Bayes), damage / KO chance, turn order.
- **Left open in v1:** exact EVs/nature (assume a common spread), exact HP (use %), crits/secondaries (expected value),
  per-player style, look-ahead beyond 1–2 turns, merging alts.
- **Time-boxed fallback:** a heuristic value (HP + Pokémon remaining + rating prior), with all the learning effort on
  the opponent action model.

## 6. Open questions across layers

- How does this bot relate to the PRD's lead idea (Momentum: win probability + coach-style replay review)? Is the value
  model shared between them? Owner saliha.
- Who owns which layer? (→ `progress.md` 👥 Team once agreed.)
