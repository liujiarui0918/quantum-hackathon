from quantum_hackathon import OptimizationProblem, QuboBuilder
from quantum_hackathon.constraints import (
    AtMostOneRepair,
    CardinalityRepair,
    ConstraintCompiler,
    ConstraintCompilerConfig,
    PenaltySweep,
    UnbalancedPenaltyConfig,
)
from quantum_hackathon.solvers import ExactSolverBackend, SamplerConfig


def test_constraint_compiler_exports_plans_and_feasible_subspace_metadata():
    problem = OptimizationProblem(sense="minimize")
    for name in ("x0", "x1", "x2"):
        problem.add_binary_var(name)
    problem.add_constraint(
        linear={"x0": 1.0, "x1": 1.0, "x2": 1.0},
        sense="==",
        rhs=1.0,
        name="choose_one",
        constraint_type="exactly_one",
        penalty_weight=10.0,
    )

    compiled = ConstraintCompiler().compile(problem)
    subspace = compiled.export_feasible_subspace()

    assert compiled.plans[0].strategy == "square_penalty"
    assert compiled.plans[0].guarantee == "exact_ground_state"
    assert subspace.one_hot_groups == (("x0", "x1", "x2"),)
    assert subspace.constraints_covered == ("choose_one",)


def test_constraint_compiler_supports_unbalanced_inequality_strategy():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_binary_var("y")
    problem.set_objective(linear={"x": -4.0, "y": -3.0})
    problem.add_constraint(
        linear={"x": 2.0, "y": 2.0},
        sense="<=",
        rhs=2.0,
        name="capacity",
        constraint_type="bounded_sum",
    )

    compiled = ConstraintCompiler(
        ConstraintCompilerConfig(
            strategy_overrides={"capacity": UnbalancedPenaltyConfig(lambda1=0.5, lambda2=2.0)}
        )
    ).compile(problem)
    model = QuboBuilder().build(compiled.to_problem())

    assert compiled.plans[0].strategy == "unbalanced"
    assert compiled.plans[0].ground_state_not_guaranteed is True
    assert model.diagnostics()["slack_variables"] == 0


def test_repairs_cardinality_and_at_most_one_assignments():
    assignment = {"x0": 1, "x1": 1, "x2": 0}
    objective = {"x0": -3.0, "x1": -1.0, "x2": -2.0}

    repaired_one = AtMostOneRepair(("x0", "x1", "x2")).repair(assignment, objective)
    repaired_k = CardinalityRepair(("x0", "x1", "x2"), k=2).repair(
        {"x0": 0, "x1": 0, "x2": 1},
        objective,
    )

    assert repaired_one.assignment == {"x0": 1, "x1": 0, "x2": 0}
    assert repaired_one.changed_variables == ("x1",)
    assert sum(repaired_k.assignment.values()) == 2
    assert repaired_k.assignment["x0"] == 1


def test_penalty_sweep_reports_feasible_ratio_and_recommended_weight():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_binary_var("y")
    problem.set_objective(linear={"x": -5.0, "y": -4.0})
    problem.add_constraint(
        linear={"x": 1.0, "y": 1.0},
        sense="<=",
        rhs=1.0,
        name="at_most_one",
        penalty_weight=1.0,
    )

    report = PenaltySweep(
        solver=ExactSolverBackend(),
        config=SamplerConfig(),
    ).run(problem, "at_most_one", weights=[1.0, 20.0])

    assert len(report.rows) == 2
    assert report.recommended_weight == 20.0
    assert report.rows[1]["best_feasible_objective"] == -5.0
