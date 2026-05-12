from __future__ import annotations

import math
import random
from time import perf_counter

from quantum_hackathon.modeling.qubo import QuboModel

from .base import RawSampleSet, SamplerBackend, SamplerConfig


class SimulatedAnnealingBackend(SamplerBackend):
    name = "simulated_annealing"

    def sample(self, model: QuboModel, config: SamplerConfig | None = None) -> RawSampleSet:
        started = perf_counter()
        resolved = config or SamplerConfig()
        rng = random.Random(resolved.seed)
        samples: list[tuple[int, ...]] = []
        for _read in range(resolved.num_reads):
            state = [rng.randrange(2) for _ in range(model.num_variables)]
            current_energy = model.energy(state)
            for sweep in range(max(1, resolved.num_sweeps)):
                beta = _geometric_beta(sweep, max(1, resolved.num_sweeps))
                indices = list(range(model.num_variables))
                rng.shuffle(indices)
                for index in indices:
                    state[index] = 1 - state[index]
                    next_energy = model.energy(state)
                    delta = next_energy - current_energy
                    if delta <= 0 or rng.random() < math.exp(-beta * delta):
                        current_energy = next_energy
                    else:
                        state[index] = 1 - state[index]
            samples.append(tuple(state))
        return RawSampleSet.from_samples(
            samples,
            source_backend=self.name,
            energy_fn=model.energy,
            timing={"sample_ms": (perf_counter() - started) * 1000.0},
            backend_metadata={
                "num_reads": resolved.num_reads,
                "num_sweeps": resolved.num_sweeps,
                "seed": resolved.seed,
            },
        )


def _geometric_beta(sweep: int, total_sweeps: int) -> float:
    beta_start = 0.1
    beta_end = 8.0
    if total_sweeps <= 1:
        return beta_end
    ratio = sweep / (total_sweeps - 1)
    return beta_start * ((beta_end / beta_start) ** ratio)
