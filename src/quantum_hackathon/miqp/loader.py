from __future__ import annotations

from pathlib import Path

import numpy as np

from .model import MiqpInstance


def load_miqp_npz(path: str | Path) -> MiqpInstance:
    source = Path(path)
    payload = np.load(source, allow_pickle=True)
    required = ("n", "p", "m1", "m2", "Q", "c", "h", "A", "G", "b", "B", "b_prime")
    missing = [key for key in required if key not in payload.files]
    if missing:
        raise ValueError(f"missing required MIQP fields: {', '.join(missing)}")

    optional_optimal = _optional_scalar(payload, "optimal_value")
    return MiqpInstance(
        name=source.stem,
        n=int(payload["n"]),
        p=int(payload["p"]),
        m1=int(payload["m1"]),
        m2=int(payload["m2"]),
        Q=np.asarray(payload["Q"], dtype=float),
        c=np.asarray(payload["c"], dtype=float),
        h=np.asarray(payload["h"], dtype=float),
        A=np.asarray(payload["A"], dtype=float),
        G=np.asarray(payload["G"], dtype=float),
        b=np.asarray(payload["b"], dtype=float),
        B=np.asarray(payload["B"], dtype=float),
        b_prime=np.asarray(payload["b_prime"], dtype=float),
        optimal_value=optional_optimal,
        x_opt=_optional_array(payload, "x_opt"),
        y_opt=_optional_array(payload, "y_opt"),
        source_path=source,
    )


def _optional_scalar(payload: np.lib.npyio.NpzFile, key: str) -> float | None:
    if key not in payload.files:
        return None
    return float(payload[key])


def _optional_array(payload: np.lib.npyio.NpzFile, key: str) -> np.ndarray | None:
    if key not in payload.files:
        return None
    return np.asarray(payload[key], dtype=float)
