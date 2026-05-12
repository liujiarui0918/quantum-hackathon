from quantum_hackathon import (
    OptimizationProblem,
    QuboBuilder,
    RawSampleSet,
    SolutionPostprocessor,
)


def test_feasibility_checker_reports_lhs_violation_and_satisfaction():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("a")
    problem.add_binary_var("b")
    problem.add_constraint(
        linear={"a": 1.0, "b": 1.0},
        sense="<=",
        rhs=1.0,
        name="at_most_one",
        constraint_type="at_most_one",
        penalty_weight=5.0,
    )

    model = QuboBuilder().build(problem)

    feasible = model.check_constraints({"a": 1, "b": 0})
    infeasible = model.check_constraints({"a": 1, "b": 1})

    assert feasible.is_feasible is True
    assert feasible.results[0].lhs == 1.0
    assert feasible.results[0].violation == 0.0
    assert infeasible.is_feasible is False
    assert infeasible.results[0].lhs == 2.0
    assert infeasible.results[0].violation == 1.0


def test_postprocessor_ranks_feasible_samples_before_lower_energy_infeasible_samples():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("a")
    problem.add_binary_var("b")
    problem.set_objective(linear={"a": -10.0, "b": -10.0})
    problem.add_constraint(
        linear={"a": 1.0, "b": 1.0},
        sense="<=",
        rhs=1.0,
        name="at_most_one",
        constraint_type="at_most_one",
        penalty_weight=1.0,
    )
    model = QuboBuilder().build(problem)

    raw = RawSampleSet.from_samples(
        [
            model.bitstring_from_logical({"a": 1, "b": 1}),
            model.bitstring_from_logical({"a": 1, "b": 0}),
            model.bitstring_from_logical({"a": 0, "b": 1}),
        ],
        source_backend="manual",
        energy_fn=model.energy,
    )

    ranked = SolutionPostprocessor().process(model, raw)

    assert ranked.samples[0].is_feasible is True
    assert ranked.samples[0].logical_solution in ({"a": 1, "b": 0}, {"a": 0, "b": 1})
    assert ranked.best_raw_energy_sample.logical_solution == {"a": 1, "b": 1}
    assert ranked.best_feasible().objective_value == -10.0
