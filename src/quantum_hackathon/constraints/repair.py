from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RepairResult:
    assignment: dict[str, int]
    changed_variables: tuple[str, ...]
    repair_reason: str


class AtMostOneRepair:
    def __init__(self, variables: tuple[str, ...]):
        self.variables = variables

    def repair(self, assignment: Mapping[str, int], objective_linear: Mapping[str, float]) -> RepairResult:
        repaired = dict(assignment)
        active = [variable for variable in self.variables if repaired.get(variable, 0) == 1]
        if len(active) <= 1:
            return RepairResult(repaired, (), "already_satisfied")
        keep = min(active, key=lambda variable: objective_linear.get(variable, 0.0))
        changed: list[str] = []
        for variable in active:
            if variable != keep:
                repaired[variable] = 0
                changed.append(variable)
        return RepairResult(repaired, tuple(changed), "kept_best_marginal_objective")


class CardinalityRepair:
    def __init__(self, variables: tuple[str, ...], k: int):
        self.variables = variables
        self.k = k

    def repair(self, assignment: Mapping[str, int], objective_linear: Mapping[str, float]) -> RepairResult:
        repaired = dict(assignment)
        changed: list[str] = []
        active = [variable for variable in self.variables if repaired.get(variable, 0) == 1]
        inactive = [variable for variable in self.variables if repaired.get(variable, 0) == 0]
        if len(active) > self.k:
            remove = sorted(active, key=lambda variable: objective_linear.get(variable, 0.0), reverse=True)
            for variable in remove[: len(active) - self.k]:
                repaired[variable] = 0
                changed.append(variable)
        elif len(active) < self.k:
            add = sorted(inactive, key=lambda variable: objective_linear.get(variable, 0.0))
            for variable in add[: self.k - len(active)]:
                repaired[variable] = 1
                changed.append(variable)
        return RepairResult(repaired, tuple(changed), "adjusted_hamming_weight")


class OneHotRepair(CardinalityRepair):
    def __init__(self, variables: tuple[str, ...]):
        super().__init__(variables, k=1)
