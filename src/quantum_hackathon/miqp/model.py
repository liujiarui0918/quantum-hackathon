from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class MiqpConstraintReport:
    mixed_lhs: np.ndarray
    binary_lhs: np.ndarray
    mixed_violation: np.ndarray
    binary_violation: np.ndarray

    @property
    def is_feasible(self) -> bool:
        return bool(np.max(self.mixed_violation, initial=0.0) <= 1e-8 and np.max(self.binary_violation, initial=0.0) <= 1e-8)

    @property
    def total_violation(self) -> float:
        return float(np.sum(np.maximum(self.mixed_violation, 0.0)) + np.sum(np.maximum(self.binary_violation, 0.0)))

    def as_record(self) -> dict[str, Any]:
        return {
            "is_feasible": self.is_feasible,
            "total_violation": self.total_violation,
            "mixed_max_violation": float(np.max(self.mixed_violation, initial=0.0)),
            "binary_max_violation": float(np.max(self.binary_violation, initial=0.0)),
            "mixed_lhs": self.mixed_lhs.tolist(),
            "binary_lhs": self.binary_lhs.tolist(),
        }


@dataclass(frozen=True)
class MiqpInstance:
    name: str
    n: int
    p: int
    m1: int
    m2: int
    Q: np.ndarray
    c: np.ndarray
    h: np.ndarray
    A: np.ndarray
    G: np.ndarray
    b: np.ndarray
    B: np.ndarray
    b_prime: np.ndarray
    optimal_value: float | None = None
    x_opt: np.ndarray | None = None
    y_opt: np.ndarray | None = None
    source_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        expected = {
            "Q": (self.n, self.n),
            "c": (self.n,),
            "h": (self.p,),
            "A": (self.m1, self.n),
            "G": (self.m1, self.p),
            "b": (self.m1,),
            "B": (self.m2, self.n),
            "b_prime": (self.m2,),
        }
        for name, shape in expected.items():
            value = getattr(self, name)
            if value.shape != shape:
                raise ValueError(f"{name} has shape {value.shape}, expected {shape}")
        if self.x_opt is not None and self.x_opt.shape != (self.n,):
            raise ValueError("x_opt shape does not match n")
        if self.y_opt is not None and self.y_opt.shape != (self.p,):
            raise ValueError("y_opt shape does not match p")

    def objective(self, x: np.ndarray, y: np.ndarray) -> float:
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        return float(x_arr @ self.Q @ x_arr + self.c @ x_arr + self.h @ y_arr)

    def binary_objective(self, x: np.ndarray) -> float:
        x_arr = np.asarray(x, dtype=float)
        return float(x_arr @ self.Q @ x_arr + self.c @ x_arr)

    def continuous_rhs(self, x: np.ndarray) -> np.ndarray:
        return self.b - self.A @ np.asarray(x, dtype=float)

    def constraint_report(self, x: np.ndarray, y: np.ndarray) -> MiqpConstraintReport:
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        mixed_lhs = self.A @ x_arr + self.G @ y_arr
        binary_lhs = self.B @ x_arr
        return MiqpConstraintReport(
            mixed_lhs=mixed_lhs,
            binary_lhs=binary_lhs,
            mixed_violation=mixed_lhs - self.b,
            binary_violation=binary_lhs - self.b_prime,
        )

    def is_feasible(self, x: np.ndarray, y: np.ndarray) -> bool:
        return self.constraint_report(x, y).is_feasible and bool(
            np.all(np.asarray(x) >= -1e-8)
            and np.all(np.asarray(x) <= 1.0 + 1e-8)
            and np.all(np.asarray(y) >= -1e-8)
        )

    def diagnostics(self) -> dict[str, Any]:
        upper = np.triu(np.abs(self.Q) > 1e-12, 1)
        density = float(np.sum(upper) / max(1, self.n * (self.n - 1) / 2))
        return {
            "name": self.name,
            "n": self.n,
            "p": self.p,
            "m1": self.m1,
            "m2": self.m2,
            "q_density": density,
            "q_abs_max": float(np.max(np.abs(self.Q), initial=0.0)),
            "a_abs_max": float(np.max(np.abs(self.A), initial=0.0)),
            "g_abs_max": float(np.max(np.abs(self.G), initial=0.0)),
            "b_min": float(np.min(self.b, initial=0.0)),
            "b_prime_min": float(np.min(self.b_prime, initial=0.0)),
            "has_reference_solution": self.x_opt is not None and self.y_opt is not None,
            "source_path": str(self.source_path) if self.source_path is not None else None,
        }

    def reference_solution_record(self) -> dict[str, Any] | None:
        if self.x_opt is None or self.y_opt is None:
            return None
        report = self.constraint_report(self.x_opt, self.y_opt)
        return {
            "objective": self.objective(self.x_opt, self.y_opt),
            "optimal_value": self.optimal_value,
            "feasible": report.is_feasible,
            "x_ones": int(np.sum(self.x_opt)),
            "y_nonzero": int(np.sum(self.y_opt > 1e-9)),
            "constraint_report": report.as_record(),
        }


@dataclass(frozen=True)
class MiqpSolution:
    x: np.ndarray
    y: np.ndarray
    objective: float
    feasible: bool
    status: str
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "objective": float(self.objective),
            "feasible": self.feasible,
            "x": [int(round(value)) for value in self.x.tolist()],
            "y": [float(value) for value in self.y.tolist()],
            "diagnostics": self.diagnostics,
        }
