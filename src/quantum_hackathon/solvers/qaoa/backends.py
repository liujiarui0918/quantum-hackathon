from __future__ import annotations

import cmath
import math
import random
from dataclasses import dataclass, field

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
