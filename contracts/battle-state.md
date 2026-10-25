> Source snapshot: main at bbb95d60fb57a01497aae370d8ca922c275bb79d. See ../DATA-CONTEXT.md for branch-specific corrections.

# BattleState contract

> **DRAFT v0**, defined by Derrick (decision layer), 2026-10-24. Not yet agreed with the bot layer owner.

**What it is:** the JSON object the bot layer's log parser hands the decision layer with every `|request|`. It covers
what the log shows and the request doesn't: both sides as seen in the battle, the field, and last turn's events.

- **Types:** [`battle_state.py`](battle_state.py) (TypedDicts; field comments are the spec).
- **Example:** [`examples/battle_state_turn2.json`](examples/battle_state_turn2.json), the state before turn 2 of
  replay `gen9ou-2703852247` (Alice = p1 = us).
- **Check:** `uv run pytest tests/test_battle_state_contract.py` keeps the example and the types in step.

## Who does what
| | Bot layer (parser) | Decision layer |
|---|---|---|
| Reads | Showdown log lines | `BattleState` + the raw `|request|` |
| Writes | `BattleState`, one per request | A choice string |
| Language | Any: it hands over JSON | Python |

## Conventions
- **Both sides have the same shape.** The parser doesn't need to know which side is us; `us` says so.
- **Names are Showdown IDs:** lowercase, letters and digits only (`samurotthisui`, `ironhead`, `heavydutyboots`).
- **HP is Showdown's 0–100 integer** for both sides. Our exact HP comes from the request.
- **Pokémon are listed in team-preview order** (`|poke|` lines), and `active` / event `pokemon` index into that list.
- **Unknown ≠ none.** `item: null` = not revealed; `item: ""` = known to have none (knocked off, consumed).
- **Turns are elapsed counts,** not turns left: the parser can't see Light Clay or Damp Rock.
- **Level defaults to 100** until a `|switch|` shows otherwise, since team preview hides levels.
- **`last_move` belongs to the Pokémon now active:** reset to `null` whenever that side switches (agreed with saliha,
  2026-10-24). Choice lock and Encore read it.
- **`Event.source` is spelled exactly** as in the examples: `"move"`, `"stealthrock"`, `"item:<id>"`,
  `"ability:<id>"`, `"tera:<type>"`. Belief matches these strings.

## Which log lines feed what
| Field | Log lines |
|---|---|
| `player`, `rating` | `|player|` |
| `pokemon[].species`, `forme_known` | `|poke|`, then `|switch|` / `|detailschange|` DETAILS |
| `hp_percent`, `status` | `|switch|`, `|-damage|`, `|-heal|`, `|-status|`, `|-curestatus|`, `|faint|` |
| `revealed_moves`, `last_move` | `|move|` |
| `item`, `ability` | `|-item|`, `|-enditem|`, `|-ability|`, and `[from] item: …` / `[from] ability: …` tags |
| `tera_type`, `terastallized`, `tera_used` | `|-terastallize|` |
| `boosts` | `|-boost|`, `|-unboost|`, cleared on `|switch|` |
| `volatiles` | `|-start|` / `|-end|`, cleared on `|switch|` |
| `hazards`, `side_effects` | `|-sidestart|` / `|-sideend|` |
| `field` | `|-weather|`, `|-fieldstart|` / `|-fieldend|` |
| `last_turn` | Everything since the previous request, as `Event`s |

## Still open
- 🟠 **Parked:** `Event.hit_count` for multi-hit moves (`|-hitcount|`). Until then belief takes no damage evidence from them.
- 🟠 Agreement from the bot layer owner (proposed: saliha) on the shape, and on JSON as the hand-over.
- 🟠 How it's handed over if the parser isn't Python (stdin, socket, file).
