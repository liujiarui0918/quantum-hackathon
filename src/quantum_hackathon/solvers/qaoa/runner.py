from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from quantum_hackathon.modeling.qubo import QuboModel
from quantum_hackathon.solvers.base import SolverResult
from quantum_hackathon.solvers.postprocess import SolutionPostprocessor

from .backends import ShotSimulatorBackend, StatevectorQaoaBackend
from .hamiltonian import CostHamiltonianBuilder
from .optimizers import OptimizerTraceEntry, SimpleQaoaOptimizer


@dataclass(frozen=True)
class QaoaConfig:
    p: int = 1
    shots: int = 100
    seed: int | None = None
    max_qubits: int = 16
    grid_size: int = 7
    random_trials: int = 20


@dataclass
class QaoaResult:
    best_parameters: dict[str, tuple[float, ...]]
    best_samples: SolverResult
    optimizer_trace: list[OptimizerTraceEntry]
    diagnostics: dict = field(default_factory=dict)


class QaoaRunner:
    def solve(self, qubo_model: QuboModel, config: QaoaConfig | None = None) -> QaoaResult:
        started = perf_counter()
        resolved = config or QaoaConfig()
        hamiltonian = CostHamiltonianBuilder.from_qubo(qubo_model)
        state_backend = StatevectorQaoaBackend(max_qubits=resolved.max_qubits)
        shot_backend = ShotSimulatorBackend(state_backend=state_backend)

        def expected_energy(gammas: list[float], betas: list[float]) -> float:
            probabilities = state_backend.probabilities(hamiltonian, gammas, betas)
            return sum(
                probability * hamiltonian.classical_energy(bitstring)
                for bitstring, probability in probabilities.items()
            )

        optimizer = SimpleQaoaOptimizer(
            grid_size=resolved.grid_size,
            random_trials=resolved.random_trials,
            seed=resolved.seed,
        )
        optimized = optimizer.minimize(expected_energy, resolved.p)
        raw_samples = shot_backend.sample(
            hamiltonian,
            list(optimized.gammas),
            list(optimized.betas),
            resolved.shots,
            resolved.seed,
        )
        raw_samples.timing["total_ms"] = (perf_counter() - started) * 1000.0
        raw_samples.backend_metadata.update(
            {
                "p": resolved.p,
                "expected_energy": optimized.value,
                "best_gammas": optimized.gammas,
                "best_betas": optimized.betas,
            }
        )

        postprocessed = SolutionPostprocessor().process(qubo_model, raw_samples)
        postprocessed.backend_name = shot_backend.name
        postprocessed.diagnostics.update(
            {
                "qaoa_trace_length": len(optimized.trace),
                "expected_energy": optimized.value,
            }
        )
        return QaoaResult(
            best_parameters={"gammas": optimized.gammas, "betas": optimized.betas},
            best_samples=postprocessed,
            optimizer_trace=optimized.trace,
            diagnostics={
                "num_qubits": hamiltonian.num_qubits,
                "shots": resolved.shots,
                "trace_length": len(optimized.trace),
                "total_ms": raw_samples.timing["total_ms"],
            },
        )
