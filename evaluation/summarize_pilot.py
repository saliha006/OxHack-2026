"""Pool recorded reliability/latency from both perspectives, without rerunning search.

    uv run python -m evaluation.summarize_pilot --games evaluation/mcts-pilot-20261025/games.jsonl
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def summarize(rows: list[dict]) -> dict:
    by_arm = defaultdict(list)
    for row in rows:
        by_arm[row["a"]].append(row)
        if row.get("opponent_metrics"):
            by_arm[row["b"]].append(row["opponent_metrics"])
    result = {}
    for arm, summaries in by_arm.items():
        milliseconds = [n for summary in summaries for n in summary.get("decision_ms", [])]
        cuts = (statistics.quantiles(milliseconds, n=100, method="inclusive") if len(milliseconds) > 1
                else [milliseconds[0] if milliseconds else None] * 99)
        counts = {key: sum(s.get(key, 0) for s in summaries) for key in
                  ("decisions", "fallbacks", "rejected_choices", "requested_worlds", "completed_worlds",
                   "failed_worlds", "usable_worlds")}
        result[arm] = {"battle_perspectives": len(summaries), **counts,
                       "p50_ms": cuts[49], "p95_ms": cuts[94], "p99_ms": cuts[98],
                       "maximum_ms": max(milliseconds) if milliseconds else None,
                       "decisions_over_3000_ms": sum(n > 3000 for n in milliseconds),
                       "actual_search_ms": sum(sum(s.get("actual_search_ms", [])) for s in summaries)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize([json.loads(line) for line in args.games.read_text().splitlines() if line.strip()])
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
