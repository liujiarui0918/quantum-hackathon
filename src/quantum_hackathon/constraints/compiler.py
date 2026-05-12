from __future__ import annotations

from quantum_hackathon.modeling.problem import OptimizationProblem

from .specs import (
    CompiledConstraints,
    ConstraintCompilerConfig,
    ConstraintEncodingPlan,
    UnbalancedPenaltyConfig,
    copy_problem,
)


class ConstraintCompiler:
    def __init__(self, config: ConstraintCompilerConfig | None = None):
        self.config = config or ConstraintCompilerConfig()

    def compile(self, problem: OptimizationProblem) -> CompiledConstraints:
        compiled = copy_problem(problem)
        plans: list[ConstraintEncodingPlan] = []
        objective_bound = _objective_bound(problem)

        for constraint in compiled.constraints:
            weight = constraint.penalty_weight or 2.0 * (objective_bound + 1.0)
            override = self.config.strategy_overrides.get(constraint.name)
            if override is not None:
                self._apply_unbalanced(compiled, constraint.name, override)
                plans.append(
                    ConstraintEncodingPlan(
                        constraint_name=constraint.name,
                        strategy="unbalanced",
                        penalty_weight=override.lambda2,
                        guarantee="heuristic_near_ground",
                        warnings=("unbalanced_ground_state_warning",),
                        ground_state_not_guaranteed=True,
                    )
                )
            elif constraint.constraint_type == "at_most_one":
                plans.append(
                    ConstraintEncodingPlan(
                        constraint_name=constraint.name,
                        strategy="known_pairwise",
                        penalty_weight=weight,
                    )
                )
            elif constraint.sense == "<=":
                plans.append(
                    ConstraintEncodingPlan(
                        constraint_name=constraint.name,
                        strategy="binary_slack",
                        penalty_weight=weight,
                    )
                )
            else:
                plans.append(
                    ConstraintEncodingPlan(
                        constraint_name=constraint.name,
                        strategy="square_penalty",
                        penalty_weight=weight,
                    )
                )
        return CompiledConstraints(original_problem=problem, problem=compiled, plans=plans)

    def _apply_unbalanced(
        self,
        problem: OptimizationProblem,
        constraint_name: str,
        config: UnbalancedPenaltyConfig,
    ) -> None:
        retained_constraints = []
        target = None
        for constraint in problem.constraints:
            if constraint.name == constraint_name:
                target = constraint
            else:
                retained_constraints.append(constraint)
        if target is None:
            raise KeyError(f"unknown constraint {constraint_name!r}")
        if target.sense != "<=":
            raise ValueError("unbalanced penalty MVP supports <= constraints only")

        # residual h(x)=rhs-a^T x, penalty=-lambda1*h + lambda2*h^2.
        # Add it directly into the objective and remove the hard constraint
        # so the base QuboBuilder does not introduce slack.
        problem.objective_offset += -config.lambda1 * target.rhs + config.lambda2 * target.rhs * target.rhs
        for name, coefficient in target.linear.items():
            problem.objective_linear[name] = (
                problem.objective_linear.get(name, 0.0)
                + config.lambda1 * coefficient
                - 2.0 * config.lambda2 * target.rhs * coefficient
                + config.lambda2 * coefficient * coefficient
            )
        items = list(target.linear.items())
        for index, (left, left_coeff) in enumerate(items):
            for right, right_coeff in items[index + 1 :]:
                key = tuple(sorted((left, right)))
                problem.objective_quadratic[key] = (
                    problem.objective_quadratic.get(key, 0.0)
                    + 2.0 * config.lambda2 * left_coeff * right_coeff
                )
        problem.constraints = retained_constraints


def _objective_bound(problem: OptimizationProblem) -> float:
    return (
        abs(problem.objective_offset)
        + sum(abs(value) for value in problem.objective_linear.values())
        + sum(abs(value) for value in problem.objective_quadratic.values())
        + sum(abs(value) for _names, value in problem.high_order_terms)
    )
