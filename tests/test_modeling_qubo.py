from quantum_hackathon import (
    OptimizationProblem,
    QuboBuilder,
    QuboBuilderConfig,
    brute_force_solve,
)


def test_qubo_builder_matches_exactly_one_original_optimum():
    problem = OptimizationProblem(sense="minimize")
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

    model = QuboBuilder(QuboBuilderConfig(default_penalty=10.0)).build(problem)
    result = brute_force_solve(model)
    decoded = model.decode(result.best_sample.bitstring)

    assert decoded.logical_solution == {"x0": 1, "x1": 0, "x2": 0}
    assert decoded.objective_value == -3.0
    assert decoded.penalty_energy == 0.0
    assert decoded.is_feasible is True
    assert model.diagnostics()["logical_variables"] == 3
    assert model.diagnostics()["total_binary_variables"] == 3


def test_bounded_integer_slack_and_ising_energy_equivalence():
    problem = OptimizationProblem(sense="minimize")
    problem.add_integer_var("z", lower=0, upper=5)
    problem.add_binary_var("y")
    problem.set_objective(linear={"z": -2.0, "y": -1.0})
    problem.add_constraint(
        linear={"z": 1.0, "y": 3.0},
        sense="<=",
        rhs=4.0,
        name="capacity",
        constraint_type="bounded_sum",
        penalty_weight=20.0,
    )

    model = QuboBuilder().build(problem)
    result = brute_force_solve(model)
    decoded = model.decode(result.best_sample.bitstring)

    assert decoded.logical_solution == {"z": 4, "y": 0}
    assert decoded.objective_value == -8.0
    assert decoded.is_feasible is True
    assert model.diagnostics()["slack_variables"] > 0

    ising = model.to_ising()
    for sample in model.iter_bitstrings():
        assert ising.energy_from_bits(sample) == model.energy(sample)


def test_high_order_monomial_is_quadratized_with_hidden_auxiliary_variable():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_binary_var("y")
    problem.add_binary_var("z")
    problem.add_high_order_term(("x", "y", "z"), -5.0)

    model = QuboBuilder(QuboBuilderConfig(default_penalty=20.0)).build(problem)
    result = brute_force_solve(model)
    decoded = model.decode(result.best_sample.bitstring)

    assert decoded.logical_solution == {"x": 1, "y": 1, "z": 1}
    assert decoded.objective_value == -5.0
    assert "aux_and_x_y" not in decoded.logical_solution
    assert model.diagnostics()["auxiliary_variables"] == 1


def test_qubo_builder_can_be_reused_without_auxiliary_cache_leakage():
    builder = QuboBuilder(QuboBuilderConfig(default_penalty=20.0))

    first = OptimizationProblem(sense="minimize")
    for name in ("x", "y", "z"):
        first.add_binary_var(name)
    first.add_high_order_term(("x", "y", "z"), -5.0)
    first_model = builder.build(first)

    second = OptimizationProblem(sense="minimize")
    for name in ("a", "b", "c"):
        second.add_binary_var(name)
    second.add_high_order_term(("a", "b", "c"), -7.0)
    second_model = builder.build(second)

    assert first_model.diagnostics()["auxiliary_variables"] == 1
    assert second_model.diagnostics()["auxiliary_variables"] == 1
    assert brute_force_solve(second_model).best_sample.logical_solution == {
        "a": 1,
        "b": 1,
        "c": 1,
    }


def test_greater_than_equal_inequality_uses_nonnegative_slack():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_binary_var("y")
    problem.set_objective(linear={"x": 1.0, "y": 1.0})
    problem.add_constraint(
        linear={"x": 1.0, "y": 1.0},
        sense=">=",
        rhs=1.0,
        name="at_least_one",
        penalty_weight=10.0,
    )

    model = QuboBuilder().build(problem)
    decoded = brute_force_solve(model).best_sample

    assert decoded.is_feasible is True
    assert decoded.objective_value == 1.0
    assert decoded.logical_solution in ({"x": 1, "y": 0}, {"x": 0, "y": 1})


def test_maximize_problem_preserves_business_objective_and_penalty_energy():
    problem = OptimizationProblem(sense="maximize")
    problem.add_binary_var("x")
    problem.set_objective(linear={"x": 5.0})

    model = QuboBuilder().build(problem)
    decoded = brute_force_solve(model).best_sample

    assert decoded.logical_solution == {"x": 1}
    assert decoded.objective_value == 5.0
    assert decoded.penalty_energy == 0.0
