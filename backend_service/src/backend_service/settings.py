from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    env = os.environ.get("QUANTUM_HACKATHON_ROOT")
    if env:
        return Path(env)

    current = Path(__file__).resolve().parent
    for ancestor in current.parents:
        if (ancestor / "data").is_dir():
            return ancestor

    raise RuntimeError("Cannot locate project root: no 'data/' directory found in ancestor tree")
