"""Battle-grouped chronological splitting, with explicit player/team overlap controls."""
import copy
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def timestamp(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def read_turns(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            for key in ("battle_id", "started_at", "winner", "state"):
                if key not in row:
                    raise ValueError(f"turn row {number} lacks {key}")
            if isinstance(row["state"], str):
                row["state"] = json.loads(row["state"])
            if row["winner"] not in ("p1", "p2") or row["state"]["us"] not in ("p1", "p2"):
                raise ValueError(f"turn row {number} has no binary outcome or valid perspective")
            rows.append(row)
    return rows


def _team_key(value) -> str:
    if isinstance(value, list):
        value = sorted(json.dumps(mon, sort_keys=True) for mon in value)
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _metadata(rows: list[dict]) -> dict:
    first = rows[0]
    players = set()
    teams = set()
    proxy = False
    for row in rows:
        if timestamp(row["started_at"]) != timestamp(first["started_at"]) or row["winner"] != first["winner"]:
            raise ValueError(f"inconsistent metadata for battle {first['battle_id']}")
        for side in ("p1", "p2"):
            player = row.get(side) or row["state"]["sides"][side].get("player", "")
            player = "".join(c for c in player.casefold() if c.isalnum())
            if not player:
                raise ValueError("player IDs are required to audit repeated-player leakage")
            players.add(player)
            exact = row.get(side + "_team")
            if exact is None:
                proxy = True
                # Roster identity is a conservative proxy; do not claim exact hidden-set disjointness.
                exact = sorted(m["species"] for m in row["state"]["sides"][side]["pokemon"])
            teams.add(_team_key(exact))
    return {"started_at": timestamp(first["started_at"]), "players": players, "teams": teams,
            "team_identity": "preview_roster_proxy" if proxy else "supplied_complete_team"}


def split_turns(rows: list[dict], validation_start: str, test_start: str) -> tuple[dict, dict]:
    validation_at, test_at = timestamp(validation_start), timestamp(test_start)
    if validation_at >= test_at:
        raise ValueError("validation_start must precede test_start")
    battles: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        battles[str(row["battle_id"])].append(row)
    metadata = {battle: _metadata(turns) for battle, turns in battles.items()}
    assigned = {"train": [], "validation": [], "test": []}
    for battle, meta in sorted(metadata.items(), key=lambda item: (item[1]["started_at"], item[0])):
        split = "train" if meta["started_at"] < validation_at else "validation" if meta["started_at"] < test_at else "test"
        assigned[split].append(battle)
    if not all(assigned.values()):
        raise ValueError("time cutoffs must leave nonempty train, validation and test battle groups")
    split_rows = {split: [row for battle in ids for row in battles[battle]] for split, ids in assigned.items()}
    known_players, known_teams = set(), set()
    controls = {}
    for split in ("train", "validation", "test"):
        ids = assigned[split]
        shared_players = [b for b in ids if metadata[b]["players"] & known_players]
        shared_teams = [b for b in ids if metadata[b]["teams"] & known_teams]
        unseen = [b for b in ids if b not in shared_players and b not in shared_teams]
        controls[split] = {"battles": len(ids), "turns": len(split_rows[split]), "battle_ids": ids,
                           "shared_player_battles": len(shared_players), "shared_team_battles": len(shared_teams),
                           "unseen_battle_ids": unseen,
                           "roster_proxy_battles": sum(metadata[b]["team_identity"] == "preview_roster_proxy" for b in ids)}
        if split != "train":
            split_rows[split + "_unseen"] = [row for b in unseen for row in battles[b]]
        for battle in ids:
            known_players.update(metadata[battle]["players"])
            known_teams.update(metadata[battle]["teams"])
    manifest = {"validation_start": validation_at.isoformat(), "test_start": test_at.isoformat(),
                "grouping": "whole battles ordered by started_at; no turn-level random split",
                "unseen_control": "exclude any player or team appearing in any earlier split",
                "splits": controls}
    return split_rows, manifest
