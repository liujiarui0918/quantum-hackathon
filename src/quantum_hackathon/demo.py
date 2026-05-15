from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

from quantum_hackathon.benchmarks.cases import exactly_one_selection, small_knapsack
from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import ConstraintCheckResult, DecodedSample, QuboBuilder
from quantum_hackathon.solvers.base import SamplerConfig
from quantum_hackathon.solvers.constrained_qaoa import ConstrainedQaoaRunner
from quantum_hackathon.solvers.exact import ExactSolverBackend
from quantum_hackathon.solvers.learning_guided import LearningGuidedSamplerBackend
from quantum_hackathon.solvers.qaoa import CostHamiltonianBuilder, QaoaConfig, QaoaRunner
from quantum_hackathon.solvers.simulated_annealing import SimulatedAnnealingBackend


def sample_assignment_problem() -> OptimizationProblem:
    problem = OptimizationProblem(sense="maximize", name="sample_assignment")
    for name in ("model_a", "model_b", "model_c", "boost_x", "boost_y"):
        problem.add_binary_var(name)
    problem.set_objective(
        linear={
            "model_a": 9.0,
            "model_b": 6.0,
            "model_c": 7.0,
            "boost_x": 3.0,
            "boost_y": 2.0,
        },
        quadratic={("model_c", "boost_x"): 1.0},
    )
    problem.add_constraint(
        linear={"model_a": 1.0, "model_b": 1.0, "model_c": 1.0},
        sense="==",
        rhs=1.0,
        name="choose_one_model",
        constraint_type="exactly_one",
        penalty_weight=15.0,
    )
    problem.add_constraint(
        linear={
            "model_a": 5.0,
            "model_b": 3.0,
            "model_c": 4.0,
            "boost_x": 2.0,
            "boost_y": 1.0,
        },
        sense="<=",
        rhs=6.0,
        name="resource_budget",
        constraint_type="bounded_sum",
        penalty_weight=20.0,
    )
    return problem


CASE_BUILDERS = {
    "sample": sample_assignment_problem,
    "small_knapsack": small_knapsack,
    "exactly_one": exactly_one_selection,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        problem, source = _resolve_problem(args)
        payload = run_demo(problem, source=source, args=args)
        _write_outputs(payload, output_path=args.output, report_path=args.report)
    except Exception as exc:  # pragma: no cover - exercised through CLI failures.
        print(f"demo failed: {exc}", file=sys.stderr)
        return 1

    print(f"wrote result json: {args.output}")
    print(f"wrote markdown report: {args.report}")
    return 0


def run_demo(problem: OptimizationProblem, *, source: str, args: argparse.Namespace) -> dict[str, Any]:
    started = perf_counter()
    model = QuboBuilder().build(problem)
    sampler_config = SamplerConfig(
        seed=args.seed,
        num_reads=args.sa_reads,
        num_sweeps=args.sa_sweeps,
        return_top_k=args.top_k,
    )

    exact_summary, exact_best = _run_backend(
        "exact",
        ExactSolverBackend(),
        model,
        SamplerConfig(seed=args.seed, return_top_k=args.top_k),
    )
    annealing_summary, annealing_best = _run_backend(
        "simulated_annealing",
        SimulatedAnnealingBackend(),
        model,
        sampler_config,
    )
    learning_summary, learning_best = _run_backend(
        "learning_guided",
        LearningGuidedSamplerBackend(),
        model,
        sampler_config,
    )
    qaoa_summary, qaoa_best = _run_qaoa(model, args)
    constrained_summary, constrained_best = _run_constrained_qaoa(problem, args)

    candidates = [exact_best, annealing_best, learning_best, qaoa_best, constrained_best]
    best_solution = _best_sample(candidates, problem.sense)
    benchmark_rows = [
        _benchmark_row("exact", exact_summary),
        _benchmark_row("simulated_annealing", annealing_summary),
        _benchmark_row("learning_guided", learning_summary),
    ]
    if qaoa_summary["status"] == "ran":
        benchmark_rows.append(_benchmark_row("qaoa_shot_simulator", qaoa_summary))
    if constrained_summary["status"] == "ran":
        benchmark_rows.append(_benchmark_row("constrained_qaoa_metadata_mvp", constrained_summary))

    payload: dict[str, Any] = {
        "problem": {
            "name": problem.name,
            "source": source,
            "sense": problem.sense,
            "variables": list(problem.variables),
            "num_logical_variables": len(problem.variables),
            "num_qubo_bits": model.num_variables,
            "constraints": [constraint.name for constraint in problem.constraints],
        },
        "run": {
            "seed": args.seed,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "total_ms": 0.0,
        },
        "diagnostics": model.diagnostics(),
        "best_solution": _sample_to_dict(best_solution),
        "benchmark": {
            "rows": benchmark_rows,
            "markdown": _rows_to_markdown(benchmark_rows),
        },
        "solvers": {
            "exact": exact_summary,
            "simulated_annealing": annealing_summary,
            "learning_guided": learning_summary,
        },
        "qaoa": qaoa_summary,
        "constrained_qaoa": constrained_summary,
    }
    payload["run"]["total_ms"] = round((perf_counter() - started) * 1000.0, 3)
    payload["report_markdown"] = _report_markdown(payload)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the reproducible quantum hackathon optimization demo.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="JSON problem file. If omitted, --case is used.",
    )
    parser.add_argument(
        "--case",
        choices=sorted(CASE_BUILDERS),
        default="sample",
        help="Built-in problem used when --input is omitted.",
    )
    parser.add_argument("--output", type=Path, default=Path("results/result.json"))
    parser.add_argument("--report", type=Path, default=Path("results/report.md"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--sa-reads", type=int, default=60)
    parser.add_argument("--sa-sweeps", type=int, default=150)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--qaoa-p", type=int, default=1)
    parser.add_argument("--qaoa-shots", type=int, default=200)
    parser.add_argument("--qaoa-max-qubits", type=int, default=12)
    parser.add_argument("--qaoa-grid-size", type=int, default=5)
    parser.add_argument("--qaoa-random-trials", type=int, default=10)
    parser.add_argument(
        "--qaoa-backend",
        choices=["local", "aer", "aer-gpu", "aer-cpu"],
        default="local",
        help="Optional QAOA execution backend; aer-gpu targets the MetaX container.",
    )
    parser.add_argument("--aer-device", choices=["CPU", "GPU"], default="GPU")
    parser.add_argument("--aer-method", default="statevector")
    parser.add_argument("--aer-max-qubits", type=int, default=30)
    parser.add_argument("--aer-optimization-level", type=int, default=1)
    parser.add_argument("--skip-qaoa", action="store_true")
    return parser


def _resolve_problem(args: argparse.Namespace) -> tuple[OptimizationProblem, str]:
    if args.input is None:
        return CASE_BUILDERS[args.case](), f"built-in:{args.case}"
    data = json.loads(args.input.read_text(encoding="utf-8"))
    return problem_from_json(data), str(args.input)


def problem_from_json(data: Mapping[str, Any]) -> OptimizationProblem:
    problem = OptimizationProblem(
        sense=str(data.get("sense", "minimize")),  # type: ignore[arg-type]
        name=str(data.get("name", "json_problem")),
    )
    variables = data.get("variables")
    if not isinstance(variables, list) or not variables:
        raise ValueError("input JSON must contain a non-empty variables list")
    for variable in variables:
        if not isinstance(variable, Mapping):
            raise ValueError("each variable entry must be an object")
        name = str(variable["name"])
        kind = str(variable.get("kind", "binary"))
        if kind == "binary":
            problem.add_binary_var(name)
        elif kind == "integer":
            problem.add_integer_var(
                name,
                lower=int(variable.get("lower", 0)),
                upper=int(variable["upper"]),
            )
        else:
            raise ValueError(f"unsupported variable kind: {kind}")

    objective = data.get("objective", {})
    if not isinstance(objective, Mapping):
        raise ValueError("objective must be an object")
    problem.set_objective(
        linear=_float_mapping(objective.get("linear", {})),
        quadratic=_parse_quadratic_terms(objective.get("quadratic", [])),
        offset=float(objective.get("offset", 0.0)),
    )
    for term in objective.get("high_order", []) or []:
        if not isinstance(term, Mapping):
            raise ValueError("high_order terms must be objects")
        problem.add_high_order_term(
            [str(name) for name in term["variables"]],
            float(term["coefficient"]),
        )

    for constraint in data.get("constraints", []) or []:
        if not isinstance(constraint, Mapping):
            raise ValueError("each constraint entry must be an object")
        penalty_weight = constraint.get("penalty_weight")
        problem.add_constraint(
            linear=_float_mapping(constraint.get("linear", {})),
            sense=str(constraint["sense"]),  # type: ignore[arg-type]
            rhs=float(constraint["rhs"]),
            name=str(constraint.get("name", f"constraint_{len(problem.constraints)}")),
            constraint_type=str(constraint.get("constraint_type", "linear")),
            hardness=str(constraint.get("hardness", "hard")),
            penalty_weight=None if penalty_weight is None else float(penalty_weight),
        )
    return problem


def _run_backend(
    label: str,
    backend: Any,
    model: Any,
    config: SamplerConfig,
) -> tuple[dict[str, Any], DecodedSample | None]:
    started = perf_counter()
    try:
        result = backend.solve(model, config)
    except ValueError as exc:
        return (
            {
                "status": "skipped",
                "backend": label,
                "reason": str(exc),
                "total_ms": round((perf_counter() - started) * 1000.0, 3),
            },
            None,
        )

    best_feasible = result.best_feasible()
    summary = {
        "status": "ran",
        "backend": result.backend_name,
        "best_feasible": _sample_to_dict(best_feasible),
        "best_raw_energy_sample": _sample_to_dict(result.best_raw_energy_sample),
        "feasible_sample_ratio": result.feasible_ratio,
        "samples_returned": len(result.samples),
        "timing": result.timing,
        "diagnostics": result.diagnostics,
        "config": _sampler_config_to_dict(config),
    }
    return summary, best_feasible


def _run_qaoa(model: Any, args: argparse.Namespace) -> tuple[dict[str, Any], DecodedSample | None]:
    circuit_summary = _qaoa_circuit_summary(model, args.qaoa_p)
    if args.skip_qaoa:
        return {"status": "skipped", "reason": "skip_qaoa", "quantum_circuit": circuit_summary}, None
    if model.num_variables > args.qaoa_max_qubits:
        return (
            {
                "status": "skipped",
                "reason": f"num_qubo_bits={model.num_variables} exceeds qaoa_max_qubits={args.qaoa_max_qubits}",
                "quantum_circuit": circuit_summary,
            },
            None,
        )

    started = perf_counter()
    config = QaoaConfig(
        p=args.qaoa_p,
        shots=args.qaoa_shots,
        seed=args.seed,
        max_qubits=args.qaoa_max_qubits,
        grid_size=args.qaoa_grid_size,
        random_trials=args.qaoa_random_trials,
        backend=args.qaoa_backend,
        aer_device=args.aer_device,
        aer_method=args.aer_method,
        aer_max_qubits=args.aer_max_qubits,
        aer_optimization_level=args.aer_optimization_level,
    )
    result = QaoaRunner().solve(model, config)
    best_feasible = result.best_samples.best_feasible()
    trace_values = [entry.value for entry in result.optimizer_trace]
    circuit_summary["execution_backend"] = result.diagnostics.get(
        "execution_backend",
        circuit_summary["execution_backend"],
    )
    summary = {
        "status": "ran",
        "backend": result.best_samples.backend_name,
        "best_feasible": _sample_to_dict(best_feasible),
        "best_raw_energy_sample": _sample_to_dict(result.best_samples.best_raw_energy_sample),
        "feasible_sample_ratio": result.best_samples.feasible_ratio,
        "samples_returned": len(result.best_samples.samples),
        "best_parameters": {
            "gammas": list(result.best_parameters["gammas"]),
            "betas": list(result.best_parameters["betas"]),
        },
        "optimizer": {
            "trace_length": len(result.optimizer_trace),
            "best_expected_energy": min(trace_values) if trace_values else None,
            "first_expected_energy": trace_values[0] if trace_values else None,
            "last_expected_energy": trace_values[-1] if trace_values else None,
        },
        "diagnostics": result.diagnostics,
        "quantum_circuit": circuit_summary,
        "total_ms": round((perf_counter() - started) * 1000.0, 3),
    }
    return summary, best_feasible


def _run_constrained_qaoa(
    problem: OptimizationProblem,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], DecodedSample | None]:
    if not _has_one_hot_constraint(problem):
        return {"status": "skipped", "reason": "no exactly_one constraint detected"}, None

    started = perf_counter()
    result = ConstrainedQaoaRunner().solve(
        problem,
        config=SamplerConfig(
            seed=args.seed,
            num_reads=args.sa_reads,
            num_sweeps=args.sa_sweeps,
            return_top_k=args.top_k,
        ),
    )
    summary = {
        "status": "ran",
        "route": "constrained_qaoa_metadata_mvp",
        "note": (
            "This route reports feasible-subspace and XY-mixer diagnostics; "
            "the current MVP samples the induced model with exact or simulated annealing backends."
        ),
        "best_feasible": _sample_to_dict(result.best_feasible_sample),
        "backend": result.backend_result.backend_name,
        "feasible_sample_ratio": result.backend_result.feasible_ratio,
        "diagnostics": result.diagnostics,
        "warnings": result.warnings,
        "total_ms": round((perf_counter() - started) * 1000.0, 3),
    }
    return summary, result.best_feasible_sample


def _qaoa_circuit_summary(model: Any, p: int) -> dict[str, Any]:
    hamiltonian = CostHamiltonianBuilder.from_qubo(model)
    return {
        "ansatz": "standard_qaoa_x_mixer",
        "execution_backend": "local_statevector_optimizer_plus_shot_sampler",
        "num_qubits": hamiltonian.num_qubits,
        "layers": p,
        "initial_state": "apply H to every qubit",
        "cost_unitary": {
            "description": "exp(-i gamma C) from QUBO-to-Ising Hamiltonian",
            "z_terms": {f"q{index}": value for index, value in hamiltonian.z_terms.items()},
            "zz_terms": {
                f"q{left},q{right}": value
                for (left, right), value in hamiltonian.zz_terms.items()
            },
        },
        "mixer_unitary": {
            "description": "exp(-i beta sum_i X_i)",
            "x_terms_per_layer": hamiltonian.num_qubits,
        },
        "gate_count_estimate": {
            "h": hamiltonian.num_qubits,
            "rz_per_layer": len(hamiltonian.z_terms),
            "rzz_per_layer": len(hamiltonian.zz_terms),
            "rx_per_layer": hamiltonian.num_qubits,
        },
    }


def _has_one_hot_constraint(problem: OptimizationProblem) -> bool:
    return any(
        constraint.constraint_type == "exactly_one"
        and constraint.sense == "=="
        and abs(constraint.rhs - 1.0) <= 1e-9
        and all(abs(value - 1.0) <= 1e-9 for value in constraint.linear.values())
        for constraint in problem.constraints
    )


def _best_sample(samples: Sequence[DecodedSample | None], sense: str) -> DecodedSample | None:
    available = [sample for sample in samples if sample is not None]
    if not available:
        return None
    return min(available, key=lambda sample: _sample_rank(sample, sense))


def _sample_rank(sample: DecodedSample, sense: str) -> tuple[Any, ...]:
    objective = sample.objective_value if sense == "minimize" else -sample.objective_value
    return (
        not sample.is_feasible,
        objective if sample.is_feasible else sample.total_violation,
        sample.total_violation,
        sample.qubo_energy,
        sample.bitstring,
    )


def _sample_to_dict(sample: DecodedSample | None) -> dict[str, Any] | None:
    if sample is None:
        return None
    return {
        "bitstring": "".join(str(bit) for bit in sample.bitstring),
        "bits": list(sample.bitstring),
        "logical_solution": sample.logical_solution,
        "objective_value": sample.objective_value,
        "qubo_energy": sample.qubo_energy,
        "penalty_energy": sample.penalty_energy,
        "is_feasible": sample.is_feasible,
        "total_violation": sample.total_violation,
        "num_occurrences": sample.num_occurrences,
        "source_backend": sample.source_backend,
        "constraint_violations": [
            _constraint_check_to_dict(result)
            for result in sample.constraint_violations
            if not result.is_satisfied
        ],
    }


def _constraint_check_to_dict(result: ConstraintCheckResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "lhs": result.lhs,
        "sense": result.sense,
        "rhs": result.rhs,
        "violation": result.violation,
        "is_satisfied": result.is_satisfied,
    }


def _benchmark_row(name: str, summary: Mapping[str, Any]) -> dict[str, Any]:
    best = summary.get("best_feasible") or {}
    return {
        "solver": name,
        "status": summary.get("status"),
        "best_feasible_objective": best.get("objective_value"),
        "best_feasible_bitstring": best.get("bitstring"),
        "feasible_sample_ratio": summary.get("feasible_sample_ratio"),
        "total_ms": summary.get("total_ms") or (summary.get("timing") or {}).get("total_ms"),
    }


def _rows_to_markdown(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def _report_markdown(payload: Mapping[str, Any]) -> str:
    best_solution = payload.get("best_solution")
    qaoa = payload.get("qaoa", {})
    circuit = qaoa.get("quantum_circuit", {}) if isinstance(qaoa, Mapping) else {}
    lines = [
        "# Quantum Hackathon Demo Report",
        "",
        "## Problem",
        "",
        f"- Name: {payload['problem']['name']}",
        f"- Source: {payload['problem']['source']}",
        f"- Sense: {payload['problem']['sense']}",
        f"- Logical variables: {payload['problem']['num_logical_variables']}",
        f"- QUBO bits: {payload['problem']['num_qubo_bits']}",
        "",
        "## Best Solution",
        "",
        "```json",
        json.dumps(best_solution, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Solver Benchmark",
        "",
        payload["benchmark"]["markdown"],
        "",
        "## Quantum Circuit Implementation",
        "",
        f"- Ansatz: {circuit.get('ansatz')}",
        f"- Backend: {circuit.get('execution_backend')}",
        f"- Qubits: {circuit.get('num_qubits')}",
        f"- Layers: {circuit.get('layers')}",
        f"- Cost unitary: {circuit.get('cost_unitary', {}).get('description')}",
        f"- Mixer unitary: {circuit.get('mixer_unitary', {}).get('description')}",
        f"- Gate count estimate: {circuit.get('gate_count_estimate')}",
        "",
        "## Reproducibility",
        "",
        f"- Seed: {payload['run']['seed']}",
        f"- Python: {payload['run']['python']}",
        f"- Total runtime ms: {payload['run']['total_ms']}",
    ]
    return "\n".join(lines) + "\n"


def _write_outputs(payload: Mapping[str, Any], *, output_path: Path, report_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = dict(payload)
    report = str(serializable.pop("report_markdown"))
    serializable["output_files"] = {
        "json": str(output_path),
        "markdown_report": str(report_path),
    }
    output_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report, encoding="utf-8")


def _float_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise ValueError("expected an object mapping variable names to coefficients")
    return {str(name): float(coefficient) for name, coefficient in value.items()}


def _parse_quadratic_terms(value: Any) -> dict[tuple[str, str], float]:
    if value in (None, [], {}):
        return {}
    terms: dict[tuple[str, str], float] = {}
    if isinstance(value, Mapping):
        for raw_key, coefficient in value.items():
            key = str(raw_key)
            names = key.split(",") if "," in key else key.split("*")
            if len(names) != 2:
                raise ValueError(f"quadratic key must contain two variables: {key}")
            terms[tuple(sorted(name.strip() for name in names))] = float(coefficient)
        return terms
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, Mapping):
                raise ValueError("quadratic terms must be objects")
            names = item.get("variables", item.get("vars"))
            if not isinstance(names, list) or len(names) != 2:
                raise ValueError("quadratic term variables must be a two-item list")
            terms[tuple(sorted(str(name) for name in names))] = float(item["coefficient"])
        return terms
    raise ValueError("quadratic must be either an object or a list")


def _sampler_config_to_dict(config: SamplerConfig) -> dict[str, Any]:
    return {
        "seed": config.seed,
        "num_reads": config.num_reads,
        "num_sweeps": config.num_sweeps,
        "return_top_k": config.return_top_k,
        "time_limit": config.time_limit,
        "max_samples": config.max_samples,
    }


if __name__ == "__main__":
    raise SystemExit(main())
