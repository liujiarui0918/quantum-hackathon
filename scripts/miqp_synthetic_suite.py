from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    rows = []
    for index in range(args.count):
        n = int(rng.integers(args.n_min, args.n_max + 1))
        p = int(rng.integers(args.p_min, args.p_max + 1))
        m1 = int(rng.integers(args.m1_min, args.m1_max + 1))
        m2 = int(rng.integers(args.m2_min, args.m2_max + 1))
        density = float(rng.choice(args.q_densities))
        payload = _make_instance(rng, n=n, p=p, m1=m1, m2=m2, density=density, index=index)
        path = args.output_dir / f"synthetic_miqp_{index:04d}.npz"
        np.savez_compressed(path, **payload)
        rows.append(
            {
                "path": str(path),
                "n": n,
                "p": p,
                "m1": m1,
                "m2": m2,
                "q_density": density,
                "x_seed_ones": int(np.sum(payload["x_seed"])),
            }
        )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote synthetic suite: {args.output_dir} ({len(rows)} instances)")
    print(f"wrote manifest: {args.manifest}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate MIQP-like synthetic .npz instances for route7++ training.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/miqp_synthetic"))
    parser.add_argument("--manifest", type=Path, default=Path("data/miqp_synthetic/manifest.json"))
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--n-min", type=int, default=40)
    parser.add_argument("--n-max", type=int, default=120)
    parser.add_argument("--p-min", type=int, default=10)
    parser.add_argument("--p-max", type=int, default=30)
    parser.add_argument("--m1-min", type=int, default=10)
    parser.add_argument("--m1-max", type=int, default=30)
    parser.add_argument("--m2-min", type=int, default=2)
    parser.add_argument("--m2-max", type=int, default=6)
    parser.add_argument("--q-densities", type=float, nargs="+", default=[0.10, 0.18, 0.30, 0.45])
    return parser


def _make_instance(
    rng: np.random.Generator,
    *,
    n: int,
    p: int,
    m1: int,
    m2: int,
    density: float,
    index: int,
) -> dict[str, np.ndarray]:
    mask = rng.random((n, n)) < density
    upper = np.triu(rng.normal(0.0, 0.8, size=(n, n)) * mask, 1)
    Q = upper + upper.T
    diag = rng.normal(0.0, 0.5, size=n)
    Q[np.diag_indices(n)] = diag
    c = rng.normal(2.5, 1.2, size=n)
    h = rng.uniform(0.1, 2.0, size=p)

    x_seed = (rng.random(n) < rng.uniform(0.18, 0.36)).astype(int)
    y_seed = rng.uniform(0.0, 2.0, size=p)

    A = rng.uniform(-0.8, 1.4, size=(m1, n))
    G = rng.uniform(0.0, 1.2, size=(m1, p))
    slack = rng.uniform(2.0, 8.0, size=m1)
    b = A @ x_seed + G @ y_seed + slack

    B = np.zeros((m2, n), dtype=float)
    b_prime = np.zeros(m2, dtype=float)
    groups = np.array_split(np.arange(n), m2)
    for row, group in enumerate(groups):
        weights = rng.integers(1, 4, size=len(group)).astype(float)
        B[row, group] = weights
        used = float(B[row] @ x_seed)
        b_prime[row] = max(1.0, used + rng.integers(1, max(2, len(group) // 5 + 2)))
    if index % 3 == 0:
        cardinality_row = index % m2
        B[cardinality_row] = 1.0
        b_prime[cardinality_row] = max(1.0, float(np.sum(x_seed) + rng.integers(1, 4)))

    return {
        "n": np.asarray(n),
        "p": np.asarray(p),
        "m1": np.asarray(m1),
        "m2": np.asarray(m2),
        "Q": Q,
        "c": c,
        "h": h,
        "A": A,
        "G": G,
        "b": b,
        "B": B,
        "b_prime": b_prime,
        "x_seed": x_seed,
        "y_seed": y_seed,
    }


if __name__ == "__main__":
    raise SystemExit(main())
