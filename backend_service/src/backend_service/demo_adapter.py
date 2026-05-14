from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend_service.errors import ApiError
from backend_service.schemas import RunOptions
from backend_service.settings import get_project_root
from quantum_hackathon.demo import problem_from_json, run_demo

WEB_RUN_DEFAULTS = {
    "seed": 7,
    "sa_reads": 60,
    "sa_sweeps": 150,
    "top_k": 20,
    "qaoa_p": 1,
    "qaoa_shots": 200,
    "qaoa_max_qubits": 12,
    "qaoa_grid_size": 5,
    "qaoa_random_trials": 10,
    "skip_qaoa": False,
}


def build_demo_args(options: RunOptions) -> argparse.Namespace:
    return argparse.Namespace(
        seed=_opt(options, "seed"),
        sa_reads=_opt(options, "sa_reads"),
        sa_sweeps=_opt(options, "sa_sweeps"),
        top_k=_opt(options, "top_k"),
        qaoa_p=_opt(options, "qaoa_p"),
        qaoa_shots=_opt(options, "qaoa_shots"),
        qaoa_max_qubits=_opt(options, "qaoa_max_qubits"),
        qaoa_grid_size=_opt(options, "qaoa_grid_size"),
        qaoa_random_trials=_opt(options, "qaoa_random_trials"),
        skip_qaoa=_opt(options, "skip_qaoa"),
    )


def _opt(options: RunOptions, field: str) -> Any:
    value = getattr(options, field, None)
    if value is None:
        return WEB_RUN_DEFAULTS[field]
    return value


def run_quantum_solve(problem_payload: dict, options: RunOptions) -> dict:
    try:
        problem = problem_from_json(problem_payload)
    except (ValueError, KeyError, TypeError) as exc:
        raise ApiError(
            status_code=400,
            code="invalid_problem",
            message=f"Failed to parse problem: {exc}",
            details={"payload_keys": list(problem_payload) if isinstance(problem_payload, dict) else None},
        ) from exc

    try:
        return run_demo(problem, source="api:request", args=build_demo_args(options))
    except Exception as exc:
        raise ApiError(
            status_code=500,
            code="solve_failed",
            message=f"Solver execution failed: {exc}",
        ) from exc


def load_sample_problem() -> dict:
    root = get_project_root()
    sample_path = root / "data" / "sample_problem.json"
    if not sample_path.is_file():
        raise ApiError(
            status_code=500,
            code="sample_problem_unavailable",
            message=f"Sample problem file not found at {sample_path}",
        )
    return json.loads(sample_path.read_text(encoding="utf-8"))
