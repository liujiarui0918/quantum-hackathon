import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from quantum_hackathon.miqp import (
    MiqpAwareRoute7Solver,
    MiqpLearnedBlockScorer,
    MiqpBlockScoreWeights,
    MiqpBlockSelector,
    MiqpCutAdvisor,
    MiqpWarmStartAdvisor,
    load_miqp_npz,
)
from quantum_hackathon.miqp_cli import main as miqp_main


SAMPLE_DIR = Path("量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据")


def test_miqp_loader_matches_sample_objective_and_feasibility():
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_A.npz")

    assert instance.n == 15
    assert instance.p == 5
    assert instance.x_opt is not None
    assert instance.y_opt is not None
    assert instance.is_feasible(instance.x_opt, instance.y_opt)
    assert instance.objective(instance.x_opt, instance.y_opt) == pytest.approx(instance.optimal_value)
    assert instance.objective(np.zeros(instance.n), np.zeros(instance.p)) == 0.0


def test_miqp_block_selector_respects_block_cap_on_medium_sample():
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_B.npz")

    block = MiqpBlockSelector(max_block_size=12, frontier_size=5).select(instance)

    assert len(block.binary_indices) == 12
    assert len(set(block.binary_indices)) == 12
    assert len(block.frontier_indices) == 5
    assert block.score > 0.0
    assert block.seed_index in block.binary_indices


def test_miqp_block_selector_supports_affinity_cluster_and_custom_weights():
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_B.npz")

    block = MiqpBlockSelector(
        max_block_size=10,
        frontier_size=4,
        strategy="affinity_cluster",
        weights=MiqpBlockScoreWeights(objective=0.2, coupling=0.5, mixed_constraint=0.2, binary_constraint=0.1),
    ).select(instance)

    assert len(block.binary_indices) == 10
    assert block.rationale["strategy"] == "affinity_cluster"
    assert block.rationale["score_weights"]["coupling"] == pytest.approx(0.5)


def test_miqp_warm_start_repairs_binary_constraints():
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_B.npz")
    block = MiqpBlockSelector(max_block_size=12).select(instance)

    plan = MiqpWarmStartAdvisor().plan(instance, block=block)
    repaired = np.asarray(plan.repaired_assignment)

    assert np.all(instance.B @ repaired <= instance.b_prime + 1e-8)
    assert plan.fixing_plan.ranked_bits


def test_miqp_cut_advisor_builds_tight_benders_cut_for_reference_solution():
    pytest.importorskip("scipy")
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_A.npz")
    assert instance.x_opt is not None

    advisor = MiqpCutAdvisor()
    continuous = advisor.solve_continuous_subproblem(instance, instance.x_opt)
    cut = advisor.advise_cut(instance, instance.x_opt, continuous)

    assert continuous.feasible
    assert cut.cut_type == "benders_optimality"
    assert cut.diagnostics["cut_tightness_gap"] <= 1e-6


def test_miqp_cli_writes_result_json_for_tiny_instance():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        instance_path = root / "tiny_miqp.npz"
        output = root / "result.json"
        solution = root / "solution.npz"
        np.savez_compressed(
            instance_path,
            n=np.asarray(3),
            p=np.asarray(1),
            m1=np.asarray(1),
            m2=np.asarray(1),
            Q=np.zeros((3, 3)),
            c=np.asarray([2.0, 3.0, 1.0]),
            h=np.asarray([4.0]),
            A=np.asarray([[-1.0, -1.0, -1.0]]),
            G=np.asarray([[1.0]]),
            b=np.asarray([2.0]),
            B=np.asarray([[1.0, 1.0, 1.0]]),
            b_prime=np.asarray([2.0]),
        )

        exit_code = miqp_main(
            [
                "--input",
                str(instance_path),
                "--output",
                str(output),
                "--solution-npz",
                str(solution),
                "--exact-binary-limit",
                "3",
            ]
        )

        assert exit_code == 0
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["miqp_aware_route7"]["solution"]["feasible"] is True
        assert payload["miqp_aware_route7"]["solution"]["objective"] >= 0.0
        assert solution.exists()


def test_miqp_route7_solver_portfolio_runs_on_tiny_instance():
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_A.npz")

    result = MiqpAwareRoute7Solver(
        block_selector=MiqpBlockSelector(max_block_size=8),
        exact_binary_limit=0,
        candidate_limit=16,
        max_iterations=1,
        qaoa_max_qubits=8,
        seed=3,
    ).solve(instance)

    assert result.solution.feasible
    assert result.diagnostics["block_history"][0]["solver_portfolio"]


def test_miqp_route7pp_block_pool_records_trace_and_cache_hits():
    instance = load_miqp_npz(SAMPLE_DIR / "miqp_sample_A.npz")

    result = MiqpAwareRoute7Solver(
        block_selector=MiqpBlockSelector(max_block_size=8),
        exact_binary_limit=0,
        candidate_limit=24,
        max_iterations=1,
        seed=5,
        qaoa_max_qubits=0,
        block_pool=True,
        blocks_per_iteration=2,
        candidate_budget_per_block=12,
        max_lp_evals=20,
        learned_block_scorer=MiqpLearnedBlockScorer(),
    ).solve(instance)

    history = result.diagnostics["block_history"]
    assert result.solution.feasible
    assert history[0]["block_pool_enabled"] is True
    assert len(history[0]["block_pool"]) >= 1
    assert history[0]["total_lp_calls"] <= 20
    assert history[0]["total_lp_cache_hits"] >= 1
    assert "score_features" in history[0]["block_pool"][0]


def test_miqp_cli_writes_route7pp_trace_jsonl():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        output = root / "result.json"
        trace = root / "trace.jsonl"
        exit_code = miqp_main(
            [
                "--input",
                str(SAMPLE_DIR / "miqp_sample_A.npz"),
                "--output",
                str(output),
                "--exact-binary-limit",
                "0",
                "--candidate-limit",
                "20",
                "--max-iterations",
                "1",
                "--block-pool",
                "--blocks-per-iteration",
                "2",
                "--candidate-budget-per-block",
                "10",
                "--max-lp-evals",
                "16",
                "--qaoa-max-qubits",
                "0",
                "--trace-jsonl",
                str(trace),
            ]
        )

        assert exit_code == 0
        rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        assert rows
        assert rows[0]["block_pool_enabled"] is True
        assert "block_pool" in rows[0]
