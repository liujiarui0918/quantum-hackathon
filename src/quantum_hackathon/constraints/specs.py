from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from quantum_hackathon.modeling.problem import ConstraintSpec, OptimizationProblem


@dataclass(frozen=True)
class UnbalancedPenaltyConfig:
    lambda1: float
    lambda2: float


@dataclass(frozen=True)
class ConstraintCompilerConfig:
    default_inequality_strategy: str = "binary_slack"
    penalty_advisor: str = "global_bound"
    strategy_overrides: Mapping[str, UnbalancedPenaltyConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class ConstraintEncodingPlan:
    constraint_name: str
    strategy: str
    penalty_weight: float
    introduced_variables: tuple[str, ...] = ()
    guarantee: str = "exact_ground_state"
    warnings: tuple[str, ...] = ()
    ground_state_not_guaranteed: bool = False


@dataclass(frozen=True)
class FeasibleSubspaceSpec:
    one_hot_groups: tuple[tuple[str, ...], ...] = ()
    exactly_k_groups: tuple[tuple[tuple[str, ...], int], ...] = ()
    constraints_covered: tuple[str, ...] = ()
    constraints_not_covered: tuple[str, ...] = ()
    encoding: str = "one_hot"


@dataclass
class CompiledConstraints:
    original_problem: OptimizationProblem
    problem: OptimizationProblem
    plans: list[ConstraintEncodingPlan]

    def to_problem(self) -> OptimizationProblem:
        return self.problem

    def export_feasible_subspace(self) -> FeasibleSubspaceSpec:
        one_hot_groups: list[tuple[str, ...]] = []
        exactly_k_groups: list[tuple[tuple[str, ...], int]] = []
        covered: list[str] = []
        not_covered: list[str] = []
        constraints_by_name = {constraint.name: constraint for constraint in self.problem.constraints}
        for plan in self.plans:
            constraint = constraints_by_name.get(plan.constraint_name)
            if constraint is None:
                continue
            variables = tuple(constraint.linear)
            if constraint.constraint_type in ("exactly_one", "one_hot") and constraint.sense == "==" and constraint.rhs == 1:
                one_hot_groups.append(variables)
                covered.append(constraint.name)
            elif constraint.constraint_type in ("exactly_k", "cardinality") and constraint.sense == "==":
                exactly_k_groups.append((variables, int(constraint.rhs)))
                covered.append(constraint.name)
            else:
                not_covered.append(constraint.name)
        return FeasibleSubspaceSpec(
            one_hot_groups=tuple(one_hot_groups),
            exactly_k_groups=tuple(exactly_k_groups),
            constraints_covered=tuple(covered),
            constraints_not_covered=tuple(not_covered),
        )


def copy_problem(problem: OptimizationProblem) -> OptimizationProblem:
    clone = OptimizationProblem(sense=problem.sense, name=problem.name)
    for spec in problem.variables.values():
        if spec.kind == "binary":
            clone.add_binary_var(spec.name)
        elif spec.kind == "integer":
            clone.add_integer_var(spec.name, spec.lower, spec.upper)
    clone.set_objective(
        linear=dict(problem.objective_linear),
        quadratic=dict(problem.objective_quadratic),
        offset=problem.objective_offset,
    )
    for names, coefficient in problem.high_order_terms:
        clone.add_high_order_term(names, coefficient)
    for constraint in problem.constraints:
        clone.add_constraint(
            linear=dict(constraint.linear),
            sense=constraint.sense,
            rhs=constraint.rhs,
            name=constraint.name,
            constraint_type=constraint.constraint_type,
            hardness=constraint.hardness,
            penalty_weight=constraint.penalty_weight,
        )
    return clone
