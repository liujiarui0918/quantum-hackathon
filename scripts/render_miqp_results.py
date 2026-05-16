from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render MIQP route-7 JSON results as a Markdown table.")
    parser.add_argument("results", nargs="+", type=Path, help="Result JSON files written by quantum-solve-miqp.")
    parser.add_argument("--output", type=Path, default=Path("results/miqp_summary.md"))
    args = parser.parse_args(argv)

    rows = [_row_from_result(path) for path in args.results]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_render_markdown(rows), encoding="utf-8")
    print(f"wrote summary: {args.output}")
    return 0


def _row_from_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    instance = payload["instance"]
    route = payload["miqp_aware_route7"]
    solution = route["solution"]
    reference = payload.get("reference_solution") or {}
    official = reference.get("optimal_value")
    objective = float(solution["objective"])
    gap = None
    if official is not None and abs(float(official)) > 1e-12:
        gap = (float(official) - objective) / abs(float(official))
    return {
        "instance": instance["name"],
        "n": instance["n"],
        "p": instance["p"],
        "m1": instance["m1"],
        "m2": instance["m2"],
        "objective": objective,
        "official": official,
        "gap": gap,
        "feasible": bool(solution["feasible"]),
        "best_seed": payload.get("best_seed"),
        "runtime_ms": payload.get("runtime_ms"),
        "mode": route["diagnostics"]["mode"],
        "candidate_evaluations": route["diagnostics"]["candidate_evaluations"],
        "path": str(path),
    }


def _render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# MIQP Route 7 Result Summary",
        "",
        "| Instance | Size | Objective | Official | Gap | Feasible | Best seed | Runtime ms | Mode | Evaluations |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |",
    ]
    for row in rows:
        official = "-" if row["official"] is None else f"{float(row['official']):.6f}"
        gap = "-" if row["gap"] is None else f"{100.0 * float(row['gap']):.2f}%"
        runtime = "-" if row["runtime_ms"] is None else f"{float(row['runtime_ms']):.3f}"
        lines.append(
            "| {instance} | n={n}, p={p}, m1={m1}, m2={m2} | {objective:.6f} | "
            "{official_text} | {gap_text} | {feasible} | {best_seed} | {runtime_text} | {mode} | "
            "{candidate_evaluations} |".format(
                official_text=official,
                gap_text=gap,
                runtime_text=runtime,
                **row,
            )
        )
    lines.extend(
        [
            "",
            "The gap is computed as `(official - objective) / abs(official)` for this maximization problem.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
