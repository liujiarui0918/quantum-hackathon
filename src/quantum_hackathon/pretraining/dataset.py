from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from quantum_hackathon.hybrid import HybridOptimizationProblem, HybridOptimizer
from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder
from quantum_hackathon.solvers import (
    ExactSolverBackend,
    LearningGuidedTrainingExample,
    QuboGraphFeatureExtractor,
    SamplerConfig,
    SimulatedAnnealingBackend,
)

from .synthetic import SyntheticProblemSpec


@dataclass(frozen=True)
class PretrainingDatasetBuild:
    examples: tuple[LearningGuidedTrainingExample, ...]
    summary: dict


class PretrainingDatasetBuilder:
    def __init__(
        self,
        *,
        exact_max_bits: int = 18,
        qubo_builder: QuboBuilder | None = None,
        extractor: QuboGraphFeatureExtractor | None = None,
        exact_backend: ExactSolverBackend | None = None,
        annealing_backend: SimulatedAnnealingBackend | None = None,
        hybrid_optimizer: HybridOptimizer | None = None,
        annealing_config: SamplerConfig | None = None,
    ):
        self.exact_max_bits = exact_max_bits
        self.qubo_builder = qubo_builder or QuboBuilder()
        self.extractor = extractor or QuboGraphFeatureExtractor()
        self.exact_backend = exact_backend or ExactSolverBackend()
        self.annealing_backend = annealing_backend or SimulatedAnnealingBackend()
        self.hybrid_optimizer = hybrid_optimizer or HybridOptimizer()
        self.annealing_config = annealing_config or SamplerConfig(seed=7, num_reads=80, num_sweeps=180)

    def build(self, specs: Sequence[SyntheticProblemSpec]) -> PretrainingDatasetBuild:
        examples = tuple(self.build_example(spec) for spec in specs)
        return PretrainingDatasetBuild(
            examples=examples,
            summary=summarize_pretraining_examples(examples),
        )

    def build_example(self, spec: SyntheticProblemSpec) -> LearningGuidedTrainingExample:
        if isinstance(spec.problem, HybridOptimizationProblem):
            return self._build_hybrid_example(spec)
        return self._build_optimization_example(spec)

    def write_jsonl(
        self,
        specs: Sequence[SyntheticProblemSpec],
        path: str | Path,
    ) -> PretrainingDatasetBuild:
        build = self.build(specs)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "".join(example.to_json_line() + "\n" for example in build.examples),
            encoding="utf-8",
        )
        return build

    def _build_optimization_example(self, spec: SyntheticProblemSpec) -> LearningGuidedTrainingExample:
        problem = spec.problem
        if not isinstance(problem, OptimizationProblem):
            raise TypeError("expected OptimizationProblem")
        model = self.qubo_builder.build(problem)
        warnings: list[str] = []
        if model.num_variables <= self.exact_max_bits:
            backend = self.exact_backend
            config = SamplerConfig(return_top_k=1)
        else:
            backend = self.annealing_backend
            config = self.annealing_config
        try:
            result = backend.solve(model, config)
        except ValueError as exc:
            warnings.append(f"{backend.name}_skipped:{exc}")
            result = self.annealing_backend.solve(model, self.annealing_config)

        sample = result.best_feasible() or result.best_raw_energy_sample
        label_bitstring = sample.bitstring if sample is not None else None
        diagnostics = _with_synthetic_metadata(model.diagnostics(), spec)
        diagnostics.update(
            {
                "label_backend": result.backend_name,
                "exact_max_bits": self.exact_max_bits,
            }
        )
        return LearningGuidedTrainingExample(
            problem_name=problem.name,
            label_source=result.backend_name,
            record=self.extractor.to_training_record(model, label_bitstring),
            objective_value=sample.objective_value if sample is not None else None,
            is_feasible=sample.is_feasible if sample is not None else None,
            diagnostics=diagnostics,
            warnings=tuple([*warnings, *model.warnings]),
        )

    def _build_hybrid_example(self, spec: SyntheticProblemSpec) -> LearningGuidedTrainingExample:
        problem = spec.problem
        if not isinstance(problem, HybridOptimizationProblem):
            raise TypeError("expected HybridOptimizationProblem")
        hybrid_result = self.hybrid_optimizer.solve(problem)
        companion = hybrid_binary_companion(problem)
        model = self.qubo_builder.build(companion)
        label_bitstring = None
        if hybrid_result.best_feasible_solution is not None:
            logical = {
                name: int(round(hybrid_result.best_feasible_solution[name]))
                for name, variable in problem.variables.items()
                if variable.kind == "binary"
            }
            label_bitstring = model.bitstring_from_logical(logical)
        diagnostics = _with_synthetic_metadata(model.diagnostics(), spec)
        diagnostics.update(
            {
                "label_backend": "hybrid_relax_round_repair",
                "hybrid_status": hybrid_result.status,
                "hybrid_diagnostics": hybrid_result.diagnostics,
                "hybrid_warm_start_metadata": hybrid_result.warm_start_metadata,
            }
        )
        warnings = list(model.warnings)
        if hybrid_result.status != "feasible":
            warnings.append("hybrid_label_infeasible")
        return LearningGuidedTrainingExample(
            problem_name=problem.name,
            label_source="hybrid_relax_round_repair",
            record=self.extractor.to_training_record(model, label_bitstring),
            objective_value=hybrid_result.objective,
            is_feasible=hybrid_result.status == "feasible",
            diagnostics=diagnostics,
            warnings=tuple(warnings),
        )


def hybrid_binary_companion(problem: HybridOptimizationProblem) -> OptimizationProblem:
    binary_names = [name for name, variable in problem.variables.items() if variable.kind == "binary"]
    companion = OptimizationProblem(sense=problem.sense, name=f"{problem.name}_binary_companion")
    for name in binary_names:
        companion.add_binary_var(name)
    binary_set = set(binary_names)
    linear = {
        name: coefficient
        for name, coefficient in problem.objective_linear.items()
        if name in binary_set
    }
    quadratic = {
        pair: coefficient
        for pair, coefficient in problem.objective_quadratic.items()
        if pair[0] in binary_set and pair[1] in binary_set
    }
    companion.set_objective(linear=linear, quadratic=quadratic, offset=problem.objective_offset)
    for constraint in problem.constraints:
        if set(constraint.linear).issubset(binary_set):
            companion.add_constraint(
                constraint.linear,
                sense=constraint.sense,
                rhs=constraint.rhs,
                name=constraint.name,
                constraint_type=constraint.constraint_type,
                penalty_weight=25.0,
            )
    return companion


def summarize_pretraining_examples(
    examples: Sequence[LearningGuidedTrainingExample],
    *,
    output_path: str | Path | None = None,
    model_path: str | Path | None = None,
) -> dict:
    family_counts = Counter()
    size_counts = Counter()
    label_counts = Counter()
    bit_counts: list[int] = []
    warnings: list[str] = []
    for example in examples:
        family_counts[example.diagnostics.get("synthetic_family", "unknown")] += 1
        size_counts[example.diagnostics.get("synthetic_size", "unknown")] += 1
        label_counts[example.label_source] += 1
        bit_counts.append(int(example.record.get("num_nodes", 0)))
        warnings.extend(example.warnings)
    return {
        "num_examples": len(examples),
        "families": dict(sorted(family_counts.items())),
        "sizes": dict(sorted(size_counts.items())),
        "label_sources": dict(sorted(label_counts.items())),
        "bit_count_min": min(bit_counts) if bit_counts else 0,
        "bit_count_max": max(bit_counts) if bit_counts else 0,
        "bit_count_avg": round(sum(bit_counts) / len(bit_counts), 3) if bit_counts else 0.0,
        "output_path": str(output_path) if output_path is not None else None,
        "model_path": str(model_path) if model_path is not None else None,
        "warnings": warnings,
    }


def write_summary(summary: dict, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _with_synthetic_metadata(diagnostics: dict, spec: SyntheticProblemSpec) -> dict:
    enriched = dict(diagnostics)
    enriched.update(
        {
            "synthetic_family": spec.family,
            "synthetic_size": spec.size,
            "route_tags": list(spec.route_tags),
            "synthetic_metadata": dict(spec.metadata),
        }
    )
    return enriched
