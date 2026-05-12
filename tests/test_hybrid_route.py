from quantum_hackathon.hybrid import (
    HybridOptimizationProblem,
    HybridOptimizer,
    ProblemDecomposer,
    RoundingStrategy,
)


def _toy_problem() -> HybridOptimizationProblem:
    problem = HybridOptimizationProblem(sense="minimize", name="toy")
    problem.add_binary_var("open")
    problem.add_continuous_var("flow", lower=0.0, upper=10.0)
    problem.set_objective(linear={"open": 1.0, "flow": -2.0})
    problem.add_constraint(
        {"flow": 1.0, "open": -5.0},
        sense="<=",
        rhs=0.0,
        name="capacity_link",
    )
    problem.add_constraint(
        {"flow": 1.0},
        sense="<=",
        rhs=4.0,
        name="allocation_limit",
    )
    return problem


def test_decomposition_classifies_binary_continuous_and_linking_terms():
    problem = _toy_problem()
    problem.add_binary_var("select")
    problem.add_continuous_var("cost", lower=0.0, upper=3.0)
    problem.set_objective(
        linear={"open": 1.0, "flow": -2.0},
        quadratic={
            ("open", "select"): -1.0,
            ("flow", "cost"): 0.5,
            ("open", "flow"): 2.0,
        },
    )
    problem.add_constraint(
        {"open": 1.0, "select": 1.0},
        sense="<=",
        rhs=1.0,
        name="binary_only",
    )

    analysis = ProblemDecomposer().analyze(problem)

    assert analysis.binary_block_vars == ("open", "select")
    assert analysis.continuous_block_vars == ("flow", "cost")
    assert [constraint.name for constraint in analysis.linking_constraints] == ["capacity_link"]
    assert analysis.pure_binary_terms == (("open", "select", -1.0),)
    assert analysis.pure_continuous_terms == (("cost", "flow", 0.5),)
    assert analysis.cross_terms == (("flow", "open", 2.0),)
    assert analysis.recommended_strategy == "relax_round_repair"


def test_threshold_and_top_k_rounding_are_deterministic():
    values = {"a": 0.2, "b": 0.5, "c": 0.8}

    assert RoundingStrategy(method="threshold", threshold=0.5).round(values) == {
        "a": 0,
        "b": 1,
        "c": 1,
    }
    assert RoundingStrategy(method="top_k", top_k=2).round(values) == {
        "a": 0,
        "b": 1,
        "c": 1,
    }


def test_relax_round_repair_returns_feasible_candidate_for_toy_problem():
    result = HybridOptimizer(strategy="relax_round_repair").solve(_toy_problem())

    assert result.status == "feasible"
    assert result.best_feasible_solution == {"open": 1, "flow": 4.0}
    assert result.objective == -7.0
    assert result.diagnostics["is_feasible"] is True
    assert result.warm_start_metadata["continuous_relaxation_values"] == {
        "open": 1.0,
        "flow": 10.0,
    }
    assert result.warm_start_metadata["rounded_assignment"] == {"open": 1}


def test_relax_round_repair_reports_infeasible_with_diagnostics():
    problem = HybridOptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_continuous_var("y", lower=0.0, upper=1.0)
    problem.set_objective(linear={"x": 1.0, "y": 1.0})
    problem.add_constraint({"y": 1.0}, sense=">=", rhs=2.0, name="impossible")

    result = HybridOptimizer(strategy="relax_round_repair").solve(problem)

    assert result.status == "infeasible"
    assert result.best_feasible_solution is None
    assert result.objective is None
    assert result.diagnostics["is_feasible"] is False
    assert result.diagnostics["violated_constraints"] == ["impossible"]
    assert "continuous_relaxation_values" in result.warm_start_metadata
    assert "rounded_assignment" in result.warm_start_metadata
