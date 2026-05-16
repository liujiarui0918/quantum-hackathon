from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from quantum_hackathon.pretraining import (
    PretrainingDatasetBuilder,
    SyntheticProblemGenerator,
    summarize_pretraining_examples,
    write_summary,
)
from quantum_hackathon.solvers import LogisticWarmStartModel, SamplerConfig


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    generator = SyntheticProblemGenerator(seed=args.seed)
    specs = generator.generate_suite(
        small_per_family=args.small_per_family,
        medium_per_family=args.medium_per_family,
        hybrid_count=args.hybrid_count,
    )
    builder = PretrainingDatasetBuilder(
        exact_max_bits=args.exact_max_bits,
        annealing_config=SamplerConfig(
            seed=args.seed,
            num_reads=args.annealing_reads,
            num_sweeps=args.annealing_sweeps,
        ),
    )
    build = builder.write_jsonl(specs, args.output)

    model = LogisticWarmStartModel.fit_training_records(
        build.examples,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    model_record = model.as_record()
    model_record["training_examples"] = len(build.examples)
    args.model_output.write_text(
        json.dumps(model_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = summarize_pretraining_examples(
        build.examples,
        output_path=args.output,
        model_path=args.model_output,
    )
    summary["seed"] = args.seed
    summary["model"] = {
        "model_type": model.name,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "l2": args.l2,
    }
    write_summary(summary, args.summary)

    print(f"wrote dataset: {args.output}")
    print(f"wrote summary: {args.summary}")
    print(f"wrote warm-start model: {args.model_output}")
    print(f"examples: {summary['num_examples']}")
    print(f"label_sources: {summary['label_sources']}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build synthetic QUBO graph pretraining data for route 7 warm-start models.",
    )
    parser.add_argument("--output", type=Path, default=Path("data/pretraining/qubo_graphs.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("data/pretraining/summary.json"))
    parser.add_argument("--model-output", type=Path, default=Path("data/pretraining/warm_start_model.json"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--small-per-family", type=int, default=2)
    parser.add_argument("--medium-per-family", type=int, default=2)
    parser.add_argument("--hybrid-count", type=int, default=2)
    parser.add_argument("--exact-max-bits", type=int, default=18)
    parser.add_argument("--annealing-reads", type=int, default=80)
    parser.add_argument("--annealing-sweeps", type=int, default=180)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=0.0005)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
