"""Pool root visit distributions as search support, never as win probabilities."""
import math

from decision.actions import Action, our_actions
from decision.state import to_id


def map_choice(choice: str, request: dict) -> Action | None:
    """Map the binding's named moves/switches to the request's current slot order.

    An ambiguous species or move is deliberately rejected rather than guessed.
    Showdown's Species Clause normally makes switch names unique in OU.
    """
    if choice.startswith("switch "):
        species = to_id(choice.removeprefix("switch "))
        matches = [Action("switch", n) for n, mon in enumerate(request["side"]["pokemon"], 1)
                   if to_id(mon["details"].split(",")[0]) == species]
    else:
        tera = choice.endswith("-tera")
        move = to_id(choice.removesuffix("-tera"))
        matches = [Action("move", n, tera) for n, entry in enumerate(
            request.get("active", [{}])[0].get("moves", []), 1) if to_id(entry["id"]) == move]
    return matches[0] if len(matches) == 1 else None


def _visits(rows: list[dict]) -> dict[str, float]:
    visits = {}
    for row in rows:
        count = row.get("visits", 0)
        if isinstance(count, (int, float)) and math.isfinite(count) and count > 0:
            choice = row.get("choice", row.get("move_choice", ""))
            visits[choice] = visits.get(choice, 0) + count
    total = sum(visits.values())
    return {choice: n / total for choice, n in visits.items()} if total else {}


def pool_results(worlds: list[dict], request: dict, *, mode: str = "sampled") -> dict:
    """Equal mass per sampled occurrence; explicit weights only for enumeration.

    Normalise native visits before pooling so iteration count cannot reweight a
    world. Filter against the caller's legal actions and renormalise once at the
    end. Opponent root distributions are retained as diagnostic predictions.
    """
    if mode not in {"sampled", "enumerated"}:
        raise ValueError("mode must be sampled or enumerated")
    legal = our_actions(request)
    allowed = set(legal)
    support, opponent = {}, {}
    mapping_failures, unusable = [], []
    usable, mass = 0, 0.0
    for index, world in enumerate(worlds):
        tag = world.get("index", index)
        if world.get("error"):
            unusable.append({"index": tag, "reason": world["error"]})
            continue
        distribution = _visits(world.get("our_visits", []))
        weight = 1.0 if mode == "sampled" else world.get("weight", 0)
        if not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0:
            unusable.append({"index": tag, "reason": "invalid_scenario_weight"})
            continue
        mapped = {}
        for choice, share in distribution.items():
            action = map_choice(choice, request)
            if action is None or action not in allowed:
                mapping_failures.append({"index": tag, "choice": choice,
                                         "reason": "unmapped" if action is None else "not_legal"})
            else:
                mapped[action] = mapped.get(action, 0) + share
        if not mapped:
            unusable.append({"index": tag, "reason": "no_supported_legal_action" if distribution else "zero_visits"})
            continue
        usable += 1
        for action, share in mapped.items():
            support[action] = support.get(action, 0) + weight * share
        opponent_distribution = _visits(world.get("opponent_visits", []))
        if opponent_distribution:
            mass += weight
        for choice, share in opponent_distribution.items():
            opponent[choice] = opponent.get(choice, 0) + weight * share
    total = sum(support.values())
    support = {a: share / total for a, share in support.items()} if total else {}
    # Request order gives a stable tie-break, independent of native result order.
    selected = max(legal, key=lambda a: support.get(a, -1)) if support else None
    return {"action": selected, "search_support": {a.to_choice(): p for a, p in support.items()},
            "opponent_support": {choice: share / mass for choice, share in opponent.items()} if mass else {},
            "usable_worlds": usable, "mapping_failures": mapping_failures, "unusable_worlds": unusable,
            "aggregation": mode}


def gate_tera(action: Action, support: dict[str, float], request: dict, worlds: list[dict],
              min_wins: int) -> tuple[Action, dict]:
    """Spend Tera only when that exact Tera choice tops at least `min_wins` worlds outright (Laplace's rule).

    Tera is spent once a game, and averaging can lift a Tera copy that is every world's runner-up over each
    world's actual pick. A blocked Tera falls back to the best-supported non-Tera choice; with none supported,
    the Tera choice stands rather than a blind one.
    """
    wins = 0
    for world in worlds:
        distribution = {} if world.get("error") else _visits(world.get("our_visits", []))
        if distribution and map_choice(max(distribution, key=distribution.get), request) == action:
            wins += 1
    record = {"top_in_worlds": wins, "min_wins": min_wins, "blocked": False}
    if not action.tera or wins >= min_wins:
        return action, record
    others = [a for a in our_actions(request) if not a.tera and support.get(a.to_choice(), 0) > 0]
    if not others:
        return action, record
    return max(others, key=lambda a: support[a.to_choice()]), {**record, "blocked": True}
