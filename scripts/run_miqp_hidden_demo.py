from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from quantum_hackathon.miqp import load_miqp_npz

try:
    from scripts import miqp_auto_sota
except ImportError:  # Allows direct execution: python scripts/run_miqp_hidden_demo.py
    import miqp_auto_sota  # type: ignore[no-redef]


@dataclass(frozen=True)
class HiddenCasePlan:
    filename: str
    n: int
    p: int
    m1: int
    m2: int
    profile: str
    seeds: str
    exact_binary_limit: int
    max_lp_evals: int
    max_configs: int | None
    time_limit_sec: float | None
    rationale: str


HIDDEN_CASES: tuple[HiddenCasePlan, ...] = (
    HiddenCasePlan(
        filename="miqp_test_1.npz",
        n=15,
        p=5,
        m1=5,
        m2=1,
        profile="quick",
        seeds="7",
        exact_binary_limit=20,
        max_lp_evals=400,
        max_configs=1,
        time_limit_sec=None,
        rationale="20-bit 内可直接精确枚举二进制部分，重点检查连续 LP 与 Benders-style cut 诊断。",
    ),
    HiddenCasePlan(
        filename="miqp_test_2.npz",
        n=40,
        p=10,
        m1=10,
        m2=2,
        profile="safe",
        seeds="3,7,11",
        exact_binary_limit=16,
        max_lp_evals=600,
        max_configs=4,
        time_limit_sec=None,
        rationale="启用 subQUBO 分块和多 seed，重点检查 block 选择、候选拼接与 LP repair。",
    ),
    HiddenCasePlan(
        filename="miqp_test_3.npz",
        n=80,
        p=20,
        m1=20,
        m2=4,
        profile="safe",
        seeds="3,7,11,19",
        exact_binary_limit=16,
        max_lp_evals=900,
        max_configs=None,
        time_limit_sec=None,
        rationale="与样例 B 同量级，使用 route7++ block pool 避免随机分块收敛慢。",
    ),
    HiddenCasePlan(
        filename="miqp_test_4.npz",
        n=120,
        p=30,
        m1=30,
        m2=6,
        profile="deep",
        seeds="3,7,11,19",
        exact_binary_limit=16,
        max_lp_evals=1400,
        max_configs=None,
        time_limit_sec=None,
        rationale="更依赖 affinity-cluster、Q-heavy 与 constraint-heavy 配置捕捉强耦合变量。",
    ),
    HiddenCasePlan(
        filename="miqp_test_5.npz",
        n=150,
        p=50,
        m1=50,
        m2=10,
        profile="deep",
        seeds="3,7,11,19,23",
        exact_binary_limit=16,
        max_lp_evals=2200,
        max_configs=None,
        time_limit_sec=None,
        rationale="极限压力测试，扩大 seed/config portfolio，并保留 LP 调用预算控制。",
    ),
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    input_dir = args.input_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for base_plan in HIDDEN_CASES:
        if args.cases and base_plan.filename not in args.cases:
            continue
        plan = _tune_plan(base_plan, args)
        input_path = _find_input(input_dir, plan.filename)
        row = {
            "filename": plan.filename,
            "expected": {"n": plan.n, "p": plan.p, "m1": plan.m1, "m2": plan.m2},
            "plan": asdict(plan),
            "status": "missing",
        }
        if input_path is None:
            if args.strict:
                raise FileNotFoundError(f"{plan.filename} not found under {input_dir}")
            summary_rows.append(row)
            print(f"[skip] {plan.filename}: not found under {input_dir}")
            continue

        instance = load_miqp_npz(input_path)
        actual = {"n": instance.n, "p": instance.p, "m1": instance.m1, "m2": instance.m2}
        row["actual"] = actual
        if actual != row["expected"]:
            row["status"] = "dimension_mismatch"
            summary_rows.append(row)
            message = f"{plan.filename}: expected {row['expected']}, got {actual}"
            if args.strict:
                raise ValueError(message)
            print(f"[warn] {message}")
            continue

        case_output_dir = output_dir / input_path.stem
        sota_args = [
            "--inputs",
            str(input_path),
            "--output-dir",
            str(case_output_dir),
            "--profile",
            plan.profile,
            "--seeds",
            plan.seeds,
            "--exact-binary-limit",
            str(plan.exact_binary_limit),
            "--max-lp-evals",
            str(plan.max_lp_evals),
        ]
        if plan.max_configs is not None:
            sota_args.extend(["--max-configs", str(plan.max_configs)])
        if plan.time_limit_sec is not None:
            sota_args.extend(["--time-limit-sec", str(plan.time_limit_sec)])
        if args.include_qaoa:
            sota_args.append("--include-qaoa")
        if args.dry_run:
            row["status"] = "planned"
            row["auto_sota_args"] = sota_args
            print(f"[plan] {plan.filename}: profile={plan.profile}, seeds={plan.seeds}, max_lp={plan.max_lp_evals}")
        else:
            print(f"[run] {plan.filename}: {plan.rationale}")
            exit_code = miqp_auto_sota.main(sota_args)
            if exit_code != 0:
                row["status"] = "failed"
                row["exit_code"] = exit_code
            else:
                row["status"] = "completed"
                row["output_dir"] = str(case_output_dir)
                _attach_best_result(row, case_output_dir, input_path.stem)
        summary_rows.append(row)

    summary = {"input_dir": str(input_dir), "output_dir": str(output_dir), "rows": summary_rows}
    summary_path = output_dir / "hidden_demo_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(summary, output_dir / "hidden_demo_summary.md")
    print(f"wrote hidden demo summary: {summary_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run tomorrow's five official MIQP hidden-test files with size-aware route7++ presets."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/final_tests"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/hidden_demo"))
    parser.add_argument("--include-qaoa", action="store_true", help="Also allow small block QAOA candidates.")
    parser.add_argument("--dry-run", action="store_true", help="Only write the planned commands and profiles.")
    parser.add_argument("--strict", action="store_true", help="Fail on missing files or dimension mismatches.")
    parser.add_argument("--cases", nargs="*", default=None, help="Optional subset, e.g. miqp_test_3.npz miqp_test_5.npz.")
    parser.add_argument("--budget-scale", type=float, default=1.0, help="Scale max_lp_evals for all cases.")
    parser.add_argument("--time-limit-sec", type=float, default=None, help="Per config/seed solver time limit.")
    parser.add_argument("--max-configs", type=int, default=None, help="Override max configs per instance.")
    parser.add_argument("--profile-override", choices=["quick", "safe", "deep"], default=None)
    return parser


def _tune_plan(plan: HiddenCasePlan, args: argparse.Namespace) -> HiddenCasePlan:
    max_lp_evals = max(1, int(round(plan.max_lp_evals * args.budget_scale)))
    return replace(
        plan,
        profile=args.profile_override or plan.profile,
        max_lp_evals=max_lp_evals,
        max_configs=args.max_configs if args.max_configs is not None else plan.max_configs,
        time_limit_sec=args.time_limit_sec if args.time_limit_sec is not None else plan.time_limit_sec,
    )


def _find_input(input_dir: Path, filename: str) -> Path | None:
    candidates = [input_dir / filename, Path(filename)]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _attach_best_result(row: dict, case_output_dir: Path, instance_name: str) -> None:
    path = case_output_dir / f"{instance_name}_all_runs.json"
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    row["best"] = payload.get("best")


def _write_markdown(summary: dict, path: Path) -> None:
    headers = ["file", "status", "profile", "seeds", "max_lp_evals", "best_objective", "feasible", "rationale"]
    lines = [
        "# MIQP Hidden Demo Summary",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in summary["rows"]:
        plan = row["plan"]
        best = row.get("best") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    row["filename"],
                    row["status"],
                    plan["profile"],
                    plan["seeds"],
                    str(plan["max_lp_evals"]),
                    str(best.get("objective", "")),
                    str(best.get("feasible", "")),
                    plan["rationale"],
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
