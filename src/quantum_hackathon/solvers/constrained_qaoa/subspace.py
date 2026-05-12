from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable


@dataclass(frozen=True)
class FeasibleSubspaceSpec:
    one_hot_groups: tuple[tuple[int, ...], ...] = ()
    exactly_k: tuple[tuple[tuple[int, ...], int], ...] = ()
    fixed_hamming_weight: int | None = None
    constraints_covered: tuple[str, ...] = field(default_factory=tuple)
    constraints_not_covered: tuple[str, ...] = field(default_factory=tuple)
    num_qubits: int | None = None

    def __post_init__(self) -> None:
        one_hot_groups = tuple(tuple(group) for group in self.one_hot_groups)
        exactly_k = tuple((tuple(group), int(k)) for group, k in self.exactly_k)
        _validate_disjoint("one_hot_groups", one_hot_groups)
        _validate_disjoint("exactly_k", tuple(group for group, _k in exactly_k))
        covered = self.constraints_covered or _infer_constraints_covered(
            one_hot_groups,
            exactly_k,
            self.fixed_hamming_weight,
        )
        inferred_qubits = _infer_num_qubits(one_hot_groups, exactly_k, self.fixed_hamming_weight)
        num_qubits = self.num_qubits if self.num_qubits is not None else inferred_qubits
        object.__setattr__(self, "one_hot_groups", one_hot_groups)
        object.__setattr__(self, "exactly_k", exactly_k)
        object.__setattr__(self, "constraints_covered", tuple(covered))
        object.__setattr__(self, "constraints_not_covered", tuple(self.constraints_not_covered))
        object.__setattr__(self, "num_qubits", num_qubits)

    def is_feasible(self, bitstring: Iterable[int]) -> bool:
        bits = tuple(int(bit) for bit in bitstring)
        for group in self.one_hot_groups:
            if sum(bits[index] for index in group) != 1:
                return False
        for group, k in self.exactly_k:
            if sum(bits[index] for index in group) != k:
                return False
        if self.fixed_hamming_weight is not None and sum(bits) != self.fixed_hamming_weight:
            return False
        return True

    def enumerate_basis_states(self) -> tuple[tuple[int, ...], ...]:
        if self.num_qubits is None:
            raise ValueError("num_qubits is required to enumerate unconstrained basis states")
        states = []
        for bits in product((0, 1), repeat=self.num_qubits):
            if self.is_feasible(bits):
                states.append(bits)
        return tuple(states)

    def diagnostics(self) -> dict:
        return {
            "num_qubits": self.num_qubits,
            "one_hot_groups": self.one_hot_groups,
            "exactly_k": self.exactly_k,
            "fixed_hamming_weight": self.fixed_hamming_weight,
            "constraints_covered": self.constraints_covered,
            "constraints_not_covered": self.constraints_not_covered,
        }


@dataclass(frozen=True)
class InitialStateSpec:
    basis_states: tuple[tuple[int, ...], ...]
    probabilities: dict[tuple[int, ...], float]
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_subspace(cls, subspace: FeasibleSubspaceSpec) -> "InitialStateSpec":
        basis_states = subspace.enumerate_basis_states()
        probability = 1.0 / len(basis_states) if basis_states else 0.0
        return cls(
            basis_states=basis_states,
            probabilities={state: probability for state in basis_states},
            metadata={"source": "uniform_feasible_subspace"},
        )


def _validate_disjoint(name: str, groups: tuple[tuple[int, ...], ...]) -> None:
    seen: dict[int, int] = {}
    for group_index, group in enumerate(groups):
        if not group:
            raise ValueError(f"{name} group {group_index} is empty")
        if len(set(group)) != len(group):
            raise ValueError(f"{name} group {group_index} contains overlap within the group")
        for index in group:
            if index < 0:
                raise ValueError(f"{name} contains negative qubit index {index}")
            if index in seen:
                raise ValueError(
                    f"{name} groups overlap on qubit {index}: groups {seen[index]} and {group_index}"
                )
            seen[index] = group_index


def _infer_constraints_covered(
    one_hot_groups: tuple[tuple[int, ...], ...],
    exactly_k: tuple[tuple[tuple[int, ...], int], ...],
    fixed_hamming_weight: int | None,
) -> tuple[str, ...]:
    covered = []
    if one_hot_groups:
        covered.append("one_hot_groups")
    if exactly_k:
        covered.append("exactly_k")
    if fixed_hamming_weight is not None:
        covered.append("fixed_hamming_weight")
    return tuple(covered)


def _infer_num_qubits(
    one_hot_groups: tuple[tuple[int, ...], ...],
    exactly_k: tuple[tuple[tuple[int, ...], int], ...],
    fixed_hamming_weight: int | None,
) -> int | None:
    indices = [index for group in one_hot_groups for index in group]
    indices.extend(index for group, _k in exactly_k for index in group)
    if indices:
        return max(indices) + 1
    if fixed_hamming_weight is not None:
        return None
    return 0
