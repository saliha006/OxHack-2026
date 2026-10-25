"""Condition on recorded modal replies before proposing a strategic guard.

Development diagnostics only: recorded sampled sets are hypotheses, not private
opponent truth. Native work uses the existing isolated streamed deadline worker.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def helpers():
    spec = importlib.util.spec_from_file_location("guard_audit_identity", ROOT / "evaluation/mcts_improvements/identity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime(plan):
    root = Path(plan["snapshot"]).resolve()
    helper = helpers()
    if helper.source_identity(root) != plan["source"] or helper.engine_identity() != plan["engine"]:
        raise RuntimeError("frozen source/engine changed")
    sys.path = [str(root)] + [path for path in sys.path if path and Path(path).resolve() != ROOT]
    from decision.actions import Action
    from decision.adapter import build_state
    from decision.search import SearchWorker, search_state
    from decision.search_policy import pool_results
    loaded = {name: str(Path(module.__file__).resolve()) for name, module in list(sys.modules.items())
              if name.startswith(("bot.", "decision.", "contracts.")) and getattr(module, "__file__", None)}
    if any(not Path(path).is_relative_to(root) for path in loaded.values()):
        raise RuntimeError("runtime import escaped frozen source")
    return loaded


def _action(choice):
    from decision.actions import Action
    parts = choice.split()
    return Action(parts[0], int(parts[1]), "terastallize" in parts)


def _sets(records):
    from decision.sets import PokemonSet
    return [PokemonSet(moves=tuple(record["moves"]), item=record["item"], ability=record["ability"],
                       tera_type=record["tera_type"], nature=record["nature"], evs=tuple(record["evs"]),
                       ivs=tuple(record.get("ivs", [31] * 6))) for record in records]


def _leaves(state, ours, reply):
    from poke_engine import generate_instructions
    from decision.simulate import engine_move
    from decision.value import value
    initial_faints = sum(mon.hp <= 0 for mon in state.side_one.pokemon)
    initial_active = int(state.side_one.active_index)
    leaves = []
    for outcome in generate_instructions(state, engine_move(state.side_one, ours), reply.removeprefix("switch ")):
        if outcome.percentage <= 0:
            continue
        after = state.apply_instructions(outcome)
        us, them = after.side_one, after.side_two
        leaves.append({"probability": outcome.percentage / 100,
                       "our_active_fainted": us.pokemon[int(us.active_index)].hp <= 0,
                       "original_active_fainted": us.pokemon[initial_active].hp <= 0,
                       "new_our_faints": sum(mon.hp <= 0 for mon in us.pokemon) - initial_faints,
                       "our_alive": sum(mon.hp > 0 for mon in us.pokemon),
                       "our_hp_fraction_sum": sum(mon.hp / mon.maxhp for mon in us.pokemon),
                       "foe_alive": sum(mon.hp > 0 for mon in them.pokemon),
                       "foe_hp_fraction_sum": sum(mon.hp / mon.maxhp for mon in them.pokemon),
                       "our_hp_by_slot": [mon.hp for mon in us.pokemon],
                       "foe_hp_by_slot": [mon.hp for mon in them.pokemon],
                       "basic_hp_value": value(after)})
    total = sum(row["probability"] for row in leaves)
    if not leaves or total <= 0:
        raise ValueError("native successor check supplied no positive-probability outcomes")
    for row in leaves:
        row["probability"] /= total
    fields = ["our_active_fainted", "original_active_fainted", "new_our_faints", "our_alive",
              "our_hp_fraction_sum", "foe_alive", "foe_hp_fraction_sum", "basic_hp_value"]
    return {"outcome_mass_before_roundoff_normalisation": total, "outcome_count": len(leaves),
            "expected": {key: sum(row["probability"] * row[key] for row in leaves) for key in fields},
            "leaves": leaves}


def _mon(species, types, moves, *, hp=300, maxhp=300, speed=100, attack=150, defense=220,
         special_attack=150, special_defense=220, item="none", ability="none"):
    from poke_engine import Move, Pokemon
    return Pokemon(id=species, level=100, types=types, base_types=types, hp=hp, maxhp=maxhp,
                   attack=attack, defense=defense, special_attack=special_attack,
                   special_defense=special_defense, speed=speed, item=item, ability=ability,
                   moves=[Move(id=move) for move in moves])


def counterexamples():
    """Concrete native mechanics showing why broad no-op/loop vetoes are unsafe."""
    from poke_engine import Side, State
    from decision.actions import Action
    slow = State(side_one=Side(pokemon=[_mon("toxapex", ("water", "poison"), ["recover", "splash"], speed=30)]),
                 side_two=Side(pokemon=[_mon("snorlax", ("normal", "typeless"), ["tackle"], speed=100)]))
    recover = _leaves(slow, Action("move", 1), "tackle")
    no_recover = _leaves(slow, Action("move", 2), "tackle")
    protect = State(side_one=Side(pokemon=[_mon("blissey", ("normal", "typeless"), ["protect"], hp=200,
                                               maxhp=400, speed=30, item="leftovers")]),
                    side_two=Side(pokemon=[_mon("snorlax", ("normal", "typeless"), ["tackle"], attack=300)]))
    protect_result = _leaves(protect, Action("move", 1), "tackle")
    immunity = State(side_one=Side(pokemon=[_mon("gengar", ("ghost", "poison"), ["shadowball"], speed=200)]),
                     side_two=Side(pokemon=[_mon("snorlax", ("normal", "typeless"), ["tackle"]),
                                            _mon("toxapex", ("water", "poison"), ["splash"])]))
    immune_stays = _leaves(immunity, Action("move", 1), "tackle")
    immune_switches = _leaves(immunity, Action("move", 1), "toxapex")
    regeneration = State(side_one=Side(pokemon=[_mon("toxapex", ("water", "poison"), ["splash"], hp=40,
                                                    maxhp=200, ability="regenerator"),
                                               _mon("corviknight", ("flying", "steel"), ["splash"], hp=200, maxhp=200)]),
                         side_two=Side(pokemon=[_mon("garchomp", ("dragon", "ground"), ["earthquake"], attack=250)]))
    regen_result = _leaves(regeneration, Action("switch", 2), "earthquake")
    return {"full_hp_slower_recovery": {"with_recover": recover, "without_recover": no_recover},
            "protect_residual_healing": protect_result,
            "immune_opponent_can_switch": {"stays": immune_stays, "switches": immune_switches},
            "regenerator_immunity_switch": regen_result}


def _offline_worker(connection, payload):
    from dataclasses import asdict
    loaded = _runtime(payload["plan"])
    from decision.adapter import build_state
    from decision.search import search_state
    try:
        while True:
            job = connection.recv()
            if job["kind"] == "close":
                return
            config = job["config"]
            case = payload["input"]["case"]
            connection.send({"kind": "prepared", "loaded_modules": loaded})
            scheduled = 0
            if config["mode"] == "counterexamples":
                connection.send({"kind": "world_started", "index": 0})
                connection.send({"kind": "world", "result": {"index": 0, "counterexamples": counterexamples()}})
                connection.send({"kind": "done", "scheduled_worlds": 1})
                continue
            tasks = payload["input"]["counterfactual_tasks"] if config["mode"] == "counterfactuals" else [
                {"index": n, "sample_index": n} for n in range(len(case["sampled_worlds"]))]
            for task in tasks:
                reserve = .15 if config["mode"] == "search" else .01
                if time.monotonic() + reserve > job["deadline"]:
                    break
                scheduled += 1
                connection.send({"kind": "world_started", "index": task["index"]})
                started = time.monotonic()
                try:
                    state = build_state(case["request"], case["battle"], _sets(case["sampled_worlds"][task["sample_index"]]))
                    if config["mode"] == "search":
                        result = search_state(state, index=task["index"], duration_ms=150, threads=1)
                    else:
                        result = {**task, "counterfactual": _leaves(state, _action(task["choice"]), task["modal_reply"])}
                    result["elapsed_total_ms"] = (time.monotonic() - started) * 1000
                except BaseException as exc:
                    result = {**task, "error": {"type": type(exc).__name__, "message": str(exc)}}
                # Stream immediately: a later native check cannot discard this completed result.
                connection.send({"kind": "world", "result": result})
            connection.send({"kind": "done", "scheduled_worlds": scheduled})
    except (EOFError, BrokenPipeError):
        pass


def _collect(plan, inputs, mode):
    from decision.search import SearchWorker
    initial = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    worker = SearchWorker({"plan": plan, "input": inputs}, target=_offline_worker)
    messages, results = [], []
    try:
        for message in worker.stream(inputs["case"]["request"], inputs["case"]["battle"],
                                     {"mode": mode}, started + 2.7):
            messages.append(message)
            if message["kind"] == "world":
                results.append(message["result"])
    finally:
        worker.close()
    final = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = sum(r.ru_utime + r.ru_stime for r in final) - sum(r.ru_utime + r.ru_stime for r in initial)
    return {"mode": mode, "wall_ms": (time.monotonic() - started) * 1000, "cpu_ms": cpu * 1000,
            "completed": len(results), "results": results, "messages": [m for m in messages if m["kind"] != "world"]}


def prepare(args):
    helper = helpers()
    loss_report = json.loads(args.loss_report.read_text())
    cases = []
    chosen = None
    for game in loss_report["games"]:
        for example in game["examples"]:
            if example["signature"] != "switch_return_cycle":
                continue
            trace_path = Path(game["trace"])
            decisions = [(line, row) for line, text in enumerate(trace_path.read_text().splitlines(), 1)
                         if (row := json.loads(text)).get("kind") in {"move", "switch"}]
            index = next(n for n, (_, row) in enumerate(decisions) if row.get("decision_id") == example["decision_id"])
            context = [row for _, row in decisions[max(0, index - 2):index + 1]]
            line, row = decisions[index]
            them = "p2" if row["state"]["us"] == "p1" else "p1"
            roots = []
            for decision in context:
                battle = decision["state"]
                us = battle["us"]
                ours, foe = battle["sides"][us], battle["sides"][them]
                roots.append({"turn": decision["turn"], "choice": decision["choice"],
                              "our_active": ours["pokemon"][ours["active"]]["species"],
                              "our_hp_percent_sum": sum(mon["hp_percent"] for mon in ours["pokemon"]),
                              "foe_active": foe["pokemon"][foe["active"]]["species"],
                              "foe_active_hp_percent": foe["pokemon"][foe["active"]]["hp_percent"]})
            original_support = row["search_support"].get(row["choice"], 0)
            near = {choice: weight for choice, weight in row["search_support"].items()
                    if choice.startswith("move ") and "terastallize" not in choice and weight >= .15 and original_support - weight <= .03}
            stable = len({root["foe_active"] for root in roots}) == 1
            cases.append({"battle": game["battle"], "role": game["role"], "trace": str(trace_path),
                          "trace_sha256": sha(trace_path), "line": line, "decision_id": example["decision_id"],
                          "roots": roots, "recorded_world_count": row["requested_worlds"],
                          "opponent_stable": stable, "near_supported_nontera_moves": near,
                          "potentially_eligible": stable and row["requested_worlds"] >= 4 and bool(near)})
            if game["battle"] == "battle-gen9ou-44" and game["role"] == "b":
                chosen = {"request": row["request"], "battle": row["state"], "sampled_worlds": row["sampled_worlds"],
                          "recorded_worlds": row["worlds"], "recorded_choice": row["choice"],
                          "recorded_support": row["search_support"], "near_moves": near,
                          "recorded_config": row["config"], "source": cases[-1]}
    if chosen is None or len(chosen["sampled_worlds"]) != 8:
        raise ValueError("expected recorded eight-world case44b")
    tasks = []
    for sample, world in enumerate(chosen["recorded_worlds"]):
        rows = world["opponent_visits"]
        modal = max(rows, key=lambda row: row["visits"])
        share = modal["visits"] / sum(row["visits"] for row in rows)
        for choice in [chosen["recorded_choice"], *chosen["near_moves"]]:
            tasks.append({"index": len(tasks), "sample_index": sample, "choice": choice,
                          "modal_reply": modal["choice"], "modal_share": share})
    inputs = {"case": chosen, "counterfactual_tasks": tasks}
    with args.inputs.open("x") as output:
        json.dump(inputs, output, indent=2)
        output.write("\n")
    plan = {"purpose": "Historical development guard evidence audit, no strength claim or runtime guard implementation",
            "snapshot": str(args.snapshot.resolve()), "source": helper.source_identity(args.snapshot),
            "engine": helper.engine_identity(), "runner_sha256": sha(__file__), "inputs": str(args.inputs.resolve()),
            "inputs_sha256": sha(args.inputs), "frozen_before_native_checks": True, "cycle_cases": cases,
            "counterfactuals": len(tasks), "world_weighting": "all8 recorded sampled occurrences equally; never weight by visits",
            "candidate_criteria": {"minimum_worlds": 4, "minimum_alternative_support": .15, "maximum_support_gap": .03,
                                   "minimum_modal_reply_support": .25, "hypothetical_mean_switch_ko_threshold": .95},
            "counterexamples": ["slower fullHP recovery after attack", "Protect residual recovery", "immune opponent can switch", "Regenerator and immunity switch"],
            "repeat_search": {"repetitions": 3, "worlds": 8, "native_ms_per_world": 150, "threads": 1,
                              "requested_native_total_ms": 3600, "same_recorded_worlds": True,
                              "batch_ceiling_seconds": 3, "worker_cutoff_seconds": 2.7},
            "stopping": "one40-counterfactual batch, one fixedcounterexample batch, three8x150mssearch repeats; retain partialcompleted results/errors, no outcome-dependent additions",
            "limits": "Native conditional successor model given recorded modal reply and sampled hypotheses; modal/root supports are not calibrated win probabilities. Historical loss and pilot outcomes known. No fresh holdout, no causal or general strength proof. Native continuations unavailable; every search starts a new tree."}
    with args.plan.open("x") as output:
        json.dump(plan, output, indent=2)
        output.write("\n")
    print(json.dumps({"frozen_plan": str(args.plan), "counterfactuals": len(tasks), "cycle_cases": len(cases)}), flush=True)


def run(args):
    plan = json.loads(args.plan.read_text())
    if sha(__file__) != plan["runner_sha256"] or sha(plan["inputs"]) != plan["inputs_sha256"]:
        raise RuntimeError("frozen measurement code or inputs changed")
    loaded = _runtime(plan)
    from decision.search_policy import pool_results
    inputs = json.loads(Path(plan["inputs"]).read_text())
    counterfactuals = _collect(plan, inputs, "counterfactuals")
    examples = _collect(plan, inputs, "counterexamples")
    repeats = []
    for repetition in range(3):
        row = _collect(plan, inputs, "search")
        pooled = pool_results(row["results"], inputs["case"]["request"])
        action = pooled.pop("action")
        row["pooled"] = {**pooled, "choice": action.to_choice() if action else None}
        row["repetition"] = repetition
        repeats.append(row)
    raw = {"counterfactuals": counterfactuals, "counterexamples": examples, "search_repeats": repeats,
           "source_sha256": plan["source"]["source_sha256"], "engine": plan["engine"], "loaded_modules": loaded}
    with args.raw.open("x") as output:
        json.dump(raw, output, indent=2)
        output.write("\n")
    groups = defaultdict(list)
    for row in counterfactuals["results"]:
        if "counterfactual" in row:
            groups[row["choice"]].append(row)
    summary = {choice: {"worlds": len(rows), "expected": {
        key: sum(row["counterfactual"]["expected"][key] for row in rows) / len(rows)
        for key in rows[0]["counterfactual"]["expected"]},
        "per_world": [{"world": row["sample_index"], "modal_reply": row["modal_reply"], "modal_share": row["modal_share"],
                       **row["counterfactual"]["expected"]} for row in rows]} for choice, rows in groups.items()}
    result = {"scope": plan["purpose"], "source_sha256": plan["source"]["source_sha256"],
              "cycle_cases": plan["cycle_cases"], "counterfactuals": summary,
              "recorded_choice": inputs["case"]["recorded_choice"], "recorded_support": inputs["case"]["recorded_support"],
              "search_repeats": [{"repetition": row["repetition"], "wall_ms": row["wall_ms"], "cpu_ms": row["cpu_ms"],
                                  "completed_worlds": len(row["results"]), "native_ms": sum(world.get("elapsed_ms", 0) for world in row["results"]),
                                  "failures": [message for message in row["messages"] if message["kind"] == "failure"],
                                  "pooled": row["pooled"]} for row in repeats],
              "counterfactual_batch": {key: value for key, value in counterfactuals.items() if key != "results"},
              "counterexamples": examples["results"][0].get("counterexamples") if examples["results"] else None,
              "counterexample_batch": {key: value for key, value in examples.items() if key != "results"},
              "raw_sha256": sha(args.raw), "plan_sha256": sha(args.plan), "runtime_guard_enabled": False,
              "interpretation_limit": plan["limits"]}
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"counterfactuals_completed": counterfactuals["completed"],
                      "repeat_choices": [r["pooled"]["choice"] for r in repeats], "output": str(args.output)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--loss-report", type=Path, required=True)
    prep.add_argument("--snapshot", type=Path, required=True)
    prep.add_argument("--inputs", type=Path, required=True)
    prep.add_argument("--plan", type=Path, required=True)
    measure = sub.add_parser("run")
    measure.add_argument("--plan", type=Path, required=True)
    measure.add_argument("--raw", type=Path, required=True)
    measure.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args) if args.command == "prepare" else run(args)


if __name__ == "__main__":
    main()
