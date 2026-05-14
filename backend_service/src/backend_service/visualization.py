from __future__ import annotations

from typing import Any


def build_visualization(problem_payload: dict, raw_result: dict) -> dict:
    return {
        "quantum": build_quantum_view(raw_result),
        "scenario": build_scenario_view(problem_payload, raw_result),
    }


def build_quantum_view(raw_result: dict) -> dict:
    problem = raw_result.get("problem", {})
    qaoa = raw_result.get("qaoa", {}) or {}
    constrained = raw_result.get("constrained_qaoa", {}) or {}
    circuit = qaoa.get("quantum_circuit", {}) or {}

    return {
        "problem": {
            "name": problem.get("name"),
            "sense": problem.get("sense"),
            "num_logical_variables": problem.get("num_logical_variables"),
            "num_qubo_bits": problem.get("num_qubo_bits"),
            "constraints": problem.get("constraints"),
        },
        "best_solution": raw_result.get("best_solution"),
        "benchmark_rows": raw_result.get("benchmark", {}).get("rows"),
        "qaoa": {
            "status": qaoa.get("status"),
            "backend": qaoa.get("backend"),
            "circuit": circuit,
            "optimizer": qaoa.get("optimizer"),
        },
        "constrained_qaoa": {
            "status": constrained.get("status"),
            "diagnostics": constrained.get("diagnostics"),
            "warnings": constrained.get("warnings"),
        },
        "diagnostics": raw_result.get("diagnostics"),
    }


def build_scenario_view(problem_payload: dict, raw_result: dict) -> dict:
    best_solution = raw_result.get("best_solution") or {}
    logical_solution = best_solution.get("logical_solution") or {}

    variables = []
    for var_entry in problem_payload.get("variables", []) or []:
        var_name = var_entry["name"]
        var_value = logical_solution.get(var_name, 0)
        variables.append({
            "name": var_name,
            "value": var_value,
            "selected": var_value == 1,
        })

    selected_variables = [v["name"] for v in variables if v["selected"]]

    constraints = []
    for violation in best_solution.get("constraint_violations", []) or []:
        constraints.append({
            "name": violation.get("name"),
            "lhs": violation.get("lhs"),
            "sense": violation.get("sense"),
            "rhs": violation.get("rhs"),
            "violation": violation.get("violation"),
            "is_satisfied": violation.get("is_satisfied"),
        })

    view: dict[str, Any] = {
        "scenario_id": problem_payload.get("name"),
        "mapping_version": 1,
        "variables": variables,
        "selected_variables": selected_variables,
        "constraints": constraints,
        "objective_value": best_solution.get("objective_value"),
    }

    problem_name = problem_payload.get("name", "")
    if problem_name.startswith("sample_assignment"):
        view["selected_models"] = [
            name for name in selected_variables if name.startswith("model_")
        ]
        view["enabled_boosts"] = [
            name for name in selected_variables if name.startswith("boost_")
        ]

    return view
