# Our actions

> Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick` (`7ab8810`), not merged.

**Job:** list our legal choices from the request.

| | |
|---|---|
| **Input** | The raw `|request|` JSON as a dict |
| **Output** | `list[Action]`; `Action.to_choice()` gives the Showdown string |
| **Build stage** | Stage 3 |
| **Owner** | Derrick |
| **Code** | `decision/actions.py` · tests `tests/test_actions.py` |

## Interface
```python
@dataclass(frozen=True)
class Action:
    kind: Literal["move", "switch", "lead"]
    slot: int          # 1-based, in the request's order
    tera: bool = False
    def to_choice(self) -> str: ...   # "move 2", "move 2 terastallize", "switch 4", "team 312456"

def our_actions(request: dict) -> list[Action]: ...
```

## Decisions (Derrick, 2026-10-24)
1. Input = the raw request dict, not `BattleState` (Showdown defines it, so it won't move when the bot layer settles its type).
2. Output = an `Action` dataclass, so later steps read `kind` / `tera` without parsing strings.
3. Handles move requests, forced switches and the **6 leads** at team preview. A lead is sent as a full order, lead
   first and the rest unchanged. Choosing the back five is feature 11.
4. `maybeTrapped` → no switches, the same as `trapped`.

## Rules (one right answer)
- Disabled moves are left out (`disabled` can be `true` or the name of the effect).
- A Tera copy of each usable move only when `canTerastallize` is set.
- Switch targets = not active and not `fnt`.
- Locked move / Struggle arrive as the only move; passed through.

## Out of scope for now
Revival Blessing (`reviving`), doubles, Mega / Z / Dynamax, pruning (feature 10).

## Done when
- [x] Never offers a disabled move, a fainted or active switch target, or a switch while trapped / maybe-trapped
- [x] Forced switch returns switches only; wait returns nothing; team preview returns 6 leads
- [ ] Checked against real captured requests (needs a running game)
