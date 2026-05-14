from __future__ import annotations

import cmath
import math
import random
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from quantum_hackathon.solvers.base import RawSampleSet

from .hamiltonian import CostHamiltonian


@dataclass(frozen=True)
class StatevectorResult:
    amplitudes: tuple[complex, ...]
    probabilities: dict[tuple[int, ...], float]


@dataclass
class StatevectorQaoaBackend:
    max_qubits: int = 16

    def run(self, hamiltonian: CostHamiltonian, gammas: list[float], betas: list[float]) -> StatevectorResult:
        if hamiltonian.num_qubits > self.max_qubits:
            raise ValueError(f"statevector backend supports at most {self.max_qubits} qubits")
        if len(gammas) != len(betas):
            raise ValueError("gammas and betas must have the same length")

        dimension = 1 << hamiltonian.num_qubits
        amplitude = 1.0 / math.sqrt(dimension)
        state = [complex(amplitude, 0.0) for _ in range(dimension)]

        for gamma, beta in zip(gammas, betas):
            self._apply_cost_phase(state, hamiltonian, gamma)
            self._apply_x_mixer(state, hamiltonian.num_qubits, beta)

        probabilities = {
            self._index_to_bitstring(index, hamiltonian.num_qubits): abs(value) ** 2
            for index, value in enumerate(state)
        }
        return StatevectorResult(amplitudes=tuple(state), probabilities=probabilities)

    def probabilities(
        self,
        hamiltonian: CostHamiltonian,
        gammas: list[float],
        betas: list[float],
    ) -> dict[tuple[int, ...], float]:
        return self.run(hamiltonian, gammas, betas).probabilities

    def _apply_cost_phase(self, state: list[complex], hamiltonian: CostHamiltonian, gamma: float) -> None:
        for index in range(len(state)):
            bitstring = self._index_to_bitstring(index, hamiltonian.num_qubits)
            energy = hamiltonian.classical_energy(bitstring)
            state[index] *= cmath.exp(-1j * gamma * energy)

    def _apply_x_mixer(self, state: list[complex], num_qubits: int, beta: float) -> None:
        cos_beta = math.cos(beta)
        minus_i_sin_beta = complex(0.0, -math.sin(beta))
        for qubit in range(num_qubits):
            stride = 1 << qubit
            block = stride << 1
            for block_start in range(0, len(state), block):
                for offset in range(stride):
                    zero_index = block_start + offset
                    one_index = zero_index + stride
                    zero_amp = state[zero_index]
                    one_amp = state[one_index]
                    state[zero_index] = cos_beta * zero_amp + minus_i_sin_beta * one_amp
                    state[one_index] = minus_i_sin_beta * zero_amp + cos_beta * one_amp

    @staticmethod
    def _index_to_bitstring(index: int, num_qubits: int) -> tuple[int, ...]:
        return tuple((index >> bit_index) & 1 for bit_index in range(num_qubits))


@dataclass
class ShotSimulatorBackend:
    state_backend: StatevectorQaoaBackend = field(default_factory=StatevectorQaoaBackend)
    name: str = "qaoa_shot_simulator"

    def sample_counts(
        self,
        hamiltonian: CostHamiltonian,
        gammas: list[float],
        betas: list[float],
        shots: int,
        seed: int | None = None,
    ) -> dict[tuple[int, ...], int]:
        if shots <= 0:
            raise ValueError("shots must be positive")

        probabilities = self.state_backend.probabilities(hamiltonian, gammas, betas)
        bitstrings = list(probabilities)
        weights = [max(0.0, probabilities[bitstring]) for bitstring in bitstrings]
        rng = random.Random(seed)
        counts: dict[tuple[int, ...], int] = {}
        for bitstring in rng.choices(bitstrings, weights=weights, k=shots):
            counts[bitstring] = counts.get(bitstring, 0) + 1
        return counts

    def sample(
        self,
        hamiltonian: CostHamiltonian,
        gammas: list[float],
        betas: list[float],
        shots: int,
        seed: int | None = None,
    ) -> RawSampleSet:
        counts = self.sample_counts(hamiltonian, gammas, betas, shots, seed)
        expanded = [
            bitstring
            for bitstring, count in counts.items()
            for _ in range(count)
        ]
        return RawSampleSet.from_samples(
            expanded,
            source_backend=self.name,
            energy_fn=hamiltonian.classical_energy,
            backend_metadata={"shots": shots, "seed": seed},
        )


class QiskitAerUnavailableError(RuntimeError):
    """Raised when the optional Qiskit Aer backend is requested but unavailable."""


@dataclass
class QiskitAerQaoaBackend:
    method: str = "statevector"
    device: str = "GPU"
    max_qubits: int = 30
    optimization_level: int = 1
    simulator_options: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"qaoa_aer_{self.device.lower()}"

    @classmethod
    def is_available(cls, device: str = "GPU", method: str = "statevector") -> bool:
        try:
            _, _, aer_simulator = cls._qiskit_imports()
            simulator = aer_simulator(method=method, device=device)
            return device in tuple(simulator.available_devices())
        except Exception:
            return False

    def sample_counts(
        self,
        hamiltonian: CostHamiltonian,
        gammas: list[float],
        betas: list[float],
        shots: int,
        seed: int | None = None,
    ) -> tuple[dict[tuple[int, ...], int], dict[str, Any]]:
        if shots <= 0:
            raise ValueError("shots must be positive")
        if hamiltonian.num_qubits > self.max_qubits:
            raise ValueError(f"qiskit-aer backend supports at most {self.max_qubits} qubits")
        if len(gammas) != len(betas):
            raise ValueError("gammas and betas must have the same length")

        quantum_circuit, transpile, aer_simulator = self._qiskit_imports()
        circuit = self._build_circuit(quantum_circuit, hamiltonian, gammas, betas)
        simulator = aer_simulator(
            method=self.method,
            device=self.device,
            **self.simulator_options,
        )
        transpiled = transpile(circuit, simulator, optimization_level=self.optimization_level)
        run_kwargs: dict[str, Any] = {"shots": shots}
        if seed is not None:
            run_kwargs["seed_simulator"] = seed
        started = perf_counter()
        result = simulator.run(transpiled, **run_kwargs).result()
        elapsed_ms = (perf_counter() - started) * 1000.0
        counts = self._counts_to_bitstrings(result.get_counts(), hamiltonian.num_qubits)
        metadata = dict(getattr(result.results[0], "metadata", {}) or {})
        metadata.update(
            {
                "shots": shots,
                "seed": seed,
                "method": metadata.get("method", self.method),
                "device": metadata.get("device", self.device),
                "elapsed_ms": elapsed_ms,
            }
        )
        return counts, metadata

    def sample(
        self,
        hamiltonian: CostHamiltonian,
        gammas: list[float],
        betas: list[float],
        shots: int,
        seed: int | None = None,
    ) -> RawSampleSet:
        counts, metadata = self.sample_counts(hamiltonian, gammas, betas, shots, seed)
        expanded = [
            bitstring
            for bitstring, count in counts.items()
            for _ in range(count)
        ]
        return RawSampleSet.from_samples(
            expanded,
            source_backend=self.name,
            energy_fn=hamiltonian.classical_energy,
            timing={"aer_run_ms": float(metadata["elapsed_ms"])},
            backend_metadata=metadata,
        )

    @staticmethod
    def _qiskit_imports() -> tuple[Any, Any, Any]:
        try:
            from qiskit import QuantumCircuit, transpile
            from qiskit_aer import AerSimulator
        except Exception as exc:  # pragma: no cover - depends on optional environment.
            raise QiskitAerUnavailableError(
                "qiskit-aer is not installed or cannot initialize in this environment"
            ) from exc
        return QuantumCircuit, transpile, AerSimulator

    @staticmethod
    def _build_circuit(
        quantum_circuit: Any,
        hamiltonian: CostHamiltonian,
        gammas: list[float],
        betas: list[float],
    ) -> Any:
        circuit = quantum_circuit(hamiltonian.num_qubits, hamiltonian.num_qubits)
        circuit.h(range(hamiltonian.num_qubits))

        for gamma, beta in zip(gammas, betas):
            for index, coefficient in sorted(hamiltonian.z_terms.items()):
                circuit.rz(2.0 * gamma * coefficient, index)
            for (left, right), coefficient in sorted(hamiltonian.zz_terms.items()):
                angle = 2.0 * gamma * coefficient
                if hasattr(circuit, "rzz"):
                    circuit.rzz(angle, left, right)
                else:  # pragma: no cover - retained for older Qiskit variants.
                    circuit.cx(left, right)
                    circuit.rz(angle, right)
                    circuit.cx(left, right)
            for qubit in range(hamiltonian.num_qubits):
                circuit.rx(2.0 * beta, qubit)

        circuit.measure(range(hamiltonian.num_qubits), range(hamiltonian.num_qubits))
        return circuit

    @staticmethod
    def _counts_to_bitstrings(counts: dict[str, int], num_qubits: int) -> dict[tuple[int, ...], int]:
        converted: dict[tuple[int, ...], int] = {}
        for raw_key, count in counts.items():
            compact = str(raw_key).replace(" ", "")
            if compact.startswith("0x"):
                value = int(compact, 16)
                bits = tuple((value >> bit_index) & 1 for bit_index in range(num_qubits))
            else:
                if len(compact) != num_qubits:
                    compact = compact.zfill(num_qubits)
                bits = tuple(int(bit) for bit in reversed(compact))
            converted[bits] = converted.get(bits, 0) + int(count)
        return converted
