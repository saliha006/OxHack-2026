"""Turn export from completed local evaluation games, keeping outcomes out of features."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def export_bot_turns(runs: str | Path, *, both_perspectives: bool = False) -> list[dict]:
    runs = Path(runs)
    manifest = json.loads((runs / "eval-manifest.json").read_text(encoding="utf-8"))
    prefix = hashlib.sha256(str(runs.resolve()).encode("utf-8")).hexdigest()[:12]
    rows = []
    seen = set()
    for results in sorted((runs / "eval").glob("*.jsonl")):
        for text in results.read_text(encoding="utf-8").splitlines():
            result = json.loads(text)
            if result["winner"] not in ("a", "b"):
                continue
            if result["battle"] in seen:
                raise ValueError("duplicate battle tag in one run; export separate server sessions separately")
            seen.add(result["battle"])
            artifacts = result.get("artifacts", {}).get("a")
            if not artifacts:
                raise ValueError("game lacks separate artifact paths; cannot safely recover old overwritten traces")
            trace = [json.loads(line) for line in Path(artifacts["trace"]).read_text(encoding="utf-8").splitlines()]
            if not any(line.get("kind") == "end" for line in trace):
                raise ValueError("cannot export an incomplete or truncated game trace")
            raw = Path(artifacts["raw_log"]).read_text(encoding="utf-8").splitlines()
            start = next((line[4:] for line in raw if line.startswith("|t:|")), None)
            if start is None:
                raise ValueError("raw game log has no start timestamp; refusing to invent a time split")
            started_at = datetime.fromtimestamp(int(start), timezone.utc).isoformat()
            a_side = result["side"]
            winner = a_side if result["winner"] == "a" else "p2" if a_side == "p1" else "p1"
            team_hash = manifest["team_hashes"][result["team"]]
            for decision in trace:
                if decision.get("kind") != "move" or "state" not in decision:
                    continue
                state = copy.deepcopy(decision["state"])
                record = {"battle_id": prefix + ":" + result["battle"], "started_at": started_at,
                          "winner": winner, "source": "bot", "state": state,
                          "p1_team": team_hash, "p2_team": team_hash,
                          "team_identity_source": "evaluation manifest full submitted team text hash"}
                rows.append(record)
                if both_perspectives:
                    mirrored = copy.deepcopy(record)
                    mirrored["state"]["us"] = "p2" if state["us"] == "p1" else "p1"
                    rows.append(mirrored)
    return rows
