from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from .subspace import FeasibleSubspaceSpec


@dataclass(frozen=True)
class MixerBuildResult:
    name: str
    preserves_feasibility: bool
    transition_graph_connected: bool
    resource_estimate: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OneHotXYMixerStrategy:
    topology: str = "complete"

    def build(self, subspace: FeasibleSubspaceSpec) -> MixerBuildResult:
        warnings: list[str] = []
        all_edges = []
        connected = True
        for group in subspace.one_hot_groups:
            edges = _edges_for_group(group, self.topology)
            all_edges.extend(edges)
            connected = connected and _is_group_connected(group, edges)
        if not subspace.one_hot_groups:
            warnings.append("no_one_hot_groups")
            connected = False
        return MixerBuildResult(
            name="one_hot_xy",
            preserves_feasibility=bool(subspace.one_hot_groups),
            transition_graph_connected=connected,
            resource_estimate={
                "num_groups": len(subspace.one_hot_groups),
                "xy_edges": len(all_edges),
                "two_qubit_terms": len(all_edges) * 2,
            },
            warnings=warnings,
            metadata={"topology": self.topology, "edges": tuple(all_edges)},
        )


@dataclass(frozen=True)
class FixedHammingWeightXYMixerStrategy:
    topology: str = "complete"

    def build(self, subspace: FeasibleSubspaceSpec) -> MixerBuildResult:
        warnings: list[str] = []
        if subspace.num_qubits is None:
            warnings.append("num_qubits_required_for_fixed_hamming_weight_mixer")
            qubits: tuple[int, ...] = ()
        else:
            qubits = tuple(range(subspace.num_qubits))
        edges = _edges_for_group(qubits, self.topology)
        connected = bool(qubits) and _is_group_connected(qubits, edges)
        return MixerBuildResult(
            name="fixed_hamming_weight_xy",
            preserves_feasibility=subspace.fixed_hamming_weight is not None,
            transition_graph_connected=connected,
            resource_estimate={
                "num_qubits": len(qubits),
                "xy_edges": len(edges),
                "two_qubit_terms": len(edges) * 2,
            },
            warnings=warnings,
            metadata={"topology": self.topology, "edges": tuple(edges)},
        )


def _edges_for_group(group: tuple[int, ...], topology: str) -> list[tuple[int, int]]:
    if len(group) < 2:
        return []
    if topology == "complete":
        return [tuple(sorted(edge)) for edge in combinations(group, 2)]
    if topology == "ring":
        return [
            tuple(sorted((group[index], group[(index + 1) % len(group)])))
            for index in range(len(group))
        ]
    if topology == "path":
        return [
            tuple(sorted((group[index], group[index + 1])))
            for index in range(len(group) - 1)
        ]
    raise ValueError(f"unsupported XY mixer topology: {topology}")


def _is_group_connected(group: tuple[int, ...], edges: list[tuple[int, int]]) -> bool:
    if len(group) <= 1:
        return True
    adjacency = {index: set() for index in group}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    seen = set()
    stack = [group[0]]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(adjacency[current] - seen)
    return seen == set(group)
