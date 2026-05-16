import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from quantum_hackathon.miqp import load_miqp_npz
from scripts import miqp_auto_sota, miqp_synthetic_suite, miqp_train_block_model, run_miqp_hidden_demo


def test_miqp_synthetic_suite_writes_loadable_npz_instances():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        exit_code = miqp_synthetic_suite.main(
            [
                "--output-dir",
                str(root / "synthetic"),
                "--manifest",
                str(root / "manifest.json"),
                "--count",
                "2",
                "--n-min",
                "12",
                "--n-max",
                "14",
                "--p-min",
                "3",
                "--p-max",
                "4",
                "--m1-min",
                "3",
                "--m1-max",
                "4",
                "--m2-min",
                "1",
                "--m2-max",
                "2",
            ]
        )

        assert exit_code == 0
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert len(manifest["rows"]) == 2
        instance = load_miqp_npz(manifest["rows"][0]["path"])
        assert instance.n >= 12
        assert instance.p >= 3


def test_miqp_train_block_model_fits_trace_jsonl():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        trace = root / "trace.jsonl"
        row = {
            "block_pool": [
                {
                    "improvement_per_lp_call": 1.5,
                    "score_features": {
                        name: float(index + 1)
                        for index, name in enumerate(miqp_train_block_model.BLOCK_SCORE_FEATURE_NAMES)
                    },
                },
                {
                    "improvement_per_lp_call": -0.5,
                    "score_features": {
                        name: float(index)
                        for index, name in enumerate(miqp_train_block_model.BLOCK_SCORE_FEATURE_NAMES)
                    },
                },
            ]
        }
        trace.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        output = root / "model.json"
        exit_code = miqp_train_block_model.main(
            [
                "--inputs",
                str(trace),
                "--output",
                str(output),
                "--summary",
                str(root / "summary.json"),
            ]
        )

        assert exit_code == 0
        model = json.loads(output.read_text(encoding="utf-8"))
        assert model["model_type"] == "linear_block_scorer"
        assert len(model["weights"]) == len(miqp_train_block_model.BLOCK_SCORE_FEATURE_NAMES)
        summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
        assert summary["model_scope"] == "non_neural_linear_ranker"


def test_miqp_auto_sota_profiles_are_non_neural_by_default():
    quick = miqp_auto_sota._configs(False, False, "quick")
    deep = miqp_auto_sota._configs(False, False, "deep")

    assert len(quick) == 2
    assert len(deep) > len(quick)
    assert all(not config.use_learned for config in deep)
    assert any(config.post_polish_rounds > 0 for config in deep)


def test_hidden_demo_dry_run_writes_size_aware_plan():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        output_dir = root / "hidden_demo"
        exit_code = run_miqp_hidden_demo.main(
            [
                "--input-dir",
                str(root / "missing_inputs"),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )

        assert exit_code == 0
        summary = json.loads((output_dir / "hidden_demo_summary.json").read_text(encoding="utf-8"))
        rows = summary["rows"]
        assert [row["filename"] for row in rows] == [f"miqp_test_{index}.npz" for index in range(1, 6)]
        assert rows[0]["plan"]["exact_binary_limit"] == 20
        assert rows[0]["plan"]["profile"] == "quick"
        assert rows[3]["plan"]["profile"] == "deep"
        assert rows[4]["plan"]["max_lp_evals"] == 2200
        assert all(row["status"] == "missing" for row in rows)
