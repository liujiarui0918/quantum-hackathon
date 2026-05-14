import pytest

from quantum_hackathon.benchmarks.cases import exactly_one_selection
from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder
from quantum_hackathon.solvers.qaoa import (
    CostHamiltonianBuilder,
    QiskitAerQaoaBackend,
    QaoaConfig,
    QaoaRunner,
    ShotSimulatorBackend,
    StatevectorQaoaBackend,
)


def _toy_qubo_model():
    problem = OptimizationProblem(sense="minimize")
    problem.add_binary_var("x")
    problem.add_binary_var("y")
    problem.set_objective(linear={"x": 1.5, "y": -2.0}, quadratic={("x", "y"): 3.0})
    return QuboBuilder().build(problem)


def test_cost_hamiltonian_classical_energy_matches_qubo_model():
    model = _toy_qubo_model()
    hamiltonian = CostHamiltonianBuilder.from_qubo(model)

    for bitstring in model.iter_bitstrings():
        assert hamiltonian.classical_energy(bitstring) == model.energy(bitstring)


def test_statevector_probabilities_are_normalized_and_shots_are_seeded():
    model = _toy_qubo_model()
    hamiltonian = CostHamiltonianBuilder.from_qubo(model)
    state_backend = StatevectorQaoaBackend()

    probabilities = state_backend.probabilities(hamiltonian, gammas=[0.2], betas=[0.4])

    assert sum(probabilities.values()) == pytest.approx(1.0)

    shot_backend = ShotSimulatorBackend(state_backend=state_backend)
    first = shot_backend.sample_counts(hamiltonian, gammas=[0.2], betas=[0.4], shots=25, seed=123)
    second = shot_backend.sample_counts(hamiltonian, gammas=[0.2], betas=[0.4], shots=25, seed=123)

    assert first == second
    assert sum(first.values()) == 25


def test_qaoa_runner_returns_postprocessed_feasible_result_for_exactly_one_selection():
    model = QuboBuilder().build(exactly_one_selection())

    result = QaoaRunner().solve(
        model,
        QaoaConfig(
            p=1,
            shots=80,
            seed=5,
            grid_size=5,
            random_trials=8,
        ),
    )

    assert result.optimizer_trace
    assert result.best_parameters
    assert result.best_samples.best_feasible() is not None
    assert result.best_samples.best_feasible().is_feasible is True


def test_qiskit_aer_backend_helper_is_safe_without_optional_dependency():
    backend = QiskitAerQaoaBackend()

    converted = backend._counts_to_bitstrings({"010": 2, "101": 1}, 3)

    assert converted == {
        (0, 1, 0): 2,
        (1, 0, 1): 1,
    }
    assert backend.is_available() in {True, False}
