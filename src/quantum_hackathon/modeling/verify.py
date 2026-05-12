from __future__ import annotations

from dataclasses import dataclass

from quantum_hackathon.solvers.base import SolverResult
from quantum_hackathon.solvers.exact import ExactSolverBackend

from .qubo import DecodedSample, QuboModel


@dataclass
class BruteForceResult:
    result: SolverResult

    @property
    def samples(self) -> list[DecodedSample]:
        return self.result.samples

    @property
    def best_sample(self) -> DecodedSample:
        best = self.result.best_feasible()
        if best is not None:
            return best
        if not self.result.samples:
            raise ValueError("brute force result has no samples")
        return self.result.samples[0]

    def best_feasible(self) -> DecodedSample | None:
        return self.result.best_feasible()


def brute_force_solve(model: QuboModel) -> BruteForceResult:
    return BruteForceResult(ExactSolverBackend().solve(model))
