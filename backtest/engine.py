"""Backtests the strat layer on Tiger's turns: every move turn of a sample of replays, against what p1 played.

The engine only reads rows and passes each turn's BattleState to the strat layer as it is; it never edits them.
"""
import argparse
import json
import math
import random
import statistics
import time
from collections import Counter
from pathlib import Path

from backtest.tiger import DUMP
from decision.adapter import replay_action
from decision.agent import Agent
from decision.belief import sets_from_game

# The other logged actions show no choice: "fainted" (knocked out before acting), "cant:<reason>", or none.
SCORABLE = ("move:", "switch:")


def battle_id(line: str) -> str:
    # row_to_json writes columns in table order, so every line opens with {"battle_id":"<id>"
    return line.split('"', 4)[3]


def sample(dump: Path, split: str, games: int, seed: int) -> list[str]:
    """Battle ids of a seeded random sample from one split ("all" for both)."""
    ids, last = [], None
    with open(dump, encoding="utf-8") as rows:
        for line in rows:
            battle = battle_id(line)
            if battle != last:
                last = battle
                if split == "all" or json.loads(line)["split"] == split:
                    ids.append(battle)
    return random.Random(seed).sample(ids, min(games, len(ids)))


def load(dump: Path, ids: list[str]) -> list[list[dict]]:
    """Each sampled game's rows, in play order (the dump is sorted by game, then turn)."""
    games = {battle: [] for battle in ids}
    with open(dump, encoding="utf-8") as rows:
        for line in rows:
            battle = battle_id(line)
            if battle in games:
                games[battle].append(json.loads(line))
    return list(games.values())


def missing_species(game: list[dict], priors: dict) -> set[str]:
    # Team preview shows all twelve, so the first turn names every species either side can bring.
    teams = game[0]["state"]["sides"].values()
    return {mon["species"] for side in teams for mon in side["pokemon"]} - priors["species"].keys()


def play(game: list[dict], priors: dict, budget: float) -> list[dict]:
    """One record per turn. Every turn goes to the strat, scorable or not, so its belief sees the whole game."""
    our_sets = sets_from_game([row["state"] for row in game], priors)
    agent = Agent(priors, budget=budget)
    turns = []
    for row in game:
        record = {"battle_id": row["battle_id"], "turn": row["turn"], "logged": row["p1_action"],
                  "logged_tera": row["p1_tera_now"]}
        start = time.perf_counter()
        try:
            action = agent.choose_public(row["state"], our_sets)
        except Exception as e:  # a strat failure is a result to record, and the next turn's state doesn't depend on it
            record["error"] = f"{type(e).__name__}: {e}"
        else:
            record.update(chose=replay_action(action, row["state"], our_sets), chose_tera=action.tera,
                          seconds=time.perf_counter() - start)
        turns.append(record)
    return turns


def is_scorable(turn: dict) -> bool:
    return "chose" in turn and (turn["logged"] or "").startswith(SCORABLE)


def is_same(turn: dict) -> bool:
    return is_scorable(turn) and turn["chose"] == turn["logged"]


def by_game_interval(per_game: list[tuple[int, int]], draws: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% interval for the share of same choices, resampling whole games: turns of one game aren't independent."""
    rng = random.Random(seed)
    rates = []
    for _ in range(draws):
        picked = rng.choices(per_game, k=len(per_game))
        rates.append(sum(same for same, _ in picked) / sum(n for _, n in picked))
    rates.sort()
    return rates[int(0.025 * draws)], rates[int(0.975 * draws) - 1]


def summary(played: list[list[dict]], skipped: list[set[str]], sampled: int) -> dict:
    turns = [t for game in played for t in game]
    scored = [t for t in turns if is_scorable(t)]
    same = [t for t in scored if is_same(t)]
    per_game = [(sum(map(is_same, game)), sum(map(is_scorable, game))) for game in played]
    per_game = [(hits, n) for hits, n in per_game if n]
    seconds = sorted(t["seconds"] for t in turns if "seconds" in t)
    return {
        "games": {"sampled": sampled, "played": len(played), "skipped_missing_species": len(skipped)},
        "missing_species": dict(Counter(species for game in skipped for species in game).most_common()),
        "turns": {"total": len(turns), "scorable": len(scored), "errors": sum("error" in t for t in turns)},
        "same_as_p1": {
            "rate": len(same) / len(scored) if scored else None,
            "interval_95": by_game_interval(per_game) if per_game else None,
            "with_tera_too": sum(t["chose_tera"] == t["logged_tera"] for t in same) / len(scored) if scored else None,
        },
        "think_seconds": {"p50": statistics.median(seconds), "p99": seconds[math.ceil(0.99 * len(seconds)) - 1],
                          "max": seconds[-1]} if seconds else None,
        "error_kinds": dict(Counter(t["error"].split(":")[0] for t in turns if "error" in t)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--split", choices=["train", "test", "all"], default="test")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--budget", type=float, default=3.0, help="think time per turn in seconds, as live")
    parser.add_argument("--dump", type=Path, default=DUMP)
    parser.add_argument("--priors", type=Path, default=Path("data/set_candidates.json"))
    parser.add_argument("--out", type=Path, default=Path("runs/backtest"))
    args = parser.parse_args(argv)

    priors = json.loads(args.priors.read_text(encoding="utf-8"))
    games = load(args.dump, sample(args.dump, args.split, args.games, args.seed))
    name = f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{args.split}-{args.games}g-seed{args.seed}"
    args.out.mkdir(parents=True, exist_ok=True)
    played, skipped = [], []
    # Written game by game, so a run cut short keeps every finished game.
    with open(args.out / f"{name}.jsonl", "w", encoding="utf-8", buffering=1) as out:
        for n, game in enumerate(games, 1):
            if missing := missing_species(game, priors):
                skipped.append(missing)
                print(f"game {n}/{len(games)} {game[0]['battle_id']}: skipped, no sets for {', '.join(sorted(missing))}")
                continue
            turns = play(game, priors, args.budget)
            played.append(turns)
            out.writelines(json.dumps(t) + "\n" for t in turns)
            print(f"game {n}/{len(games)} {game[0]['battle_id']}: "
                  f"{sum(map(is_same, turns))}/{sum(map(is_scorable, turns))} same as p1")
    report = summary(played, skipped, len(games))
    (args.out / f"{name}.summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"turns -> {args.out / name}.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
