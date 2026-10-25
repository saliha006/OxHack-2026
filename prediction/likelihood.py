"""Held-out belief-revelation and observed opponent-action scoring."""
import math
from collections import defaultdict


def reveal_distribution(candidates: list[dict], kind: str, known_moves: list[str] = ()) -> dict[str, float]:
    """Move predictions assume a uniform next new move within each complete candidate set."""
    if kind not in ("move", "item", "ability", "tera_type"):
        raise ValueError("reveal kind must be move, item, ability or tera_type")
    probabilities: dict[str, float] = defaultdict(float)
    for candidate in candidates:
        weight = candidate.get("weight", 0)
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("candidate weights must be finite and nonnegative")
        choices = sorted(set(candidate["moves"]) - set(known_moves)) if kind == "move" else [candidate[kind] or "none"]
        for choice in choices:
            probabilities[choice] += weight / len(choices)
    total = sum(probabilities.values())
    return {key: value / total for key, value in probabilities.items()} if total else {}


def _smoothed(probability: float, categories: int, alpha: float) -> float:
    return (probability + alpha) / (1 + alpha * categories)


def _complete_key(candidate: dict):
    spread = candidate.get("spread", candidate)
    return (tuple(sorted(candidate["moves"])), candidate.get("item") or "none", candidate["ability"],
            candidate["tera_type"], spread["nature"], tuple(spread["evs"]), tuple(candidate.get("ivs", [31] * 6)))


def score_reveals(records: list[dict], *, alpha: float = 1e-6) -> dict:
    """All three candidate distributions must precede the target revelation; source groups never mix."""
    if alpha <= 0:
        raise ValueError("smoothing alpha must be positive")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        source = record["source"]
        if source not in ("bot", "human", "public_ladder", "synthetic"):
            raise ValueError("source must identify bot, human, public_ladder or synthetic evidence")
        grouped[source].append(record)
    results = {}
    for source, mine in grouped.items():
        losses = {name: [] for name in ("prior", "hard_filter", "updated")}
        coverage = {name: [] for name in losses}
        for record in mine:
            distributions = {name: reveal_distribution(record[name], record["kind"], record.get("known_moves", []))
                             for name in losses}
            # Reserve an OTHER category in advance rather than changing the universe after seeing the target.
            options = set().union(*(set(d) for d in distributions.values()))
            target = record["revealed"]
            for name, distribution in distributions.items():
                probability = _smoothed(distribution.get(target, 0), len(options) + 1, alpha)
                losses[name].append(-math.log(probability))
                if record.get("ground_truth_set") is not None:
                    truth = _complete_key(record["ground_truth_set"])
                    coverage[name].append(any(_complete_key(c) == truth and c["weight"] > 0 for c in record[name]))
        results[source] = {"revelations": len(mine), "smoothing_alpha": alpha,
                           "next_move_assumption": "uniform over each set's remaining unrevealed moves",
                           "log_loss": {name: sum(values) / len(values) for name, values in losses.items()},
                           "ground_truth_examples": len(coverage["prior"]),
                           "full_set_coverage": {name: sum(values) / len(values) if values else None
                                                 for name, values in coverage.items()}}
    return results


def score_opponent_traces(records: list[dict], *, source: str, alpha: float = 1e-6) -> dict:
    """Score root visit shares against uniform over recorded native root options, with an OTHER bucket."""
    if source not in ("bot", "human", "public_ladder", "synthetic") or alpha <= 0:
        raise ValueError("provide a valid evidence source and positive smoothing")
    if any(record.get("source", source) != source for record in records):
        raise ValueError("trace source labels differ; score bot and replay evidence separately")
    decisions = {(record.get("_trace_namespace", ""), record["decision_id"]): record for record in records
                 if record.get("decision_id") and record.get("kind") in ("move", "switch", "team")}
    losses, uniform_losses = [], []
    unknown = unsupported = no_prediction = previews = 0
    seen_observations = set()
    for record in records:
        if record.get("kind") != "observation":
            continue
        identity = (record.get("_trace_namespace", ""), record["decision_id"])
        if identity in seen_observations:
            raise ValueError("duplicate observation for one decision")
        seen_observations.add(identity)
        decision = decisions.get(identity)
        if decision is not None and decision.get("kind") == "team":
            previews += 1
            continue
        if not record.get("opponent_actions"):
            unknown += 1
            continue
        if decision is None or not decision.get("opponent_support"):
            no_prediction += 1
            continue
        support = decision["opponent_support"]
        options = set(support)
        for world in decision.get("worlds", []):
            options.update(row["choice"] for row in world.get("opponent_visits", []))
        if not options:
            no_prediction += 1
            continue
        action = record["opponent_actions"][0]
        if action["kind"] == "move":
            target = action["move"] + ("-tera" if action.get("tera") else "")
        elif action["kind"] == "switch":
            us = decision["state"]["us"]
            them = "p2" if us == "p1" else "p1"
            team = decision["state"]["sides"][them]["pokemon"]
            target = "switch " + team[action["slot"]]["species"]
        else:
            unknown += 1
            continue
        total = sum(support.values())
        if total <= 0 or any(not math.isfinite(p) or p < 0 for p in support.values()):
            raise ValueError("invalid opponent visit distribution")
        unsupported += target not in options
        probability = support.get(target, 0) / total
        uniform = 1 / len(options) if target in options else 0
        losses.append(-math.log(_smoothed(probability, len(options) + 1, alpha)))
        uniform_losses.append(-math.log(_smoothed(uniform, len(options) + 1, alpha)))
    return {"source": source, "observed_replies": len(losses), "unknown_replies_excluded": unknown,
            "team_preview_excluded": previews,
            "missing_prediction_excluded": no_prediction, "outside_native_options": unsupported,
            "smoothing_alpha": alpha, "smoothing": "add alpha to every native option plus a reserved OTHER category",
            "visit_log_loss": sum(losses) / len(losses) if losses else None,
            "uniform_log_loss": sum(uniform_losses) / len(uniform_losses) if uniform_losses else None,
            "interpretation": "diagnostic visit-share likelihood, not calibrated action probabilities"}
