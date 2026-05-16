from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np

from quantum_hackathon.miqp import (
    MiqpAwareRoute7Solver,
    MiqpLearnedBlockScorer,
    MiqpBlockScoreWeights,
    MiqpBlockSelector,
    load_miqp_npz,
)
from quantum_hackathon.miqp.model import MiqpInstance


@dataclass(frozen=True)
class SotaConfig:
    name: str
    block_pool: bool
    blocks_per_iteration: int
    max_block_size: int
    candidate_limit: int
    candidate_budget_per_block: int | None
    max_iterations: int
    weights: MiqpBlockScoreWeights
    strategy: str = "greedy"
    qaoa_max_qubits: int = 10
    use_learned: bool = False
    augment_repaired_candidates: bool = True
    post_polish_rounds: int = 0
    polish_candidate_limit: int = 64


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scorer = MiqpLearnedBlockScorer.from_path(args.learned_block_model) if args.learned_block_model else None
    all_rows = []
    for path in _resolve_inputs(args.inputs):
        instance = load_miqp_npz(path)
        rows, best = _run_instance(instance, args, scorer)
        all_rows.extend(rows)
        _write_instance_outputs(instance, rows, best, args.output_dir)
    summary = {"rows": all_rows}
    (args.output_dir / "auto_sota_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown(all_rows, args.output_dir / "auto_sota_summary.md")
    print(f"wrote auto SOTA results: {args.output_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run route7++ config race and select the best feasible MIQP result.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/auto_sota"))
    parser.add_argument("--seeds", default="3,7,11,19")
    parser.add_argument("--exact-binary-limit", type=int, default=16)
    parser.add_argument("--max-lp-evals", type=int, default=800)
    parser.add_argument("--time-limit-sec", type=float, default=None)
    parser.add_argument("--learned-block-model", type=Path, default=None)
    parser.add_argument("--include-qaoa", action="store_true")
    parser.add_argument("--profile", choices=["quick", "safe", "deep"], default="safe")
    parser.add_argument("--max-configs", type=int, default=None)
    parser.add_argument("--disable-candidate-augmentation", action="store_true")
    return parser


def _resolve_inputs(paths: Sequence[Path]) -> list[Path]:
    resolved = []
    for path in paths:
        if path.is_dir():
            resolved.extend(sorted(path.glob("*.npz")))
        else:
            resolved.append(path)
    return resolved


def _configs(has_learned: bool, include_qaoa: bool, profile: str = "safe") -> list[SotaConfig]:
    qaoa_cap = 10 if include_qaoa else 0
    configs = [
        SotaConfig(
            "route7_safe",
            block_pool=False,
            blocks_per_iteration=1,
            max_block_size=20,
            candidate_limit=128,
            candidate_budget_per_block=None,
            max_iterations=5,
            weights=MiqpBlockScoreWeights(),
            qaoa_max_qubits=qaoa_cap,
        ),
        SotaConfig(
            "route7pp_balanced",
            block_pool=True,
            blocks_per_iteration=3,
            max_block_size=20,
            candidate_limit=192,
            candidate_budget_per_block=64,
            max_iterations=4,
            weights=MiqpBlockScoreWeights(0.25, 0.25, 0.25, 0.25),
            qaoa_max_qubits=qaoa_cap,
        ),
        SotaConfig(
            "route7pp_cluster",
            block_pool=True,
            blocks_per_iteration=3,
            max_block_size=20,
            candidate_limit=192,
            candidate_budget_per_block=64,
            max_iterations=4,
            weights=MiqpBlockScoreWeights(0.30, 0.35, 0.20, 0.15),
            strategy="affinity_cluster",
            qaoa_max_qubits=qaoa_cap,
        ),
        SotaConfig(
            "route7pp_wide",
            block_pool=True,
            blocks_per_iteration=4,
            max_block_size=20,
            candidate_limit=256,
            candidate_budget_per_block=64,
            max_iterations=5,
            weights=MiqpBlockScoreWeights(0.20, 0.35, 0.25, 0.20),
            qaoa_max_qubits=qaoa_cap,
        ),
    ]
    if profile in {"safe", "deep"}:
        configs.extend(
            [
                SotaConfig(
                    "route7pp_b_heavy",
                    block_pool=True,
                    blocks_per_iteration=3,
                    max_block_size=20,
                    candidate_limit=224,
                    candidate_budget_per_block=72,
                    max_iterations=5,
                    weights=MiqpBlockScoreWeights(0.18, 0.22, 0.22, 0.38),
                    qaoa_max_qubits=qaoa_cap,
                    post_polish_rounds=1,
                    polish_candidate_limit=48,
                ),
                SotaConfig(
                    "route7pp_q_heavy",
                    block_pool=True,
                    blocks_per_iteration=3,
                    max_block_size=20,
                    candidate_limit=224,
                    candidate_budget_per_block=72,
                    max_iterations=5,
                    weights=MiqpBlockScoreWeights(0.15, 0.58, 0.17, 0.10),
                    qaoa_max_qubits=qaoa_cap,
                    post_polish_rounds=1,
                    polish_candidate_limit=48,
                ),
            ]
        )
    if profile == "deep":
        configs.extend(
            [
                SotaConfig(
                    "route7pp_cluster_deep",
                    block_pool=True,
                    blocks_per_iteration=4,
                    max_block_size=22,
                    candidate_limit=320,
                    candidate_budget_per_block=80,
                    max_iterations=6,
                    weights=MiqpBlockScoreWeights(0.22, 0.42, 0.20, 0.16),
                    strategy="affinity_cluster",
                    qaoa_max_qubits=qaoa_cap,
                    post_polish_rounds=2,
                    polish_candidate_limit=96,
                ),
                SotaConfig(
                    "route7pp_large_block_polish",
                    block_pool=True,
                    blocks_per_iteration=4,
                    max_block_size=24,
                    candidate_limit=384,
                    candidate_budget_per_block=96,
                    max_iterations=6,
                    weights=MiqpBlockScoreWeights(0.20, 0.35, 0.20, 0.25),
                    qaoa_max_qubits=qaoa_cap,
                    post_polish_rounds=2,
                    polish_candidate_limit=128,
                ),
            ]
        )
    if profile == "quick":
        configs = configs[:2]
    if has_learned:
        configs.append(
            SotaConfig(
                "learned_route7_shadow",
                block_pool=True,
                blocks_per_iteration=4,
                max_block_size=20,
                candidate_limit=256,
                candidate_budget_per_block=64,
                max_iterations=5,
                weights=MiqpBlockScoreWeights(0.25, 0.25, 0.25, 0.25),
                qaoa_max_qubits=qaoa_cap,
                use_learned=True,
                post_polish_rounds=1,
            )
        )
    return configs


def _run_instance(
    instance: MiqpInstance,
    args: argparse.Namespace,
    scorer: MiqpLearnedBlockScorer | None,
) -> tuple[list[dict], tuple[dict, object]]:
    rows = []
    best_pair: tuple[dict, object] | None = None
    configs = _configs(scorer is not None, args.include_qaoa, args.profile)
    if args.max_configs is not None:
        configs = configs[: max(1, args.max_configs)]
    for config in configs:
        for seed in _parse_seeds(args.seeds):
            started = perf_counter()
            solver = MiqpAwareRoute7Solver(
                block_selector=MiqpBlockSelector(
                    max_block_size=min(config.max_block_size, instance.n),
                    frontier_size=10,
                    strategy=config.strategy,
                    weights=config.weights,
                ),
                exact_binary_limit=args.exact_binary_limit,
                candidate_limit=config.candidate_limit,
                max_iterations=config.max_iterations,
                seed=seed,
                block_pool=config.block_pool,
                blocks_per_iteration=config.blocks_per_iteration,
                candidate_budget_per_block=config.candidate_budget_per_block,
                max_lp_evals=args.max_lp_evals,
                time_limit_sec=args.time_limit_sec,
                qaoa_max_qubits=config.qaoa_max_qubits,
                learned_block_scorer=scorer if config.use_learned else None,
                augment_repaired_candidates=config.augment_repaired_candidates
                and not args.disable_candidate_augmentation,
                post_polish_rounds=config.post_polish_rounds,
                polish_candidate_limit=config.polish_candidate_limit,
            )
            result = solver.solve(instance)
            runtime_ms = (perf_counter() - started) * 1000.0
            gap = None
            if instance.optimal_value is not None and abs(instance.optimal_value) > 1e-12:
                gap = 100.0 * (instance.optimal_value - result.solution.objective) / abs(instance.optimal_value)
            row = {
                "instance": instance.name,
                "config": config.name,
                "seed": seed,
                "objective": result.solution.objective,
                "feasible": result.solution.feasible,
                "gap_percent": gap,
                "runtime_ms": round(runtime_ms, 3),
                "lp_calls": result.diagnostics.get("candidate_evaluations", 0),
                "block_pool": config.block_pool,
                "use_learned": config.use_learned,
                "profile": args.profile,
                "post_polish_rounds": config.post_polish_rounds,
                "polish_candidate_limit": config.polish_candidate_limit,
                "augment_repaired_candidates": config.augment_repaired_candidates
                and not args.disable_candidate_augmentation,
            }
            history = result.diagnostics.get("block_history", [])
            if history:
                polish_records = history[-1].get("polish", [])
                row["polish_rounds_ran"] = len(polish_records)
                row["polish_lp_calls"] = sum(int(item.get("lp_calls", 0)) for item in polish_records)
            rows.append(row)
            if result.solution.feasible and (
                best_pair is None or result.solution.objective > best_pair[0]["objective"]
            ):
                best_pair = (row, result)
    if best_pair is None:
        best_pair = (rows[0], None)
    return rows, best_pair


def _write_instance_outputs(
    instance: MiqpInstance,
    rows: list[dict],
    best_pair: tuple[dict, object],
    output_dir: Path,
) -> None:
    best_row, best_result = best_pair
    (output_dir / f"{instance.name}_all_runs.json").write_text(
        json.dumps({"rows": rows, "best": best_row}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if best_result is None:
        return
    result_payload = {
        "instance": instance.diagnostics(),
        "best_run": best_row,
        "miqp_aware_route7": best_result.as_record(),
    }
    (output_dir / f"{instance.name}_best_route7.json").write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(
        output_dir / f"{instance.name}_best_solution.npz",
        x=best_result.solution.x.astype(int),
        y=best_result.solution.y.astype(float),
        objective=np.asarray(best_result.solution.objective, dtype=float),
        feasible=np.asarray(best_result.solution.feasible, dtype=bool),
    )


def _write_markdown(rows: list[dict], path: Path) -> None:
    headers = [
        "instance",
        "config",
        "profile",
        "seed",
        "objective",
        "gap_percent",
        "feasible",
        "runtime_ms",
        "lp_calls",
        "polish_rounds_ran",
    ]
    lines = ["# MIQP Auto SOTA Summary", "", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    return seeds or [7]


if __name__ == "__main__":
    raise SystemExit(main())
