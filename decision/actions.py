from dataclasses import dataclass
from typing import Literal

# gen9ou team preview always shows six Pokémon.
TEAM_SIZE = 6


@dataclass(frozen=True)
class Action:
    kind: Literal["move", "switch", "lead"]
    slot: int  # 1-based, in the request's own order: Showdown choices index that way
    tera: bool = False

    def to_choice(self) -> str:
        if self.kind == "move":
            return f"move {self.slot} terastallize" if self.tera else f"move {self.slot}"
        if self.kind == "switch":
            return f"switch {self.slot}"
        # A full order, lead first and the rest unchanged: feature 11 picks only the lead.
        rest = (n for n in range(1, TEAM_SIZE + 1) if n != self.slot)
        return "team " + str(self.slot) + "".join(map(str, rest))


def our_actions(request: dict) -> list[Action]:
    if request.get("wait"):
        return []
    team = request["side"]["pokemon"]
    if request.get("teamPreview"):
        return [Action("lead", n) for n in range(1, len(team) + 1)]
    if any(request.get("forceSwitch", [])):
        return _switches(team)

    active = request["active"][0]
    # `disabled` is either a bool or the name of the effect disabling the move.
    usable = [n for n, move in enumerate(active["moves"], 1)
              if not move.get("disabled") and move.get("pp", 1) > 0]
    actions = [Action("move", n) for n in usable]
    if active.get("canTerastallize"):
        actions += [Action("move", n, tera=True) for n in usable]
    # maybeTrapped is treated as trapped (Derrick, 2026-10-24): never offer a switch Showdown might reject.
    if not (active.get("trapped") or active.get("maybeTrapped")):
        actions += _switches(team)
    return actions


def _switches(team: list[dict]) -> list[Action]:
    return [
        Action("switch", n)
        for n, mon in enumerate(team, 1)
        if not mon["active"] and not mon["condition"].endswith("fnt")
    ]
