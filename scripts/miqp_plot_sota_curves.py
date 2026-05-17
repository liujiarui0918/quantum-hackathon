from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    rows = _collect_rows(args.input_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "sota_loss_curves.csv"
    _write_csv(rows, csv_path)
    if rows:
        _plot(rows, args.output_dir / "sota_loss_curves.png")
    print(f"wrote SOTA curve data: {csv_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot incumbent objective/loss curves from MIQP route7++ outputs.")
    parser.add_argument("--input-dir", type=Path, default=Path("results/hidden_demo"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/hidden_demo/figures"))
    return parser


def _collect_rows(input_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("miqp_test_*/*_best_route7.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        instance = payload.get("instance", {}).get("name", path.parent.name)
        best_run = payload.get("best_run", {})
        final_objective = float(best_run.get("objective", 0.0))
        history = payload.get("miqp_aware_route7", {}).get("diagnostics", {}).get("block_history", [])
        cumulative_lp = 0
        best_so_far: float | None = None
        for record in history:
            cumulative_lp += int(record.get("lp_calls") or 0)
            objective = record.get("global_best_objective")
            if objective is None:
                objective = record.get("iteration_best_objective")
            if objective is None:
                continue
            best_so_far = max(float(objective), best_so_far) if best_so_far is not None else float(objective)
            rows.append(_curve_row(instance, cumulative_lp, best_so_far, final_objective, "block"))
        for record in history[-1].get("polish", []) if history else []:
            cumulative_lp += int(record.get("lp_calls") or 0)
            objective = record.get("best_objective")
            if objective is None:
                continue
            best_so_far = max(float(objective), best_so_far) if best_so_far is not None else float(objective)
            rows.append(_curve_row(instance, cumulative_lp, best_so_far, final_objective, "polish"))
        if not any(row["instance"] == instance for row in rows):
            rows.append(_curve_row(instance, 0, final_objective, final_objective, "final"))
    return rows


def _curve_row(instance: str, lp_calls: int, objective: float, final_objective: float, phase: str) -> dict[str, Any]:
    loss = max(0.0, final_objective - objective)
    loss_percent = None if abs(final_objective) <= 1e-12 else 100.0 * loss / abs(final_objective)
    return {
        "instance": instance,
        "lp_calls": lp_calls,
        "objective": objective,
        "final_objective": final_objective,
        "relative_loss": loss,
        "relative_loss_percent": loss_percent,
        "phase": phase,
    }


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    headers = [
        "instance",
        "lp_calls",
        "objective",
        "final_objective",
        "relative_loss",
        "relative_loss_percent",
        "phase",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _plot(rows: list[dict[str, Any]], path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib unavailable, skipped PNG plot: {exc}")
        return
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for instance in sorted({row["instance"] for row in rows}):
        series = [row for row in rows if row["instance"] == instance]
        xs = [row["lp_calls"] for row in series]
        ys = [row["relative_loss_percent"] or 0.0 for row in series]
        ax.plot(xs, ys, marker="o", linewidth=2, label=instance)
    ax.set_xlabel("LP evaluations")
    ax.set_ylabel("Relative loss to final incumbent (%)")
    ax.set_title("route7++ SOTA convergence curve")
    ax.grid(True, alpha=0.28)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    print(f"wrote SOTA loss curve: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
