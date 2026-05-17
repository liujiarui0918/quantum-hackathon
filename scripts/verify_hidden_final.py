from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from quantum_hackathon.miqp import load_miqp_npz


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    rows = []
    ok = True
    for index in range(1, 6):
        instance_name = f"miqp_test_{index}"
        input_path = args.input_dir / f"{instance_name}.npz"
        solution_path = _solution_path(args, index, instance_name)
        instance = load_miqp_npz(input_path)
        payload = np.load(solution_path)
        x = np.asarray(payload["x"], dtype=int)
        y = np.asarray(payload["y"], dtype=float)
        objective = instance.objective(x, y)
        report = instance.constraint_report(x, y)
        feasible = instance.is_feasible(x, y)
        stored_objective = float(np.asarray(payload["objective"]))
        stored_feasible = bool(np.asarray(payload["feasible"]))
        objective_delta = abs(objective - stored_objective)
        row = {
            "instance": instance_name,
            "solution": str(solution_path),
            "objective": objective,
            "stored_objective": stored_objective,
            "objective_delta": objective_delta,
            "stored_feasible": stored_feasible,
            "recomputed_feasible": bool(feasible),
            "mixed_max_violation": float(np.max(report.mixed_violation, initial=0.0)),
            "binary_max_violation": float(np.max(report.binary_violation, initial=0.0)),
            "x_ones": int(np.sum(x)),
            "y_nonzero": int(np.sum(np.abs(y) > 1e-9)),
        }
        rows.append(row)
        ok = ok and feasible and stored_feasible and objective_delta <= args.objective_tol
        ok = ok and row["mixed_max_violation"] <= args.violation_tol
        ok = ok and row["binary_max_violation"] <= args.violation_tol

    summary = {"ok": ok, "rows": rows}
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print_markdown(rows)
    return 0 if ok else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify final MIQP hidden-test solution NPZ files.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing miqp_test_1.npz ... miqp_test_5.npz.")
    parser.add_argument("--results-dir", type=Path, default=None, help="Directory containing miqp_test_X_solution.npz.")
    parser.add_argument("--predictions-dir", type=Path, default=None, help="Directory containing miqpscaleX.npz.")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--objective-tol", type=float, default=1e-8)
    parser.add_argument("--violation-tol", type=float, default=1e-7)
    return parser


def _solution_path(args: argparse.Namespace, index: int, instance_name: str) -> Path:
    candidates = []
    if args.predictions_dir is not None:
        candidates.append(args.predictions_dir / f"miqpscale{index}.npz")
    if args.results_dir is not None:
        candidates.append(args.results_dir / f"{instance_name}_solution.npz")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    names = ", ".join(str(candidate) for candidate in candidates) or "no solution directory provided"
    raise FileNotFoundError(f"missing solution for {instance_name}: {names}")


def _print_markdown(rows: list[dict]) -> None:
    headers = [
        "instance",
        "objective",
        "stored_feasible",
        "recomputed_feasible",
        "mixed_max_violation",
        "binary_max_violation",
    ]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        print(
            "| "
            + " | ".join(
                [
                    row["instance"],
                    f"{row['objective']:.12f}",
                    str(row["stored_feasible"]),
                    str(row["recomputed_feasible"]),
                    f"{row['mixed_max_violation']:.3e}",
                    f"{row['binary_max_violation']:.3e}",
                ]
            )
            + " |"
        )


if __name__ == "__main__":
    raise SystemExit(main())
