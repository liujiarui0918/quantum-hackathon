from __future__ import annotations

import argparse
import csv
import json
import math
import random
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from quantum_hackathon.miqp import (
    MiqpAwareRoute7Solver,
    MiqpBlockSelector,
    MiqpCutAdvisor,
    MiqpWarmStartAdvisor,
    load_miqp_npz,
)
from quantum_hackathon.miqp.model import MiqpInstance, MiqpSolution
from quantum_hackathon.miqp.route7 import build_block_binary_problem, repair_binary_constraints
from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder
from quantum_hackathon.solvers.base import SamplerConfig
from quantum_hackathon.solvers.exact import ExactSolverBackend
from quantum_hackathon.solvers.learning_guided import LearningGuidedSamplerBackend
from quantum_hackathon.solvers.qaoa import CostHamiltonianBuilder, QaoaConfig, QaoaRunner
from quantum_hackathon.solvers.simulated_annealing import SimulatedAnnealingBackend


@dataclass
class StudyRecord:
    instance: str
    method: str
    family: str
    status: str
    feasible: bool
    objective: float | None
    official: float | None
    gap_percent: float | None
    runtime_ms: float
    peak_kib: float
    candidates_evaluated: int
    binary_variables: int
    search_bits: int
    qaoa_qubits: int = 0
    qaoa_layers: int = 0
    qaoa_shots: int = 0
    qaoa_rzz_per_layer: int = 0
    notes: str = ""
    x: list[int] = field(default_factory=list)

    def as_row(self) -> dict[str, Any]:
        return {
            "instance": self.instance,
            "method": self.method,
            "family": self.family,
            "status": self.status,
            "feasible": self.feasible,
            "objective": _round_optional(self.objective),
            "official": _round_optional(self.official),
            "gap_percent": _round_optional(self.gap_percent),
            "runtime_ms": round(self.runtime_ms, 3) if math.isfinite(self.runtime_ms) else None,
            "peak_kib": round(self.peak_kib, 3) if math.isfinite(self.peak_kib) else None,
            "candidates_evaluated": self.candidates_evaluated,
            "binary_variables": self.binary_variables,
            "search_bits": self.search_bits,
            "qaoa_qubits": self.qaoa_qubits,
            "qaoa_layers": self.qaoa_layers,
            "qaoa_shots": self.qaoa_shots,
            "qaoa_rzz_per_layer": self.qaoa_rzz_per_layer,
            "notes": self.notes,
        }


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = args.output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[StudyRecord] = []
    instances = [load_miqp_npz(path) for path in args.inputs]
    for instance in instances:
        records = run_instance_study(
            instance,
            seed=args.seed,
            random_reads=args.random_reads,
            sa_reads=args.sa_reads,
            sa_sweeps=args.sa_sweeps,
            qaoa_block_size=args.qaoa_block_size,
            qaoa_shots=args.qaoa_shots,
            global_binary_bit_cap=args.global_binary_bit_cap,
            meta_population=args.meta_population,
            meta_iterations=args.meta_iterations,
            route7_json_dir=args.route7_json_dir,
            route7_max_iterations=args.route7_max_iterations,
            route7_candidate_limit=args.route7_candidate_limit,
        )
        all_records.extend(records)
        _plot_instance_figures(instance, records, figure_dir)

    _plot_cross_instance_figures(all_records, figure_dir)
    _write_outputs(all_records, args.output_dir)
    print(f"wrote benchmark study: {args.output_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MIQP baselines and render comparison figures.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("submission/baseline_study"))
    parser.add_argument("--route7-json-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--random-reads", type=int, default=96)
    parser.add_argument("--sa-reads", type=int, default=48)
    parser.add_argument("--sa-sweeps", type=int, default=80)
    parser.add_argument("--qaoa-block-size", type=int, default=10)
    parser.add_argument("--qaoa-shots", type=int, default=160)
    parser.add_argument("--global-binary-bit-cap", type=int, default=32)
    parser.add_argument("--meta-population", type=int, default=24)
    parser.add_argument("--meta-iterations", type=int, default=8)
    parser.add_argument("--route7-max-iterations", type=int, default=5)
    parser.add_argument("--route7-candidate-limit", type=int, default=128)
    return parser


def run_instance_study(
    instance: MiqpInstance,
    *,
    seed: int,
    random_reads: int,
    sa_reads: int,
    sa_sweeps: int,
    qaoa_block_size: int,
    qaoa_shots: int,
    global_binary_bit_cap: int,
    meta_population: int,
    meta_iterations: int,
    route7_json_dir: Path | None,
    route7_max_iterations: int,
    route7_candidate_limit: int,
) -> list[StudyRecord]:
    advisor = MiqpCutAdvisor()
    rng = random.Random(seed)
    records: list[StudyRecord] = []

    records.append(
        _profile(
            instance,
            "zero_x_lp",
            "classical_baseline",
            lambda: _evaluate_single_x(instance, advisor, np.zeros(instance.n, dtype=int), "x=0"),
            search_bits=0,
            candidates_evaluated=1,
        )
    )

    records.append(
        _profile(
            instance,
            "marginal_greedy_lp",
            "classical_baseline",
            lambda: _marginal_greedy(instance, advisor),
            search_bits=instance.n,
            candidates_evaluated=instance.n,
        )
    )

    records.append(
        _profile(
            instance,
            "structural_warm_start_lp",
            "learning_guided_baseline",
            lambda: _warm_start_candidate(instance, advisor),
            search_bits=instance.n,
            candidates_evaluated=1,
        )
    )

    records.append(
        _profile(
            instance,
            "random_repair_lp",
            "classical_stochastic",
            lambda: _random_repair_search(instance, advisor, rng, random_reads),
            search_bits=instance.n,
            candidates_evaluated=random_reads,
        )
    )

    records.append(
        _profile(
            instance,
            "genetic_repair_lp",
            "classical_metaheuristic",
            lambda: _genetic_algorithm_search(instance, advisor, rng, meta_population, meta_iterations),
            search_bits=instance.n,
            candidates_evaluated=meta_population * meta_iterations,
        )
    )

    records.append(
        _profile(
            instance,
            "binary_pso_repair_lp",
            "classical_metaheuristic",
            lambda: _binary_pso_search(instance, advisor, rng, meta_population, meta_iterations),
            search_bits=instance.n,
            candidates_evaluated=meta_population * meta_iterations,
        )
    )

    if instance.n <= 22:
        exact_evaluations = 2**instance.n
        records.append(
            _profile(
                instance,
                "exact_binary_lp",
                "classical_exact",
                lambda: _exact_binary_search(instance, advisor),
                search_bits=instance.n,
                candidates_evaluated=exact_evaluations,
            )
        )
    else:
        records.append(
            _skipped_record(
                instance,
                method="exact_binary_lp",
                family="classical_exact",
                reason=f"skipped because n={instance.n} would require 2^n enumeration",
                search_bits=instance.n,
            )
        )

    if instance.n <= global_binary_bit_cap:
        records.append(
            _profile(
                instance,
                "global_binary_sa_lp",
                "classical_annealing",
                lambda: _global_binary_backend_search(
                    instance,
                    advisor,
                    SimulatedAnnealingBackend(),
                    SamplerConfig(seed=seed, num_reads=sa_reads, num_sweeps=sa_sweeps, return_top_k=20),
                ),
                search_bits=instance.n,
                candidates_evaluated=sa_reads,
            )
        )

        records.append(
            _profile(
                instance,
                "global_learning_guided_lp",
                "learning_guided_baseline",
                lambda: _global_binary_backend_search(
                    instance,
                    advisor,
                    LearningGuidedSamplerBackend(),
                    SamplerConfig(seed=seed, num_reads=sa_reads, num_sweeps=max(8, sa_sweeps // 2), return_top_k=20),
                ),
                search_bits=instance.n,
                candidates_evaluated=sa_reads,
            )
        )
    else:
        records.append(
            _skipped_record(
                instance,
                method="global_binary_sa_lp",
                family="classical_annealing",
                reason=f"skipped: n={instance.n} exceeds global binary cap {global_binary_bit_cap}",
                search_bits=instance.n,
            )
        )
        records.append(
            _skipped_record(
                instance,
                method="global_learning_guided_lp",
                family="learning_guided_baseline",
                reason=f"skipped: n={instance.n} exceeds global binary cap {global_binary_bit_cap}",
                search_bits=instance.n,
            )
        )

    records.append(
        _profile(
            instance,
            "block_sa_lp",
            "classical_annealing",
            lambda: _block_backend_search(
                instance,
                advisor,
                SimulatedAnnealingBackend(),
                SamplerConfig(seed=seed, num_reads=sa_reads, num_sweeps=sa_sweeps, return_top_k=20),
                qaoa_block_size,
            ),
            search_bits=min(qaoa_block_size, instance.n),
            candidates_evaluated=sa_reads,
        )
    )

    records.append(
        _profile(
            instance,
            "block_learning_guided_lp",
            "learning_guided_baseline",
            lambda: _block_backend_search(
                instance,
                advisor,
                LearningGuidedSamplerBackend(),
                SamplerConfig(seed=seed, num_reads=sa_reads, num_sweeps=max(8, sa_sweeps // 2), return_top_k=20),
                qaoa_block_size,
            ),
            search_bits=min(qaoa_block_size, instance.n),
            candidates_evaluated=sa_reads,
        )
    )

    qaoa_record = _profile(
        instance,
        "block_qaoa_lp",
        "quantum_model",
        lambda: _block_qaoa_search(instance, advisor, seed, qaoa_block_size, qaoa_shots),
        search_bits=min(qaoa_block_size, instance.n),
        candidates_evaluated=qaoa_shots,
    )
    records.append(qaoa_record)

    route7_payload = _load_route7_payload(instance, route7_json_dir)
    if route7_payload is not None:
        records.append(_route7_record_from_payload(instance, route7_payload))
    else:
        records.append(
            _profile(
                instance,
                "miqp_aware_route7",
                "proposed_hybrid_quantum",
                lambda: _run_route7(instance, seed, route7_max_iterations, route7_candidate_limit),
                search_bits=min(20, instance.n),
                candidates_evaluated=route7_candidate_limit * route7_max_iterations,
            )
        )

    if instance.x_opt is not None and instance.y_opt is not None:
        reference = MiqpSolution(
            x=np.asarray(instance.x_opt, dtype=int),
            y=np.asarray(instance.y_opt, dtype=float),
            objective=instance.objective(instance.x_opt, instance.y_opt),
            feasible=instance.is_feasible(instance.x_opt, instance.y_opt),
            status="reference",
        )
        records.append(
            _record_from_solution(
                instance,
                method="official_reference",
                family="reference",
                status="reference",
                solution=reference,
                runtime_ms=0.0,
                peak_kib=0.0,
                candidates_evaluated=0,
                search_bits=0,
                notes="provided in sample data; not used as a solver",
            )
        )

    return records


def _profile(
    instance: MiqpInstance,
    method: str,
    family: str,
    runner: Callable[[], tuple[MiqpSolution, dict[str, Any]]],
    *,
    search_bits: int,
    candidates_evaluated: int,
) -> StudyRecord:
    started = perf_counter()
    tracemalloc.start()
    try:
        solution, metadata = runner()
        _current, peak = tracemalloc.get_traced_memory()
    except Exception as exc:
        _current, peak = tracemalloc.get_traced_memory()
        runtime_ms = (perf_counter() - started) * 1000.0
        tracemalloc.stop()
        return _skipped_record(
            instance,
            method=method,
            family=family,
            reason=f"{type(exc).__name__}: {exc}",
            search_bits=search_bits,
            runtime_ms=runtime_ms,
            peak_kib=peak / 1024.0,
        )
    runtime_ms = (perf_counter() - started) * 1000.0
    tracemalloc.stop()

    record = _record_from_solution(
        instance,
        method=method,
        family=family,
        status=solution.status,
        solution=solution,
        runtime_ms=runtime_ms,
        peak_kib=peak / 1024.0,
        candidates_evaluated=int(metadata.get("candidates_evaluated", candidates_evaluated)),
        search_bits=int(metadata.get("search_bits", search_bits)),
        notes=str(metadata.get("notes", "")),
    )
    record.qaoa_qubits = int(metadata.get("qaoa_qubits", 0))
    record.qaoa_layers = int(metadata.get("qaoa_layers", 0))
    record.qaoa_shots = int(metadata.get("qaoa_shots", 0))
    record.qaoa_rzz_per_layer = int(metadata.get("qaoa_rzz_per_layer", 0))
    return record


def _evaluate_single_x(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    x: np.ndarray,
    note: str,
) -> tuple[MiqpSolution, dict[str, Any]]:
    continuous = advisor.solve_continuous_subproblem(instance, x)
    return _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible"), {
        "candidates_evaluated": 1,
        "notes": note,
    }


def _marginal_greedy(instance: MiqpInstance, advisor: MiqpCutAdvisor) -> tuple[MiqpSolution, dict[str, Any]]:
    scores = instance.c + np.diag(instance.Q)
    order = sorted(range(instance.n), key=lambda index: (-scores[index], index))
    x = np.zeros(instance.n, dtype=int)
    probabilities = tuple()
    best_solution, _metadata = _evaluate_single_x(instance, advisor, x, "empty greedy start")
    for index in order:
        trial = x.copy()
        trial[index] = 1
        if instance.m2 and np.max(instance.B @ trial - instance.b_prime, initial=0.0) > 1e-8:
            continue
        continuous = advisor.solve_continuous_subproblem(instance, trial)
        candidate = _solution_from_continuous(instance, trial, continuous, "feasible" if continuous.feasible else "infeasible")
        if candidate.feasible and (not best_solution.feasible or candidate.objective > best_solution.objective):
            x = trial
            best_solution = candidate
    repaired = repair_binary_constraints(instance, x, probabilities)
    if not np.array_equal(repaired, x):
        return _evaluate_single_x(instance, advisor, repaired, "marginal greedy repaired")
    return best_solution, {"candidates_evaluated": instance.n, "notes": "adds positive marginal bits under B constraints"}


def _warm_start_candidate(instance: MiqpInstance, advisor: MiqpCutAdvisor) -> tuple[MiqpSolution, dict[str, Any]]:
    block = MiqpBlockSelector(max_block_size=min(20, instance.n)).select(instance)
    plan = MiqpWarmStartAdvisor().plan(instance, block=block)
    x = np.asarray(plan.repaired_assignment, dtype=int)
    solution, metadata = _evaluate_single_x(instance, advisor, x, "MIQP structural warm start")
    metadata["search_bits"] = instance.n
    return solution, metadata


def _random_repair_search(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    rng: random.Random,
    reads: int,
) -> tuple[MiqpSolution, dict[str, Any]]:
    probabilities = tuple()
    best: MiqpSolution | None = None
    evaluated = 0
    for _ in range(reads):
        raw = np.asarray([1 if rng.random() < 0.5 else 0 for _index in range(instance.n)], dtype=int)
        x = repair_binary_constraints(instance, raw, probabilities)
        continuous = advisor.solve_continuous_subproblem(instance, x)
        evaluated += 1
        candidate = _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible")
        if candidate.feasible and (best is None or candidate.objective > best.objective):
            best = candidate
    if best is None:
        best, _metadata = _evaluate_single_x(instance, advisor, np.zeros(instance.n, dtype=int), "random fallback")
    return best, {"candidates_evaluated": evaluated, "notes": f"{reads} random repaired candidates"}


def _genetic_algorithm_search(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    rng: random.Random,
    population_size: int,
    generations: int,
) -> tuple[MiqpSolution, dict[str, Any]]:
    probabilities = tuple()
    population = _initial_population(instance, advisor, rng, population_size)
    cache: dict[tuple[int, ...], MiqpSolution] = {}
    best: MiqpSolution | None = None
    evaluated = 0
    for generation in range(max(1, generations)):
        scored = []
        for member in population:
            key = tuple(int(value) for value in member.tolist())
            if key not in cache:
                cache[key] = _evaluate_x_solution(instance, advisor, member)
                evaluated += 1
            solution = cache[key]
            scored.append((solution.objective if solution.feasible else float("-inf"), member))
            if solution.feasible and (best is None or solution.objective > best.objective):
                best = solution
        scored.sort(key=lambda item: item[0], reverse=True)
        elites = [member.copy() for _score, member in scored[: max(2, population_size // 4)]]
        next_population = elites.copy()
        while len(next_population) < population_size:
            left = rng.choice(elites)
            right = rng.choice(elites)
            mask = np.asarray([1 if rng.random() < 0.5 else 0 for _ in range(instance.n)], dtype=int)
            child = np.where(mask, left, right).astype(int)
            mutation_rate = 0.08 if generation < generations // 2 else 0.04
            for index in range(instance.n):
                if rng.random() < mutation_rate:
                    child[index] = 1 - child[index]
            next_population.append(repair_binary_constraints(instance, child, probabilities))
        population = next_population
    if best is None:
        best, _metadata = _evaluate_single_x(instance, advisor, np.zeros(instance.n, dtype=int), "GA fallback")
    return best, {
        "candidates_evaluated": evaluated,
        "notes": f"genetic algorithm with population={population_size}, generations={generations}",
    }


def _binary_pso_search(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    rng: random.Random,
    swarm_size: int,
    iterations: int,
) -> tuple[MiqpSolution, dict[str, Any]]:
    probabilities = tuple()
    positions = _initial_population(instance, advisor, rng, swarm_size)
    velocities = np.zeros((swarm_size, instance.n), dtype=float)
    personal_best = [position.copy() for position in positions]
    personal_scores = [float("-inf")] * swarm_size
    global_best: np.ndarray | None = None
    global_solution: MiqpSolution | None = None
    evaluated = 0
    cache: dict[tuple[int, ...], MiqpSolution] = {}
    for _iteration in range(max(1, iterations)):
        for particle, position in enumerate(positions):
            key = tuple(int(value) for value in position.tolist())
            if key not in cache:
                cache[key] = _evaluate_x_solution(instance, advisor, position)
                evaluated += 1
            solution = cache[key]
            score = solution.objective if solution.feasible else float("-inf")
            if score > personal_scores[particle]:
                personal_scores[particle] = score
                personal_best[particle] = position.copy()
            if solution.feasible and (global_solution is None or solution.objective > global_solution.objective):
                global_solution = solution
                global_best = position.copy()
        if global_best is None:
            global_best = positions[0].copy()
        for particle, position in enumerate(positions):
            inertia = 0.55 * velocities[particle]
            cognitive = 1.20 * rng.random() * (personal_best[particle] - position)
            social = 1.20 * rng.random() * (global_best - position)
            velocities[particle] = np.clip(inertia + cognitive + social, -6.0, 6.0)
            probs = 1.0 / (1.0 + np.exp(-velocities[particle]))
            next_position = np.asarray([1 if rng.random() < prob else 0 for prob in probs], dtype=int)
            positions[particle] = repair_binary_constraints(instance, next_position, probabilities)
    if global_solution is None:
        global_solution, _metadata = _evaluate_single_x(instance, advisor, np.zeros(instance.n, dtype=int), "PSO fallback")
    return global_solution, {
        "candidates_evaluated": evaluated,
        "notes": f"binary PSO with swarm_size={swarm_size}, iterations={iterations}",
    }


def _initial_population(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    rng: random.Random,
    size: int,
) -> list[np.ndarray]:
    probabilities = tuple()
    population = [np.zeros(instance.n, dtype=int)]
    try:
        warm, _metadata = _warm_start_candidate(instance, advisor)
        population.append(warm.x.copy())
    except Exception:
        pass
    try:
        greedy, _metadata = _marginal_greedy(instance, advisor)
        population.append(greedy.x.copy())
    except Exception:
        pass
    while len(population) < max(1, size):
        raw = np.asarray([1 if rng.random() < 0.5 else 0 for _index in range(instance.n)], dtype=int)
        population.append(repair_binary_constraints(instance, raw, probabilities))
    return population[: max(1, size)]


def _evaluate_x_solution(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    x: np.ndarray,
) -> MiqpSolution:
    continuous = advisor.solve_continuous_subproblem(instance, x)
    return _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible")


def _exact_binary_search(instance: MiqpInstance, advisor: MiqpCutAdvisor) -> tuple[MiqpSolution, dict[str, Any]]:
    best: MiqpSolution | None = None
    evaluated = 0
    for value in range(2**instance.n):
        bits = [(value >> bit) & 1 for bit in range(instance.n)]
        x = np.asarray(bits, dtype=int)
        if instance.m2 and np.max(instance.B @ x - instance.b_prime, initial=0.0) > 1e-8:
            continue
        continuous = advisor.solve_continuous_subproblem(instance, x)
        evaluated += 1
        candidate = _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible")
        if candidate.feasible and (best is None or candidate.objective > best.objective):
            best = candidate
    if best is None:
        best, _metadata = _evaluate_single_x(instance, advisor, np.zeros(instance.n, dtype=int), "exact fallback")
    return best, {"candidates_evaluated": evaluated, "notes": "enumerates all binary x passing B constraints"}


def _global_binary_backend_search(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    backend: Any,
    config: SamplerConfig,
) -> tuple[MiqpSolution, dict[str, Any]]:
    problem = _build_global_binary_problem(instance)
    model = QuboBuilder().build(problem)
    result = backend.solve(model, config)
    best: MiqpSolution | None = None
    evaluated = 0
    for sample in result.samples:
        x = np.asarray([sample.logical_solution[f"x{index}"] for index in range(instance.n)], dtype=int)
        continuous = advisor.solve_continuous_subproblem(instance, x)
        evaluated += 1
        candidate = _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible")
        if candidate.feasible and (best is None or candidate.objective > best.objective):
            best = candidate
    if best is None:
        best, _metadata = _evaluate_single_x(instance, advisor, np.zeros(instance.n, dtype=int), "backend fallback")
    return best, {
        "candidates_evaluated": evaluated,
        "search_bits": model.num_variables,
        "notes": f"{backend.name}; qubo_bits={model.num_variables}; feasible_sample_ratio={result.feasible_ratio:.3f}",
    }


def _block_backend_search(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    backend: Any,
    config: SamplerConfig,
    block_size: int,
) -> tuple[MiqpSolution, dict[str, Any]]:
    selector = MiqpBlockSelector(max_block_size=min(block_size, instance.n), frontier_size=5)
    block = selector.select(instance)
    plan = MiqpWarmStartAdvisor().plan(instance, block=block)
    base = np.asarray(plan.repaired_assignment, dtype=int)
    problem = build_block_binary_problem(instance, block, base)
    model = QuboBuilder().build(problem)
    result = backend.solve(model, config)
    best: MiqpSolution | None = None
    evaluated = 0
    for sample in result.samples:
        x = base.copy()
        for original_index in block.binary_indices:
            x[original_index] = int(sample.logical_solution[f"x{original_index}"])
        x = repair_binary_constraints(instance, x, plan.probabilities)
        continuous = advisor.solve_continuous_subproblem(instance, x)
        evaluated += 1
        candidate = _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible")
        if candidate.feasible and (best is None or candidate.objective > best.objective):
            best = candidate
    if best is None:
        best, _metadata = _evaluate_single_x(instance, advisor, base, "block backend fallback warm start")
    return best, {
        "candidates_evaluated": evaluated,
        "search_bits": model.num_variables,
        "notes": f"{backend.name} on selected block {list(block.binary_indices)}; feasible_sample_ratio={result.feasible_ratio:.3f}",
    }


def _block_qaoa_search(
    instance: MiqpInstance,
    advisor: MiqpCutAdvisor,
    seed: int,
    block_size: int,
    shots: int,
) -> tuple[MiqpSolution, dict[str, Any]]:
    selector = MiqpBlockSelector(max_block_size=min(block_size, instance.n), frontier_size=5)
    block = selector.select(instance)
    plan = MiqpWarmStartAdvisor().plan(instance, block=block)
    base = np.asarray(plan.repaired_assignment, dtype=int)
    problem = _build_objective_only_block_problem(instance, block.binary_indices, base)
    model = QuboBuilder().build(problem)
    hamiltonian = CostHamiltonianBuilder.from_qubo(model)
    result = QaoaRunner().solve(
        model,
        QaoaConfig(
            p=1,
            shots=shots,
            seed=seed,
            max_qubits=max(block_size, model.num_variables),
            grid_size=5,
            random_trials=8,
            backend="local",
        ),
    )
    best: MiqpSolution | None = None
    evaluated = 0
    for sample in result.best_samples.samples:
        x = base.copy()
        for original_index in block.binary_indices:
            x[original_index] = int(sample.logical_solution[f"x{original_index}"])
        x = repair_binary_constraints(instance, x, plan.probabilities)
        continuous = advisor.solve_continuous_subproblem(instance, x)
        evaluated += 1
        candidate = _solution_from_continuous(instance, x, continuous, "feasible" if continuous.feasible else "infeasible")
        if candidate.feasible and (best is None or candidate.objective > best.objective):
            best = candidate
    if best is None:
        best, _metadata = _evaluate_single_x(instance, advisor, base, "qaoa fallback warm start")
    return best, {
        "candidates_evaluated": evaluated,
        "search_bits": model.num_variables,
        "qaoa_qubits": hamiltonian.num_qubits,
        "qaoa_layers": 1,
        "qaoa_shots": shots,
        "qaoa_rzz_per_layer": len(hamiltonian.zz_terms),
        "notes": f"objective-only QAOA on block {list(block.binary_indices)}; candidates repaired against B constraints",
    }


def _build_objective_only_block_problem(
    instance: MiqpInstance,
    binary_indices: Iterable[int],
    incumbent_x: np.ndarray,
) -> OptimizationProblem:
    selected = tuple(binary_indices)
    fixed = np.asarray(incumbent_x, dtype=float)
    selected_set = set(selected)
    problem = OptimizationProblem(sense="maximize", name=f"{instance.name}_objective_block")
    names = {index: problem.add_binary_var(f"x{index}") for index in selected}
    linear: dict[str, float] = {}
    quadratic: dict[tuple[str, str], float] = {}
    for index in selected:
        coefficient = instance.c[index] + instance.Q[index, index]
        for other in range(instance.n):
            if other not in selected_set:
                coefficient += (instance.Q[index, other] + instance.Q[other, index]) * fixed[other]
        linear[names[index]] = float(coefficient)
    for left_position, left in enumerate(selected):
        for right in selected[left_position + 1 :]:
            coefficient = float(instance.Q[left, right] + instance.Q[right, left])
            if abs(coefficient) > 1e-12:
                quadratic[(names[left], names[right])] = coefficient
    problem.set_objective(linear=linear, quadratic=quadratic)
    return problem


def _run_route7(
    instance: MiqpInstance,
    seed: int,
    max_iterations: int,
    candidate_limit: int,
) -> tuple[MiqpSolution, dict[str, Any]]:
    exact_limit = instance.n if instance.n <= 16 else 16
    result = MiqpAwareRoute7Solver(
        block_selector=MiqpBlockSelector(max_block_size=min(20, instance.n), frontier_size=10),
        exact_binary_limit=exact_limit,
        candidate_limit=candidate_limit,
        max_iterations=max_iterations,
        seed=seed,
    ).solve(instance)
    return result.solution, {
        "candidates_evaluated": result.diagnostics.get("candidate_evaluations", 0),
        "search_bits": len(result.block.binary_indices),
        "notes": result.diagnostics.get("mode", ""),
    }


def _load_route7_payload(instance: MiqpInstance, route7_json_dir: Path | None) -> dict[str, Any] | None:
    if route7_json_dir is None:
        return None
    path = route7_json_dir / f"{instance.name}_route7.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _route7_record_from_payload(instance: MiqpInstance, payload: dict[str, Any]) -> StudyRecord:
    route = payload["miqp_aware_route7"]
    sol = route["solution"]
    solution = MiqpSolution(
        x=np.asarray(sol["x"], dtype=int),
        y=np.asarray(sol["y"], dtype=float),
        objective=float(sol["objective"]),
        feasible=bool(sol["feasible"]),
        status=str(sol["status"]),
    )
    block_size = len(route["block"]["binary_indices"])
    record = _record_from_solution(
        instance,
        method="miqp_aware_route7",
        family="proposed_hybrid_quantum",
        status=solution.status,
        solution=solution,
        runtime_ms=float(payload["runtime_ms"]) if "runtime_ms" in payload else float("nan"),
        peak_kib=float("nan"),
        candidates_evaluated=int(route["diagnostics"].get("candidate_evaluations", 0)),
        search_bits=block_size,
        notes=f"loaded existing result; runtime loaded from route7 JSON; {route['diagnostics'].get('mode', '')}; best_seed={payload.get('best_seed')}",
    )
    return record


def _build_global_binary_problem(instance: MiqpInstance) -> OptimizationProblem:
    problem = OptimizationProblem(sense="maximize", name=f"{instance.name}_binary_proxy")
    names = [problem.add_binary_var(f"x{index}") for index in range(instance.n)]
    linear = {names[index]: float(instance.c[index] + instance.Q[index, index]) for index in range(instance.n)}
    quadratic: dict[tuple[str, str], float] = {}
    for left in range(instance.n):
        for right in range(left + 1, instance.n):
            coefficient = float(instance.Q[left, right] + instance.Q[right, left])
            if abs(coefficient) > 1e-12:
                quadratic[(names[left], names[right])] = coefficient
    problem.set_objective(linear=linear, quadratic=quadratic)
    for row in range(instance.m2):
        coefficients = {
            names[index]: float(instance.B[row, index])
            for index in range(instance.n)
            if abs(instance.B[row, index]) > 1e-12
        }
        if coefficients:
            problem.add_constraint(
                coefficients,
                sense="<=",
                rhs=float(instance.b_prime[row]),
                name=f"binary_row_{row}",
                constraint_type="bounded_sum",
                penalty_weight=80.0,
            )
    return problem


def _solution_from_continuous(instance: MiqpInstance, x: np.ndarray, continuous: Any, status: str) -> MiqpSolution:
    report = instance.constraint_report(x, continuous.y)
    feasible = bool(continuous.feasible and report.is_feasible)
    objective = instance.binary_objective(x) + continuous.objective if feasible else float("-inf")
    return MiqpSolution(
        x=np.asarray(x, dtype=int),
        y=np.asarray(continuous.y, dtype=float),
        objective=float(objective),
        feasible=feasible,
        status=status if feasible else f"{status}:{continuous.status}",
        diagnostics={"constraint_report": report.as_record()},
    )


def _record_from_solution(
    instance: MiqpInstance,
    *,
    method: str,
    family: str,
    status: str,
    solution: MiqpSolution,
    runtime_ms: float,
    peak_kib: float,
    candidates_evaluated: int,
    search_bits: int,
    notes: str,
) -> StudyRecord:
    objective = float(solution.objective) if solution.feasible else None
    official = instance.optimal_value
    gap = _gap_percent(objective, official)
    return StudyRecord(
        instance=instance.name,
        method=method,
        family=family,
        status=status,
        feasible=solution.feasible,
        objective=objective,
        official=official,
        gap_percent=gap,
        runtime_ms=runtime_ms,
        peak_kib=peak_kib,
        candidates_evaluated=candidates_evaluated,
        binary_variables=instance.n,
        search_bits=search_bits,
        notes=notes,
        x=[int(value) for value in solution.x.tolist()],
    )


def _skipped_record(
    instance: MiqpInstance,
    *,
    method: str,
    family: str,
    reason: str,
    search_bits: int,
    runtime_ms: float = 0.0,
    peak_kib: float = 0.0,
) -> StudyRecord:
    return StudyRecord(
        instance=instance.name,
        method=method,
        family=family,
        status="skipped",
        feasible=False,
        objective=None,
        official=instance.optimal_value,
        gap_percent=None,
        runtime_ms=runtime_ms,
        peak_kib=peak_kib,
        candidates_evaluated=0,
        binary_variables=instance.n,
        search_bits=search_bits,
        notes=reason,
    )


def _write_outputs(records: list[StudyRecord], output_dir: Path) -> None:
    rows = [record.as_row() for record in records]
    (output_dir / "miqp_baseline_study.json").write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "miqp_baseline_study.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "miqp_baseline_study.md").write_text(_render_markdown(rows), encoding="utf-8")


def _render_markdown(rows: list[dict[str, Any]]) -> str:
    headers = [
        "instance",
        "method",
        "family",
        "objective",
        "official",
        "gap_percent",
        "feasible",
        "runtime_ms",
        "search_bits",
        "qaoa_qubits",
        "candidates_evaluated",
    ]
    lines = [
        "# MIQP Baseline Study",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    lines.append("")
    lines.append("Gap is `(official - objective) / abs(official) * 100` because the task is maximization.")
    lines.append("Peak memory is Python heap measured by `tracemalloc`, so native LP/BLAS memory is not fully counted.")
    lines.append("")
    return "\n".join(lines)


def _plot_instance_figures(instance: MiqpInstance, records: list[StudyRecord], figure_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return

    comparable = [record for record in records if record.method != "official_reference" and record.status != "skipped"]
    methods = [record.method for record in comparable]
    objectives = [record.objective if record.objective is not None else 0.0 for record in comparable]
    scatter_records = [
        record
        for record in comparable
        if math.isfinite(record.runtime_ms) and record.runtime_ms > 0 and record.gap_percent is not None
    ]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = ["#4C78A8" if record.family != "proposed_hybrid_quantum" else "#1B8A5A" for record in comparable]
    ax.bar(range(len(methods)), objectives, color=colors)
    if instance.optimal_value is not None:
        ax.axhline(instance.optimal_value, color="#C44E52", linestyle="--", linewidth=1.8, label="official optimum")
        ax.legend(frameon=False)
    ax.set_title(f"{instance.name}: objective by method")
    ax.set_ylabel("objective (maximize)")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / f"{instance.name}_objective_by_method.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for record in scatter_records:
        marker = "*" if record.family == "proposed_hybrid_quantum" else "o"
        size = 170 if marker == "*" else 80
        ax.scatter(record.runtime_ms, record.gap_percent, s=size, marker=marker, label=record.method, alpha=0.85)
    ax.set_xscale("log")
    ax.set_title(f"{instance.name}: quality-runtime frontier")
    ax.set_xlabel("runtime ms (log scale)")
    ax.set_ylabel("gap to official optimum (%)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(figure_dir / f"{instance.name}_gap_runtime_frontier.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    bits = [record.search_bits for record in comparable]
    evals = [record.candidates_evaluated for record in comparable]
    qaoa = [record.qaoa_qubits for record in comparable]
    xloc = np.arange(len(methods))
    ax.bar(xloc - 0.25, bits, width=0.25, label="search bits")
    ax.bar(xloc, evals, width=0.25, label="candidate evals")
    ax.bar(xloc + 0.25, qaoa, width=0.25, label="QAOA qubits")
    ax.set_yscale("symlog")
    ax.set_title(f"{instance.name}: resource profile")
    ax.set_xticks(xloc)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / f"{instance.name}_resource_profile.png", dpi=180)
    plt.close(fig)

    block = MiqpBlockSelector(max_block_size=min(20, instance.n)).select(instance)
    matrix = instance.Q[np.ix_(block.binary_indices, block.binary_indices)]
    fig, ax = plt.subplots(figsize=(6, 5.4))
    image = ax.imshow(matrix, cmap="coolwarm", aspect="auto")
    ax.set_title(f"{instance.name}: selected-block Q coupling")
    ax.set_xlabel("block variable order")
    ax.set_ylabel("block variable order")
    fig.colorbar(image, ax=ax, shrink=0.8, label="Q coefficient")
    fig.tight_layout()
    fig.savefig(figure_dir / f"{instance.name}_block_coupling_heatmap.png", dpi=180)
    plt.close(fig)

    warm = MiqpWarmStartAdvisor().plan(instance, block=block)
    top = sorted(warm.probabilities, key=lambda item: item.index)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar([item.index for item in top], [item.probability_one for item in top], color="#59A14F")
    ax.axhline(0.5, color="#666666", linestyle="--", linewidth=1)
    ax.set_ylim(0.0, 1.0)
    ax.set_title(f"{instance.name}: warm-start bit probabilities")
    ax.set_xlabel("binary variable index")
    ax.set_ylabel("P(x_i=1)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / f"{instance.name}_warm_start_probabilities.png", dpi=180)
    plt.close(fig)


def _plot_cross_instance_figures(records: list[StudyRecord], figure_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyArrowPatch
    except Exception:
        return

    comparable = [
        record
        for record in records
        if record.method != "official_reference" and record.status != "skipped" and record.gap_percent is not None
    ]
    methods = sorted({record.method for record in comparable})
    instances = sorted({record.instance for record in comparable})
    xloc = np.arange(len(methods))
    width = 0.8 / max(1, len(instances))
    fig, ax = plt.subplots(figsize=(11, 5))
    for offset, instance in enumerate(instances):
        values = []
        for method in methods:
            match = next((record for record in comparable if record.instance == instance and record.method == method), None)
            values.append(match.gap_percent if match is not None else math.nan)
        ax.bar(xloc + (offset - (len(instances) - 1) / 2) * width, values, width=width, label=instance)
    ax.set_title("Optimality gap across instances")
    ax.set_ylabel("gap to official optimum (%)")
    ax.set_xticks(xloc)
    ax.set_xticklabels(methods, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "cross_instance_gap.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.axis("off")
    nodes = [
        ("MIQP\n.npz", 0.06),
        ("Block\nselector", 0.22),
        ("Warm start\nprobabilities", 0.40),
        ("QUBO / Ising\nblock backend", 0.60),
        ("LP over y\n+ cut advice", 0.78),
        ("Best feasible\nsolution", 0.94),
    ]
    for text, xpos in nodes:
        ax.text(
            xpos,
            0.5,
            text,
            ha="center",
            va="center",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.35", fc="#F7F7F7", ec="#2F5D7C", lw=1.5),
        )
    for (_left_text, left), (_right_text, right) in zip(nodes, nodes[1:]):
        ax.add_patch(
            FancyArrowPatch(
                (left + 0.055, 0.5),
                (right - 0.065, 0.5),
                arrowstyle="->",
                mutation_scale=12,
                linewidth=1.4,
                color="#444444",
            )
        )
    ax.set_title("MIQP-aware route 7 workflow", fontsize=13)
    fig.tight_layout()
    fig.savefig(figure_dir / "miqp_route7_workflow.png", dpi=180)
    plt.close(fig)


def _gap_percent(objective: float | None, official: float | None) -> float | None:
    if objective is None or official is None or abs(official) <= 1e-12:
        return None
    return 100.0 * (official - objective) / abs(official)


def _round_optional(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
