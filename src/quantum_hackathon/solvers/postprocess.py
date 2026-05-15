from __future__ import annotations

from time import perf_counter

from quantum_hackathon.modeling.qubo import QuboModel

from .base import RawSampleSet, SolverResult


class SolutionPostprocessor:
    def process(self, model: QuboModel, raw_sampleset: RawSampleSet) -> SolverResult:
        started = perf_counter()
        decoded = [
            model.decode(
                raw_sample.bitstring,
                num_occurrences=raw_sample.num_occurrences,
                source_backend=raw_sampleset.source_backend,
            )
            for raw_sample in raw_sampleset.samples
        ]
        best_raw = min(decoded, key=lambda sample: sample.qubo_energy, default=None)
        objective_direction = -1.0 if model.problem.sense == "maximize" else 1.0
        ranked = sorted(
            decoded,
            key=lambda sample: (
                not sample.is_feasible,
                objective_direction * sample.objective_value if sample.is_feasible else sample.total_violation,
                sample.total_violation,
                sample.qubo_energy,
                -sample.num_occurrences,
                sample.bitstring,
            ),
        )
        timing = dict(raw_sampleset.timing)
        timing.setdefault("postprocess_ms", (perf_counter() - started) * 1000.0)
        return SolverResult(
            samples=ranked,
            best_raw_energy_sample=best_raw,
            backend_name=raw_sampleset.source_backend,
            timing=timing,
            diagnostics={"raw_sample_count": len(raw_sampleset.samples), **raw_sampleset.backend_metadata},
        )
