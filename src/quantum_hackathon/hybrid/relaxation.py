from __future__ import annotations

from dataclasses import dataclass, field

from .problem import HybridOptimizationProblem


@dataclass(frozen=True)
class RelaxationResult:
    status: str
    objective: float
    variable_values: dict[str, float]
    metadata: dict = field(default_factory=dict)


class RelaxationSolver:
    def solve(self, problem: HybridOptimizationProblem) -> RelaxationResult:
        values: dict[str, float] = {}
        for name, variable in problem.variables.items():
            coefficient = _effective_linear_coefficient(problem, name)
            if problem.sense == "maximize":
                choose_upper = coefficient >= 0.0
            else:
                choose_upper = coefficient < 0.0
            values[name] = variable.upper if choose_upper else variable.lower
        _apply_constraint_sign_pressure(problem, values)
        objective = problem.evaluate_objective(values)
        return RelaxationResult(
            status="heuristic",
            objective=objective,
            variable_values=values,
            metadata={
                "method": "bounds_objective_sign",
                "lower_bound": objective if problem.sense == "minimize" else None,
                "upper_bound": objective if problem.sense == "maximize" else None,
            },
        )


def _effective_linear_coefficient(problem: HybridOptimizationProblem, name: str) -> float:
    coefficient = problem.objective_linear.get(name, 0.0)
    for (left, right), value in problem.objective_quadratic.items():
        if left == name or right == name:
            coefficient += value / 2.0
    return coefficient


def _apply_constraint_sign_pressure(problem: HybridOptimizationProblem, values: dict[str, float]) -> None:
    for constraint in problem.constraints:
        lhs = sum(coefficient * values[name] for name, coefficient in constraint.linear.items())
        if constraint.sense == "<=" and lhs > constraint.rhs:
            for name, coefficient in constraint.linear.items():
                if coefficient < 0.0:
                    values[name] = problem.variables[name].upper
        elif constraint.sense == ">=" and lhs < constraint.rhs:
            for name, coefficient in constraint.linear.items():
                if coefficient > 0.0:
                    values[name] = problem.variables[name].upper
