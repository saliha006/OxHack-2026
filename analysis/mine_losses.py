"""Find investigation leads in saved decisions, with wins as controls.

These are observable signatures, not labels saying a move was a blunder.
Rates use signature-specific opportunity denominators. Final-turn transitions
without a following state are missing evidence and are not counted as negatives.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from decision.opponent import MOVES
from decision.state import to_id

HAZARDS = {"stealthrock": 1, "spikes": 3, "toxicspikes": 2, "stickyweb": 1}


def selected_move(row):
    choice = row.get("choice") or ""
    if not choice.startswith("move "):
        return None
    try:
        return to_id(row["request"]["active"][0]["moves"][int(choice.split()[1]) - 1]["id"])
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def signatures(decisions):
    counts, exposure, examples = Counter(), Counter(), []
    switches = []
    for index, row in enumerate(decisions[:-1]):
        state, after = row["state"], decisions[index + 1]["state"]
        us = state["us"]
        them = "p2" if us == "p1" else "p1"
        ours, foe = state["sides"][us], state["sides"][them]
        active, opposing = ours["active"], foe["active"]
        if active is None or opposing is None:
            continue
        if row.get("request", {}).get("forceSwitch") or ours["pokemon"][active]["hp_percent"] <= 0:
            continue  # replacements/pivot continuations are not another root opportunity
        # Continuation requests can share a turn. Events are interval snapshots;
        # checking execution explicitly prevents treating a rejected action as played.
        events = after.get("last_turn", [])
        move = selected_move(row)
        executed = move and any(e["type"] == "move" and e["side"] == us
                                and e["pokemon"] == active and e["move"] == move for e in events)
        found = []
        if executed and move in HAZARDS:
            exposure["hazard_at_cap"] += 1
            if foe["hazards"].get(move, 0) >= HAZARDS[move]:
                found.append("hazard_at_cap")
        boosts = MOVES.get(move, {}).get("boosts", {}) if executed else {}
        positive = {k: v for k, v in boosts.items() if v > 0}
        if positive and MOVES.get(move, {}).get("target") == "self":
            exposure["setup_at_cap"] += 1
            if all(ours["boosts"].get(stat, 0) >= 6 for stat in positive):
                found.append("setup_at_cap")
        if executed and MOVES.get(move, {}).get("category") in {"Physical", "Special"}:
            exposure["attack_chip_erased"] += 1
            hits = [e for e in events if e["side"] == them and e["pokemon"] == opposing
                    and e["type"] == "damage" and e.get("source") == "move"]
            same_target = after["sides"][them]["active"] == opposing
            if hits and same_target and after["sides"][them]["pokemon"][opposing]["hp_percent"] >= foe["pokemon"][opposing]["hp_percent"]:
                found.append("attack_chip_erased")
        if executed and "terastallize" in (row.get("choice") or ""):
            exposure["tera_then_faint"] += 1
            if after["sides"][us]["pokemon"][active]["hp_percent"] == 0:
                found.append("tera_then_faint")
        if (row.get("choice") or "").startswith("switch "):
            exposure["switch_return_cycle"] += 1
            switches.append((index, active))
            # Three successive switch decisions with the same initial active is a
            # visible A->B->A return. It can still be a sensible response to the foe.
            if len(switches) >= 3 and switches[-1][0] - switches[-3][0] == 2 and switches[-1][1] == switches[-3][1]:
                found.append("switch_return_cycle")
        else:
            switches = []
        if max(foe["boosts"].get("atk", 0), foe["boosts"].get("spa", 0)) >= 2:
            exposure["boosted_foe_faint"] += 1
            if after["sides"][us]["pokemon"][active]["hp_percent"] == 0:
                found.append("boosted_foe_faint")
        for name in found:
            counts[name] += 1
            if sum(e["signature"] == name for e in examples) < 5:
                examples.append({"signature": name, "decision_id": row.get("decision_id"),
                                 "turn": state["turn"], "choice": row.get("choice"), "move": move})
    return {"counts": dict(counts), "opportunities": dict(exposure), "examples": examples}


def analyze_games(games):
    totals = defaultdict(lambda: {"perspectives": 0, "counts": Counter(), "opportunities": Counter()})
    records, unavailable = [], []
    for game in games:
        for role, artifacts in game.get("artifacts", {}).items():
            path = artifacts.get("trace")
            if not path or not Path(path).is_file():
                unavailable.append({"battle": game.get("battle"), "role": role, "reason": "trace_unavailable"})
                continue
            rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
            decisions = [r for r in rows if "state" in r and r.get("kind") in {"move", "switch"}]
            result = signatures(decisions)
            outcome = "unknown" if game.get("winner") not in {"a", "b"} else "win" if game["winner"] == role else "loss"
            totals[outcome]["perspectives"] += 1
            for field in ("counts", "opportunities"):
                totals[outcome][field].update(result[field])
            records.append({"battle": game.get("battle"), "role": role, "outcome": outcome,
                            "trace": path, **result})
    summary = {}
    for outcome, total in totals.items():
        summary[outcome] = {**total, "rates": {
            name: total["counts"].get(name, 0) / n for name, n in total["opportunities"].items() if n}}
    return {"interpretation": "Descriptive investigation leads; no causal or strength claim. Repeated turns are not independent games.",
            "missingness": "Final transition without next decision excluded; no unseen final-turn negative imputed.",
            "by_outcome": summary, "games": records, "unavailable": unavailable}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    games = [json.loads(line) for line in args.games.read_text().splitlines() if line.strip()]
    args.output.write_text(json.dumps(analyze_games(games), indent=2) + "\n")


if __name__ == "__main__":
    main()
