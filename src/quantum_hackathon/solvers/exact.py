from __future__ import annotations

from time import perf_counter

from quantum_hackathon.modeling.qubo import QuboModel

from .base import RawSampleSet, SamplerBackend, SamplerConfig


class ExactSolverBackend(SamplerBackend):
    name = "exact"

    def sample(self, model: QuboModel, config: SamplerConfig | None = None) -> RawSampleSet:
        started = perf_counter()
        if model.num_variables > 25:
            raise ValueError("ExactSolverBackend refuses to enumerate more than 25 binary variables")
        samples = list(model.iter_bitstrings())
        return RawSampleSet.from_samples(
            samples,
            source_backend=self.name,
            energy_fn=model.energy,
            timing={"sample_ms": (perf_counter() - started) * 1000.0},
            backend_metadata={"enumerated": len(samples)},
        )
