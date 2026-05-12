from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Literal, Tuple

from quantum_hackathon.modeling.problem import OptimizationProblem


Sense = Literal["minimize", "maximize"]
ConstraintSense = Literal["==", "<=", ">="]
VariableKind = Literal["binary", "continuous"]


@dataclass(frozen=True)
class HybridVariableSpec:
    name: str
    kind: VariableKind
    lower: float = 0.0
    upper: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class HybridConstraintSpec:
    name: str
    linear: Dict[str, float]
    sense: ConstraintSense
    rhs: float
    constraint_type: str = "linear"
    metadata: dict = field(default_factory=dict)

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(self.linear)


@dataclass
class HybridOptimizationProblem:
    sense: Sense = "minimize"
    name: str = "hybrid_problem"
    variables: Dict[str, HybridVariableSpec] = field(default_factory=dict)
    objective_linear: Dict[str, float] = field(default_factory=dict)
    objective_quadratic: Dict[Tuple[str, str], float] = field(default_factory=dict)
    objective_offset: float = 0.0
    constraints: list[HybridConstraintSpec] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_optimization_problem(cls, problem: OptimizationProblem) -> "HybridOptimizationProblem":
        hybrid = cls(sense=problem.sense, name=problem.name, metadata={"source": "OptimizationProblem"})
        for variable in problem.variables.values():
            if variable.kind not in ("binary", "integer"):
                raise ValueError(f"unsupported source variable kind {variable.kind!r}")
            if variable.kind == "integer" and (variable.lower, variable.upper) != (0, 1):
                raise ValueError("only pure binary/integer 0-1 problems can be converted")
            hybrid.add_binary_var(variable.name, metadata={"source_kind": variable.kind})
        hybrid.set_objective(
            linear=problem.objective_linear,
            quadratic=problem.objective_quadratic,
            offset=problem.objective_offset,
        )
        if problem.high_order_terms:
            raise ValueError("high-order terms are not supported by the hybrid MVP")
        for constraint in problem.constraints:
            hybrid.add_constraint(
                constraint.linear,
                sense=constraint.sense,
                rhs=constraint.rhs,
                name=constraint.name,
                constraint_type=constraint.constraint_type,
                metadata={"hardness": constraint.hardness, "penalty_weight": constraint.penalty_weight},
            )
        return hybrid

    def add_binary_var(self, name: str, *, metadata: dict | None = None) -> str:
        self._ensure_new_variable(name)
        self.variables[name] = HybridVariableSpec(
            name=name,
            kind="binary",
            lower=0.0,
            upper=1.0,
            metadata=dict(metadata or {}),
        )
        return name

    def add_continuous_var(
        self,
        name: str,
        *,
        lower: float = 0.0,
        upper: float = 1.0,
        metadata: dict | None = None,
    ) -> str:
        if upper < lower:
            raise ValueError(f"continuous variable {name!r} has upper < lower")
        self._ensure_new_variable(name)
        self.variables[name] = HybridVariableSpec(
            name=name,
            kind="continuous",
            lower=float(lower),
            upper=float(upper),
            metadata=dict(metadata or {}),
        )
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
        self.objective_offset = float(offset)
        self._validate_variable_names(self.objective_linear)
        for left, right in self.objective_quadratic:
            self._validate_variable_names((left, right))

    def add_constraint(
        self,
        linear: dict[str, float],
        *,
        sense: ConstraintSense,
        rhs: float,
        name: str,
        constraint_type: str = "linear",
        metadata: dict | None = None,
    ) -> HybridConstraintSpec:
        if sense not in ("==", "<=", ">="):
            raise ValueError(f"unsupported constraint sense: {sense}")
        self._validate_variable_names(linear)
        spec = HybridConstraintSpec(
            name=name,
            linear=dict(linear),
            sense=sense,
            rhs=float(rhs),
            constraint_type=constraint_type,
            metadata=dict(metadata or {}),
        )
        self.constraints.append(spec)
        return spec

    def variable_bounds(self, name: str) -> tuple[float, float]:
        variable = self.variables[name]
        return variable.lower, variable.upper

    def evaluate_objective(self, assignment: dict[str, float]) -> float:
        value = self.objective_offset
        for name, coefficient in self.objective_linear.items():
            value += coefficient * assignment[name]
        for (left, right), coefficient in self.objective_quadratic.items():
            value += coefficient * assignment[left] * assignment[right]
        return round(value, 12)

    def check_constraints(self, assignment: dict[str, float], *, tolerance: float = 1e-9) -> dict:
        results = []
        for constraint in self.constraints:
            lhs = sum(coefficient * assignment[name] for name, coefficient in constraint.linear.items())
            violation = constraint_violation(lhs, constraint.sense, constraint.rhs)
            results.append(
                {
                    "name": constraint.name,
                    "lhs": round(lhs, 12),
                    "sense": constraint.sense,
                    "rhs": constraint.rhs,
                    "violation": round(violation, 12),
                    "is_satisfied": violation <= tolerance,
                }
            )
        return {
            "is_feasible": all(result["is_satisfied"] for result in results),
            "total_violation": round(sum(result["violation"] for result in results), 12),
            "violated_constraints": [result["name"] for result in results if not result["is_satisfied"]],
            "constraint_results": results,
        }

    def _ensure_new_variable(self, name: str) -> None:
        if name in self.variables:
            raise ValueError(f"variable {name!r} already exists")

    def _validate_variable_names(self, coefficients: dict[str, float] | Iterable[str]) -> None:
        names = coefficients.keys() if isinstance(coefficients, dict) else coefficients
        missing = [name for name in names if name not in self.variables]
        if missing:
            raise KeyError(f"unknown variable(s): {', '.join(missing)}")


def constraint_violation(lhs: float, sense: str, rhs: float) -> float:
    if sense == "==":
        return abs(lhs - rhs)
    if sense == "<=":
        return max(0.0, lhs - rhs)
    if sense == ">=":
        return max(0.0, rhs - lhs)
    raise ValueError(f"unsupported constraint sense {sense!r}")
