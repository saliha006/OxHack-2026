# Bot layer

> **Implementation audit: 25 October 2026.** Read [CURRENT-STATUS.md](../CURRENT-STATUS.md) for the exact branch
> snapshot and measured evidence. Back to the map: [DESIGN.md](DESIGN.md).

**Job:** connect to a Showdown server, turn the battle log into a structured `BattleState`, ask the decision layer for
a choice string, and send it. Strategy lives in the decision layer. Local complete-game play is implemented;
the protocol discussion below is retained as a historical reference, not a claim that every listed mechanic is
fully represented by our parser.


## Current implementation (25 October 2026)

The bot layer is shipped on `main` at `bbb95d6`, not a proposed skeleton:

- **Connection and decisions:** `bot.player.AgentPlayer` uses **poke-env 0.16.1**, feeds raw protocol lines to our
  `Parser`, and creates one decision `Agent` per battle. Each new request calls `agent.choose(request, snapshot)`.
  It logs raw battle lines, JSONL decisions with public state and think time, and decision errors. Rejected
  requests retry with a legal fallback, then `default`; outer message failures also have a default-choice path.
- **Seams are implemented:** `contracts/battle_state.py` defines public state and last-turn events;
  `decision.actions.Action.to_choice()` emits choices. A wait produces no choice. Parser output and the private
  request remain separate inputs, rather than replacing the private request with a merged public-only state.
- **Smoke and demo:** `bot.smoke` runs complete local games against RandomPlayer. `bot.demo live` streams decisions
  to the terminal and prints a local Showdown spectator URL; `bot.demo replay` renders a saved JSONL trace offline.
  This is a terminal/live-client demo, not a shipped coaching dashboard.
- **Evaluation:** `bot.eval` supports seeded, sharded, resumable pairings, belief/uncertainty ablations,
  Random/MaxBasePower/SimpleHeuristics baselines and optional separately installed Foul Play bots. Reports include
  win rate, Wilson and team-bootstrap intervals, fallback rates and latency, plus internal Bradley–Terry ratings.
  A scheduled pairing or fitted internal rating is not a measured public-ladder result.
- **Defaults differ by branch:** `main` still uses legacy one-ply `Agent` with five belief scenarios, uniform
  opponent replies and HP/alive value. Pushed `Kenar-mcts` at `2c02fc8` defaults its Agent, smoke and demo to MCTS
  (8 hidden worlds ×150ms, one native thread, 3s Agent budget); legacy one-ply remains selectable and old evaluation
  arms remain available. Further local MCTS corrections and opt-in policies are documented in CURRENT-STATUS.
- **Demonstration has limits:** the legacy progress log records 10/10 RandomPlayer smoke wins with **12.7%**
  fallbacks before later belief fixes. Treat that as a dated plumbing result, not present reliability or evidence
  of strong-opponent performance. Team-derived exact priors are a smoke option and can reveal the answer in a
  mirror match. Use the branch-specific evaluation artifacts for current measured comparisons.

Pinned sources: [player/session integration](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/bot/player.py),
[parser](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/bot/parser.py),
[demo](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/bot/demo.py),
[evaluation](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/bot/eval.py),
[MCTS-default Agent](https://github.com/saliha006/OxHack-2026/blob/2c02fc8daa84f047ea2bddd7d0f36f6463fff1e2/decision/agent.py),
[MCTS smoke flags](https://github.com/saliha006/OxHack-2026/blob/2c02fc8daa84f047ea2bddd7d0f36f6463fff1e2/bot/smoke.py).

**Remaining scope:** independently validated team-pool/demo selection and any public-ladder deployment require
separate evidence. The request-free Tiger replay backtest is on Derrick's branch and is a CLI; see
[Backtesting](backtesting.md). Historical unchecked choices below are superseded where the current source answers
them. Unimplemented product features stay pending.

---

## 1. Flow per request

```
Showdown server ──log lines──► parser ──► BattleState ──► decision layer
       ▲                                                        │
       └───────────── "move N" / "move N terastallize" / "switch N" ◄── Choice
```

## 1a. What Showdown sends us and what it takes back

Checked 2026-10-24 against `sim/SIM-PROTOCOL.md`, `sim/SIMULATOR.md` and the sim source (`side.ts`, `pokemon.ts`,
`battle-actions.ts`) on `smogon/pokemon-showdown` master. Sources: §5.

**Showdown never sends us "the state".** It sends two things, and we build the state ourselves:

| Stream | What it is | Who sees it |
|---|---|---|
| **Battle log lines** (`|move|`, `|-damage|`, …) | Events as they happen | Everyone; our own HP exact, the opponent's as `%/100` |
| **`|request|` JSON** | What *we* must decide now, plus our own full team | Only us (a `sideupdate` in the sim) |

### The request (one of four kinds)

| Kind | How to tell | Key fields |
|---|---|---|
| Team preview | `teamPreview: true` | `side`, `maxChosenTeamSize?` |
| Move | `active` present | `active[]`, `side` |
| Forced switch | `forceSwitch: boolean[]` | `side` |
| Wait | `wait: true` | `side` (send nothing) |

All four can carry `noCancel?`. On a real server there's also `rqid`, which we echo back. The sim used directly doesn't send it.

**`active[i]`** (our active Pokémon, move requests only):
- `moves[]`: `{ move, id, pp, maxpp, target, disabled }`
- Optional flags: `trapped`, `maybeTrapped`, `maybeDisabled`, `maybeLocked`, `canTerastallize` (the Tera type, when Tera is still available)

**`side.pokemon[]`** (our whole team): `ident`, `details`, `condition` (`"hp/maxhp status"`, or `"0 fnt"`), `active`,
`stats` {atk, def, spa, spd, spe}, `moves`, `baseAbility`, `item`, `pokeball`, `ability`, and in Gen 9 `teraType` and
`terastallized` (`''` if not).

### The log lines we need to parse

| Group | Lines |
|---|---|
| Setup / preview | `|player|p1|NAME|AVATAR|RATING`, `|teamsize|`, `|gen|`, `|tier|`, `|rule|`, `|clearpoke`, `|poke|PLAYER|DETAILS|ITEM` (ITEM = `item` or blank; unknown forme = `-*`), `|teampreview`, `|start` |
| Turn flow | `|turn|N`, `|upkeep`, `|faint|`, `|win|USER`, `|tie` |
| Actions | `|move|POKEMON|MOVE|TARGET`, `|switch|` / `|drag|POKEMON|DETAILS|HP STATUS`, `|cant|`, `|detailschange|`, `|-formechange|`, `|replace|` (Illusion) |
| Effects | `|-damage|`, `|-heal|`, `|-status|`, `|-curestatus|`, `|-boost|`, `|-unboost|`, `|-weather|`, `|-fieldstart|`/`end`, `|-sidestart|`/`end` (hazards, screens), `|-item|`, `|-enditem|`, `|-ability|`, `|-activate|` |
| Tera | `|-terastallize|POKEMON|TYPE`; after that, `DETAILS` gains `, tera:TYPE` |
| Errors | `|error|[Invalid choice] …` / `[Unavailable choice] …`, followed by a fresh `|request|` |

Revealed info for the belief layer comes mostly from `|move|`, `|-item|`/`|-enditem|`, `|-ability|`, `|-terastallize|`,
and the `[from]` tags on `|-damage|`/`|-heal|` (for example, Leftovers).

### What we send back

| Request | Choice | Notes |
|---|---|---|
| Team preview | `team 213456` | Order of slots; first = lead |
| Move | `move N` (1-based slot or move name), `move N terastallize`, `switch N` (1-based team slot) | Singles = one choice |
| Forced switch | `switch N` | |
| Any | `default`, `undo` (before the opponent chooses) | |

On a server: `/choose <choice>|<rqid>`. In the sim: `>p1 <choice>`. ⚠️ Check the exact `terastallize` spelling against a
local server before relying on it.

### Libraries that already do this parsing
- **`@pkmn/protocol`:** typed parsing of protocol lines into a `Handler`.
- **`@pkmn/client`:** a `Battle` that tracks "all known information about a battle" from protocol lines, and merges
  `|request|` into it. Its README doesn't say which fields it tracks or whether it suits bots.

## 1b. Sample log (real gen9ou game)

From public replay `gen9ou-2703852247` (both players ~1600–1650; pulled 2026-10-24 from
`replay.pokemonshowdown.com/gen9ou-2703852247.log`). **Edited:** usernames → `Alice` / `Bob`; chat (`|c|`), join/leave
(`|j|`, `|l|`) and timer (`|inactive|`) lines removed; turns 6–33 cut.

⚠️ A replay is the **spectator view**: there are no `|request|` lines, and both sides' HP is shown as `%`. A live bot also
gets its own `|request|` JSON and exact HP for its own team.

```
|t:|1792848107
|gametype|singles
|player|p1|Alice|2|1654                      ← name, avatar, start Elo
|player|p2|Bob|yancy|1625
|gen|9
|tier|[Gen 9] OU
|rated|
|rule|HP Percentage Mod: HP is shown in percentages
|rule|Species Clause: Limit one of each Pokemon
|rule|Sleep Moves Clause: Sleep-inducing moves are banned
|clearpoke
|poke|p1|Meowscarada, M|                    ← team preview: species, gender, item flag (blank here)
|poke|p1|Raging Bolt|
|poke|p1|Hatterene, F|
|poke|p1|Cinderace, M|
|poke|p1|Landorus-Therian, M|
|poke|p1|Kingambit, F|
|poke|p2|Dragonite, F|
|poke|p2|Samurott-Hisui, F|
|poke|p2|Gholdengo|
|poke|p2|Pecharunt|
|poke|p2|Walking Wake|
|poke|p2|Ting-Lu|
|teampreview                                  ← REQUEST: team preview (choose lead)
|
|t:|1792848234
|teamsize|p1|6
|teamsize|p2|6
|start
|switch|p1a: Meowscarada|Meowscarada, M|100/100   ← leads revealed
|switch|p2a: Gholdengo|Gholdengo|100/100
|turn|1                                       ← REQUEST: move
|
|t:|1792848285
|switch|p1a: Kingambit|Kingambit, F|100/100      ← switches go before moves
|-terastallize|p2a: Gholdengo|Steel                ← Tera type revealed; their Tera is now used
|move|p2a: Gholdengo|Make It Rain|p1a: Kingambit  ← move revealed
|-resisted|p1a: Kingambit
|-damage|p1a: Kingambit|60/100                    ← damage taken → bulk / spread evidence
|-unboost|p2a: Gholdengo|spa|1
|
|-heal|p1a: Kingambit|66/100|[from] item: Leftovers   ← item revealed via [from]
|upkeep
|turn|2
|
|t:|1792848300
|switch|p2a: Samurott|Samurott-Hisui, F|100/100
|move|p1a: Kingambit|Low Kick|p2a: Samurott
|-supereffective|p2a: Samurott
|-damage|p2a: Samurott|31/100
|
|-heal|p1a: Kingambit|72/100|[from] item: Leftovers
|upkeep
|turn|3
|
|t:|1792848357
|move|p2a: Samurott|Ceaseless Edge|p1a: Kingambit  ← Samurott moved first → speed order evidence
|-resisted|p1a: Kingambit
|-damage|p1a: Kingambit|58/100
|-sidestart|p1: Alice|Spikes                        ← hazard on p1's side
|move|p1a: Kingambit|Low Kick|p2a: Samurott
|-supereffective|p2a: Samurott
|-damage|p2a: Samurott|0 fnt
|faint|p2a: Samurott
|
|-heal|p1a: Kingambit|64/100|[from] item: Leftovers
|upkeep
|                                             ← REQUEST: forced switch (p2 only; p1 waits)
|t:|1792848366
|switch|p2a: Dragonite|Dragonite, F|100/100
|turn|4
|
|t:|1792848370
|switch|p1a: Landorus|Landorus-Therian, M|100/100
|-ability|p1a: Landorus|Intimidate|boost         ← ability revealed on switch-in
|-unboost|p2a: Dragonite|atk|1
|move|p2a: Dragonite|Low Kick|p1a: Landorus
|-resisted|p1a: Landorus
|-damage|p1a: Landorus|91/100
|-damage|p2a: Dragonite|84/100|[from] item: Rocky Helmet|[of] p1a: Landorus
|
|upkeep
|turn|5
  … turns 5–33 cut …
|turn|34
|
|t:|1792848654
|move|p1a: Cinderace|U-turn|p2a: Walking Wake
|-start|p1a: Cinderace|typechange|Bug|[from] ability: Libero
|-damage|p2a: Walking Wake|0 fnt
|faint|p2a: Walking Wake
|-end|p2a: Walking Wake|Protosynthesis|[silent]
|
|win|Alice
|raw|Alice's rating: 1654 &rarr; <strong>1672</strong><br />(+18 for winning)   ← post-game Elo
|raw|Bob's rating: 1625 &rarr; <strong>1607</strong><br />(-18 for losing)
```

**Parser gotchas this sample shows:**
- **Ident vs species:** the ident (`p2a: Samurott`) shows the Pokémon's name: a nickname, or the base species when it
  has none. The real forme (`Samurott-Hisui`) is only in `DETAILS`. Key Pokémon by species from `DETAILS`.
- **`[from]` / `[of]` tags** carry most item and ability reveals (Leftovers, Rocky Helmet on the *other* Pokémon).
- **A blank `|` line** separates the actions from the end-of-turn effects.
- **A forced switch has no `|turn|` before it.** The `|switch|` after a `|faint|` arrives before the next `|turn|`.
- **`|raw|` is HTML**, so the Elo needs stripping out of the tags.

## 2. Observe: what the parser tracks

| Group | Fields |
|---|---|
| Actives | Species / forme, HP %, status, boosts |
| Field | Weather, terrain, hazards per side, screens, field/side effects and observed durations |
| Revealed info | Per Pokémon: observed moves, item, ability, Tera; decision-layer belief derives guarded item inferences from public events |
| Players | Names, start Elo (`|player|` line) |
| Request (separate input) | poke-env supplies the private request; decision/actions.py derives legal options |

HP is a **percentage** in v1 (the opponent's exact HP is hidden anyway).

## 3. Request types

| Request | What we send | Notes |
|---|---|---|
| Team preview | Team order (picks the lead) | |
| Move | `move N`, `move N terastallize`, or `switch N` | Tera once per game |
| Forced switch | `switch N` | The opponent doesn't act |
| Wait | Nothing | |

## 4. Historical skeleton choices: current resolution

The earlier PRD skeleton checklist is superseded by source for the following items:

- **Framework:** poke-env 0.16.1 plus our own parser over raw lines.
- **State and events:** `Agent.choose(request, battle)` receives a public `BattleState`, including ordered
  `last_turn` events, separately from the private request. The contract and adapter exist.
- **Server and format:** local Showdown, gen9ou. Public-ladder deployment remains a separate scope item.
- **Teams:** smoke/evaluation support the committed stand-in team(s), a team file/folder and optional priors
  derived from those teams. A planned 60-team pool or final chosen demo team is not proven by those flags alone.
- **Serving behavior:** record errors and fall back so a decision failure does not leave the battle unanswered;
  MCTS branch workers add search isolation and trace fields described in CURRENT-STATUS.

## 5. Sources (ledger)

> Historical protocol research ledger, checked 24 October 2026. Upstream master links below are moving references;
> current implementation claims are supported by the pinned repository sources above.

| Source | Verdict | Supports |
|---|---|---|
| [`sim/SIM-PROTOCOL.md`](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md) | KEEP | Log line formats, choice syntax, `rqid`, HP shown as % to the opponent |
| [`sim/SIMULATOR.md`](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIMULATOR.md) | KEEP | `BattleStream`, `>start` / `>player` / `>p1 …`, `update` / `sideupdate` / `end` |
| [`sim/side.ts`](https://github.com/smogon/pokemon-showdown/blob/master/sim/side.ts) | KEEP | The four request types and their fields (the doc leaves these out) |
| [`sim/pokemon.ts`](https://github.com/smogon/pokemon-showdown/blob/master/sim/pokemon.ts) | KEEP | `active[]` move data, `canTerastallize`, `trapped`, `side.pokemon[]` fields, the `condition` format |
| [`sim/battle-actions.ts`](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle-actions.ts) | KEEP | `|-terastallize|POKEMON|TYPE` (missing from SIM-PROTOCOL.md) |
| [`@pkmn/protocol` README](https://github.com/pkmn/ps/blob/main/protocol/README.md) | WEAK | Typed protocol parsing; no field list |
| [`@pkmn/client` README](https://github.com/pkmn/ps/blob/main/client/README.md) | WEAK | Tracks known battle info and merges requests; fields not listed, bot use not stated |
