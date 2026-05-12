from __future__ import annotations

import random
from time import perf_counter

from quantum_hackathon.modeling.qubo import QuboModel

from .base import RawSampleSet, SamplerBackend, SamplerConfig


class RandomSamplerBackend(SamplerBackend):
    name = "random"

    def sample(self, model: QuboModel, config: SamplerConfig | None = None) -> RawSampleSet:
        started = perf_counter()
        resolved = config or SamplerConfig()
        rng = random.Random(resolved.seed)
        samples = [
            tuple(rng.randrange(2) for _ in range(model.num_variables))
            for _ in range(resolved.num_reads)
        ]
        return RawSampleSet.from_samples(
            samples,
            source_backend=self.name,
            energy_fn=model.energy,
            timing={"sample_ms": (perf_counter() - started) * 1000.0},
            backend_metadata={"num_reads": resolved.num_reads, "seed": resolved.seed},
        )
