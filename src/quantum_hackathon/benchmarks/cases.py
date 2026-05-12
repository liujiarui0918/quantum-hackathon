from __future__ import annotations

from quantum_hackathon.modeling.problem import OptimizationProblem


def exactly_one_selection() -> OptimizationProblem:
    problem = OptimizationProblem(sense="minimize", name="exactly_one_selection")
    problem.add_binary_var("x0")
    problem.add_binary_var("x1")
    problem.add_binary_var("x2")
    problem.set_objective(linear={"x0": -3.0, "x1": -1.0, "x2": -2.0})
    problem.add_constraint(
        linear={"x0": 1.0, "x1": 1.0, "x2": 1.0},
        sense="==",
        rhs=1.0,
        name="choose_one",
        constraint_type="exactly_one",
        penalty_weight=10.0,
    )
    return problem


def small_knapsack() -> OptimizationProblem:
    problem = OptimizationProblem(sense="minimize", name="small_knapsack")
    for index in range(4):
        problem.add_binary_var(f"x{index}")
    profits = [8.0, 6.0, 5.0, 4.0]
    weights = [4.0, 3.0, 2.0, 2.0]
    problem.set_objective(linear={f"x{index}": -profit for index, profit in enumerate(profits)})
    problem.add_constraint(
        linear={f"x{index}": weight for index, weight in enumerate(weights)},
        sense="<=",
        rhs=5.0,
        name="capacity",
        constraint_type="bounded_sum",
        penalty_weight=20.0,
    )
    return problem
