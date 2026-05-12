from __future__ import annotations

from dataclasses import dataclass, field

from .subspace import FeasibleSubspaceSpec, InitialStateSpec


@dataclass(frozen=True)
class WarmStartStateSpec:
    group_probabilities: dict[tuple[int, ...], dict[int, float]]
    initial_state: InitialStateSpec
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_probabilities(
        cls,
        subspace: FeasibleSubspaceSpec,
        probabilities: dict[int, float],
        *,
        smoothing: float = 1e-6,
    ) -> "WarmStartStateSpec":
        if smoothing < 0:
            raise ValueError("smoothing must be non-negative")
        group_probabilities: dict[tuple[int, ...], dict[int, float]] = {}
        for group in subspace.one_hot_groups:
            raw = {
                index: min(1.0, max(0.0, float(probabilities.get(index, 0.0)))) + smoothing
                for index in group
            }
            group_probabilities[group] = _normalize(raw)
        initial_state = _initial_state_from_group_probabilities(subspace, group_probabilities)
        return cls(
            group_probabilities=group_probabilities,
            initial_state=initial_state,
            metadata={"smoothing": smoothing, "source": "warm_start_probabilities"},
        )


def _normalize(values: dict[int, float]) -> dict[int, float]:
    total = sum(values.values())
    if total <= 0.0:
        uniform = 1.0 / len(values) if values else 0.0
        return {index: uniform for index in values}
    return {index: value / total for index, value in values.items()}


def _initial_state_from_group_probabilities(
    subspace: FeasibleSubspaceSpec,
    group_probabilities: dict[tuple[int, ...], dict[int, float]],
) -> InitialStateSpec:
    basis_states = subspace.enumerate_basis_states()
    state_probabilities: dict[tuple[int, ...], float] = {}
    for state in basis_states:
        probability = 1.0
        for group, probabilities in group_probabilities.items():
            selected = next(index for index in group if state[index] == 1)
            probability *= probabilities[selected]
        state_probabilities[state] = probability
    return InitialStateSpec(
        basis_states=basis_states,
        probabilities=state_probabilities,
        metadata={"source": "warm_start_product_distribution"},
    )
