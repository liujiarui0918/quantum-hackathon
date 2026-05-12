from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Iterable

from quantum_hackathon.modeling.qubo import DecodedSample, QuboModel


@dataclass(frozen=True)
class SamplerConfig:
    seed: int | None = None
    num_reads: int = 100
    num_sweeps: int = 1000
    return_top_k: int = 20
    time_limit: float | None = None
    max_samples: int | None = None


@dataclass(frozen=True)
class RawSample:
    bitstring: tuple[int, ...]
    energy: float
    num_occurrences: int = 1


@dataclass
class RawSampleSet:
    samples: list[RawSample]
    source_backend: str
    timing: dict[str, float] = field(default_factory=dict)
    backend_metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_samples(
        cls,
        samples: Iterable[Iterable[int]],
        *,
        source_backend: str,
        energy_fn: Callable[[tuple[int, ...]], float],
        timing: dict[str, float] | None = None,
        backend_metadata: dict | None = None,
    ) -> "RawSampleSet":
        aggregated: dict[tuple[int, ...], RawSample] = {}
        for sample in samples:
            bitstring = tuple(int(bit) for bit in sample)
            if bitstring in aggregated:
                existing = aggregated[bitstring]
                aggregated[bitstring] = RawSample(
                    bitstring=existing.bitstring,
                    energy=existing.energy,
                    num_occurrences=existing.num_occurrences + 1,
                )
            else:
                aggregated[bitstring] = RawSample(bitstring=bitstring, energy=energy_fn(bitstring))
        ordered = sorted(aggregated.values(), key=lambda item: (item.energy, item.bitstring))
        return cls(
            samples=ordered,
            source_backend=source_backend,
            timing=timing or {},
            backend_metadata=backend_metadata or {},
        )


@dataclass
class SolverResult:
    samples: list[DecodedSample]
    best_raw_energy_sample: DecodedSample | None
    backend_name: str
    timing: dict[str, float] = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    config: SamplerConfig | None = None

    @property
    def feasible_ratio(self) -> float:
        total = sum(sample.num_occurrences for sample in self.samples)
        if total == 0:
            return 0.0
        feasible = sum(sample.num_occurrences for sample in self.samples if sample.is_feasible)
        return feasible / total

    def best_feasible(self) -> DecodedSample | None:
        for sample in self.samples:
            if sample.is_feasible:
                return sample
        return None


class SamplerBackend:
    name = "sampler"

    def sample(self, model: QuboModel, config: SamplerConfig) -> RawSampleSet:
        raise NotImplementedError

    def solve(self, model: QuboModel, config: SamplerConfig | None = None) -> SolverResult:
        from .postprocess import SolutionPostprocessor

        started = perf_counter()
        resolved_config = config or SamplerConfig()
        raw = self.sample(model, resolved_config)
        result = SolutionPostprocessor().process(model, raw)
        result.backend_name = self.name
        result.config = resolved_config
        result.timing.setdefault("total_ms", (perf_counter() - started) * 1000.0)
        return result
