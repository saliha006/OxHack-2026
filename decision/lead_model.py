"""Optional preview heuristic using our private request and public opponent priors.

This is a small, explicit approximation rather than a native battle rollout. It
never loads team exports. Weights are fixed development choices, not fitted to
the screening or confirmation teams.
"""
import math
import re
import time
from collections import Counter

from decision.actions import Action
from decision.belief import _apply_revelations, _fits, _prior_entry, _recovery_set, _to_set
from decision.lead import MULTIPLIER, TYPECHART, _types, pick_lead
from decision.opponent import MOVES
from decision.sets import STAT_ORDER, stats
from decision.state import DEX, to_id

WEIGHTS = {"offense": 1.0, "incoming": -.55, "tempo": .12, "fragility": -.30,
           "hazard": .08, "pivot": .06, "taunt": .05}
PIVOTS = {"uturn", "voltswitch", "flipturn", "partingshot", "chillyreception", "teleport"}
HAZARDS = {"stealthrock": 1.0, "spikes": .8, "toxicspikes": .5, "stickyweb": .6}
IMMUNITIES = {"ground": {"levitate", "eartheater"}, "water": {"waterabsorb", "stormdrain", "dryskin"},
              "electric": {"voltabsorb", "lightningrod", "motordrive"}, "grass": {"sapsipper"},
              "fire": {"flashfire", "wellbakedbody"}}
MOLD_BREAKERS = {"moldbreaker", "teravolt", "turboblaze"}


def pick_lead_model(request: dict, battle: dict, priors: dict) -> tuple[Action, dict]:
    """Return a deterministic lead and transparent score components.

    Opposing preview species have equal lead mass. Each species' compatible
    existing set prior is normalised separately; no opposing private moves,
    spreads or team-file paths are accepted as inputs.
    """
    started = time.perf_counter()
    diagnostic = {"policy": "moves_stats_v1", "weights": dict(WEIGHTS), "enabled_by_default": False,
                  "opponent_lead_prior": "uniform preview species", "rows": [], "fallback": None,
                  "approximations": ["expected damage, not a simulated first turn", "no Tera at preview",
                                     "weather, terrain, secondary effects and future switches omitted",
                                     "variable power and conditional priority use explicit estimates"]}
    try:
        them = "p2" if battle["us"] == "p1" else "p1"
        opponents = [_opponent_models(mon, priors) for mon in battle["sides"][them]["pokemon"]]
        if not opponents:
            raise ValueError("empty opponent preview")
        ours = [_own_model(mon) for mon in request["side"]["pokemon"]]
        if not ours:
            raise ValueError("empty own preview")
        evaluations = 0
        for slot, own in enumerate(ours, 1):
            total = dict.fromkeys(WEIGHTS, 0.0)
            matchups = []
            for species, candidates, prior_note in opponents:
                components = dict.fromkeys(WEIGHTS, 0.0)
                best_moves = Counter()
                for foe, weight in candidates:
                    measured, move = _matchup(own, foe)
                    for key, value in measured.items():
                        components[key] += weight * value
                    best_moves[move] += weight
                    evaluations += 1
                for key in total:
                    total[key] += components[key] / len(opponents)
                matchups.append({"species": species, "candidate_count": len(candidates), "prior": prior_note,
                                 "components": components, "estimated_attack_choices": dict(best_moves)})
            score = sum(WEIGHTS[key] * value for key, value in total.items())
            if not math.isfinite(score):
                raise ValueError("non-finite lead score")
            diagnostic["rows"].append({"slot": slot, "species": own["species"], "score": score,
                                       "components": total, "matchups": matchups})
        best = max(diagnostic["rows"], key=lambda row: row["score"])
        action = Action("lead", best["slot"])
        diagnostic["evaluated_pair_sets"] = evaluations
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        diagnostic["fallback"] = {"type": type(exc).__name__, "reason": str(exc), "policy": "historical_types"}
        try:
            action = pick_lead(request, battle)
        except (KeyError, TypeError, ValueError):
            action = Action("lead", 1)
            diagnostic["fallback"]["policy"] = "first_slot"
    diagnostic["chosen_slot"] = action.slot
    diagnostic["elapsed_ms"] = (time.perf_counter() - started) * 1000
    return action, diagnostic


def _own_model(mon: dict) -> dict:
    species = to_id(mon["details"].split(",")[0])
    level = next((int(flag.strip()[1:]) for flag in mon["details"].split(",")
                  if re.fullmatch(r"L\d+", flag.strip())), 100)
    hp_text = mon["condition"].split()[0]
    current, maximum = (int(value) for value in hp_text.split("/"))
    stat_values = {key: float(mon["stats"][key]) for key in STAT_ORDER if key != "hp"}
    if maximum <= 0 or any(not math.isfinite(value) or value <= 0 for value in stat_values.values()):
        raise ValueError("invalid supplied own stats")
    return {"species": species, "level": level, "types": _types(species), "hp": current, "maxhp": maximum,
            "stats": stat_values, "moves": tuple(mon["moves"]), "item": mon.get("item") or "none",
            "ability": mon.get("ability", mon.get("baseAbility")) or "none"}


def _opponent_models(mon: dict, priors: dict) -> tuple[str, list[tuple[dict, float]], str]:
    species = mon["species"]
    entry, source = _prior_entry(priors, species)
    candidates = []
    for record in entry.get("sets", []):
        weight = float(record["weight"])
        candidate = _to_set(record)
        if math.isfinite(weight) and weight > 0 and _fits(candidate, mon, set()):
            candidates.append((_apply_revelations(candidate, mon), weight))
    note = "compatible existing prior" if source == species else "compatible forme-alias prior"
    if not candidates:
        candidates = [(_recovery_set(mon), 1.0)]
        note = "neutral fallback preserving revelations; set coverage unavailable"
    # Tera is unused before transforming. Coalesce only otherwise identical
    # hypotheses, summing their full probability mass rather than truncating.
    equivalent = {}
    for candidate, weight in candidates:
        key = (candidate.moves, candidate.item, candidate.ability, candidate.nature, candidate.evs, candidate.ivs)
        if key in equivalent:
            prior_candidate, prior_weight = equivalent[key]
            equivalent[key] = prior_candidate, prior_weight + weight
        else:
            equivalent[key] = candidate, weight
    candidates = list(equivalent.values())
    total = sum(weight for _, weight in candidates)
    result = []
    for candidate, weight in candidates:
        values = stats(species, mon["level"], candidate)
        hp, *rest = values
        result.append(({"species": species, "level": mon["level"], "types": _types(species),
                        "hp": hp * mon["hp_percent"] / 100, "maxhp": hp,
                        "stats": dict(zip(STAT_ORDER[1:], rest)), "moves": candidate.moves,
                        "item": candidate.item, "ability": candidate.ability}, weight / total))
    return species, result, note


def _effective_speed(mon: dict) -> float:
    multiplier = 1.5 if mon["item"] == "choicescarf" else .5 if mon["item"] in {"ironball", "machobrace"} else 1.0
    return mon["stats"]["spe"] * multiplier


def _priority(move: str, mon: dict) -> int:
    data = MOVES.get(move, {})
    priority = data.get("priority", 0)
    if data.get("category") == "Status" and mon["ability"] == "prankster":
        priority += 1
    if mon["ability"] == "galewings" and data.get("type") == "Flying" and mon["hp"] == mon["maxhp"]:
        priority += 1
    return priority


def _first(own: dict, foe: dict, move: str, reply: str) -> float:
    ours, theirs = _priority(move, own), _priority(reply, foe)
    if ours != theirs:
        return float(ours > theirs)
    a, b = _effective_speed(own), _effective_speed(foe)
    return .5 if a == b else float(a > b)


def _power(move: str, attacker: dict, defender: dict) -> float:
    data = MOVES.get(move, {})
    value = float(data.get("basePower", 0) or 0)
    if move in {"lowkick", "grassknot"}:
        weight = DEX[defender["species"]]["weightkg"]
        value = next(power for ceiling, power in [(10, 20), (25, 40), (50, 60), (100, 80), (200, 100), (math.inf, 120)]
                     if weight < ceiling)
    elif move == "gyroball":
        value = min(150, 25 * _effective_speed(defender) / max(1, _effective_speed(attacker)) + 1)
    elif move == "electroball":
        ratio = _effective_speed(attacker) / max(1, _effective_speed(defender))
        value = 150 if ratio >= 4 else 120 if ratio >= 3 else 80 if ratio >= 2 else 60 if ratio >= 1 else 40
    elif move in {"eruption", "waterspout", "dragonenergy"}:
        value = max(1, 150 * attacker["hp"] / attacker["maxhp"])
    elif move == "acrobatics" and attacker["item"] == "none":
        value *= 2
    # Other zero-power callbacks have no invented damage estimate.
    hit_count = data.get("multihit", 1)
    if isinstance(hit_count, list):
        hit_count = (hit_count[-1] if attacker["ability"] == "skilllink" else
                     4.5 if attacker["item"] == "loadeddice" else
                     3.1 if hit_count == [2, 5] else sum(hit_count) / 2)
    return max(0.0, value * hit_count)


def _damage(move: str, attacker: dict, defender: dict) -> float:
    """Approximate expected damage as a fraction of the defender's current HP."""
    data = MOVES.get(move, {})
    if data.get("category") not in {"Physical", "Special"}:
        return 0.0
    move_type = data.get("type", "Normal").lower()
    if move == "revelationdance":
        move_type = attacker["types"][0]
    effectiveness = math.prod((2.0 if move == "freezedry" and def_type == "water" else
                               1.0 if move == "thousandarrows" and def_type == "flying" else
                               MULTIPLIER[TYPECHART[def_type][move_type]]) for def_type in defender["types"])
    if move == "flyingpress":
        effectiveness *= math.prod(MULTIPLIER[TYPECHART[t]["flying"]] for t in defender["types"])
    if not effectiveness:
        return 0.0
    ability = defender["ability"] if attacker["ability"] not in MOLD_BREAKERS else "none"
    if ability in IMMUNITIES.get(move_type, set()) and not (move == "thousandarrows" and ability == "levitate"):
        return 0.0
    if ability == "soundproof" and data.get("flags", {}).get("sound") or ability == "bulletproof" and data.get("flags", {}).get("bullet"):
        return 0.0
    fixed = data.get("damage")
    if fixed == "level":
        return attacker["level"] / max(1, defender["hp"])
    if isinstance(fixed, (int, float)):
        return fixed / max(1, defender["hp"])
    if move in {"superfang", "naturesmadness", "ruination"}:
        return .5
    physical = data["category"] == "Physical"
    attack = attacker["stats"]["atk" if physical else "spa"]
    if move == "bodypress":
        attack = attacker["stats"]["def"]
    elif move == "foulplay":
        attack = defender["stats"]["atk"]
    defense_key = "def" if physical or move in {"psyshock", "psystrike", "secretsword"} else "spd"
    defense = defender["stats"][defense_key]
    if attacker["item"] == ("choiceband" if physical else "choicespecs"):
        attack *= 1.5
    if attacker["ability"] in {"hugepower", "purepower"} and physical:
        attack *= 2
    if defender["item"] == "assaultvest" and defense_key == "spd":
        defense *= 1.5
    if ability == "furcoat" and defense_key == "def":
        defense *= 2
    stab = (2.0 if attacker["ability"] == "adaptability" else 1.5) if move_type in attacker["types"] else 1.0
    power = _power(move, attacker, defender)
    if not power:
        return 0.0
    damage = ((2 * attacker["level"] / 5 + 2) * power * attack / max(1, defense) / 50 + 2)
    damage *= stab * effectiveness * .925
    accuracy = data.get("accuracy", True)
    damage *= 1.0 if accuracy is True else max(0.0, min(1.0, float(accuracy) / 100))
    if attacker["item"] == "lifeorb":
        damage *= 1.3
    if ability in {"multiscale", "shadowshield"} and defender["hp"] == defender["maxhp"]:
        damage *= .5
    if ability == "thickfat" and move_type in {"fire", "ice"} or ability == "icescales" and not physical:
        damage *= .5
    if ability in {"filter", "solidrock", "prismarmor"} and effectiveness > 1:
        damage *= .75
    if move == "suckerpunch":
        # It fails against status moves or switches; this set-only estimate knows
        # the status fraction but makes no prediction about future switching.
        damage *= sum(MOVES.get(m, {}).get("category") in {"Physical", "Special"} for m in defender["moves"]) / max(1, len(defender["moves"]))
    return damage / max(1, defender["hp"])


def _matchup(own: dict, foe: dict) -> tuple[dict[str, float], str]:
    incoming, reply = max(((_damage(move, foe, own), move) for move in foe["moves"]), default=(0.0, "none"))
    incoming = min(1.5, incoming)
    own_damage = {move: min(1.5, _damage(move, own, foe)) for move in own["moves"]}
    sash = (own["hp"] == own["maxhp"] and (own["item"] == "focussash" or own["ability"] == "sturdy") and
            not MOVES.get(reply, {}).get("multihit"))
    best = None
    for move in own["moves"]:
        if MOVES.get(move, {}).get("category") == "Status":
            continue
        damage = own_damage[move]
        first = _first(own, foe, move, reply)
        survival = .25 if sash else 1.0
        fragility = max(0.0, incoming - .75) * (1 - first * min(1.0, damage)) * survival
        value = damage + WEIGHTS["tempo"] * (first - .5) + WEIGHTS["fragility"] * fragility
        if best is None or value > best[0]:
            best = value, move, damage, first, fragility
    _, best_move, outgoing, first, fragility = best or (0.0, "none", 0.0, .5, max(0, incoming - .75))
    def survives(move):
        return 1.0 if sash else max(0.0, 1.0 - (1 - _first(own, foe, move, reply)) * min(1.0, incoming))
    hazard = max((value * survives(move) for move, value in HAZARDS.items() if move in own["moves"]), default=0.0)
    if foe["ability"] == "magicbounce":
        hazard = 0.0
    elif foe["item"] == "heavydutyboots":
        hazard *= .5
    if "taunt" in foe["moves"]:
        hazard *= .35 + .65 * _first(own, foe, "stealthrock", "taunt")
    pivot = 0.0
    for move in own["moves"]:
        if move in PIVOTS and ((MOVES[move]["category"] != "Status" and own_damage[move] > 0) or
                              (MOVES[move]["category"] == "Status" and not
                               (move == "partingshot" and foe["ability"] in {"goodasgold", "magicbounce"}))):
            pivot = max(pivot, (.6 + .4 * (1 - _first(own, foe, move, reply))) * survives(move))
    taunt = 0.0
    if "taunt" in own["moves"] and foe["ability"] not in {"goodasgold", "magicbounce", "oblivious", "aromaveil"}:
        if not (own["ability"] == "prankster" and "dark" in foe["types"]):
            statuses = sum(MOVES.get(move, {}).get("category") == "Status" for move in foe["moves"])
            taunt = (statuses / max(1, len(foe["moves"])) * (.35 + .65 * _first(own, foe, "taunt", reply)) *
                     survives("taunt"))
    return {"offense": outgoing, "incoming": incoming, "tempo": first - .5, "fragility": fragility,
            "hazard": hazard, "pivot": pivot, "taunt": taunt}, best_move
