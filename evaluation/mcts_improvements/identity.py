"""Content identities of the effective decision pipeline and native binary."""
import hashlib
import importlib.metadata
import json
from pathlib import Path


SOURCE_FOLDERS = ("bot", "decision", "contracts")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_identity(root):
    root = Path(root).resolve()
    paths = [p for name in SOURCE_FOLDERS for p in sorted((root / name).rglob("*.py"))]
    paths += [p for p in (root / "decision/data").glob("*.json")]
    digest = hashlib.sha256()
    files = {}
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        value = file_hash(path)
        files[relative] = value
        digest.update(relative.encode() + b"\0" + value.encode() + b"\0")
    return {"source_sha256": digest.hexdigest(), "files": files}


def engine_identity():
    import poke_engine
    root = Path(poke_engine.__file__).parent
    return {"version": importlib.metadata.version("poke-engine"),
            "binaries": {p.name: file_hash(p) for p in sorted(root.glob("*.so"))}}


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
