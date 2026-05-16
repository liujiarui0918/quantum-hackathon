from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np

from quantum_hackathon.miqp import (
    MiqpAwareRoute7Solver,
    MiqpLearnedBlockScorer,
    MiqpBlockScoreWeights,
    MiqpBlockSelector,
    MiqpWarmStartAdvisor,
    load_miqp_npz,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    scorer = MiqpLearnedBlockScorer.from_path(args.learned_block_model) if args.learned_block_model else None
    rows = []
    summary_rows = []
    for path in args.inputs:
        instance = load_miqp_npz(path)
        for seed in _parse_seeds(args.seeds):
            started = perf_counter()
            solver = MiqpAwareRoute7Solver(
                block_selector=MiqpBlockSelector(
                    max_block_size=min(args.max_block_size, instance.n),
                    frontier_size=args.frontier_size,
                    strategy=args.block_strategy,
                    weights=MiqpBlockScoreWeights(
                        objective=args.weight_objective,
                        coupling=args.weight_coupling,
                        mixed_constraint=args.weight_mixed,
                        binary_constraint=args.weight_binary,
                    ),
                ),
                warm_start_advisor=MiqpWarmStartAdvisor(),
                exact_binary_limit=args.exact_binary_limit,
                candidate_limit=args.candidate_limit,
                max_iterations=args.max_iterations,
                seed=seed,
                block_pool=args.block_pool,
                blocks_per_iteration=args.blocks_per_iteration,
                candidate_budget_per_block=args.candidate_budget_per_block,
                max_lp_evals=args.max_lp_evals,
                time_limit_sec=args.time_limit_sec,
                qaoa_max_qubits=args.qaoa_max_qubits,
                learned_block_scorer=scorer,
            )
            result = solver.solve(instance)
            runtime_ms = (perf_counter() - started) * 1000.0
            result_path = args.results_dir / f"{instance.name}_seed{seed}_trace_result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "instance": instance.diagnostics(),
                        "seed": seed,
                        "runtime_ms": round(runtime_ms, 3),
                        "miqp_aware_route7": result.as_record(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            summary_rows.append(
                {
                    "instance": instance.name,
                    "seed": seed,
                    "objective": result.solution.objective,
                    "feasible": result.solution.feasible,
                    "runtime_ms": round(runtime_ms, 3),
                    "lp_calls": result.diagnostics.get("candidate_evaluations", 0),
                    "result_path": str(result_path),
                }
            )
            for record in result.diagnostics.get("trace_records", []):
                base = {
                    "instance": instance.name,
                    "source_path": str(path),
                    "seed": seed,
                    "objective": result.solution.objective,
                    "feasible": result.solution.feasible,
                    "runtime_ms": round(runtime_ms, 3),
                }
                rows.append({**base, **record})
    args.output_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps({"rows": summary_rows, "trace_rows": len(rows)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote trace rows: {args.output_jsonl} ({len(rows)})")
    print(f"wrote summary: {args.summary}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run route7++ and record block-level training traces.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-jsonl", type=Path, default=Path("results/route7pp/block_traces.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("results/route7pp/trace_summary.json"))
    parser.add_argument("--results-dir", type=Path, default=Path("results/route7pp/results"))
    parser.add_argument("--seeds", default="3,7,11")
    parser.add_argument("--max-block-size", type=int, default=20)
    parser.add_argument("--frontier-size", type=int, default=10)
    parser.add_argument("--block-strategy", choices=["greedy", "affinity_cluster"], default="greedy")
    parser.add_argument("--weight-objective", type=float, default=0.30)
    parser.add_argument("--weight-coupling", type=float, default=0.35)
    parser.add_argument("--weight-mixed", type=float, default=0.20)
    parser.add_argument("--weight-binary", type=float, default=0.15)
    parser.add_argument("--exact-binary-limit", type=int, default=0)
    parser.add_argument("--candidate-limit", type=int, default=128)
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("--block-pool", action="store_true")
    parser.add_argument("--blocks-per-iteration", type=int, default=3)
    parser.add_argument("--candidate-budget-per-block", type=int, default=64)
    parser.add_argument("--max-lp-evals", type=int, default=None)
    parser.add_argument("--time-limit-sec", type=float, default=None)
    parser.add_argument("--qaoa-max-qubits", type=int, default=10)
    parser.add_argument("--learned-block-model", type=Path, default=None)
    return parser


def _parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    return seeds or [7]


if __name__ == "__main__":
    raise SystemExit(main())
