from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder
from quantum_hackathon.solvers import (
    BitProbability,
    LearningGuidedSamplerBackend,
    SamplerConfig,
    SimulatedAnnealingBackend,
    VariableFixingPlan,
)

from .model import MiqpInstance, MiqpSolution


@dataclass(frozen=True)
class MiqpVariableScore:
    index: int
    objective_score: float
    coupling_score: float
    mixed_constraint_score: float
    binary_constraint_score: float
    total_score: float

    def as_record(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "objective_score": round(self.objective_score, 6),
            "coupling_score": round(self.coupling_score, 6),
            "mixed_constraint_score": round(self.mixed_constraint_score, 6),
            "binary_constraint_score": round(self.binary_constraint_score, 6),
            "total_score": round(self.total_score, 6),
        }


@dataclass(frozen=True)
class MiqpBlock:
    binary_indices: tuple[int, ...]
    frontier_indices: tuple[int, ...]
    seed_index: int
    score: float
    variable_scores: tuple[MiqpVariableScore, ...]
    rationale: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "binary_indices": list(self.binary_indices),
            "frontier_indices": list(self.frontier_indices),
            "seed_index": self.seed_index,
            "score": round(self.score, 6),
            "variable_scores": [score.as_record() for score in self.variable_scores],
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class MiqpWarmStartPlan:
    probabilities: tuple[BitProbability, ...]
    fixing_plan: VariableFixingPlan
    threshold_assignment: tuple[int, ...]
    repaired_assignment: tuple[int, ...]
    rationale: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "probabilities": [prob.as_record() for prob in self.probabilities],
            "fixing_plan": self.fixing_plan.as_record(),
            "threshold_assignment": list(self.threshold_assignment),
            "repaired_assignment": list(self.repaired_assignment),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ContinuousSubproblemResult:
    status: str
    feasible: bool
    y: np.ndarray
    objective: float
    dual_multipliers: np.ndarray | None = None
    message: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "feasible": self.feasible,
            "objective": float(self.objective),
            "y": [float(value) for value in self.y.tolist()],
            "dual_multipliers": (
                [float(value) for value in self.dual_multipliers.tolist()]
                if self.dual_multipliers is not None
                else None
            ),
            "message": self.message,
            "diagnostics": self.diagnostics,
        }


@dataclass(frozen=True)
class MiqpCutAdvice:
    cut_type: str
    theta_rhs: float | None
    x_coefficients: tuple[float, ...]
    active_constraints: tuple[int, ...]
    violation_rows: tuple[int, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "cut_type": self.cut_type,
            "theta_rhs": self.theta_rhs,
            "x_coefficients": [float(value) for value in self.x_coefficients],
            "active_constraints": list(self.active_constraints),
            "violation_rows": list(self.violation_rows),
            "diagnostics": self.diagnostics,
        }


@dataclass(frozen=True)
class MiqpAwareRoute7Result:
    instance_name: str
    solution: MiqpSolution
    block: MiqpBlock
    warm_start: MiqpWarmStartPlan
    cuts: tuple[MiqpCutAdvice, ...]
    continuous_result: ContinuousSubproblemResult
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "instance_name": self.instance_name,
            "solution": self.solution.as_record(),
            "block": self.block.as_record(),
            "warm_start": self.warm_start.as_record(),
            "cuts": [cut.as_record() for cut in self.cuts],
            "continuous_subproblem": self.continuous_result.as_record(),
            "diagnostics": self.diagnostics,
        }


class MiqpBlockSelector:
    def __init__(self, *, max_block_size: int = 20, frontier_size: int = 10):
        if not 1 <= max_block_size <= 30:
            raise ValueError("max_block_size must be in [1, 30]")
        self.max_block_size = max_block_size
        self.frontier_size = frontier_size

    def score_variables(self, instance: MiqpInstance) -> tuple[MiqpVariableScore, ...]:
        objective = np.abs(instance.c + np.diag(instance.Q))
        coupling = np.sum(np.abs(instance.Q), axis=1) - np.abs(np.diag(instance.Q))
        mixed = np.sum(np.abs(instance.A), axis=0)
        binary = np.sum(np.abs(instance.B), axis=0) if instance.m2 else np.zeros(instance.n)
        objective_n = _normalize(objective)
        coupling_n = _normalize(coupling)
        mixed_n = _normalize(mixed)
        binary_n = _normalize(binary)
        scores = []
        for index in range(instance.n):
            total = (
                0.30 * objective_n[index]
                + 0.35 * coupling_n[index]
                + 0.20 * mixed_n[index]
                + 0.15 * binary_n[index]
            )
            scores.append(
                MiqpVariableScore(
                    index=index,
                    objective_score=float(objective_n[index]),
                    coupling_score=float(coupling_n[index]),
                    mixed_constraint_score=float(mixed_n[index]),
                    binary_constraint_score=float(binary_n[index]),
                    total_score=float(total),
                )
            )
        return tuple(sorted(scores, key=lambda item: (-item.total_score, item.index)))

    def select(
        self,
        instance: MiqpInstance,
        *,
        incumbent_x: np.ndarray | None = None,
        seed_index: int | None = None,
        exclude_indices: Iterable[int] = (),
    ) -> MiqpBlock:
        excluded = set(exclude_indices)
        scores = tuple(score for score in self.score_variables(instance) if score.index not in excluded)
        if not scores:
            raise ValueError("cannot select a block from an empty MIQP instance")
        score_by_index = {score.index: score for score in scores}
        seed = seed_index if seed_index in score_by_index else scores[0].index
        selected = [seed]
        candidate_pool = set(score_by_index) - {seed}
        while len(selected) < min(self.max_block_size, instance.n) and candidate_pool:
            best = max(
                candidate_pool,
                key=lambda candidate: (
                    _neighbor_affinity(instance, candidate, selected)
                    + 0.45 * score_by_index[candidate].total_score,
                    -candidate,
                ),
            )
            selected.append(best)
            candidate_pool.remove(best)

        frontier = sorted(
            candidate_pool,
            key=lambda candidate: (
                -_neighbor_affinity(instance, candidate, selected),
                -score_by_index[candidate].total_score,
                candidate,
            ),
        )[: self.frontier_size]
        selected_tuple = tuple(sorted(selected))
        block_scores = tuple(score_by_index[index] for index in selected_tuple)
        block_score = float(sum(score.total_score for score in block_scores) / max(1, len(block_scores)))
        return MiqpBlock(
            binary_indices=selected_tuple,
            frontier_indices=tuple(frontier),
            seed_index=seed,
            score=block_score,
            variable_scores=block_scores,
            rationale={
                "strategy": "greedy_dense_coupling_and_constraint_growth",
                "max_block_size": self.max_block_size,
                "frontier_size": self.frontier_size,
                "incumbent_ones": int(np.sum(incumbent_x)) if incumbent_x is not None else None,
                "excluded_count": len(excluded),
            },
        )


class MiqpWarmStartAdvisor:
    def __init__(self, *, temperature: float = 1.0, confidence_threshold: float = 0.82):
        self.temperature = max(1e-6, temperature)
        self.confidence_threshold = confidence_threshold

    def plan(
        self,
        instance: MiqpInstance,
        *,
        block: MiqpBlock | None = None,
        incumbent_x: np.ndarray | None = None,
    ) -> MiqpWarmStartPlan:
        base_x = np.zeros(instance.n) if incumbent_x is None else np.asarray(incumbent_x, dtype=float)
        marginal = instance.c + np.diag(instance.Q) + 2.0 * (instance.Q @ base_x)
        mixed_relief = -np.sum(instance.A, axis=0)
        binary_pressure = (
            np.sum(instance.B / np.maximum(instance.b_prime[:, None], 1e-9), axis=0)
            if instance.m2
            else np.zeros(instance.n)
        )
        score = _normalize_signed(marginal) + 0.45 * _normalize_signed(mixed_relief) - 0.35 * _normalize(binary_pressure)
        probabilities = tuple(
            sorted(
                (
                    BitProbability(
                        index=index,
                        score=float(score[index]),
                        probability_one=_sigmoid(float(score[index]) / self.temperature),
                    )
                    for index in range(instance.n)
                ),
                key=lambda item: (-item.score, item.index),
            )
        )
        assignment = np.array([1 if score[index] >= 0.0 else 0 for index in range(instance.n)], dtype=int)
        repaired = repair_binary_constraints(instance, assignment, probabilities)
        fixing_plan = _fixing_plan_from_probabilities(
            probabilities,
            confidence_threshold=self.confidence_threshold,
            allowed_indices=set(block.binary_indices) if block is not None else None,
        )
        return MiqpWarmStartPlan(
            probabilities=probabilities,
            fixing_plan=fixing_plan,
            threshold_assignment=tuple(int(value) for value in assignment.tolist()),
            repaired_assignment=tuple(int(value) for value in repaired.tolist()),
            rationale={
                "strategy": "objective_marginal_plus_constraint_relief",
                "temperature": self.temperature,
                "confidence_threshold": self.confidence_threshold,
                "block_size": len(block.binary_indices) if block is not None else instance.n,
            },
        )


class MiqpCutAdvisor:
    def solve_continuous_subproblem(self, instance: MiqpInstance, x: Iterable[int]) -> ContinuousSubproblemResult:
        x_arr = np.asarray(tuple(x), dtype=float)
        if x_arr.shape != (instance.n,):
            raise ValueError("x assignment shape does not match instance.n")
        binary_violation = instance.B @ x_arr - instance.b_prime
        if np.max(binary_violation, initial=0.0) > 1e-8:
            return ContinuousSubproblemResult(
                status="binary_constraints_violated",
                feasible=False,
                y=np.zeros(instance.p),
                objective=float("-inf"),
                diagnostics={
                    "binary_violation": binary_violation.tolist(),
                    "violated_binary_rows": np.where(binary_violation > 1e-8)[0].astype(int).tolist(),
                },
            )

        try:
            from scipy.optimize import linprog
        except Exception:
            return self._fallback_zero_y(instance, x_arr)

        rhs = instance.continuous_rhs(x_arr)
        completed = linprog(
            -instance.h,
            A_ub=instance.G,
            b_ub=rhs,
            bounds=[(0.0, None)] * instance.p,
            method="highs",
        )
        if not completed.success:
            return ContinuousSubproblemResult(
                status=f"lp_{completed.status}",
                feasible=False,
                y=np.zeros(instance.p),
                objective=float("-inf"),
                message=str(completed.message),
                diagnostics={
                    "mixed_rhs": rhs.tolist(),
                    "violated_zero_y_rows": np.where(-rhs > 1e-8)[0].astype(int).tolist(),
                },
            )

        y = np.asarray(completed.x, dtype=float)
        duals = None
        try:
            marginals = np.asarray(completed.ineqlin.marginals, dtype=float)
            duals = np.maximum(0.0, -marginals)
        except Exception:
            duals = None
        return ContinuousSubproblemResult(
            status="optimal",
            feasible=True,
            y=y,
            objective=float(instance.h @ y),
            dual_multipliers=duals,
            message=str(completed.message),
            diagnostics={
                "lp_fun": float(completed.fun),
                "mixed_rhs": rhs.tolist(),
                "active_mixed_rows": np.where(np.abs(instance.G @ y - rhs) <= 1e-7)[0].astype(int).tolist(),
            },
        )

    def advise_cut(
        self,
        instance: MiqpInstance,
        x: Iterable[int],
        continuous: ContinuousSubproblemResult,
    ) -> MiqpCutAdvice:
        x_arr = np.asarray(tuple(x), dtype=float)
        if continuous.feasible and continuous.dual_multipliers is not None:
            pi = continuous.dual_multipliers
            rhs = float(instance.b @ pi)
            coefficients = -(instance.A.T @ pi)
            active = tuple(int(index) for index in np.where(pi > 1e-9)[0])
            predicted_at_x = rhs + float(coefficients @ x_arr)
            return MiqpCutAdvice(
                cut_type="benders_optimality",
                theta_rhs=rhs,
                x_coefficients=tuple(float(value) for value in coefficients.tolist()),
                active_constraints=active,
                violation_rows=(),
                diagnostics={
                    "continuous_objective": continuous.objective,
                    "cut_value_at_current_x": predicted_at_x,
                    "cut_tightness_gap": float(abs(predicted_at_x - continuous.objective)),
                },
            )

        report = instance.constraint_report(x_arr, np.zeros(instance.p))
        mixed_rows = tuple(int(index) for index in np.where(report.mixed_violation > 1e-8)[0])
        binary_rows = tuple(int(index) for index in np.where(report.binary_violation > 1e-8)[0])
        return MiqpCutAdvice(
            cut_type="feasibility_advisory",
            theta_rhs=None,
            x_coefficients=tuple(0.0 for _ in range(instance.n)),
            active_constraints=(),
            violation_rows=tuple([*mixed_rows, *binary_rows]),
            diagnostics={
                "zero_y_constraint_report": report.as_record(),
                "continuous_status": continuous.status,
            },
        )

    def _fallback_zero_y(self, instance: MiqpInstance, x: np.ndarray) -> ContinuousSubproblemResult:
        y = np.zeros(instance.p)
        report = instance.constraint_report(x, y)
        return ContinuousSubproblemResult(
            status="fallback_zero_y",
            feasible=report.is_feasible,
            y=y,
            objective=float(instance.h @ y) if report.is_feasible else float("-inf"),
            diagnostics={"reason": "scipy_unavailable", "constraint_report": report.as_record()},
        )


class MiqpAwareRoute7Solver:
    def __init__(
        self,
        *,
        block_selector: MiqpBlockSelector | None = None,
        warm_start_advisor: MiqpWarmStartAdvisor | None = None,
        cut_advisor: MiqpCutAdvisor | None = None,
        exact_binary_limit: int = 16,
        candidate_limit: int = 128,
        max_iterations: int = 4,
        seed: int = 7,
    ):
        self.block_selector = block_selector or MiqpBlockSelector()
        self.warm_start_advisor = warm_start_advisor or MiqpWarmStartAdvisor()
        self.cut_advisor = cut_advisor or MiqpCutAdvisor()
        self.exact_binary_limit = exact_binary_limit
        self.candidate_limit = candidate_limit
        self.max_iterations = max(1, max_iterations)
        self.seed = seed

    def solve(self, instance: MiqpInstance) -> MiqpAwareRoute7Result:
        block = self.block_selector.select(instance)
        warm_start = self.warm_start_advisor.plan(instance, block=block)
        if instance.n <= self.exact_binary_limit:
            solution, continuous, cut, evaluated = self._solve_exact_binary(instance, block, warm_start)
            mode = "exact_binary_plus_continuous_lp"
            block_history: list[dict[str, Any]] = []
        else:
            solution, continuous, cut, evaluated, block_history = self._solve_block_heuristic(instance, block, warm_start)
            mode = "miqp_aware_block_heuristic"
        return MiqpAwareRoute7Result(
            instance_name=instance.name,
            solution=solution,
            block=block,
            warm_start=warm_start,
            cuts=(cut,),
            continuous_result=continuous,
            diagnostics={
                "route": "miqp_aware_learning_guided",
                "mode": mode,
                "candidate_evaluations": evaluated,
                "exact_binary_limit": self.exact_binary_limit,
                "candidate_limit": self.candidate_limit,
                "max_iterations": self.max_iterations,
                "block_history": block_history,
            },
        )

    def _solve_exact_binary(
        self,
        instance: MiqpInstance,
        block: MiqpBlock,
        warm_start: MiqpWarmStartPlan,
    ) -> tuple[MiqpSolution, ContinuousSubproblemResult, MiqpCutAdvice, int]:
        best_solution: MiqpSolution | None = None
        best_continuous: ContinuousSubproblemResult | None = None
        evaluated = 0
        for bits in itertools.product((0, 1), repeat=instance.n):
            x = np.asarray(bits, dtype=int)
            if np.max(instance.B @ x - instance.b_prime, initial=0.0) > 1e-8:
                continue
            continuous = self.cut_advisor.solve_continuous_subproblem(instance, x)
            evaluated += 1
            if not continuous.feasible:
                continue
            objective = instance.binary_objective(x) + continuous.objective
            report = instance.constraint_report(x, continuous.y)
            candidate = MiqpSolution(
                x=x,
                y=continuous.y,
                objective=objective,
                feasible=report.is_feasible,
                status="feasible" if report.is_feasible else "constraint_violation",
                diagnostics={"constraint_report": report.as_record()},
            )
            if candidate.feasible and (best_solution is None or candidate.objective > best_solution.objective):
                best_solution = candidate
                best_continuous = continuous
        if best_solution is None or best_continuous is None:
            x = np.asarray(warm_start.repaired_assignment, dtype=int)
            best_continuous = self.cut_advisor.solve_continuous_subproblem(instance, x)
            best_solution = _solution_from_continuous(instance, x, best_continuous, status="no_feasible_exact_candidate")
        return (
            best_solution,
            best_continuous,
            self.cut_advisor.advise_cut(instance, best_solution.x, best_continuous),
            evaluated,
        )

    def _solve_block_heuristic(
        self,
        instance: MiqpInstance,
        block: MiqpBlock,
        warm_start: MiqpWarmStartPlan,
    ) -> tuple[MiqpSolution, ContinuousSubproblemResult, MiqpCutAdvice, int, list[dict[str, Any]]]:
        rng = random.Random(self.seed)
        best_solution: MiqpSolution | None = None
        best_continuous: ContinuousSubproblemResult | None = None
        incumbent = np.asarray(warm_start.repaired_assignment, dtype=int)
        evaluated = 0
        visited: set[int] = set()
        history: list[dict[str, Any]] = []
        current_block = block
        current_warm_start = warm_start
        for iteration in range(self.max_iterations):
            if iteration > 0:
                seed_index = _next_seed_index(instance, visited, incumbent)
                current_block = self.block_selector.select(
                    instance,
                    incumbent_x=incumbent,
                    seed_index=seed_index,
                    exclude_indices=() if len(visited) + self.block_selector.max_block_size >= instance.n else visited,
                )
                current_warm_start = self.warm_start_advisor.plan(instance, block=current_block, incumbent_x=incumbent)
            base = incumbent.copy()
            candidates = _dedupe_x_candidates(
                [
                    base,
                    np.zeros(instance.n, dtype=int),
                    _binary_constraint_repaired_random(instance, rng),
                    *_block_candidates_from_subqubo(
                        instance,
                        current_block,
                        base,
                        self.seed + iteration,
                        self.candidate_limit // 2,
                    ),
                    *_single_flip_candidates(instance, current_block, base, current_warm_start.probabilities),
                ]
            )
            candidates = [
                repair_binary_constraints(instance, candidate, current_warm_start.probabilities)
                for candidate in candidates
            ]
            candidates = _dedupe_x_candidates(candidates)[: max(1, self.candidate_limit)]
            iteration_best: MiqpSolution | None = None
            for candidate_x in candidates:
                continuous = self.cut_advisor.solve_continuous_subproblem(instance, candidate_x)
                evaluated += 1
                if not continuous.feasible:
                    continue
                solution = _solution_from_continuous(instance, candidate_x, continuous, status="feasible")
                if solution.feasible and (iteration_best is None or solution.objective > iteration_best.objective):
                    iteration_best = solution
                if solution.feasible and (best_solution is None or solution.objective > best_solution.objective):
                    best_solution = solution
                    best_continuous = continuous
            if iteration_best is not None and iteration_best.objective >= instance.binary_objective(incumbent):
                incumbent = iteration_best.x.copy()
            visited.update(current_block.binary_indices)
            history.append(
                {
                    "iteration": iteration,
                    "block_indices": list(current_block.binary_indices),
                    "candidate_count": len(candidates),
                    "iteration_best_objective": iteration_best.objective if iteration_best is not None else None,
                    "global_best_objective": best_solution.objective if best_solution is not None else None,
                }
            )
        if best_solution is None or best_continuous is None:
            x = incumbent
            best_continuous = self.cut_advisor.solve_continuous_subproblem(instance, x)
            best_solution = _solution_from_continuous(instance, x, best_continuous, status="heuristic_no_feasible_candidate")
        return (
            best_solution,
            best_continuous,
            self.cut_advisor.advise_cut(instance, best_solution.x, best_continuous),
            evaluated,
            history,
        )


def build_block_binary_problem(
    instance: MiqpInstance,
    block: MiqpBlock,
    incumbent_x: np.ndarray,
) -> OptimizationProblem:
    fixed = np.asarray(incumbent_x, dtype=float).copy()
    selected = set(block.binary_indices)
    problem = OptimizationProblem(sense="maximize", name=f"{instance.name}_subqubo_block")
    name_by_index = {index: problem.add_binary_var(f"x{index}") for index in block.binary_indices}
    linear: dict[str, float] = {}
    quadratic: dict[tuple[str, str], float] = {}
    for index in block.binary_indices:
        coefficient = instance.c[index] + instance.Q[index, index]
        for other in range(instance.n):
            if other not in selected:
                coefficient += 2.0 * instance.Q[index, other] * fixed[other]
        linear[name_by_index[index]] = float(coefficient)
    for left_pos, left in enumerate(block.binary_indices):
        for right in block.binary_indices[left_pos + 1 :]:
            coefficient = 2.0 * instance.Q[left, right]
            if abs(coefficient) > 1e-12:
                quadratic[(name_by_index[left], name_by_index[right])] = float(coefficient)
    problem.set_objective(linear=linear, quadratic=quadratic)
    for row in range(instance.m2):
        fixed_usage = float(sum(instance.B[row, index] * fixed[index] for index in range(instance.n) if index not in selected))
        block_coefficients = {
            name_by_index[index]: float(instance.B[row, index])
            for index in block.binary_indices
            if abs(instance.B[row, index]) > 1e-12
        }
        if block_coefficients:
            problem.add_constraint(
                block_coefficients,
                sense="<=",
                rhs=float(instance.b_prime[row] - fixed_usage),
                name=f"binary_row_{row}",
                constraint_type="bounded_sum",
                penalty_weight=40.0,
            )
    return problem


def repair_binary_constraints(
    instance: MiqpInstance,
    x: np.ndarray,
    probabilities: Iterable[BitProbability],
) -> np.ndarray:
    repaired = np.asarray(x, dtype=int).copy()
    confidence = {item.index: item.probability_one for item in probabilities}
    for row in range(instance.m2):
        while float(instance.B[row] @ repaired) > instance.b_prime[row] + 1e-8:
            active = [
                index
                for index in np.where((instance.B[row] > 1e-12) & (repaired > 0))[0].astype(int).tolist()
            ]
            if not active:
                break
            drop = min(active, key=lambda index: (confidence.get(index, 0.5), instance.c[index], -index))
            repaired[drop] = 0
    return repaired


def _block_candidates_from_subqubo(
    instance: MiqpInstance,
    block: MiqpBlock,
    base_x: np.ndarray,
    seed: int,
    limit: int,
) -> list[np.ndarray]:
    if limit <= 0 or not block.binary_indices:
        return []
    try:
        problem = build_block_binary_problem(instance, block, base_x)
        model = QuboBuilder().build(problem)
    except Exception:
        return []
    config = SamplerConfig(seed=seed, num_reads=max(4, limit), num_sweeps=80, return_top_k=min(20, limit))
    samples = []
    for backend in (LearningGuidedSamplerBackend(), SimulatedAnnealingBackend()):
        try:
            result = backend.solve(model, config)
        except Exception:
            continue
        samples.extend(result.samples[:limit])
    candidates = []
    for sample in samples[:limit]:
        candidate = base_x.copy()
        for bit_index, original_index in enumerate(block.binary_indices):
            candidate[original_index] = sample.bitstring[bit_index]
        candidates.append(candidate)
    return candidates


def _single_flip_candidates(
    instance: MiqpInstance,
    block: MiqpBlock,
    base_x: np.ndarray,
    probabilities: tuple[BitProbability, ...],
) -> list[np.ndarray]:
    by_confidence = sorted(
        [item for item in probabilities if item.index in set(block.binary_indices)],
        key=lambda item: (-item.confidence, item.index),
    )
    candidates = []
    for item in by_confidence[: min(24, len(by_confidence))]:
        candidate = base_x.copy()
        candidate[item.index] = 1 - candidate[item.index]
        candidates.append(candidate)
    return candidates


def _binary_constraint_repaired_random(instance: MiqpInstance, rng: random.Random) -> np.ndarray:
    x = np.asarray([1 if rng.random() < 0.5 else 0 for _ in range(instance.n)], dtype=int)
    probabilities = tuple(BitProbability(index=index, score=0.0, probability_one=0.5) for index in range(instance.n))
    return repair_binary_constraints(instance, x, probabilities)


def _next_seed_index(instance: MiqpInstance, visited: set[int], incumbent: np.ndarray) -> int | None:
    marginal = instance.c + np.diag(instance.Q) + 2.0 * (instance.Q @ np.asarray(incumbent, dtype=float))
    available = [index for index in range(instance.n) if index not in visited]
    if not available:
        return None
    return max(available, key=lambda index: (abs(float(marginal[index])), -index))


def _solution_from_continuous(
    instance: MiqpInstance,
    x: np.ndarray,
    continuous: ContinuousSubproblemResult,
    *,
    status: str,
) -> MiqpSolution:
    objective = instance.binary_objective(x) + continuous.objective if continuous.feasible else float("-inf")
    report = instance.constraint_report(x, continuous.y)
    return MiqpSolution(
        x=x,
        y=continuous.y,
        objective=objective,
        feasible=continuous.feasible and report.is_feasible,
        status=status,
        diagnostics={
            "binary_objective": instance.binary_objective(x),
            "continuous_objective": continuous.objective,
            "constraint_report": report.as_record(),
        },
    )


def _dedupe_x_candidates(candidates: Iterable[np.ndarray]) -> list[np.ndarray]:
    deduped: list[np.ndarray] = []
    seen: set[tuple[int, ...]] = set()
    for candidate in candidates:
        key = tuple(int(value) for value in candidate.tolist())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(np.asarray(key, dtype=int))
    return deduped


def _fixing_plan_from_probabilities(
    probabilities: Iterable[BitProbability],
    *,
    confidence_threshold: float,
    allowed_indices: set[int] | None = None,
) -> VariableFixingPlan:
    fixed = []
    free = []
    ranked = []
    for item in probabilities:
        if allowed_indices is not None and item.index not in allowed_indices:
            continue
        if item.confidence >= confidence_threshold:
            fixed.append((item.index, 1 if item.probability_one >= 0.5 else 0, round(item.confidence, 6)))
        else:
            free.append(item.index)
        ranked.append((item.index, round(item.score, 6), round(item.probability_one, 6)))
    return VariableFixingPlan(
        fixed_bits=tuple(fixed),
        free_bits=tuple(free),
        ranked_bits=tuple(ranked),
        confidence_threshold=confidence_threshold,
    )


def _neighbor_affinity(instance: MiqpInstance, candidate: int, selected: list[int]) -> float:
    q_affinity = sum(abs(instance.Q[candidate, other]) + abs(instance.Q[other, candidate]) for other in selected)
    a_affinity = sum(float(np.abs(instance.A[:, candidate]) @ np.abs(instance.A[:, other])) for other in selected)
    b_affinity = sum(float(np.abs(instance.B[:, candidate]) @ np.abs(instance.B[:, other])) for other in selected) if instance.m2 else 0.0
    return float(_safe_scale(q_affinity) + 0.08 * _safe_scale(a_affinity) + 0.15 * _safe_scale(b_affinity))


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    max_value = float(np.max(np.abs(values), initial=0.0))
    if max_value <= 1e-12:
        return np.zeros_like(values, dtype=float)
    return np.abs(values) / max_value


def _normalize_signed(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    max_value = float(np.max(np.abs(values), initial=0.0))
    if max_value <= 1e-12:
        return np.zeros_like(values, dtype=float)
    return values / max_value


def _safe_scale(value: float) -> float:
    return math.log1p(max(0.0, value))


def _sigmoid(value: float) -> float:
    if value >= 50:
        return 1.0
    if value <= -50:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))
