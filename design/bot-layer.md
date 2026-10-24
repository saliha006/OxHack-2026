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
- ✅ **Framework (2026-10-24):** poke-env 0.16.1 with our own parser over its raw lines; own websocket client is the fallback (research pass 8).
- 🟠 **What the bot passes on:** the merged state only, or the state plus this turn's raw events? (Decision layer Q7.)
- ✅ **Server:** local first; the public ladder is a stretch that needs bot registration.
- ✅ **Format:** gen9ou. Random battles use role-based sets that don't match our gen9ou priors.
- 🟠 **Bot ↔ decision contract:** the `BattleState` / `Choice` shapes ([DESIGN.md §2](DESIGN.md#2-seams-the-contracts-between-layers)).
- ✅ **Our team:** one fixed validated team; opponents from a seeded pool (Nate's task 6).

## 5. Sources (ledger)

> Copy to the research doc once its path is set (CLAUDE.md §10). No community pass yet.

| Source | Verdict | Supports |
|---|---|---|
| [`sim/SIM-PROTOCOL.md`](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md) | KEEP | Log line formats, choice syntax, `rqid`, HP shown as % to the opponent |
| [`sim/SIMULATOR.md`](https://github.com/smogon/pokemon-showdown/blob/master/sim/SIMULATOR.md) | KEEP | `BattleStream`, `>start` / `>player` / `>p1 …`, `update` / `sideupdate` / `end` |
| [`sim/side.ts`](https://github.com/smogon/pokemon-showdown/blob/master/sim/side.ts) | KEEP | The four request types and their fields (the doc leaves these out) |
| [`sim/pokemon.ts`](https://github.com/smogon/pokemon-showdown/blob/master/sim/pokemon.ts) | KEEP | `active[]` move data, `canTerastallize`, `trapped`, `side.pokemon[]` fields, the `condition` format |
| [`sim/battle-actions.ts`](https://github.com/smogon/pokemon-showdown/blob/master/sim/battle-actions.ts) | KEEP | `|-terastallize|POKEMON|TYPE` (missing from SIM-PROTOCOL.md) |
| [`@pkmn/protocol` README](https://github.com/pkmn/ps/blob/main/protocol/README.md) | WEAK | Typed protocol parsing; no field list |
| [`@pkmn/client` README](https://github.com/pkmn/ps/blob/main/client/README.md) | WEAK | Tracks known battle info and merges requests; fields not listed, bot use not stated |
