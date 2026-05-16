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
    parser = _build_parser()
    args = parser.parse_args(argv)
    started = perf_counter()
    instance = load_miqp_npz(args.input)
    seeds = _resolve_seeds(args)
    learned_block_scorer = MiqpLearnedBlockScorer.from_path(args.learned_block_model) if args.learned_block_model else None
    results = []
    for seed in seeds:
        solver = MiqpAwareRoute7Solver(
            block_selector=MiqpBlockSelector(
                max_block_size=args.max_block_size,
                frontier_size=args.frontier_size,
                strategy=args.block_strategy,
                weights=MiqpBlockScoreWeights(
                    objective=args.weight_objective,
                    coupling=args.weight_coupling,
                    mixed_constraint=args.weight_mixed,
                    binary_constraint=args.weight_binary,
                ),
            ),
            warm_start_advisor=MiqpWarmStartAdvisor(
                temperature=args.temperature,
                confidence_threshold=args.confidence_threshold,
            ),
            exact_binary_limit=args.exact_binary_limit,
            candidate_limit=args.candidate_limit,
            max_iterations=args.max_iterations,
            seed=seed,
            enable_solver_portfolio=not args.disable_solver_portfolio,
            qaoa_max_qubits=args.qaoa_max_qubits,
            block_pool=args.block_pool,
            blocks_per_iteration=args.blocks_per_iteration,
            candidate_budget_per_block=args.candidate_budget_per_block,
            max_lp_evals=args.max_lp_evals,
            time_limit_sec=args.time_limit_sec,
            learned_block_scorer=learned_block_scorer,
            augment_repaired_candidates=not args.disable_candidate_augmentation,
            post_polish_rounds=args.post_polish_rounds,
            polish_candidate_limit=args.polish_candidate_limit,
        )
        results.append((seed, solver.solve(instance)))
    best_seed, result = max(
        results,
        key=lambda item: (
            item[1].solution.feasible,
            item[1].solution.objective,
        ),
    )
    payload = {
        "instance": instance.diagnostics(),
        "reference_solution": instance.reference_solution_record(),
        "portfolio": [
            {
                "seed": seed,
                "objective": route_result.solution.objective,
                "feasible": route_result.solution.feasible,
                "mode": route_result.diagnostics["mode"],
            }
            for seed, route_result in results
        ],
        "best_seed": best_seed,
        "miqp_aware_route7": result.as_record(),
        "runtime_ms": round((perf_counter() - started) * 1000.0, 3),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.solution_npz is not None:
        args.solution_npz.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            args.solution_npz,
            x=result.solution.x.astype(int),
            y=result.solution.y.astype(float),
            objective=np.asarray(result.solution.objective, dtype=float),
            feasible=np.asarray(result.solution.feasible, dtype=bool),
        )
    if args.trace_jsonl is not None:
        args.trace_jsonl.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for seed, route_result in results:
            for record in route_result.diagnostics.get("trace_records", []):
                row = {
                    "seed": seed,
                    "instance": instance.name,
                    "best_seed": best_seed,
                    "selected_for_submission": seed == best_seed,
                    **record,
                }
                lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
        args.trace_jsonl.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"instance: {instance.name}")
    print(f"objective: {result.solution.objective}")
    print(f"feasible: {result.solution.feasible}")
    print(f"best_seed: {best_seed}")
    print(f"block_size: {len(result.block.binary_indices)}")
    print(f"mode: {result.diagnostics['mode']}")
    print(f"wrote result json: {args.output}")
    if args.solution_npz is not None:
        print(f"wrote solution npz: {args.solution_npz}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solve official MIQP .npz instances with MIQP-aware route 7.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results/miqp_route7_result.json"))
    parser.add_argument("--solution-npz", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--seeds", default=None, help="Comma-separated seed portfolio, e.g. 3,7,11.")
    parser.add_argument("--max-block-size", type=int, default=20)
    parser.add_argument("--frontier-size", type=int, default=10)
    parser.add_argument("--block-strategy", choices=["greedy", "affinity_cluster"], default="greedy")
    parser.add_argument("--weight-objective", type=float, default=0.30)
    parser.add_argument("--weight-coupling", type=float, default=0.35)
    parser.add_argument("--weight-mixed", type=float, default=0.20)
    parser.add_argument("--weight-binary", type=float, default=0.15)
    parser.add_argument("--exact-binary-limit", type=int, default=16)
    parser.add_argument("--candidate-limit", type=int, default=128)
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--confidence-threshold", type=float, default=0.82)
    parser.add_argument("--disable-solver-portfolio", action="store_true")
    parser.add_argument("--qaoa-max-qubits", type=int, default=10)
    parser.add_argument("--block-pool", action="store_true", help="Enable route7++ multi-block pool selection.")
    parser.add_argument("--blocks-per-iteration", type=int, default=1)
    parser.add_argument("--candidate-budget-per-block", type=int, default=None)
    parser.add_argument("--max-lp-evals", type=int, default=None)
    parser.add_argument("--time-limit-sec", type=float, default=None)
    parser.add_argument("--learned-block-model", type=Path, default=None)
    parser.add_argument("--disable-candidate-augmentation", action="store_true")
    parser.add_argument("--post-polish-rounds", type=int, default=0)
    parser.add_argument("--polish-candidate-limit", type=int, default=64)
    parser.add_argument("--trace-jsonl", type=Path, default=None)
    return parser


def _resolve_seeds(args: argparse.Namespace) -> list[int]:
    if args.seeds is None:
        return [args.seed]
    seeds = [int(item.strip()) for item in str(args.seeds).split(",") if item.strip()]
    return seeds or [args.seed]


if __name__ == "__main__":
    raise SystemExit(main())
