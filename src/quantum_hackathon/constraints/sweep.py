from __future__ import annotations

from dataclasses import dataclass

from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder
from quantum_hackathon.solvers import ExactSolverBackend, SamplerConfig, SamplerBackend

from .specs import copy_problem


@dataclass(frozen=True)
class PenaltySweepReport:
    rows: list[dict]
    recommended_weight: float | None


class PenaltySweep:
    def __init__(self, solver: SamplerBackend | None = None, config: SamplerConfig | None = None):
        self.solver = solver or ExactSolverBackend()
        self.config = config or SamplerConfig()

    def run(
        self,
        problem: OptimizationProblem,
        constraint_name: str,
        *,
        weights: list[float],
    ) -> PenaltySweepReport:
        rows: list[dict] = []
        recommended: float | None = None
        for weight in weights:
            candidate = copy_problem(problem)
            for constraint in candidate.constraints:
                if constraint.name == constraint_name:
                    object.__setattr__(constraint, "penalty_weight", weight)
            model = QuboBuilder().build(candidate)
            result = self.solver.solve(model, self.config)
            best_feasible = result.best_feasible()
            row = {
                "constraint_name": constraint_name,
                "weight": weight,
                "best_feasible_objective": best_feasible.objective_value if best_feasible else None,
                "best_raw_energy": result.best_raw_energy_sample.qubo_energy if result.best_raw_energy_sample else None,
                "best_raw_energy_feasible": (
                    result.best_raw_energy_sample.is_feasible if result.best_raw_energy_sample else False
                ),
                "feasible_ratio": result.feasible_ratio,
                "coefficient_ratio": model.diagnostics()["coefficient_ratio"],
            }
            rows.append(row)
            if recommended is None and row["best_raw_energy_feasible"] and best_feasible is not None:
                recommended = weight
        return PenaltySweepReport(rows=rows, recommended_weight=recommended)
