from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class ReductionStep:
    eliminated_variable: int
    kept_variable: int
    relation: str
    correlation: float


@dataclass(frozen=True)
class RecursiveReductionResult:
    elimination_history: list[ReductionStep]
    reverse_map: dict[int, tuple[int, str]]
    metadata: dict = field(default_factory=dict)


class RecursiveQaoaReducer:
    def reduce_once(self, samples: Iterable[Iterable[int]]) -> RecursiveReductionResult:
        bitstrings = [tuple(int(bit) for bit in sample) for sample in samples]
        if not bitstrings:
            return RecursiveReductionResult([], {}, {"reason": "empty_sample_set"})
        pair = self.strongest_correlation(bitstrings)
        if pair is None:
            return RecursiveReductionResult([], {}, {"reason": "fewer_than_two_variables"})
        left, right, correlation = pair
        relation = "same" if correlation >= 0.0 else "opposite"
        step = ReductionStep(
            eliminated_variable=right,
            kept_variable=left,
            relation=relation,
            correlation=correlation,
        )
        return RecursiveReductionResult(
            elimination_history=[step],
            reverse_map={right: (left, relation)},
            metadata={"num_samples": len(bitstrings), "num_variables": len(bitstrings[0])},
        )

    def strongest_correlation(
        self,
        samples: Iterable[Iterable[int]],
    ) -> tuple[int, int, float] | None:
        bitstrings = [tuple(int(bit) for bit in sample) for sample in samples]
        if not bitstrings or len(bitstrings[0]) < 2:
            return None
        num_variables = len(bitstrings[0])
        best: tuple[int, int, float] | None = None
        for left in range(num_variables):
            for right in range(left + 1, num_variables):
                correlation = _spin_correlation(bitstrings, left, right)
                if best is None or abs(correlation) > abs(best[2]):
                    best = (left, right, correlation)
        return best


def _spin_correlation(samples: list[tuple[int, ...]], left: int, right: int) -> float:
    total = 0.0
    for bits in samples:
        left_spin = 1 - 2 * bits[left]
        right_spin = 1 - 2 * bits[right]
        total += left_spin * right_spin
    return total / len(samples)
