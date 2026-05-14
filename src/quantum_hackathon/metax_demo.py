from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence

from .demo import CASE_BUILDERS, problem_from_json, run_demo


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        problem, source = _resolve_problem(args)
        demo_args = _demo_namespace(args)
        payload = run_demo(problem, source=source, args=demo_args)
        payload["metax"] = {
            "profile": "qiskit-aer-maca",
            "qaoa_backend": "aer-gpu",
            "notes": [
                "Routes 1, 2, 3, 5, and 6 remain deterministic CPU-side model and solver paths.",
                "Route 4 QAOA shot execution targets Qiskit Aer on MetaX GPU when available.",
            ],
        }
        if not args.skip_stress:
            payload["metax"]["aer_gpu_stress"] = run_aer_gpu_stress(
                num_qubits=args.stress_qubits,
                depth=args.stress_depth,
                shots=args.stress_shots,
                seed=args.seed,
            )
        _write_outputs(payload, output_path=args.output, report_path=args.report)
    except Exception as exc:  # pragma: no cover - CLI failure surface.
        print(f"metax demo failed: {exc}")
        return 1

    print(f"wrote result json: {args.output}")
    print(f"wrote markdown report: {args.report}")
    return 0


def run_aer_gpu_stress(
    *,
    num_qubits: int = 28,
    depth: int = 8,
    shots: int = 128,
    seed: int | None = 7,
) -> dict[str, Any]:
    if num_qubits <= 0:
        raise ValueError("stress qubits must be positive")
    if shots <= 0:
        raise ValueError("stress shots must be positive")

    mx_smi_before = _mx_smi_snapshot()
    started = perf_counter()

    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except Exception as exc:  # pragma: no cover - optional environment.
        return {
            "status": "skipped",
            "reason": f"qiskit-aer unavailable: {type(exc).__name__}: {exc}",
            "mx_smi_before": mx_smi_before,
        }

    circuit = QuantumCircuit(num_qubits, num_qubits)
    circuit.h(range(num_qubits))
    for layer in range(depth):
        for qubit in range(num_qubits):
            angle = (layer + 1) * (qubit + 1) * math.pi / (num_qubits * depth + 1)
            circuit.rz(angle, qubit)
            circuit.rx(angle / 2.0, qubit)
        for qubit in range(layer % 2, num_qubits - 1, 2):
            circuit.cx(qubit, qubit + 1)
        for qubit in range((layer + 1) % 2, num_qubits - 1, 2):
            if hasattr(circuit, "rzz"):
                circuit.rzz(0.05 * (layer + 1), qubit, qubit + 1)
            else:  # pragma: no cover - retained for older Qiskit variants.
                circuit.cx(qubit, qubit + 1)
                circuit.rz(0.05 * (layer + 1), qubit + 1)
                circuit.cx(qubit, qubit + 1)
    circuit.measure(range(num_qubits), range(num_qubits))

    simulator = AerSimulator(method="statevector", device="GPU")
    transpiled = transpile(circuit, simulator, optimization_level=1)
    run_kwargs: dict[str, Any] = {"shots": shots}
    if seed is not None:
        run_kwargs["seed_simulator"] = seed
    result = simulator.run(transpiled, **run_kwargs).result()
    elapsed_ms = (perf_counter() - started) * 1000.0
    metadata = dict(getattr(result.results[0], "metadata", {}) or {})
    counts = result.get_counts()

    return {
        "status": "ran",
        "num_qubits": num_qubits,
        "depth": depth,
        "shots": shots,
        "elapsed_ms": round(elapsed_ms, 3),
        "metadata": _jsonable(metadata),
        "counts_preview": list(counts.items())[:5],
        "mx_smi_before": mx_smi_before,
        "mx_smi_after": _mx_smi_snapshot(),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the six-route demo with MetaX/qiskit-aer-maca GPU adaptation.",
    )
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--case", choices=sorted(CASE_BUILDERS), default="sample")
    parser.add_argument("--output", type=Path, default=Path("results/metax_result.json"))
    parser.add_argument("--report", type=Path, default=Path("results/metax_report.md"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--sa-reads", type=int, default=120)
    parser.add_argument("--sa-sweeps", type=int, default=300)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--qaoa-p", type=int, default=1)
    parser.add_argument("--qaoa-shots", type=int, default=512)
    parser.add_argument("--qaoa-max-qubits", type=int, default=16)
    parser.add_argument("--qaoa-grid-size", type=int, default=5)
    parser.add_argument("--qaoa-random-trials", type=int, default=10)
    parser.add_argument("--aer-max-qubits", type=int, default=30)
    parser.add_argument("--skip-stress", action="store_true")
    parser.add_argument("--stress-qubits", type=int, default=28)
    parser.add_argument("--stress-depth", type=int, default=8)
    parser.add_argument("--stress-shots", type=int, default=128)
    return parser


def _resolve_problem(args: argparse.Namespace) -> tuple[Any, str]:
    if args.input is None:
        return CASE_BUILDERS[args.case](), f"built-in:{args.case}"
    data = json.loads(args.input.read_text(encoding="utf-8"))
    return problem_from_json(data), str(args.input)


def _demo_namespace(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        seed=args.seed,
        sa_reads=args.sa_reads,
        sa_sweeps=args.sa_sweeps,
        top_k=args.top_k,
        qaoa_p=args.qaoa_p,
        qaoa_shots=args.qaoa_shots,
        qaoa_max_qubits=args.qaoa_max_qubits,
        qaoa_grid_size=args.qaoa_grid_size,
        qaoa_random_trials=args.qaoa_random_trials,
        qaoa_backend="aer-gpu",
        aer_device="GPU",
        aer_method="statevector",
        aer_max_qubits=args.aer_max_qubits,
        aer_optimization_level=1,
        skip_qaoa=False,
    )


def _write_outputs(payload: dict[str, Any], *, output_path: Path, report_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = str(payload.pop("report_markdown"))
    payload["output_files"] = {
        "json": str(output_path),
        "markdown_report": str(report_path),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")


def _mx_smi_snapshot() -> dict[str, Any]:
    candidates = ("/opt/mxdriver/bin/mx-smi", "mx-smi")
    for command in candidates:
        try:
            completed = subprocess.run(
                [command],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            continue
        if completed.returncode == 0:
            return {
                "command": command,
                "returncode": completed.returncode,
                "text": completed.stdout,
            }
    return {"command": None, "returncode": None, "text": ""}


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_jsonable(item) for item in value]
        return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
