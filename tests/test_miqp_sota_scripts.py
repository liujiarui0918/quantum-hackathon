import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from quantum_hackathon.miqp import load_miqp_npz
from scripts import miqp_synthetic_suite, miqp_train_block_model


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
