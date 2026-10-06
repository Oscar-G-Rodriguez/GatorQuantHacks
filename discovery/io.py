"""Portable snapshots, atomic receipts and content identities."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def remote_base():
    """Read the personal Blue destination from local configuration, not source control."""
    value = os.environ.get("GQH_REMOTE_BASE", "")
    if not value and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            key, separator, setting = line.partition("=")
            if separator and key.strip() == "GQH_REMOTE_BASE":
                value = setting.strip().strip('"\'')
                break
    if not re.fullmatch(r"/blue/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/quanthacks/discovery", value):
        raise ValueError("Set GQH_REMOTE_BASE in the ignored root .env or environment")
    return value


STUDIES = {
    "H03": "H03 - Lag and Horizon Maps",
    "H04": "H04 - Nonlinear Dependence",
    "H05": "H05 - Controlled Relationships",
    "H06": "H06 - Matched Event Responses",
    "H07": "H07 - Event Sequences and Interactions",
    "H08": "H08 - Incremental Prediction",
    "H09": "H09 - Regime and Tail Effects",
    "H10": "H10 - Feature Redundancy",
    "H11": "H11 - Robustness and Uncertainty",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    """A killed worker leaves no seemingly complete half-written result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def code_identity():
    # Includes dirty/uncommitted implementation, without inventing a commit hash.
    paths = list((ROOT / "discovery").glob("*.py")) + [ROOT / "pyproject.toml", ROOT / "uv.lock"]
    paths += [ROOT / "Hypotheses" / folder / "analysis.py" for folder in STUDIES.values()]
    paths += list((ROOT / "tests").glob("*.py"))
    paths += [ROOT / ".python-version", ROOT / "research_config.py", ROOT / "tools/check_massive_coverage.py"]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in sorted(paths)}


def safe_child(root, relative):
    p = (Path(root) / relative).resolve()
    if not p.is_relative_to(Path(root).resolve()):
        raise ValueError("Path escapes its snapshot")
    return p
