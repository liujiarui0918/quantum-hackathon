from __future__ import annotations

from dataclasses import dataclass, field

from quantum_hackathon.modeling.problem import OptimizationProblem

from .decomposition import ProblemDecomposer
from .problem import HybridOptimizationProblem
from .relaxation import RelaxationResult, RelaxationSolver
from .rounding import RoundingStrategy


@dataclass(frozen=True)
class HybridResult:
    status: str
    best_feasible_solution: dict[str, float] | None
    objective: float | None
    diagnostics: dict = field(default_factory=dict)
    warm_start_metadata: dict = field(default_factory=dict)


class HybridOptimizer:
    def __init__(
        self,
        *,
        strategy: str = "relax_round_repair",
        rounding: RoundingStrategy | None = None,
        relaxation_solver: RelaxationSolver | None = None,
    ):
        if strategy != "relax_round_repair":
            raise ValueError(f"unsupported hybrid strategy {strategy!r}")
        self.strategy = strategy
        self.rounding = rounding or RoundingStrategy(method="threshold", threshold=0.5)
        self.relaxation_solver = relaxation_solver or RelaxationSolver()

    def solve(self, problem: HybridOptimizationProblem) -> HybridResult:
        analysis = ProblemDecomposer().analyze(problem)
        relaxation = self.relaxation_solver.solve(problem)
        binary_values = {
            name: relaxation.variable_values[name]
            for name in analysis.binary_block_vars
            if name in relaxation.variable_values
        }
        rounded = self.rounding.round(binary_values)
        solution: dict[str, float] = {}
        solution.update(rounded)
        for name in analysis.continuous_block_vars:
            solution[name] = relaxation.variable_values[name]

        solution = _repair_continuous_bounds(problem, solution, fixed_binary=set(analysis.binary_block_vars))
        feasibility = problem.check_constraints(solution)
        warm_start_metadata = {
            "continuous_relaxation_status": relaxation.status,
            "continuous_relaxation_objective": relaxation.objective,
            "continuous_relaxation_values": dict(relaxation.variable_values),
            "rounded_assignment": dict(rounded),
            "relaxation_metadata": dict(relaxation.metadata),
        }

        diagnostics = {
            "strategy": self.strategy,
            "binary_variables": len(analysis.binary_block_vars),
            "continuous_variables": len(analysis.continuous_block_vars),
            **feasibility,
        }
        if not feasibility["is_feasible"]:
            return HybridResult(
                status="infeasible",
                best_feasible_solution=None,
                objective=None,
                diagnostics=diagnostics,
                warm_start_metadata=warm_start_metadata,
            )
        return HybridResult(
            status="feasible",
            best_feasible_solution=solution,
            objective=problem.evaluate_objective(solution),
            diagnostics=diagnostics,
            warm_start_metadata=warm_start_metadata,
        )


class FixAndOptimize:
    def __init__(self, *, uncertainty_window: float = 0.15):
        self.uncertainty_window = uncertainty_window

    def uncertain_binary_vars(self, relaxation: RelaxationResult) -> tuple[str, ...]:
        low = 0.5 - self.uncertainty_window
        high = 0.5 + self.uncertainty_window
        return tuple(name for name, value in relaxation.variable_values.items() if low <= value <= high)

    def build_binary_subproblem(
        self,
        problem: HybridOptimizationProblem,
        selected_binary_vars: tuple[str, ...],
    ) -> OptimizationProblem | None:
        selected = set(selected_binary_vars)
        if not selected:
            return None
        if any(problem.variables[name].kind != "binary" for name in selected):
            return None
        subproblem = OptimizationProblem(sense=problem.sense, name=f"{problem.name}_fix_and_optimize")
        for name in selected_binary_vars:
            subproblem.add_binary_var(name)
        linear = {name: value for name, value in problem.objective_linear.items() if name in selected}
        quadratic = {
            pair: value
            for pair, value in problem.objective_quadratic.items()
            if pair[0] in selected and pair[1] in selected
        }
        subproblem.set_objective(linear=linear, quadratic=quadratic, offset=problem.objective_offset)
        for constraint in problem.constraints:
            if set(constraint.linear).issubset(selected):
                subproblem.add_constraint(
                    constraint.linear,
                    sense=constraint.sense,
                    rhs=constraint.rhs,
                    name=constraint.name,
                    constraint_type=constraint.constraint_type,
                )
        return subproblem


def _repair_continuous_bounds(
    problem: HybridOptimizationProblem,
    solution: dict[str, float],
    *,
    fixed_binary: set[str],
) -> dict[str, float]:
    repaired = dict(solution)
    continuous_vars = [name for name, spec in problem.variables.items() if spec.kind == "continuous"]
    for _iteration in range(20):
        changed = False
        for constraint in problem.constraints:
            lhs = sum(coefficient * repaired[name] for name, coefficient in constraint.linear.items())
            if constraint.sense == "<=" and lhs > constraint.rhs:
                changed |= _repair_single_constraint(problem, repaired, continuous_vars, constraint.linear, lhs - constraint.rhs)
            elif constraint.sense == ">=" and lhs < constraint.rhs:
                changed |= _repair_single_constraint(
                    problem,
                    repaired,
                    continuous_vars,
                    {name: -coefficient for name, coefficient in constraint.linear.items()},
                    constraint.rhs - lhs,
                )
            elif constraint.sense == "==" and abs(lhs - constraint.rhs) > 1e-9:
                difference = lhs - constraint.rhs
                linear = constraint.linear if difference > 0 else {
                    name: -coefficient for name, coefficient in constraint.linear.items()
                }
                changed |= _repair_single_constraint(problem, repaired, continuous_vars, linear, abs(difference))
        if not changed:
            break
    for name in fixed_binary:
        repaired[name] = int(repaired[name])
    return repaired


def _repair_single_constraint(
    problem: HybridOptimizationProblem,
    repaired: dict[str, float],
    continuous_vars: list[str],
    linear: dict[str, float],
    excess: float,
) -> bool:
    changed = False
    for name in continuous_vars:
        coefficient = linear.get(name, 0.0)
        if abs(coefficient) <= 1e-12:
            continue
        lower, upper = problem.variable_bounds(name)
        current = repaired[name]
        if coefficient > 0:
            delta = min(current - lower, excess / coefficient)
            if delta > 1e-12:
                repaired[name] = current - delta
                excess -= coefficient * delta
                changed = True
        else:
            delta = min(upper - current, excess / abs(coefficient))
            if delta > 1e-12:
                repaired[name] = current + delta
                excess -= abs(coefficient) * delta
                changed = True
        if excess <= 1e-9:
            break
    return changed
