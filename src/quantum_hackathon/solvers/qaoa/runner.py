from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from quantum_hackathon.modeling.qubo import QuboModel
from quantum_hackathon.solvers.base import SolverResult
from quantum_hackathon.solvers.postprocess import SolutionPostprocessor

from .backends import (
    QiskitAerQaoaBackend,
    QiskitAerUnavailableError,
    ShotSimulatorBackend,
    StatevectorQaoaBackend,
)
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
    backend: str = "local"
    aer_device: str = "GPU"
    aer_method: str = "statevector"
    aer_max_qubits: int = 30
    aer_optimization_level: int = 1


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
        execution_backend = shot_backend
        execution_warnings: list[str] = []
        if resolved.backend in {"aer", "aer-gpu", "aer-cpu"}:
            device = (
                "GPU"
                if resolved.backend == "aer-gpu"
                else "CPU"
                if resolved.backend == "aer-cpu"
                else resolved.aer_device
            )
            execution_backend = QiskitAerQaoaBackend(
                method=resolved.aer_method,
                device=device,
                max_qubits=resolved.aer_max_qubits,
                optimization_level=resolved.aer_optimization_level,
            )
        elif resolved.backend != "local":
            raise ValueError(f"unsupported qaoa backend: {resolved.backend}")

        try:
            raw_samples = execution_backend.sample(
                hamiltonian,
                list(optimized.gammas),
                list(optimized.betas),
                resolved.shots,
                resolved.seed,
            )
        except QiskitAerUnavailableError as exc:
            execution_warnings.append(f"falling back to local qaoa shot simulator: {exc}")
            execution_backend = shot_backend
            raw_samples = shot_backend.sample(
                hamiltonian,
                list(optimized.gammas),
                list(optimized.betas),
                resolved.shots,
                resolved.seed,
            )
        except Exception as exc:
            if not isinstance(execution_backend, QiskitAerQaoaBackend):
                raise
            execution_warnings.append(
                f"falling back to local qaoa shot simulator after Aer failure: {type(exc).__name__}: {exc}"
            )
            execution_backend = shot_backend
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
                "requested_backend": resolved.backend,
                "execution_backend": execution_backend.name,
                "expected_energy": optimized.value,
                "best_gammas": optimized.gammas,
                "best_betas": optimized.betas,
            }
        )
        raw_samples.warnings.extend(execution_warnings)

        postprocessed = SolutionPostprocessor().process(qubo_model, raw_samples)
        postprocessed.backend_name = execution_backend.name
        postprocessed.diagnostics.update(
            {
                "qaoa_trace_length": len(optimized.trace),
                "expected_energy": optimized.value,
                "backend_metadata": raw_samples.backend_metadata,
                "warnings": list(raw_samples.warnings),
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
                "requested_backend": resolved.backend,
                "execution_backend": execution_backend.name,
                "backend_metadata": raw_samples.backend_metadata,
                "warnings": list(raw_samples.warnings),
                "total_ms": raw_samples.timing["total_ms"],
            },
        )
