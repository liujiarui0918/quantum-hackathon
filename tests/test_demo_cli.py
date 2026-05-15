import json
from pathlib import Path
from tempfile import TemporaryDirectory

from quantum_hackathon.demo import main, problem_from_json


def test_problem_from_json_loads_sample_problem():
    data = {
        "name": "two_choice",
        "sense": "maximize",
        "variables": [
            {"name": "x0", "kind": "binary"},
            {"name": "x1", "kind": "binary"},
        ],
        "objective": {
            "linear": {"x0": 1.0, "x1": 2.0},
            "quadratic": [{"variables": ["x0", "x1"], "coefficient": -0.5}],
        },
        "constraints": [
            {
                "name": "choose_one",
                "linear": {"x0": 1.0, "x1": 1.0},
                "sense": "==",
                "rhs": 1.0,
                "constraint_type": "exactly_one",
                "penalty_weight": 5.0,
            }
        ],
    }

    problem = problem_from_json(data)

    assert problem.name == "two_choice"
    assert problem.sense == "maximize"
    assert list(problem.variables) == ["x0", "x1"]
    assert problem.objective_quadratic == {("x0", "x1"): -0.5}
    assert problem.constraints[0].constraint_type == "exactly_one"


def test_demo_cli_writes_result_and_report():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        output = Path(temp_dir) / "result.json"
        report = Path(temp_dir) / "report.md"

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
            ]
        )

        assert exit_code == 0
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["problem"]["name"] == "sample_assignment"
        assert payload["best_solution"]["is_feasible"] is True
        assert payload["qaoa"]["status"] == "ran"
        assert payload["constrained_qaoa"]["status"] == "ran"
        assert payload["solvers"]["learning_guided"]["status"] == "ran"
        assert payload["solvers"]["learning_guided"]["best_feasible"]["objective_value"] == 11.0
        assert any(row["solver"] == "learning_guided" for row in payload["benchmark"]["rows"])
        assert payload["qaoa"]["quantum_circuit"]["num_qubits"] >= 1
        assert "Solver Benchmark" in report.read_text(encoding="utf-8")
