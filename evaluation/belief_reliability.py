"""Pre-revelation ablations on saved public/request snapshots, without future inputs.

Historical pilot results are retrospective diagnostics. Fresh battle scores use
the same fixed floor and smoothing; they are not used to tune either parameter.
"""
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from decision.actions import Action
from decision.belief import Belief
from prediction.belief_export import _next_reveals
from prediction.likelihood import reveal_distribution
from evaluation.mcts_improvements.identity import source_identity, engine_identity

MODES = {"revelations_only": "revelations", "legacy_hard_inference": "legacy",
         "reliable_hard_inference": "reliable", "reliable_soft_updates": "reliable"}
ALPHA = 1e-6


def records(belief):
    return [[{"weight": weight, **asdict(candidate)} for candidate, weight in slot]
            for slot in belief.candidates]


def action_from_choice(choice):
    parts = (choice or "").split()
    if len(parts) < 2 or parts[0] not in {"move", "switch"}:
        return None
    try:
        return Action(parts[0], int(parts[1]), "terastallize" in parts)
    except ValueError:
        return None


def score_transitions(decisions, priors, *, battle_id, role, subset="scoring"):
    """Freeze each prediction before inspecting the next snapshot's labels."""
    if not decisions:
        return [], {}
    first = decisions[0]["state"]
    them = "p2" if first["us"] == "p1" else "p1"
    original = records(Belief(priors, first, inference_mode="revelations"))
    beliefs = {name: Belief(priors, first, inference_mode=mode) for name, mode in MODES.items()}
    pending, output = None, []
    diagnostics = defaultdict(Counter)
    for decision in decisions:
        state = decision["state"]
        if pending is not None:
            before, predictions = pending
            for slot, kind, revealed, known in _next_reveals(before, state, them):
                output.append({"battle_id": battle_id, "role": role, "subset": subset,
                               "predicted_at_turn": before["turn"], "revealed_by_turn": state["turn"],
                               "kind": kind, "revealed": revealed, "known_moves": known,
                               "predictions": {"original_prior": original[slot],
                                               **{name: value[slot] for name, value in predictions.items()}}})
        predictions = {}
        for name, belief in beliefs.items():
            if name != "reliable_soft_updates":
                belief.last_choice = belief.last_request = None
            belief.update(state)
            predictions[name] = copy.deepcopy(records(belief))
            for key, value in belief.last_diagnostics.items():
                if key != "turn" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    diagnostics[name][key] += value
            for key, value in belief.last_diagnostics.get("soft", {}).items():
                diagnostics[name]["soft_" + key] += value
            for skipped in belief.last_diagnostics.get("skipped", []):
                diagnostics[name]["skipped:" + skipped["reason"]] += 1
            chosen = action_from_choice(decision.get("choice"))
            if name == "reliable_soft_updates" and chosen is not None and not decision.get("replay_not_recorded"):
                belief.chose(decision["request"], chosen)
        pending = (copy.deepcopy(state), predictions)
    return output, {key: dict(value) for key, value in diagnostics.items()}


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["subset"]].append(row)
    result = {}
    for subset, mine in groups.items():
        loss, zeros, by_kind, per_game = defaultdict(list), Counter(), defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))
        for row in mine:
            distributions = {name: reveal_distribution(candidates, row["kind"], row["known_moves"])
                             for name, candidates in row["predictions"].items()}
            options = set().union(*(set(value) for value in distributions.values()))
            for name, distribution in distributions.items():
                raw = distribution.get(row["revealed"], 0)
                value = -math.log((raw + ALPHA) / (1 + ALPHA * (len(options) + 1)))
                zeros[name] += raw == 0
                loss[name].append(value)
                by_kind[row["kind"]][name].append(value)
                per_game[row["battle_id"]][name].append(value)
        result[subset] = {"revelations": len(mine), "games": len(per_game),
                          "log_loss": {k: sum(v) / len(v) for k, v in loss.items()},
                          "zero_support_revelations": dict(zeros),
                          "candidate_coverage": {k: 1 - zeros[k] / len(v) for k, v in loss.items()},
                          "by_kind": {kind: {k: {"n": len(v), "log_loss": sum(v) / len(v)}
                                             for k, v in arms.items()} for kind, arms in by_kind.items()},
                          "per_game": {game: {k: sum(v) / len(v) for k, v in arms.items()}
                                       for game, arms in per_game.items()}}
    return {"subsets": result, "smoothing_alpha": ALPHA,
            "smoothing": "Add alpha to the union of pre-reveal supported categories plus one reserved OTHER category.",
            "assumptions": "Uniform next new move within each candidate's unrevealed moves; only subsequently revealed facts are labels. No full-set truth supplied, no full-set accuracy claim. Final unseen transition excluded.",
            "parameter_selection": "Likelihood floor remains 0.03; no fitting or tuning on scoring positions."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--priors", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    development = set(plan["development_battles"])
    scoring = set(plan["scoring_battles"])
    if development & scoring:
        raise ValueError("development/scoring battles overlap")
    priors = json.loads(args.priors.read_text())
    rows, unavailable, all_diagnostics = [], [], []
    metadata = Counter()
    for line in args.games.read_text().splitlines():
        game = json.loads(line)
        battle = game.get("battle", f"battle-mcts-{game['game']}" if "game" in game else "unknown")
        if battle not in development | scoring:
            continue
        for role, artifacts in game.get("artifacts", {}).items():
            if role not in plan.get("roles", ["a", "b"]):
                continue
            path = Path(artifacts.get("trace", ""))
            if not path.is_file():
                unavailable.append({"battle": battle, "role": role})
                continue
            decisions = [r for text in path.read_text().splitlines() if (r := json.loads(text)).get("kind") in {"move", "switch"} and "state" in r]
            metadata["decisions"] += len(decisions)
            metadata["completion_metadata_present"] += sum("last_turn_complete" in d["state"] for d in decisions)
            scored_rows, diagnostics = score_transitions(decisions, priors, battle_id=battle, role=role,
                                                        subset="development" if battle in development else "scoring")
            rows.extend(scored_rows)
            all_diagnostics.append({"battle": battle, "role": role, "counts": diagnostics})
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_text("".join(json.dumps(r) + "\n" for r in rows))
    result = {**summarize(rows), "unavailable": unavailable, "diagnostics": all_diagnostics,
              "observation_metadata": dict(metadata),
              "inputs": {"games": str(args.games), "prior_sha256": hashlib.sha256(args.priors.read_bytes()).hexdigest(),
                         "scorer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "runtime_source_sha256": source_identity(Path(__file__).parents[1])["source_sha256"],
                         "engine": engine_identity(),
                         "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest()},
              "scope": plan["scope"]}
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
