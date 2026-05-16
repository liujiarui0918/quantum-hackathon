from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

from quantum_hackathon.hybrid import HybridOptimizationProblem
from quantum_hackathon.modeling.problem import OptimizationProblem


ProblemSize = Literal["small", "medium", "hybrid"]


@dataclass(frozen=True)
class SyntheticProblemSpec:
    family: str
    size: ProblemSize
    problem: OptimizationProblem | HybridOptimizationProblem
    route_tags: tuple[str, ...]
    metadata: dict = field(default_factory=dict)


class SyntheticProblemGenerator:
    ordinary_families = (
        "one_hot_selection",
        "knapsack",
        "portfolio",
        "unit_commitment",
        "scheduling_assignment",
        "graph_cut",
    )

    def __init__(self, *, seed: int = 7):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_suite(
        self,
        *,
        small_per_family: int = 2,
        medium_per_family: int = 2,
        hybrid_count: int = 2,
    ) -> tuple[SyntheticProblemSpec, ...]:
        specs: list[SyntheticProblemSpec] = []
        for family in self.ordinary_families:
            for index in range(small_per_family):
                specs.append(self._ordinary(family, "small", index))
            for index in range(medium_per_family):
                specs.append(self._ordinary(family, "medium", index))
        for index in range(hybrid_count):
            specs.append(self.hybrid_dispatch(index=index))
        return tuple(specs)

    def _ordinary(self, family: str, size: ProblemSize, index: int) -> SyntheticProblemSpec:
        if family == "one_hot_selection":
            return self.one_hot_selection(size=size, index=index)
        if family == "knapsack":
            return self.knapsack(size=size, index=index)
        if family == "portfolio":
            return self.portfolio(size=size, index=index)
        if family == "unit_commitment":
            return self.unit_commitment(size=size, index=index)
        if family == "scheduling_assignment":
            return self.scheduling_assignment(size=size, index=index)
        if family == "graph_cut":
            return self.graph_cut(size=size, index=index)
        raise ValueError(f"unsupported synthetic family {family!r}")

    def one_hot_selection(self, *, size: ProblemSize, index: int = 0) -> SyntheticProblemSpec:
        groups = 2 if size == "small" else 4
        choices = 3 if size == "small" else 4
        problem = OptimizationProblem(sense="minimize", name=f"synthetic_one_hot_{size}_{index}")
        variables_by_group: list[list[str]] = []
        linear: dict[str, float] = {}
        quadratic: dict[tuple[str, str], float] = {}
        for group in range(groups):
            group_vars = []
            for choice in range(choices):
                name = problem.add_binary_var(f"sel_{group}_{choice}")
                group_vars.append(name)
                profit = self.rng.randint(3, 14) + group
                linear[name] = -float(profit)
            variables_by_group.append(group_vars)
            problem.add_constraint(
                {name: 1.0 for name in group_vars},
                sense="==",
                rhs=1.0,
                name=f"choose_group_{group}",
                constraint_type="exactly_one",
                penalty_weight=25.0,
            )
        for group in range(groups - 1):
            for left_choice, left in enumerate(variables_by_group[group]):
                for right_choice, right in enumerate(variables_by_group[group + 1]):
                    if (left_choice + right_choice + index) % 3 == 0:
                        quadratic[tuple(sorted((left, right)))] = float(self.rng.randint(1, 6))
        problem.set_objective(linear=linear, quadratic=quadratic)
        return SyntheticProblemSpec(
            family="one_hot_selection",
            size=size,
            problem=problem,
            route_tags=("qubo", "constraints", "constrained_qaoa", "learning_guided"),
            metadata={"groups": groups, "choices": choices},
        )

    def knapsack(self, *, size: ProblemSize, index: int = 0) -> SyntheticProblemSpec:
        item_count = 6 if size == "small" else 16
        problem = OptimizationProblem(sense="minimize", name=f"synthetic_knapsack_{size}_{index}")
        linear: dict[str, float] = {}
        capacity_terms: dict[str, float] = {}
        total_weight = 0
        for item in range(item_count):
            name = problem.add_binary_var(f"item_{item}")
            weight = self.rng.randint(1, 9)
            profit = weight + self.rng.randint(2, 12)
            total_weight += weight
            capacity_terms[name] = float(weight)
            linear[name] = -float(profit)
        capacity = max(1, int(total_weight * (0.42 if size == "small" else 0.38)))
        problem.set_objective(linear=linear)
        problem.add_constraint(
            capacity_terms,
            sense="<=",
            rhs=float(capacity),
            name="capacity",
            constraint_type="bounded_sum",
            penalty_weight=35.0,
        )
        return SyntheticProblemSpec(
            family="knapsack",
            size=size,
            problem=problem,
            route_tags=("qubo", "annealing", "learning_guided"),
            metadata={"item_count": item_count, "capacity": capacity},
        )

    def portfolio(self, *, size: ProblemSize, index: int = 0) -> SyntheticProblemSpec:
        asset_count = 6 if size == "small" else 14
        target_count = 2 if size == "small" else 4
        problem = OptimizationProblem(sense="minimize", name=f"synthetic_portfolio_{size}_{index}")
        variables = [problem.add_binary_var(f"asset_{asset}") for asset in range(asset_count)]
        linear = {}
        for asset, name in enumerate(variables):
            expected_return = self.rng.randint(4, 16)
            standalone_risk = self.rng.randint(1, 5)
            linear[name] = float(standalone_risk) - float(expected_return)
        quadratic: dict[tuple[str, str], float] = {}
        for left in range(asset_count):
            for right in range(left + 1, asset_count):
                if self.rng.random() < (0.25 if size == "small" else 0.18):
                    quadratic[(variables[left], variables[right])] = float(self.rng.randint(1, 7))
        problem.set_objective(linear=linear, quadratic=quadratic)
        problem.add_constraint(
            {name: 1.0 for name in variables},
            sense="==",
            rhs=float(target_count),
            name="cardinality",
            constraint_type="cardinality",
            penalty_weight=30.0,
        )
        return SyntheticProblemSpec(
            family="portfolio",
            size=size,
            problem=problem,
            route_tags=("qubo", "annealing", "hybrid_ready", "learning_guided"),
            metadata={"asset_count": asset_count, "target_count": target_count},
        )

    def unit_commitment(self, *, size: ProblemSize, index: int = 0) -> SyntheticProblemSpec:
        units = 3 if size == "small" else 5
        periods = 2 if size == "small" else 4
        problem = OptimizationProblem(sense="minimize", name=f"synthetic_unit_commitment_{size}_{index}")
        capacities = [self.rng.randint(4, 12) for _unit in range(units)]
        costs = [self.rng.randint(2, 9) for _unit in range(units)]
        linear: dict[str, float] = {}
        quadratic: dict[tuple[str, str], float] = {}
        for period in range(periods):
            demand = max(1, int(sum(capacities) * self.rng.uniform(0.38, 0.62)))
            demand_terms = {}
            for unit in range(units):
                name = problem.add_binary_var(f"on_{unit}_{period}")
                linear[name] = float(costs[unit])
                demand_terms[name] = float(capacities[unit])
                if period > 0:
                    previous = f"on_{unit}_{period - 1}"
                    quadratic[tuple(sorted((previous, name)))] = -float(self.rng.randint(1, 3))
            problem.add_constraint(
                demand_terms,
                sense=">=",
                rhs=float(demand),
                name=f"demand_period_{period}",
                constraint_type="demand",
                penalty_weight=45.0,
            )
        problem.set_objective(linear=linear, quadratic=quadratic)
        return SyntheticProblemSpec(
            family="unit_commitment",
            size=size,
            problem=problem,
            route_tags=("qubo", "constraints", "annealing", "power", "learning_guided"),
            metadata={"units": units, "periods": periods},
        )

    def scheduling_assignment(self, *, size: ProblemSize, index: int = 0) -> SyntheticProblemSpec:
        jobs = 4 if size == "small" else 7
        slots = 3 if size == "small" else 5
        capacity = 2
        problem = OptimizationProblem(sense="minimize", name=f"synthetic_scheduling_{size}_{index}")
        linear: dict[str, float] = {}
        variables_by_job: list[list[str]] = []
        variables_by_slot: list[list[str]] = [[] for _slot in range(slots)]
        for job in range(jobs):
            job_vars = []
            preferred_slot = self.rng.randrange(slots)
            for slot in range(slots):
                name = problem.add_binary_var(f"job_{job}_slot_{slot}")
                job_vars.append(name)
                variables_by_slot[slot].append(name)
                linear[name] = float(abs(slot - preferred_slot) + self.rng.randint(0, 3))
            variables_by_job.append(job_vars)
            problem.add_constraint(
                {name: 1.0 for name in job_vars},
                sense="==",
                rhs=1.0,
                name=f"assign_job_{job}",
                constraint_type="exactly_one",
                penalty_weight=25.0,
            )
        for slot, slot_vars in enumerate(variables_by_slot):
            problem.add_constraint(
                {name: 1.0 for name in slot_vars},
                sense="<=",
                rhs=float(capacity),
                name=f"slot_capacity_{slot}",
                constraint_type="bounded_sum",
                penalty_weight=35.0,
            )
        quadratic: dict[tuple[str, str], float] = {}
        for job in range(jobs - 1):
            for slot in range(slots):
                if self.rng.random() < 0.45:
                    quadratic[(variables_by_job[job][slot], variables_by_job[job + 1][slot])] = float(
                        self.rng.randint(1, 5)
                    )
        problem.set_objective(linear=linear, quadratic=quadratic)
        return SyntheticProblemSpec(
            family="scheduling_assignment",
            size=size,
            problem=problem,
            route_tags=("qubo", "constraints", "scheduling", "learning_guided"),
            metadata={"jobs": jobs, "slots": slots, "capacity": capacity},
        )

    def graph_cut(self, *, size: ProblemSize, index: int = 0) -> SyntheticProblemSpec:
        node_count = 7 if size == "small" else 18
        problem = OptimizationProblem(sense="minimize", name=f"synthetic_graph_cut_{size}_{index}")
        names = [problem.add_binary_var(f"node_{node}") for node in range(node_count)]
        linear = {name: 0.0 for name in names}
        quadratic: dict[tuple[str, str], float] = {}
        edge_probability = 0.38 if size == "small" else 0.18
        for left in range(node_count):
            for right in range(left + 1, node_count):
                if self.rng.random() >= edge_probability:
                    continue
                weight = float(self.rng.randint(1, 8))
                linear[names[left]] -= weight
                linear[names[right]] -= weight
                quadratic[(names[left], names[right])] = quadratic.get((names[left], names[right]), 0.0) + 2.0 * weight
        problem.set_objective(linear=linear, quadratic=quadratic)
        return SyntheticProblemSpec(
            family="graph_cut",
            size=size,
            problem=problem,
            route_tags=("qubo", "annealing", "learning_guided"),
            metadata={"node_count": node_count},
        )

    def hybrid_dispatch(self, *, index: int = 0) -> SyntheticProblemSpec:
        units = 4 + (index % 2)
        problem = HybridOptimizationProblem(sense="minimize", name=f"synthetic_hybrid_dispatch_{index}")
        capacities = [float(self.rng.randint(5, 16)) for _unit in range(units)]
        demand = float(max(1, int(sum(capacities) * self.rng.uniform(0.45, 0.65))))
        linear: dict[str, float] = {}
        for unit, capacity in enumerate(capacities):
            open_var = problem.add_binary_var(f"open_{unit}")
            flow_var = problem.add_continuous_var(f"flow_{unit}", lower=0.0, upper=capacity)
            linear[open_var] = float(self.rng.randint(1, 8))
            linear[flow_var] = -float(self.rng.randint(3, 9))
            problem.add_constraint(
                {flow_var: 1.0, open_var: -capacity},
                sense="<=",
                rhs=0.0,
                name=f"link_{unit}",
                constraint_type="linking",
            )
        problem.set_objective(linear=linear)
        problem.add_constraint(
            {f"flow_{unit}": 1.0 for unit in range(units)},
            sense=">=",
            rhs=demand,
            name="demand",
            constraint_type="demand",
        )
        problem.add_constraint(
            {f"open_{unit}": 1.0 for unit in range(units)},
            sense=">=",
            rhs=1.0,
            name="minimum_open",
            constraint_type="binary_cardinality",
        )
        return SyntheticProblemSpec(
            family="hybrid_dispatch",
            size="hybrid",
            problem=problem,
            route_tags=("hybrid", "power", "learning_guided"),
            metadata={"units": units, "demand": demand},
        )
