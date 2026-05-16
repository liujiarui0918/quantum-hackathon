import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from quantum_hackathon.miqp import (
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
