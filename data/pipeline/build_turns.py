"""One row per turn: the state at the start of the turn, what each side did, and how the game ended.

States come from saliha's Parser, the one the live bot uses, so features built from these rows match what the agent
sees in a match. The full start-of-turn BattleState is kept as JSON in `state` for derrick's featurizer.
"""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from bot.parser import Parser
from contracts.battle_state import BattleState, SideId

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "clean" / "battles"
OUT = ROOT / "data" / "clean" / "turns"

# The sample: recent training games (2025 onwards) and the test split (games from 2026-05-19, see clean_battles.py).
TRAIN_FROM = "2025-01-01"
TEST_SHARE = 0.25

SIDES: tuple[SideId, SideId] = ("p1", "p2")
TEAM_SIZE = 6
BOOSTS = ("atk", "def", "spa", "spd", "spe")
HAZARDS = ("stealthrock", "spikes", "toxicspikes", "stickyweb")
SIDE_EFFECTS = ("reflect", "lightscreen", "auroraveil", "tailwind")


def snapshots(log: str) -> tuple[list[tuple[BattleState, int | None]], BattleState, int | None]:
    """The parser's state at each |turn| with that moment's |t:| time, then the state and time where the log ends."""
    parser, states, t = Parser("p1"), [], None
    for line in log.split("\n"):
        if line.startswith("|t:|"):
            t = int(line[4:])
        parser.feed(line)
        if line.startswith("|turn|"):
            states.append((parser.snapshot(), t))
    return states, parser.snapshot(), t


def side_columns(state: BattleState, side_id: SideId) -> dict:
    side = state["sides"][side_id]
    team = side["pokemon"]
    active = team[side["active"]] if side["active"] is not None else None
    return {
        "active": active and active["species"],
        "active_hp": active and active["hp_percent"],
        "active_status": (active["status"] or None) if active else None,
        "alive": sum(mon["hp_percent"] > 0 for mon in team),
        # Out of 6: every Pokémon's HP fraction added up. Unrevealed Pokémon count as full, as the bot assumes.
        "hp_total": sum(mon["hp_percent"] for mon in team) / 100,
        "statused": sum(bool(mon["status"]) and mon["hp_percent"] > 0 for mon in team),
        **{boost: side["boosts"].get(boost, 0) for boost in BOOSTS},
        "tera_used": side["tera_used"],
        # Hazards and screens on this side: hazards hurt this side's switch-ins, screens protect this side.
        **{hazard: side["hazards"].get(hazard, 0) for hazard in HAZARDS},
        **{effect: effect in side["side_effects"] for effect in SIDE_EFFECTS},
        "substitute": "substitute" in side["volatiles"],
        # Every Pokémon in team preview order, which holds for the whole game: mon3 is the same Pokémon every turn.
        **{f"mon{k + 1}_{key}": mon and value(mon)
           for k, mon in enumerate(team[:TEAM_SIZE] + [None] * (TEAM_SIZE - len(team)))
           for key, value in (("species", lambda m: m["species"]), ("hp", lambda m: m["hp_percent"]),
                              ("status", lambda m: m["status"] or None))},
    }


def actions(after: BattleState) -> tuple[dict[SideId, str], SideId | None, bool]:
    """What each side did this turn, which side acted first, and whether any hit was a critical.

    A side's action is its first move, switch or can't-move line. If its active Pokémon fainted before acting, the
    action is "fainted": the replacement that follows was forced, not chosen.
    """
    chosen, first = {}, None
    for event in after["last_turn"]:
        side = event["side"]
        if event["type"] == "damage" and event["hp_percent"] == 0 and side not in chosen:
            chosen[side] = "fainted"
        elif event["type"] in ("move", "switch", "cant") and side not in chosen:
            if event["type"] == "move":
                chosen[side] = f"move:{event['move']}"
            elif event["type"] == "switch":
                chosen[side] = "switch:" + after["sides"][side]["pokemon"][event["pokemon"]]["species"]
            else:
                chosen[side] = f"cant:{event['reason']}"
            if first is None and event["type"] != "cant":
                first = side
    crit = any(event["type"] == "damage" and event["crit"] for event in after["last_turn"])
    return chosen, first, crit


def turn_rows(battle_id: str, log: str, started_at: datetime, winner: str, split: str) -> list[dict]:
    states, final, end_t = snapshots(log)
    rows = []
    for i, (state, t) in enumerate(states):
        after, next_t = states[i + 1] if i + 1 < len(states) else (final, end_t)
        chosen, first, crit = actions(after)
        row = {
            "battle_id": battle_id,
            "turn": state["turn"],
            "started_at": started_at,
            "turn_started_at": datetime.fromtimestamp(t, timezone.utc) if t is not None else None,
            # Wall-clock time until the next turn began: both players' thinking plus the turn playing out.
            "seconds_taken": next_t - t if t is not None and next_t is not None else None,
            "split": split,
            "winner": winner,
            "p1_elo": state["sides"]["p1"]["rating"],
            "p2_elo": state["sides"]["p2"]["rating"],
        }
        for side in SIDES:
            before, later = side_columns(state, side), side_columns(after, side)
            row |= {f"{side}_{key}": value for key, value in before.items()}
            row |= {
                f"{side}_action": chosen.get(side),
                f"{side}_tera_now": later["tera_used"] and not before["tera_used"],
                f"{side}_fainted_now": before["alive"] - later["alive"],
            }
        row |= {
            "weather": state["field"]["weather"] or None,
            "terrain": state["field"]["terrain"] or None,
            "trickroom": "trickroom" in state["field"]["effects"],
            "first_mover": first,
            "crit": crit,
            "state": json.dumps(state),
        }
        rows.append(row)
    return rows


def rows_for(battles: list[tuple]) -> list[dict]:
    return [row for battle in battles for row in turn_rows(*battle)]


def sample(games: int, seed: int) -> list[tuple]:
    """Rated games with both Elos, 6+ turns and a winner: (1 - TEST_SHARE) from training since TRAIN_FROM, the rest test."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    con.execute("SET threads = 1")  # REPEATABLE samples are only reproducible on one thread
    files = (CLEAN / "*.parquet").as_posix()
    eligible = (f"SELECT id FROM read_parquet('{files}') WHERE rated AND p1_elo IS NOT NULL AND p2_elo IS NOT NULL"
                " AND turns >= 6 AND winner IN ('p1', 'p2')")
    test = round(games * TEST_SHARE)
    con.execute(f"""CREATE TABLE chosen AS
        SELECT id FROM ({eligible} AND split = 'train' AND started_at >= TIMESTAMPTZ '{TRAIN_FROM}')
            USING SAMPLE reservoir({games - test} ROWS) REPEATABLE ({seed})
        UNION ALL
        SELECT id FROM ({eligible} AND split = 'test') USING SAMPLE reservoir({test} ROWS) REPEATABLE ({seed})""")
    con.execute("SET threads = 8")
    return con.sql(f"""SELECT id, log, started_at, winner, split FROM read_parquet('{files}')
                       WHERE id IN (SELECT id FROM chosen) ORDER BY id""").fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=OUT / "turns_20k.parquet")
    args = parser.parse_args()
    battles = sample(args.games, args.seed)
    batches = [battles[i:i + 200] for i in range(0, len(battles), 200)]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 2)) as pool:
        for batch_rows in pool.map(rows_for, batches):
            rows += batch_rows
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), args.out, compression="zstd")
    acted = [r[f"{s}_action"] for r in rows for s in SIDES if r[f"{s}_action"] not in (None, "fainted")]
    switches = sum(a.startswith("switch:") for a in acted)
    print(f"{args.out.name}: {len(battles)} games, {len(rows)} turns; players switched on {switches / len(acted):.1%}"
          f" of the turns they acted")


if __name__ == "__main__":
    main()
