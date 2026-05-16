from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np

from quantum_hackathon.miqp import (
    MiqpAwareRoute7Solver,
    MiqpBlockScoreWeights,
    MiqpBlockSelector,
    load_miqp_npz,
)
from quantum_hackathon.miqp.model import MiqpInstance


@dataclass(frozen=True)
class SelectorConfig:
    name: str
    strategy: str
    weights: MiqpBlockScoreWeights


CONFIGS = (
    SelectorConfig("default_greedy", "greedy", MiqpBlockScoreWeights(0.30, 0.35, 0.20, 0.15)),
    SelectorConfig("q_heavy_greedy", "greedy", MiqpBlockScoreWeights(0.15, 0.60, 0.15, 0.10)),
    SelectorConfig("constraint_heavy_greedy", "greedy", MiqpBlockScoreWeights(0.15, 0.25, 0.35, 0.25)),
    SelectorConfig("balanced_greedy", "greedy", MiqpBlockScoreWeights(0.25, 0.25, 0.25, 0.25)),
    SelectorConfig("default_cluster", "affinity_cluster", MiqpBlockScoreWeights(0.30, 0.35, 0.20, 0.15)),
    SelectorConfig("q_heavy_cluster", "affinity_cluster", MiqpBlockScoreWeights(0.15, 0.60, 0.15, 0.10)),
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in args.inputs:
        instance = load_miqp_npz(path)
        for config in CONFIGS:
            rows.append(
                _run_config(
                    instance,
                    config,
                    seed=args.seed,
                    max_block_size=args.max_block_size,
                    max_iterations=args.max_iterations,
                    candidate_limit=args.candidate_limit,
                )
            )
    _write_outputs(rows, args.output_dir)
    _plot(rows, args.output_dir / "selector_ablation_gap.png")
    print(f"wrote selector ablation: {args.output_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ablate MIQP route7 block selector weights and cluster strategy.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("submission/selector_ablation"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-block-size", type=int, default=16)
    parser.add_argument("--max-iterations", type=int, default=2)
    parser.add_argument("--candidate-limit", type=int, default=48)
    return parser


def _run_config(
    instance: MiqpInstance,
    config: SelectorConfig,
    *,
    seed: int,
    max_block_size: int,
    max_iterations: int,
    candidate_limit: int,
) -> dict:
    started = perf_counter()
    solver = MiqpAwareRoute7Solver(
        block_selector=MiqpBlockSelector(
            max_block_size=min(max_block_size, instance.n),
            frontier_size=8,
            strategy=config.strategy,
            weights=config.weights,
        ),
        exact_binary_limit=0,
        candidate_limit=candidate_limit,
        max_iterations=max_iterations,
        seed=seed,
        qaoa_max_qubits=0,
    )
    result = solver.solve(instance)
    runtime_ms = (perf_counter() - started) * 1000.0
    objective = result.solution.objective if result.solution.feasible else None
    official = instance.optimal_value
    gap = None
    if objective is not None and official is not None and abs(official) > 1e-12:
        gap = 100.0 * (official - objective) / abs(official)
    history = result.diagnostics.get("block_history", [])
    return {
        "instance": instance.name,
        "selector": config.name,
        "strategy": config.strategy,
        "weights": json.dumps(config.weights.normalized().as_record(), sort_keys=True),
        "objective": _round(objective),
        "official": _round(official),
        "gap_percent": _round(gap),
        "feasible": result.solution.feasible,
        "runtime_ms": round(runtime_ms, 3),
        "candidate_evaluations": result.diagnostics.get("candidate_evaluations", 0),
        "first_block": json.dumps(list(result.block.binary_indices)),
        "block_count": len(history),
    }


def _write_outputs(rows: list[dict], output_dir: Path) -> None:
    (output_dir / "selector_ablation.json").write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "selector_ablation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# MIQP Block Selector Ablation",
        "",
        "| instance | selector | objective | gap_percent | runtime_ms | candidate_evaluations |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['instance']} | {row['selector']} | {row['objective']} | "
            f"{row['gap_percent']} | {row['runtime_ms']} | {row['candidate_evaluations']} |"
        )
    (output_dir / "selector_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(rows: list[dict], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    instances = sorted({row["instance"] for row in rows})
    selectors = [config.name for config in CONFIGS]
    x = np.arange(len(selectors))
    width = 0.8 / max(1, len(instances))
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for offset, instance in enumerate(instances):
        values = []
        for selector in selectors:
            match = next(row for row in rows if row["instance"] == instance and row["selector"] == selector)
            values.append(float(match["gap_percent"]) if match["gap_percent"] is not None else np.nan)
        ax.bar(x + (offset - (len(instances) - 1) / 2) * width, values, width=width, label=instance)
    ax.set_title("Block selector weight/cluster ablation")
    ax.set_ylabel("gap to official optimum (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(selectors, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
