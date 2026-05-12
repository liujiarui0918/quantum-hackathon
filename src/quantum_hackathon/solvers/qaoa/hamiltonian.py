from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from quantum_hackathon.modeling.qubo import QuboModel


@dataclass(frozen=True)
class CostHamiltonian:
    num_qubits: int
    offset: float
    z_terms: dict[int, float] = field(default_factory=dict)
    zz_terms: dict[tuple[int, int], float] = field(default_factory=dict)

    def classical_energy(self, bitstring: Iterable[int]) -> float:
        bits = tuple(int(bit) for bit in bitstring)
        if len(bits) != self.num_qubits:
            raise ValueError(f"expected {self.num_qubits} bits, got {len(bits)}")

        spins = [1 - 2 * bit for bit in bits]
        energy = self.offset
        for index, coefficient in self.z_terms.items():
            energy += coefficient * spins[index]
        for (left, right), coefficient in self.zz_terms.items():
            energy += coefficient * spins[left] * spins[right]
        return round(energy, 12)

    def iter_bitstrings(self) -> Iterable[tuple[int, ...]]:
        for state_index in range(1 << self.num_qubits):
            yield tuple((state_index >> bit_index) & 1 for bit_index in range(self.num_qubits))


class CostHamiltonianBuilder:
    @staticmethod
    def from_qubo(model: QuboModel) -> CostHamiltonian:
        z_terms: dict[int, float] = {}
        zz_terms: dict[tuple[int, int], float] = {}
        offset = model.offset

        for (left, right), coefficient in model.qubo.items():
            if left == right:
                offset += coefficient / 2.0
                z_terms[left] = z_terms.get(left, 0.0) - coefficient / 2.0
                continue

            ordered = (left, right) if left < right else (right, left)
            offset += coefficient / 4.0
            z_terms[left] = z_terms.get(left, 0.0) - coefficient / 4.0
            z_terms[right] = z_terms.get(right, 0.0) - coefficient / 4.0
            zz_terms[ordered] = zz_terms.get(ordered, 0.0) + coefficient / 4.0

        return CostHamiltonian(
            num_qubits=model.num_variables,
            offset=offset,
            z_terms={index: value for index, value in z_terms.items() if abs(value) > 1e-12},
            zz_terms={indices: value for indices, value in zz_terms.items() if abs(value) > 1e-12},
        )
