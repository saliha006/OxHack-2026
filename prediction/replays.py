"""Bounded public replay acquisition and start-of-turn observations, without look-ahead features."""
import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from bot.parser import Parser

BASE = "https://replay.pokemonshowdown.com"


def replay_rows(replay: dict, *, both_perspectives: bool = False) -> tuple[list[dict], dict]:
    if replay.get("private", 0) != 0:
        raise ValueError("private replay")
    if replay.get("formatid", "gen9ou") != "gen9ou":
        raise ValueError("not gen9ou")
    lines = replay["log"].splitlines()
    if "|rated|" not in lines:
        raise ValueError("not marked rated")
    parser, states = Parser("p1"), []
    for line in lines:
        parser.feed(line)
        if line.startswith("|turn|"):
            states.append(parser.snapshot())
    if len(states) < 6:
        raise ValueError("fewer than six turns")
    winner_name = next((line[5:] for line in reversed(lines) if line.startswith("|win|")), None)
    if winner_name is None:
        raise ValueError("no binary winner")
    normal = lambda name: "".join(c for c in name.casefold() if c.isalnum())
    winner = next((side for side in ("p1", "p2") if normal(parser.state["sides"][side]["player"]) == normal(winner_name)), None)
    if winner is None:
        raise ValueError("winner does not match either player")
    if any(len(states[0]["sides"][side]["pokemon"]) != 6 for side in ("p1", "p2")):
        raise ValueError("not six preview species per side")
    start = next((int(line[4:]) for line in lines if line.startswith("|t:|")), None)
    source = "first public protocol timestamp" if start is not None else "uploadtime approximation"
    if start is None:
        start = replay["uploadtime"]
    started_at = datetime.fromtimestamp(start, timezone.utc).isoformat()
    rows = []
    for state in states:
        row = {"battle_id": replay["id"], "started_at": started_at, "winner": winner, "state": state,
               "source": "public_ladder", "human_status": "unverified", "time_source": source}
        rows.append(row)
        if both_perspectives:
            mirror = copy.deepcopy(row)
            mirror["state"]["us"] = "p2"
            rows.append(mirror)
    return rows, {"battle_id": replay["id"], "turns": len(states), "winner": winner, "started_at": started_at,
                  "time_source": source, "rating": replay.get("rating")}


def chronological_cutoffs(rows: list[dict]) -> tuple[str, str]:
    dates = sorted({row["battle_id"]: row["started_at"] for row in rows}.values())
    if len(dates) < 6:
        raise ValueError("at least six completed battles are needed for a chronological smoke split")
    validation = dates[int(len(dates) * 0.7)]
    test = dates[int(len(dates) * 0.85)]
    if validation >= test or validation <= dates[0]:
        raise ValueError("too few distinct timestamps for three chronological partitions")
    return validation, test


def fetch_replays(output: Path, *, pages: int = 2, limit: int = 100, both_perspectives: bool = False,
                  replay_manifest: Path | None = None) -> dict:
    import requests
    if not 1 <= pages <= 2 or not 1 <= limit <= 100:
        raise ValueError("bounded acquisition supports one/two pages and at most 100 replays")
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "raw"
    raw.mkdir(exist_ok=True)
    entries, sources, expected_logs = {}, [], {}
    if replay_manifest:
        frozen = json.loads(replay_manifest.read_text(encoding="utf-8"))
        entries = {identity: {} for identity in frozen["selected_replays"]}
        sources = frozen["search_sources"]
        expected_logs = {entry["battle_id"]: entry.get("log_sha256") for entry in frozen["accepted"]}
    else:
        for page in range(1, pages + 1):
            url = BASE + "/search.json?format=gen9ou" + (f"&page={page}" if page > 1 else "")
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            content = response.content
            (raw / f"search-page-{page}.json").write_bytes(content)
            sources.append({"url": url, "sha256": hashlib.sha256(content).hexdigest(), "page": page})
            for entry in response.json():
                if entry.get("private", 0) == 0:
                    entries.setdefault(entry["id"], entry)
    selected = list(entries)[:limit]
    def download(identity):
        url = BASE + "/" + identity + ".json"
        path = raw / (identity + ".json")
        try:
            if path.exists():
                content = path.read_bytes()
            else:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                content = response.content
                path.write_bytes(content)
            replay = json.loads(content)
            log_sha = hashlib.sha256(replay["log"].encode("utf-8")).hexdigest()
            if expected_logs.get(identity) and expected_logs[identity] != log_sha:
                raise ValueError("replay log content changed from frozen source manifest")
            rows, metadata = replay_rows(replay, both_perspectives=both_perspectives)
            metadata.update(url=url, sha256=hashlib.sha256(content).hexdigest(), log_sha256=log_sha)
            return rows, metadata, None
        except Exception as error:
            return [], None, {"battle_id": identity, "url": url, "reason": f"{type(error).__name__}: {error}"}
    rows, accepted, rejected = [], [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for turns, meta, rejection in pool.map(download, selected):
            rows.extend(turns)
            if meta:
                accepted.append(meta)
            if rejection:
                rejected.append(rejection)
    rows.sort(key=lambda row: (row["started_at"], row["battle_id"], row["state"]["turn"], row["state"]["us"]))
    data = "".join(json.dumps(row) + "\n" for row in rows).encode("utf-8")
    (output / "turns.jsonl").write_bytes(data)
    validation_start, test_start = chronological_cutoffs(rows)
    manifest = {"source": "public_ladder", "human_status": "unverified; API does not identify bots",
                "acquired_at": datetime.now(timezone.utc).isoformat(), "query": "latest public gen9ou, API order",
                "requested_pages": pages, "limit": limit, "selected_replays": selected,
                "eligibility": "public, gen9ou, marked rated, six preview species per side, >=6 turns, binary winner",
                "selection": "first API entries, no selection by result or model performance",
                "search_sources": sources, "accepted": accepted, "rejected": rejected,
                "turn_rows": len(rows), "turns_sha256": hashlib.sha256(data).hexdigest(),
                "validation_start": validation_start, "test_start": test_start,
                "split_rule": "chronological battle-count boundaries at approximately 70% and 85%; ties stay together"}
    if replay_manifest:
        manifest["frozen_selection_manifest_sha256"] = hashlib.sha256(replay_manifest.read_bytes()).hexdigest()
    (output / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
