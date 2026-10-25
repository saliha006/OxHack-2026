"""Offline prediction CLI: train, serve and score separately from search."""
import argparse
import hashlib
import json
from pathlib import Path

from prediction.data import read_turns, split_turns
from prediction.evaluation import evaluate, plot_calibration
from prediction.export import export_bot_turns
from prediction.features import FEATURE_NAMES, VERSION
from prediction.likelihood import score_opponent_traces, score_reveals
from prediction.model import WinModel, calibrate, fit_model


def jsonl(paths):
    return [{**json.loads(line), "_trace_namespace": str(Path(path).resolve())}
            for path in paths for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def train(args) -> dict:
    rows = read_turns(args.turns)
    if any(row.get("source", args.source) != args.source for row in rows):
        raise ValueError("input source labels differ from --source; do not relabel bot/public/synthetic evidence")
    splits, manifest = split_turns(rows, args.validation_start, args.test_start)
    model = fit_model(splits["train"], epochs=args.epochs, rate=args.rate, l2=args.l2)
    calibrate(model, splits["validation"], epochs=args.epochs)
    model.metadata.update(source=args.source, input_sha256=hashlib.sha256(args.turns.read_bytes()).hexdigest(),
                          validation_start=manifest["validation_start"], test_start=manifest["test_start"])
    constant = sum(row["winner"] == row["state"]["us"] for row in splits["train"]) / len(splits["train"])
    metrics = {split: evaluate(model, splits[split], constant) for split in ("validation", "test", "test_unseen")}
    results = {"source": args.source, "feature_version": VERSION, "feature_names": FEATURE_NAMES,
               "models": metrics, "split_manifest": manifest, "metadata": model.metadata,
               "claim": "offline prediction experiment; not used in search"}
    args.output.mkdir(parents=True, exist_ok=True)
    model.save(args.output / "model.json")
    (args.output / "metrics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    plot_calibration(metrics["test"], args.output / "calibration")
    if splits["test_unseen"]:
        plot_calibration(metrics["test_unseen"], args.output / "calibration-unseen")
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    training = sub.add_parser("train")
    training.add_argument("--turns", required=True, type=Path)
    training.add_argument("--validation-start", required=True)
    training.add_argument("--test-start", required=True)
    training.add_argument("--source", required=True, choices=("bot", "human", "public_ladder", "synthetic"))
    training.add_argument("--output", type=Path, required=True)
    training.add_argument("--epochs", type=int, default=400)
    training.add_argument("--rate", type=float, default=0.2)
    training.add_argument("--l2", type=float, default=0.001)
    serving = sub.add_parser("predict")
    serving.add_argument("--model", type=Path, required=True)
    serving.add_argument("--state", type=Path, required=True)
    exporting = sub.add_parser("export-bot", help="completed evaluation game artifacts to supervised turn JSONL")
    exporting.add_argument("--runs", type=Path, required=True)
    exporting.add_argument("--output", type=Path, required=True)
    exporting.add_argument("--both-perspectives", action="store_true")
    fetching = sub.add_parser("fetch-replays", help="bounded first one/two pages of latest public gen9ou replays")
    fetching.add_argument("--output", type=Path, required=True)
    fetching.add_argument("--pages", type=int, default=2)
    fetching.add_argument("--limit", type=int, default=100)
    fetching.add_argument("--both-perspectives", action="store_true")
    fetching.add_argument("--manifest", type=Path, help="reuse a frozen selected replay list and verify stable log hashes")
    beliefs = sub.add_parser("score-bot-beliefs", help="pre-reveal exact posterior snapshots against prior/hard-filter baselines")
    beliefs.add_argument("--runs", type=Path, required=True)
    beliefs.add_argument("--priors", type=Path, default=Path("data/set_candidates.json"))
    beliefs.add_argument("--output", type=Path, required=True)
    beliefs.add_argument("--alpha", type=float, default=1e-6)
    for command in ("score-beliefs", "score-actions"):
        scoring = sub.add_parser(command)
        scoring.add_argument("inputs", nargs="+", type=Path)
        scoring.add_argument("--alpha", type=float, default=1e-6)
        scoring.add_argument("--output", type=Path)
        if command == "score-actions":
            scoring.add_argument("--source", required=True, choices=("bot", "human", "public_ladder", "synthetic"))
    args = parser.parse_args(argv)
    if args.command == "score-bot-beliefs":
        from prediction.belief_export import export_belief_records
        priors = json.loads(args.priors.read_text(encoding="utf-8"))
        records, summary = export_belief_records(args.runs, priors)
        result = {"coverage": summary, "scores": score_reveals(records, alpha=args.alpha)}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "pre-reveal-records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        (args.output / "scores.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    elif args.command == "fetch-replays":
        from prediction.replays import fetch_replays
        manifest = fetch_replays(args.output, pages=args.pages, limit=args.limit, both_perspectives=args.both_perspectives,
                                 replay_manifest=args.manifest)
        print(json.dumps({"accepted": len(manifest["accepted"]), "rejected": len(manifest["rejected"]),
                          "turn_rows": manifest["turn_rows"], "validation_start": manifest["validation_start"],
                          "test_start": manifest["test_start"]}, indent=2))
    elif args.command == "export-bot":
        rows = export_bot_turns(args.runs, both_perspectives=args.both_perspectives)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        print(json.dumps({"source": "bot", "rows": len(rows), "battles": len({r['battle_id'] for r in rows})}))
    elif args.command == "train":
        if args.epochs < 1 or args.rate <= 0 or args.l2 < 0:
            parser.error("epochs/rate must be positive and l2 nonnegative")
        result = train(args)
        print(json.dumps({"source": result["source"], "test": result["models"]["test"],
                          "test_unseen": result["models"]["test_unseen"]}, indent=2))
    elif args.command == "predict":
        state = json.loads(args.state.read_text(encoding="utf-8"))
        state = state.get("state", state.get("battle", state))
        model = WinModel.load(args.model)
        print(json.dumps({"win_probability": model.predict(state), "raw_win_probability": model.predict(state, calibrated=False),
                          "feature_version": VERSION, "source": model.metadata.get("source")}))
    else:
        records = jsonl(args.inputs)
        result = (score_reveals(records, alpha=args.alpha) if args.command == "score-beliefs" else
                  score_opponent_traces(records, source=args.source, alpha=args.alpha))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
