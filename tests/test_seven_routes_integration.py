from quantum_hackathon import (
    AnnealingBenchmarkRunner,
    ConstrainedQaoaRunner,
    ConstraintCompiler,
    ExactSolverBackend,
    FeasibleSubspaceSpec,
    HybridOptimizationProblem,
    HybridOptimizer,
    LearningGuidedSamplerBackend,
    OneHotXYMixerStrategy,
    ProblemDecomposer,
    QaoaConfig,
    QaoaRunner,
    QuboBuilder,
    SamplerConfig,
    SimulatedAnnealingBackend,
)
from quantum_hackathon.benchmarks.cases import exactly_one_selection


def test_all_seven_requirement_routes_have_a_runnable_integration_path():
    problem = exactly_one_selection()

    # Route 1: QUBO / Ising modeling.
    qubo_model = QuboBuilder().build(problem)
    assert qubo_model.to_ising().energy_from_bits((1, 0, 0)) == qubo_model.energy((1, 0, 0))

    # Route 2: constraint compiler and feasible subspace metadata.
    compiled = ConstraintCompiler().compile(problem)
    exported_subspace = compiled.export_feasible_subspace()
    assert exported_subspace.one_hot_groups == (("x0", "x1", "x2"),)

    # Route 3: annealing-style solver and benchmark.
    annealing_result = SimulatedAnnealingBackend().solve(
        qubo_model,
        SamplerConfig(seed=3, num_reads=20, num_sweeps=50),
    )
    report = AnnealingBenchmarkRunner(
        backends=[ExactSolverBackend(), SimulatedAnnealingBackend()],
        config=SamplerConfig(seed=3, num_reads=20, num_sweeps=50),
    ).run([problem])
    assert annealing_result.best_feasible() is not None
    assert len(report.rows) == 2

    # Route 7: learning-guided warm-start and variable fixing scaffold.
    learning_result = LearningGuidedSamplerBackend().solve(
        qubo_model,
        SamplerConfig(seed=3, num_reads=8, num_sweeps=10),
    )
    assert learning_result.best_feasible() is not None
    assert learning_result.diagnostics["ml_role"] == "warm_start_variable_ranking"

    # Route 4: standard QAOA / VQA local simulator.
    qaoa_result = QaoaRunner().solve(
        qubo_model,
        QaoaConfig(p=1, shots=60, seed=3, grid_size=3, random_trials=3),
    )
    assert qaoa_result.best_samples.best_feasible() is not None

    # Route 5: constrained mixer / feasible subspace route.
    constrained_subspace = FeasibleSubspaceSpec(one_hot_groups=((0, 1, 2),))
    mixer = OneHotXYMixerStrategy(topology="complete").build(constrained_subspace)
    constrained_result = ConstrainedQaoaRunner().solve(problem, subspace=constrained_subspace)
    assert mixer.preserves_feasibility is True
    assert constrained_result.best_feasible_sample is not None

    # Route 6: hybrid MILP / MIQP scaffold.
    hybrid_problem = HybridOptimizationProblem(sense="minimize", name="integration_hybrid")
    hybrid_problem.add_binary_var("open")
    hybrid_problem.add_continuous_var("flow", lower=0.0, upper=5.0)
    hybrid_problem.set_objective(linear={"open": 1.0, "flow": -2.0})
    hybrid_problem.add_constraint({"flow": 1.0, "open": -5.0}, sense="<=", rhs=0.0, name="link")
    decomposition = ProblemDecomposer().analyze(hybrid_problem)
    hybrid_result = HybridOptimizer().solve(hybrid_problem)
    assert decomposition.recommended_strategy == "relax_round_repair"
    assert hybrid_result.status == "feasible"
