import json
from pathlib import Path
from tempfile import TemporaryDirectory

from quantum_hackathon.metax_demo import main


def test_metax_demo_writes_six_route_outputs_with_stress_disabled():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        output = Path(temp_dir) / "metax_result.json"
        report = Path(temp_dir) / "metax_report.md"

        exit_code = main(
            [
                "--case",
                "sample",
                "--output",
                str(output),
                "--report",
                str(report),
                "--qaoa-shots",
                "40",
                "--qaoa-grid-size",
                "2",
                "--qaoa-random-trials",
                "1",
                "--sa-reads",
                "20",
                "--sa-sweeps",
                "50",
                "--skip-stress",
            ]
        )

        assert exit_code == 0
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["metax"]["qaoa_backend"] == "aer-gpu"
        assert payload["best_solution"]["is_feasible"] is True
        assert payload["qaoa"]["status"] == "ran"
        assert "Solver Benchmark" in report.read_text(encoding="utf-8")
