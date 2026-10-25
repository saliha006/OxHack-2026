"""Score pre-reveal posterior snapshots against OU-prior and persistent hard-filter baselines."""
import copy
import json
from dataclasses import asdict
from pathlib import Path

from bot.parser import Parser
from decision.belief import Belief


def _records(belief):
    return [[{"weight": weight, **asdict(candidate)} for candidate, weight in slot] for slot in belief.candidates]


def _next_reveals(before: dict, after: dict, them: str):
    for slot, (old, new) in enumerate(zip(before["sides"][them]["pokemon"], after["sides"][them]["pokemon"])):
        moves = [move for move in new["revealed_moves"] if move not in old["revealed_moves"]]
        if moves:
            yield slot, "move", moves[0], old["revealed_moves"]
        for kind in ("item", "ability", "tera_type"):
            if old.get(kind) is None and new.get(kind):
                yield slot, kind, new[kind], old["revealed_moves"]


def export_belief_records(runs: Path, priors: dict) -> tuple[list[dict], dict]:
    rows, skipped, traces_seen, prior_recoveries, external_roles = [], 0, 0, 0, 0
    for file in sorted((runs / "eval").glob("*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            game = json.loads(line)
            for role, artifacts in game.get("artifacts", {}).items():
                if not artifacts.get("trace"):
                    external_roles += 1
                    continue  # external opponents expose their own log/search artifacts, not our posterior trace
                lines = [json.loads(text) for text in Path(artifacts["trace"]).read_text(encoding="utf-8").splitlines()]
                decisions = [record for record in lines if record.get("kind") in ("move", "switch") and "state" in record]
                if not decisions:
                    continue
                traces_seen += 1
                first = decisions[0]["state"]
                them = "p2" if first["us"] == "p1" else "p1"
                hard = Belief(priors, first)
                prior_recoveries += len(hard.recovery_events)
                original = _records(hard)  # before any update/revelation filtering
                pending = None
                def score_into(next_state):
                    if pending is None:
                        return
                    prediction, hard_sets = pending
                    updated = prediction.get("belief_candidates")
                    if not updated:
                        return
                    for slot, kind, target, known in _next_reveals(prediction["state"], next_state, them):
                        rows.append({"source": "bot", "battle_id": game["battle"], "role": role,
                                     "decision_id": prediction["decision_id"], "kind": kind, "revealed": target,
                                     "predicted_at_turn": prediction["state"]["turn"],
                                     "revealed_by_turn": next_state["turn"], "known_moves": known,
                                     "prior": original[slot], "hard_filter": hard_sets[slot],
                                     "updated": updated[slot]["sets"]})
                for decision in decisions:
                    state = decision["state"]
                    score_into(state)  # strictly before using the next observation to update either baseline
                    hard.last_request = hard.last_choice = None
                    hard.update(state)
                    if not decision.get("belief_candidates"):
                        skipped += 1
                    pending = (decision, copy.deepcopy(_records(hard)))
                final = Parser(first["us"])
                for raw in Path(artifacts["raw_log"]).read_text(encoding="utf-8").splitlines():
                    final.feed(raw)
                score_into(final.snapshot())
    return rows, {"traces": traces_seen, "decisions_without_posterior_excluded": skipped,
                  "revelations": len(rows), "original_prior_recoveries": prior_recoveries,
                  "external_roles_without_trace": external_roles,
                  "ground_truth_sets": "not supplied; no full-set coverage claim"}
