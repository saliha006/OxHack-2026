"""Freeze and measure equal-requested-effort allocations on historical development positions.

This is a cold-posterior mechanism/compute diagnostic, not a battle-strength test.
The measured decision pipeline is imported only from an immutable snapshot.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ALLOCATIONS = [(4, 300), (8, 150), (12, 100)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def identity_helpers():
    path = ROOT / "evaluation/mcts_improvements/identity.py"
    spec = importlib.util.spec_from_file_location("allocation_identity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    lo, hi = int(index), min(int(index) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def root_metrics(trace, request, pool_results):
    winners, policies = [], []
    for world in trace.get("worlds", []):
        pooled = pool_results([world], request)
        if pooled["action"] is not None:
            winners.append(pooled["action"].to_choice())
            policies.append({"index": world["index"], "support": pooled["search_support"]})
    counts = Counter(winners)
    support = sorted(trace.get("search_support", {}).values(), reverse=True)
    margin = support[0] - (support[1] if len(support) > 1 else 0) if support else None
    return {"world_winner_counts": dict(counts),
            "world_winner_disagreement": 1 - max(counts.values()) / len(winners) if winners else None,
            "pooled_top_two_margin": margin, "per_world_normalised_support": policies}


def prepare(args):
    helper = identity_helpers()
    snapshot = args.snapshot.resolve()
    prior = (snapshot / "data/set_candidates.json").resolve()
    prior_plan = json.loads(args.development_plan.read_text())
    games = prior_plan["development_battles"][:2]
    positions = []
    for battle in games:
        traces = sorted(args.logs.glob("*/" + battle + ".jsonl"))
        if not traces:
            raise ValueError(f"no trace for planned development battle {battle}")
        path = traces[0]
        eligible = []
        for number, line in enumerate(path.read_text().splitlines(), 1):
            row = json.loads(line)
            request = row.get("request", {})
            if row.get("kind") == "move" and request.get("active") and not any(request.get("forceSwitch", [])):
                eligible.append((number, row))
        if len(eligible) < 3:
            raise ValueError("planned battle needs at least three ordinary move requests")
        for label, index in [("first", 0), ("middle", len(eligible) // 2), ("last", len(eligible) - 1)]:
            line, row = eligible[index]
            positions.append({"id": f"{battle}-{label}", "request": row["request"], "battle": row["state"],
                              "source": {"file": str(path.resolve()), "sha256": sha(path), "line": line,
                                         "battle_id": battle, "turn": row["turn"], "selection": label,
                                         "eligible_move_requests": len(eligible)}})
    args.inputs.parent.mkdir(parents=True, exist_ok=True)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    with args.inputs.open("x") as output:
        json.dump({"positions": positions}, output, indent=2)
        output.write("\n")
    schedule = []
    for repetition in range(3):
        for position, row in enumerate(positions):
            rotation = (position + repetition) % len(ALLOCATIONS)
            for worlds, milliseconds in ALLOCATIONS[rotation:] + ALLOCATIONS[:rotation]:
                schedule.append({"id": len(schedule), "position": row["id"], "repetition": repetition,
                                 "allocation": f"{worlds}x{milliseconds}", "config": {
                                     "backend": "mcts", "budget": 3.0, "mcts_worlds": worlds,
                                     "search_ms": milliseconds, "engine_threads": 1, "sampling": "team",
                                     "frozen_beliefs": False, "belief_mode": "reliable",
                                     "seed": 2026102540 + position}})
    plan = {"schema": 1, "purpose": "historical development mechanism/compute study; no strength or fresh holdout claim",
            "frozen_before_new_measurements": True, "snapshot": str(snapshot), "source": helper.source_identity(snapshot),
            "engine": helper.engine_identity(), "priors": str(prior), "priors_sha256": sha(prior),
            "runner_sha256": sha(__file__), "identity_helper_sha256": sha(ROOT / "evaluation/mcts_improvements/identity.py"),
            "inputs": str(args.inputs.resolve()), "inputs_sha256": sha(args.inputs),
            "positions": [{"id": p["id"], "source": p["source"], "input_sha256": json_sha({"request": p["request"], "battle": p["battle"]})}
                          for p in positions], "schedule": schedule,
            "selection_rule": "first two development battle IDs in existing disjoint plan; first sorted perspective file; first/middle/last ordinary move request by index; no outcome filter",
            "development_plan_sha256": sha(args.development_plan),
            "stopping_rule": "all 54 scheduled calls, including failed calls; no outcome-dependent stopping or resampling",
            "equal_effort": "4x300,8x150,12x100 request1200 native ms each; one thread and3s decision ceiling; actual effort measured separately",
            "sampling": "same world-sampling seed per position across configurations/repeats; native MCTS has no exposed deterministic RNG seed",
            "state_limit": "historical snapshots lack later PP/upkeep metadata; identical supplied facts and fresh posteriors without accumulated soft history in every arm",
            "cpu_scope": "Bot Python process plus reaped SearchWorker descendants between Agent construction and close; source validation/import and coordinator CPU excluded from this delta",
            "tree_continuation": "installed stock wrapper accepts state/duration/iterations/threads; Rust mcts constructs a fresh state and returns root statistics, with no exported tree handle; no tree reuse claimed",
            "load": "one additional sequential native search at a time while separately scheduled game batches may be running; per-call OS load recorded",
            "environment": {"python": platform.python_version(), "logical_cpus": os.cpu_count(),
                            "available_cpu_affinity": len(os.sched_getaffinity(0)), "loadavg": os.getloadavg()},
            "descriptive_close_margin": .05}
    with args.plan.open("x") as output:
        json.dump(plan, output, indent=2)
        output.write("\n")
    print(json.dumps({"frozen_plan": str(args.plan), "positions": len(positions), "calls": len(schedule)}), flush=True)


def worker():
    started = time.monotonic()
    job = json.loads(sys.stdin.read())
    plan, position = job["plan"], job["position"]
    helper = identity_helpers()
    snapshot = Path(plan["snapshot"]).resolve()
    if helper.source_identity(snapshot) != plan["source"] or sha(plan["priors"]) != plan["priors_sha256"]:
        raise RuntimeError("frozen runtime or priors changed")
    sys.path = [str(snapshot)] + [p for p in sys.path if p and Path(p).resolve() != ROOT]
    os.chdir(snapshot)
    from decision.agent import Agent
    from decision.actions import our_actions
    from decision.search_policy import pool_results
    loaded = {name: str(Path(module.__file__).resolve()) for name, module in list(sys.modules.items())
              if name.startswith(("bot.", "decision.", "contracts.")) and getattr(module, "__file__", None)}
    if any(not Path(path).is_relative_to(snapshot) for path in loaded.values()):
        raise RuntimeError("runtime import escaped frozen snapshot")
    if helper.engine_identity() != plan["engine"]:
        raise RuntimeError("engine changed after plan freeze")
    priors = json.loads(Path(plan["priors"]).read_text())
    initial = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    decision_started = time.monotonic()
    agent = Agent(priors, **job["schedule"]["config"])
    try:
        choice = agent.choose(position["request"], position["battle"])
        trace = agent.last_trace
    finally:
        agent.close()
    final = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = sum(r.ru_utime + r.ru_stime for r in final) - sum(r.ru_utime + r.ru_stime for r in initial)
    summary = {"choice": choice, "choice_legal": choice in {a.to_choice() for a in our_actions(position["request"])},
               "latency_ms": trace.get("total_ms"), "native_elapsed_ms": trace.get("search_ms"),
               "preparation_ms": trace.get("state_preparation_ms"), "cpu_ms": cpu * 1000,
               "decision_and_close_ms": (time.monotonic() - decision_started) * 1000,
               "worker_total_wall_ms": (time.monotonic() - started) * 1000,
               "visits": sum(w.get("total_visits", 0) for w in trace.get("worlds", [])),
               **{key: trace.get(key) for key in ("requested_worlds", "scheduled_worlds", "completed_worlds", "usable_worlds",
                                                  "failed_worlds", "interrupted_worlds", "fallback_reason")},
               **root_metrics(trace, position["request"], pool_results)}
    print(json.dumps({"summary": summary, "trace": trace, "loaded_modules": loaded,
                      "source_sha256": plan["source"]["source_sha256"], "engine": plan["engine"],
                      "priors_sha256": plan["priors_sha256"]}), flush=True)


def summarize(rows, plan):
    groups = defaultdict(list)
    for row in rows:
        groups[row["allocation"]].append(row)
    results = {}
    for allocation, mine in groups.items():
        good = [r["result"]["summary"] for r in mine if r.get("result")]
        numeric = ["latency_ms", "native_elapsed_ms", "preparation_ms", "cpu_ms", "visits",
                   "completed_worlds", "usable_worlds", "failed_worlds", "world_winner_disagreement", "pooled_top_two_margin"]
        statistics = {}
        for key in numeric:
            values = [r[key] for r in good if r.get(key) is not None]
            statistics[key] = {"n": len(values), "mean": sum(values) / len(values) if values else None,
                               "p50": percentile(values, .5), "p95": percentile(values, .95),
                               "p99": percentile(values, .99), "max": max(values) if values else None}
        repeats = defaultdict(list)
        for row in mine:
            if row.get("result"):
                repeats[row["position"]].append(row["result"]["summary"]["choice"])
        results[allocation] = {"scheduled": len(mine), "returned": len(good), "worker_errors": len(mine) - len(good),
                               "illegal_choices": sum(not r["choice_legal"] for r in good),
                               "fallbacks": dict(Counter(r["fallback_reason"] for r in good if r["fallback_reason"])),
                               "statistics": statistics,
                               "action_repeat_agreement": {p: {"counts": dict(Counter(values)),
                                                                 "modal_fraction": max(Counter(values).values()) / len(values)}
                                                           for p, values in repeats.items()}}
    return {"scope": plan["purpose"], "planned_calls": len(plan["schedule"]), "recorded_calls": len(rows),
            "source_sha256": plan["source"]["source_sha256"], "engine": plan["engine"],
            "priors_sha256": plan["priors_sha256"], "cpu_scope": plan["cpu_scope"], "allocations": results,
            "interpretation_limit": "six historical positions/three native repeats are descriptive. Search support is not calibrated win probability. Fresh controlled games decide promotion; no adaptive behavior enabled."}


def run(args):
    plan = json.loads(args.plan.read_text())
    if sha(__file__) != plan["runner_sha256"] or sha(ROOT / "evaluation/mcts_improvements/identity.py") != plan["identity_helper_sha256"]:
        raise RuntimeError("measurement code changed after plan freeze")
    if sha(plan["inputs"]) != plan["inputs_sha256"]:
        raise RuntimeError("inputs changed after plan freeze")
    inputs = json.loads(Path(plan["inputs"]).read_text())
    positions = {p["id"]: p for p in inputs["positions"]}
    rows = []
    with args.raw.open("x") as output:
        for schedule in plan["schedule"]:
            load = os.getloadavg()
            row = {**schedule, "loadavg_before": load}
            started = time.monotonic()
            try:
                completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), "worker"],
                                           input=json.dumps({"plan": plan, "position": positions[schedule["position"]],
                                                             "schedule": schedule}), text=True, capture_output=True, timeout=20)
                if completed.returncode:
                    raise RuntimeError(f"worker exited {completed.returncode}: {completed.stderr[-2000:]}")
                row["result"] = json.loads(completed.stdout)
                if completed.stderr:
                    row["stderr"] = completed.stderr
            except Exception as exc:
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
            row.update(coordinator_wall_ms=(time.monotonic() - started) * 1000, loadavg_after=os.getloadavg())
            rows.append(row)
            output.write(json.dumps(row) + "\n")
            output.flush()
            summary = row.get("result", {}).get("summary", {})
            print(json.dumps({"completed": len(rows), "planned": len(plan["schedule"]), "position": schedule["position"],
                              "allocation": schedule["allocation"], "latency_ms": summary.get("latency_ms"),
                              "worlds": summary.get("completed_worlds"), "error": row.get("error")}), flush=True)
    with args.output.open("x") as output:
        json.dump(summarize(rows, plan), output, indent=2)
        output.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("worker")
    prep = sub.add_parser("prepare")
    prep.add_argument("--snapshot", type=Path, required=True)
    prep.add_argument("--development-plan", type=Path, required=True)
    prep.add_argument("--logs", type=Path, required=True)
    prep.add_argument("--inputs", type=Path, required=True)
    prep.add_argument("--plan", type=Path, required=True)
    measure = sub.add_parser("run")
    measure.add_argument("--plan", type=Path, required=True)
    measure.add_argument("--raw", type=Path, required=True)
    measure.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "worker":
        worker()
    elif args.command == "prepare":
        prepare(args)
    else:
        run(args)


if __name__ == "__main__":
    main()
