"""A single observed-BattleState feature schema shared by training and serving."""
import math

VERSION = 1
BOOSTS = ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
HAZARDS = ("stealthrock", "spikes", "toxicspikes", "stickyweb")
SCREENS = ("reflect", "lightscreen", "auroraveil", "tailwind", "safeguard")
VOLATILES = ("substitute", "taunt", "encore", "confusion", "leechseed", "yawn")
SIDE_FEATURES = ("alive", "hp", "active_hp", "statused", "tera_available", "revealed_moves",
                 *BOOSTS, *HAZARDS, *SCREENS, *VOLATILES, "wish", "future_sight")
FEATURE_NAMES = tuple("difference_" + name for name in SIDE_FEATURES) + ("turn", "trickroom",)


def _side(side: dict) -> list[float]:
    team = side["pokemon"]
    active = side.get("active")
    active_hp = team[active]["hp_percent"] / 100 if active is not None and active < len(team) else 0
    values = [sum(m["hp_percent"] > 0 for m in team) / 6,
              sum(m["hp_percent"] for m in team) / 600, active_hp,
              sum(bool(m.get("status")) and m["hp_percent"] > 0 for m in team) / 6,
              float(not side.get("tera_used", False)),
              sum(len(m.get("revealed_moves", [])) for m in team) / 24]
    values += [side.get("boosts", {}).get(k, 0) / 6 for k in BOOSTS]
    values += [side.get("hazards", {}).get(k, 0) / (3 if k == "spikes" else 2 if k == "toxicspikes" else 1)
               for k in HAZARDS]
    values += [float(k in side.get("side_effects", {})) for k in SCREENS]
    values += [float(k in side.get("volatiles", [])) for k in VOLATILES]
    values += [float(bool(side.get(k))) for k in ("wish", "future_sight")]
    return values


def featurize(state: dict) -> list[float]:
    """Only explicit public fields; ignores requests, labels, names, IDs and post-turn columns."""
    us = state["us"]
    them = "p2" if us == "p1" else "p1"
    ours, theirs = _side(state["sides"][us]), _side(state["sides"][them])
    vector = [a - b for a, b in zip(ours, theirs)]
    vector += [min(state["turn"], 300) / 100,
               float("trickroom" in state.get("field", {}).get("effects", {}))]
    if len(vector) != len(FEATURE_NAMES) or not all(math.isfinite(x) for x in vector):
        raise ValueError("invalid observed feature vector")
    return vector


def hp_baseline(state: dict) -> float:
    """The public-state HP/alive heuristic in contracts/turns.md, clipped only by metric code."""
    us = state["us"]
    them = "p2" if us == "p1" else "p1"
    def score(side):
        return sum((m["hp_percent"] > 0) + m["hp_percent"] / 100 for m in side["pokemon"])
    return 0.5 + (score(state["sides"][us]) - score(state["sides"][them])) / 24

