from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder, QuboBuilderConfig
from quantum_hackathon.solvers.base import SamplerBackend, SamplerConfig


@dataclass
class BenchmarkReport:
    rows: list[dict]

    def to_markdown(self) -> str:
        if not self.rows:
            return ""
        headers = list(self.rows[0])
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in self.rows:
            lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
        return "\n".join(lines)


class AnnealingBenchmarkRunner:
    def __init__(
        self,
        *,
        backends: list[SamplerBackend],
        config: SamplerConfig | None = None,
        builder_config: QuboBuilderConfig | None = None,
    ):
        self.backends = backends
        self.config = config or SamplerConfig()
        self.builder_config = builder_config or QuboBuilderConfig()

    def run(self, problem_suite: list[OptimizationProblem]) -> BenchmarkReport:
        rows: list[dict] = []
        for problem in problem_suite:
            model = QuboBuilder(self.builder_config).build(problem)
            for backend in self.backends:
                started = perf_counter()
                result = backend.solve(model, self.config)
                best_feasible = result.best_feasible()
                elapsed_ms = (perf_counter() - started) * 1000.0
                rows.append(
                    {
                        "problem_name": problem.name,
                        "solver": backend.name,
                        "best_feasible_objective": (
                            best_feasible.objective_value if best_feasible is not None else None
                        ),
                        "best_raw_energy": (
                            result.best_raw_energy_sample.qubo_energy
                            if result.best_raw_energy_sample is not None
                            else None
                        ),
                        "best_raw_energy_feasible": (
                            result.best_raw_energy_sample.is_feasible
                            if result.best_raw_energy_sample is not None
                            else None
                        ),
                        "feasible_sample_ratio": result.feasible_ratio,
                        "unique_feasible_samples": sum(1 for sample in result.samples if sample.is_feasible),
                        "total_ms": result.timing.get("total_ms", elapsed_ms),
                        "seed": self.config.seed,
                    }
                )
        return BenchmarkReport(rows)
