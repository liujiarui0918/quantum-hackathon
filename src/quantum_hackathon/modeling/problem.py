from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Literal, Sequence, Tuple


Sense = Literal["minimize", "maximize"]
ConstraintSense = Literal["==", "<=", ">="]


@dataclass(frozen=True)
class VariableSpec:
    name: str
    kind: str
    lower: int = 0
    upper: int = 1


@dataclass(frozen=True)
class ConstraintSpec:
    name: str
    linear: Dict[str, float]
    sense: ConstraintSense
    rhs: float
    constraint_type: str = "linear"
    hardness: str = "hard"
    penalty_weight: float | None = None

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(self.linear)


@dataclass
class OptimizationProblem:
    sense: Sense = "minimize"
    name: str = "problem"
    variables: Dict[str, VariableSpec] = field(default_factory=dict)
    objective_linear: Dict[str, float] = field(default_factory=dict)
    objective_quadratic: Dict[Tuple[str, str], float] = field(default_factory=dict)
    objective_offset: float = 0.0
    high_order_terms: list[tuple[tuple[str, ...], float]] = field(default_factory=list)
    constraints: list[ConstraintSpec] = field(default_factory=list)

    def add_binary_var(self, name: str) -> str:
        self._ensure_new_variable(name)
        self.variables[name] = VariableSpec(name=name, kind="binary", lower=0, upper=1)
        return name

    def add_binary_vars(self, prefix: str, count: int) -> list[str]:
        return [self.add_binary_var(f"{prefix}{i}") for i in range(count)]

    def add_integer_var(self, name: str, lower: int, upper: int) -> str:
        if upper < lower:
            raise ValueError(f"integer variable {name!r} has upper < lower")
        self._ensure_new_variable(name)
        self.variables[name] = VariableSpec(name=name, kind="integer", lower=lower, upper=upper)
        return name

    def set_objective(
        self,
        *,
        linear: dict[str, float] | None = None,
        quadratic: dict[tuple[str, str], float] | None = None,
        offset: float = 0.0,
    ) -> None:
        self.objective_linear = dict(linear or {})
        self.objective_quadratic = {
            tuple(sorted(pair)): coefficient for pair, coefficient in (quadratic or {}).items()
        }
        self.objective_offset = offset
        self._validate_variable_names(self.objective_linear)
        for left, right in self.objective_quadratic:
            self._validate_variable_names({left: 0.0, right: 0.0})

    def add_high_order_term(self, variables: Sequence[str], coefficient: float) -> None:
        if len(variables) < 3:
            raise ValueError("high-order terms must contain at least three variables")
        self._validate_variable_names({name: 0.0 for name in variables})
        self.high_order_terms.append((tuple(variables), coefficient))

    def add_constraint(
        self,
        linear: dict[str, float],
        *,
        sense: ConstraintSense,
        rhs: float,
        name: str,
        constraint_type: str = "linear",
        hardness: str = "hard",
        penalty_weight: float | None = None,
    ) -> ConstraintSpec:
        self._validate_variable_names(linear)
        if sense not in ("==", "<=", ">="):
            raise ValueError(f"unsupported constraint sense: {sense}")
        spec = ConstraintSpec(
            name=name,
            linear=dict(linear),
            sense=sense,
            rhs=rhs,
            constraint_type=constraint_type,
            hardness=hardness,
            penalty_weight=penalty_weight,
        )
        self.constraints.append(spec)
        return spec

    def variable_bounds(self, name: str) -> tuple[int, int]:
        spec = self.variables[name]
        return spec.lower, spec.upper

    def evaluate_objective(self, assignment: dict[str, int]) -> float:
        value = self.objective_offset
        for name, coefficient in self.objective_linear.items():
            value += coefficient * assignment[name]
        for (left, right), coefficient in self.objective_quadratic.items():
            value += coefficient * assignment[left] * assignment[right]
        for names, coefficient in self.high_order_terms:
            product = 1
            for name in names:
                product *= assignment[name]
            value += coefficient * product
        return value

    def _ensure_new_variable(self, name: str) -> None:
        if name in self.variables:
            raise ValueError(f"variable {name!r} already exists")

    def _validate_variable_names(self, coefficients: dict[str, float] | Iterable[str]) -> None:
        names = coefficients.keys() if isinstance(coefficients, dict) else coefficients
        missing = [name for name in names if name not in self.variables]
        if missing:
            raise KeyError(f"unknown variable(s): {', '.join(missing)}")
