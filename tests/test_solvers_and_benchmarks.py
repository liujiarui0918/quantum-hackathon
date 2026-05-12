from quantum_hackathon import (
    AnnealingBenchmarkRunner,
    ExactSolverBackend,
    OptimizationProblem,
    QuboBuilder,
    RandomSamplerBackend,
    SamplerConfig,
    SimulatedAnnealingBackend,
)
from quantum_hackathon.benchmarks.cases import exactly_one_selection, small_knapsack


def test_exact_solver_finds_best_feasible_solution():
    model = QuboBuilder().build(exactly_one_selection())

    result = ExactSolverBackend().solve(model, SamplerConfig())

    assert result.best_feasible().logical_solution == {"x0": 1, "x1": 0, "x2": 0}
    assert result.best_feasible().objective_value == -3.0
    assert result.feasible_ratio > 0.0


def test_random_sampler_is_seed_reproducible():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_binary_var("y")
    problem.set_objective(linear={"x": 1.0, "y": -1.0})
    model = QuboBuilder().build(problem)
    config = SamplerConfig(seed=123, num_reads=8)

    first = RandomSamplerBackend().sample(model, config)
    second = RandomSamplerBackend().sample(model, config)

    assert [sample.bitstring for sample in first.samples] == [
        sample.bitstring for sample in second.samples
    ]


def test_simulated_annealing_returns_a_feasible_knapsack_candidate():
    model = QuboBuilder().build(small_knapsack())

    result = SimulatedAnnealingBackend().solve(
        model,
        SamplerConfig(seed=7, num_reads=40, num_sweeps=200),
    )

    assert result.best_feasible() is not None
    assert result.best_feasible().is_feasible is True


def test_benchmark_runner_reports_core_metrics_for_each_backend():
    runner = AnnealingBenchmarkRunner(
        backends=[ExactSolverBackend(), RandomSamplerBackend()],
        config=SamplerConfig(seed=11, num_reads=20),
    )

    report = runner.run([exactly_one_selection(), small_knapsack()])

    assert len(report.rows) == 4
    assert {
        "problem_name",
        "solver",
        "best_feasible_objective",
        "best_raw_energy",
        "feasible_sample_ratio",
        "total_ms",
        "seed",
    }.issubset(report.rows[0])
