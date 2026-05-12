from __future__ import annotations

from dataclasses import dataclass, field

from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import DecodedSample, QuboBuilder, QuboModel
from quantum_hackathon.solvers.base import SamplerConfig, SolverResult
from quantum_hackathon.solvers.exact import ExactSolverBackend
from quantum_hackathon.solvers.simulated_annealing import SimulatedAnnealingBackend

from .mixers import MixerBuildResult, OneHotXYMixerStrategy
from .subspace import FeasibleSubspaceSpec


@dataclass
class ConstrainedQaoaResult:
    samples: list[DecodedSample]
    best_feasible_sample: DecodedSample | None
    backend_result: SolverResult
    diagnostics: dict
    warnings: list[str] = field(default_factory=list)


class ConstrainedQaoaRunner:
    def __init__(self, *, exact_variable_limit: int = 25):
        self.exact_variable_limit = exact_variable_limit

    def solve(
        self,
        problem: OptimizationProblem | QuboModel,
        *,
        subspace: FeasibleSubspaceSpec | None = None,
        mixer: MixerBuildResult | None = None,
        config: SamplerConfig | None = None,
    ) -> ConstrainedQaoaResult:
        model = problem if isinstance(problem, QuboModel) else QuboBuilder().build(problem)
        resolved_subspace = subspace or _infer_subspace(model.problem)
        resolved_mixer = mixer or OneHotXYMixerStrategy().build(resolved_subspace)
        backend = (
            ExactSolverBackend()
            if model.num_variables <= self.exact_variable_limit
            else SimulatedAnnealingBackend()
        )
        backend_result = backend.solve(model, config or SamplerConfig(seed=0))
        best_feasible = _best_feasible_in_subspace(backend_result.samples, resolved_subspace)
        diagnostics = {
            "route": "constrained_qaoa_metadata_mvp",
            "backend": backend_result.backend_name,
            "subspace": resolved_subspace.diagnostics(),
            "mixer": {
                "name": resolved_mixer.name,
                "preserves_feasibility": resolved_mixer.preserves_feasibility,
                "transition_graph_connected": resolved_mixer.transition_graph_connected,
                "resource_estimate": resolved_mixer.resource_estimate,
                "warnings": resolved_mixer.warnings,
            },
            "feasible_ratio": backend_result.feasible_ratio,
        }
        warnings = list(resolved_mixer.warnings)
        if best_feasible is None:
            warnings.append("no_feasible_sample_found_in_subspace")
        return ConstrainedQaoaResult(
            samples=backend_result.samples,
            best_feasible_sample=best_feasible,
            backend_result=backend_result,
            diagnostics=diagnostics,
            warnings=warnings,
        )


def _infer_subspace(problem: OptimizationProblem) -> FeasibleSubspaceSpec:
    variable_order = tuple(problem.variables)
    groups = []
    covered = []
    not_covered = []
    for constraint in problem.constraints:
        if (
            constraint.constraint_type == "exactly_one"
            and constraint.sense == "=="
            and abs(constraint.rhs - 1.0) <= 1e-9
            and all(abs(coefficient - 1.0) <= 1e-9 for coefficient in constraint.linear.values())
        ):
            groups.append(tuple(variable_order.index(name) for name in constraint.linear))
            covered.append(constraint.name)
        else:
            not_covered.append(constraint.name)
    return FeasibleSubspaceSpec(
        one_hot_groups=tuple(groups),
        constraints_covered=tuple(covered) if covered else (),
        constraints_not_covered=tuple(not_covered),
        num_qubits=len(variable_order),
    )


def _best_feasible_in_subspace(
    samples: list[DecodedSample],
    subspace: FeasibleSubspaceSpec,
) -> DecodedSample | None:
    for sample in samples:
        if sample.is_feasible and subspace.is_feasible(sample.bitstring):
            return sample
    return None
