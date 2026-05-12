import pytest

from quantum_hackathon.benchmarks.cases import exactly_one_selection
from quantum_hackathon.solvers.constrained_qaoa import (
    ConstrainedQaoaRunner,
    FeasibleSubspaceSpec,
    InitialStateSpec,
    OneHotXYMixerStrategy,
    RecursiveQaoaReducer,
    WarmStartStateSpec,
)


def test_one_hot_subspace_validation_catches_overlapping_groups():
    with pytest.raises(ValueError, match="overlap"):
        FeasibleSubspaceSpec(one_hot_groups=((0, 1), (1, 2)))


def test_one_hot_subspace_validation_accepts_disjoint_groups():
    spec = FeasibleSubspaceSpec(one_hot_groups=((0, 1), (2, 3)))

    assert spec.num_qubits == 4
    assert spec.constraints_covered == ("one_hot_groups",)


def test_one_hot_initial_state_basis_states_have_one_bit_per_group():
    subspace = FeasibleSubspaceSpec(one_hot_groups=((0, 1, 2), (3, 4)))
    state = InitialStateSpec.from_subspace(subspace)

    assert len(state.basis_states) == 6
    for bits in state.basis_states:
        assert sum(bits[index] for index in (0, 1, 2)) == 1
        assert sum(bits[index] for index in (3, 4)) == 1


def test_warm_start_group_probabilities_clip_smooth_and_sum_to_one():
    subspace = FeasibleSubspaceSpec(one_hot_groups=((0, 1, 2),))
    state = WarmStartStateSpec.from_probabilities(
        subspace,
        probabilities={0: -0.4, 1: 0.0, 2: 1.8},
        smoothing=0.1,
    )

    group_probs = state.group_probabilities[(0, 1, 2)]
    assert all(probability > 0.0 for probability in group_probs.values())
    assert group_probs[2] > group_probs[1]
    assert group_probs[1] == group_probs[0]
    assert sum(group_probs.values()) == pytest.approx(1.0)


def test_one_hot_xy_mixer_metadata_preserves_feasibility_and_complete_connected():
    subspace = FeasibleSubspaceSpec(one_hot_groups=((0, 1, 2),))
    result = OneHotXYMixerStrategy(topology="complete").build(subspace)

    assert result.preserves_feasibility is True
    assert result.transition_graph_connected is True
    assert result.resource_estimate["xy_edges"] == 3
    assert result.warnings == []


def test_constrained_qaoa_runner_returns_diagnostics_and_best_feasible_sample():
    result = ConstrainedQaoaRunner().solve(
        exactly_one_selection(),
        subspace=FeasibleSubspaceSpec(one_hot_groups=((0, 1, 2),)),
    )

    assert result.best_feasible_sample is not None
    assert result.best_feasible_sample.logical_solution == {"x0": 1, "x1": 0, "x2": 0}
    assert result.diagnostics["subspace"]["constraints_covered"] == ("one_hot_groups",)
    assert result.diagnostics["backend"] == "exact"


def test_recursive_qaoa_reducer_reports_pairwise_elimination_metadata():
    result = RecursiveQaoaReducer().reduce_once(
        [
            (0, 0, 1),
            (0, 0, 0),
            (1, 1, 1),
            (1, 1, 0),
        ]
    )

    assert len(result.elimination_history) == 1
    step = result.elimination_history[0]
    assert (step.kept_variable, step.eliminated_variable) == (0, 1)
    assert step.relation == "same"
    assert step.correlation == pytest.approx(1.0)
    assert result.reverse_map == {1: (0, "same")}
