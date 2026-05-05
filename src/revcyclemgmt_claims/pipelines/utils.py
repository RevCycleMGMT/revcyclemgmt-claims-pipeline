from pathlib import Path
import hashlib
import json

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def write_json_lines(path: Path, rows):
    ensure_dir(path.parent)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

def lineage_hash(record: dict, keys: list[str]) -> str:
    payload = "|".join(str(record.get(k, "")) for k in keys)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
