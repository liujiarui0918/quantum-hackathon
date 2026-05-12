from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable


ObjectiveFunction = Callable[[list[float], list[float]], float]


@dataclass(frozen=True)
class OptimizerTraceEntry:
    gammas: tuple[float, ...]
    betas: tuple[float, ...]
    value: float


@dataclass(frozen=True)
class OptimizerResult:
    gammas: tuple[float, ...]
    betas: tuple[float, ...]
    value: float
    trace: list[OptimizerTraceEntry]


@dataclass(frozen=True)
class FixedInitializer:
    gamma: float = 0.1
    beta: float = 0.2

    def initial_parameters(self, p: int) -> tuple[list[float], list[float]]:
        return [self.gamma] * p, [self.beta] * p


@dataclass(frozen=True)
class RandomInitializer:
    seed: int | None = None

    def initial_parameters(self, p: int) -> tuple[list[float], list[float]]:
        rng = random.Random(self.seed)
        return (
            [rng.uniform(0.0, 2.0 * math.pi) for _ in range(p)],
            [rng.uniform(0.0, math.pi) for _ in range(p)],
        )


@dataclass
class SimpleQaoaOptimizer:
    grid_size: int = 7
    random_trials: int = 20
    seed: int | None = None

    def minimize(self, objective: ObjectiveFunction, p: int) -> OptimizerResult:
        if p != 1:
            return self._random_search(objective, p)

        trace: list[OptimizerTraceEntry] = []
        grid_points = max(2, self.grid_size)
        for gamma_index in range(grid_points):
            gamma = 2.0 * math.pi * gamma_index / grid_points
            for beta_index in range(grid_points):
                beta = math.pi * beta_index / grid_points
                self._evaluate(objective, [gamma], [beta], trace)

        rng = random.Random(self.seed)
        for _ in range(max(0, self.random_trials)):
            gamma = rng.uniform(0.0, 2.0 * math.pi)
            beta = rng.uniform(0.0, math.pi)
            self._evaluate(objective, [gamma], [beta], trace)

        return self._best(trace)

    def _random_search(self, objective: ObjectiveFunction, p: int) -> OptimizerResult:
        trace: list[OptimizerTraceEntry] = []
        rng = random.Random(self.seed)
        gammas, betas = FixedInitializer().initial_parameters(p)
        self._evaluate(objective, gammas, betas, trace)
        for _ in range(max(1, self.random_trials)):
            gammas = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(p)]
            betas = [rng.uniform(0.0, math.pi) for _ in range(p)]
            self._evaluate(objective, gammas, betas, trace)
        return self._best(trace)

    def _evaluate(
        self,
        objective: ObjectiveFunction,
        gammas: list[float],
        betas: list[float],
        trace: list[OptimizerTraceEntry],
    ) -> None:
        value = objective(gammas, betas)
        trace.append(
            OptimizerTraceEntry(
                gammas=tuple(gammas),
                betas=tuple(betas),
                value=value,
            )
        )

    @staticmethod
    def _best(trace: list[OptimizerTraceEntry]) -> OptimizerResult:
        best = min(trace, key=lambda entry: entry.value)
        return OptimizerResult(
            gammas=best.gammas,
            betas=best.betas,
            value=best.value,
            trace=trace,
        )
