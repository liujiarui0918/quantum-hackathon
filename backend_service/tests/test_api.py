import pytest
from fastapi.testclient import TestClient
from backend_service.main import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "backend_service"


class TestSampleProblem:
    def test_returns_ok_with_problem(self):
        resp = client.get("/api/quantum/sample-problem")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "problem" in data
        assert data["problem"]["name"] == "sample_assignment"


class TestSolve:
    def test_solve_sample_problem_defaults(self):
        sample = client.get("/api/quantum/sample-problem").json()
        resp = client.post("/api/quantum/solve", json={
            "problem": sample["problem"],
            "run_options": {}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "raw_result" in data
        assert "visualization" in data
        raw = data["raw_result"]
        assert raw["best_solution"]["is_feasible"] is True
        assert "benchmark" in raw
        vis = data["visualization"]
        assert "quantum" in vis
        assert "scenario" in vis

    def test_solve_with_seed(self):
        sample = client.get("/api/quantum/sample-problem").json()
        seed = 42
        resp = client.post("/api/quantum/solve", json={
            "problem": sample["problem"],
            "run_options": {"seed": seed}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["raw_result"]["run"]["seed"] == seed

    def test_solve_with_skip_qaoa(self):
        sample = client.get("/api/quantum/sample-problem").json()
        resp = client.post("/api/quantum/solve", json={
            "problem": sample["problem"],
            "run_options": {"skip_qaoa": True}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["raw_result"]["qaoa"]["status"] == "skipped"
        assert "quantum_circuit" in data["raw_result"]["qaoa"]


class TestInvalidProblem:
    def test_empty_variables(self):
        resp = client.post("/api/quantum/solve", json={
            "problem": {"name": "bad", "sense": "minimize", "variables": [], "objective": {"linear": {}}},
            "run_options": {}
        })
        assert resp.status_code in (400, 422)
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data
        assert "code" in data["error"]

    def test_invalid_variable_kind(self):
        resp = client.post("/api/quantum/solve", json={
            "problem": {
                "name": "bad",
                "sense": "minimize",
                "variables": [{"name": "x", "kind": "float"}],
                "objective": {"linear": {}}
            },
            "run_options": {}
        })
        assert resp.status_code in (400, 422)
        data = resp.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "invalid_problem"

    def test_missing_variable_name(self):
        resp = client.post("/api/quantum/solve", json={
            "problem": {
                "name": "bad",
                "sense": "minimize",
                "variables": [{"kind": "binary"}],
                "objective": {"linear": {}}
            },
            "run_options": {}
        })
        assert resp.status_code in (400, 422)
        data = resp.json()
        assert data["ok"] is False


class TestVisualizationFields:
    def test_visualization_has_required_layers(self):
        sample = client.get("/api/quantum/sample-problem").json()
        resp = client.post("/api/quantum/solve", json={
            "problem": sample["problem"],
            "run_options": {}
        })
        vis = resp.json()["visualization"]
        quantum = vis["quantum"]
        assert "problem" in quantum
        assert "best_solution" in quantum
        assert "benchmark_rows" in quantum
        scenario = vis["scenario"]
        assert "scenario_id" in scenario
        assert "variables" in scenario
        assert "selected_variables" in scenario
        assert "constraints" in scenario
