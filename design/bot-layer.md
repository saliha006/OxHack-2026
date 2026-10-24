# Bot layer

> **DRAFT, not team-agreed.** Back to the map: [DESIGN.md](DESIGN.md).

**Job:** connect to a Showdown server, turn the battle log into a structured `BattleState`, ask the decision layer for
a `Choice`, and send it. It holds no strategy. **Stage 1** is done when it plays full games against a local Showdown server.

---

## 1. Flow per request

```
Showdown server ──log lines──► parser ──► BattleState ──► decision layer
       ▲                                                        │
       └───────────── "move N" / "move N terastallize" / "switch N" ◄── Choice
```

## 2. Observe: what the parser tracks

| Group | Fields |
|---|---|
| Actives | Species / forme, HP %, status, boosts |
| Field | Weather, terrain, hazards per side, screens, {{…}} |
| Revealed info | Per opp Pokémon: moves, item, ability, Tera seen so far; implied-item hints (Choice lock, Boots, no Leftovers heal) |
| Players | Names, start Elo (`|player|` line) |
| Request | Type (team preview / move / forced switch / wait) and legal options |

HP is a **percentage** in v1 (the opponent's exact HP is hidden anyway).

## 3. Request types

| Request | What we send | Notes |
|---|---|---|
| Team preview | Team order (picks the lead) | |
| Move | `move N`, `move N terastallize`, or `switch N` | Tera once per game |
| Forced switch | `switch N` | The opponent doesn't act |
| Wait | Nothing | |

## 4. Open decisions

These match the "four bot-skeleton choices" pending in PRD → §0 NOW:
- 🟠 **Framework:** write our own client, or build on an existing Showdown client library?
- 🟠 **Server:** a local Showdown server only, or also the public ladder? (The ladder brings rate limits and rules.)
- 🟠 **Format:** gen9ou only, or a simpler format first (e.g. random battles, no team building)?
- 🟠 **Bot ↔ decision contract:** the `BattleState` / `Choice` shapes ([DESIGN.md §2](DESIGN.md#2-seams-the-contracts-between-layers)).
- 🟠 **Our team:** a fixed team, or picked per game? Not covered in the pasted design yet.
