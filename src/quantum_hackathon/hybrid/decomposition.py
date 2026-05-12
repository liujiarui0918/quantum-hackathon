from __future__ import annotations

from dataclasses import dataclass

from .problem import HybridConstraintSpec, HybridOptimizationProblem


@dataclass(frozen=True)
class DecompositionAnalysis:
    binary_block_vars: tuple[str, ...]
    continuous_block_vars: tuple[str, ...]
    linking_constraints: tuple[HybridConstraintSpec, ...]
    pure_binary_terms: tuple[tuple[str, str, float], ...]
    pure_continuous_terms: tuple[tuple[str, str, float], ...]
    cross_terms: tuple[tuple[str, str, float], ...]
    recommended_strategy: str


class ProblemDecomposer:
    def analyze(self, problem: HybridOptimizationProblem) -> DecompositionAnalysis:
        binary_vars = tuple(name for name, spec in problem.variables.items() if spec.kind == "binary")
        continuous_vars = tuple(name for name, spec in problem.variables.items() if spec.kind == "continuous")
        binary_set = set(binary_vars)
        continuous_set = set(continuous_vars)

        linking_constraints = []
        for constraint in problem.constraints:
            names = set(constraint.linear)
            if names & binary_set and names & continuous_set:
                linking_constraints.append(constraint)

        pure_binary_terms: list[tuple[str, str, float]] = []
        pure_continuous_terms: list[tuple[str, str, float]] = []
        cross_terms: list[tuple[str, str, float]] = []
        for (left, right), coefficient in problem.objective_quadratic.items():
            term = (left, right, coefficient)
            if left in binary_set and right in binary_set:
                pure_binary_terms.append(term)
            elif left in continuous_set and right in continuous_set:
                pure_continuous_terms.append(term)
            else:
                cross_terms.append(term)

        if continuous_vars and binary_vars:
            strategy = "relax_round_repair"
        elif binary_vars:
            strategy = "binary_only"
        else:
            strategy = "continuous_relaxation"

        return DecompositionAnalysis(
            binary_block_vars=binary_vars,
            continuous_block_vars=continuous_vars,
            linking_constraints=tuple(linking_constraints),
            pure_binary_terms=tuple(pure_binary_terms),
            pure_continuous_terms=tuple(pure_continuous_terms),
            cross_terms=tuple(cross_terms),
            recommended_strategy=strategy,
        )
