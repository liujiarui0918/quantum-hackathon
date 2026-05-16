from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import product
from math import exp, sqrt
from pathlib import Path
from time import perf_counter
from typing import Iterable, Protocol, Sequence

from quantum_hackathon.modeling.problem import OptimizationProblem
from quantum_hackathon.modeling.qubo import QuboBuilder, QuboModel

from .base import RawSampleSet, SamplerBackend, SamplerConfig
from .exact import ExactSolverBackend


FEATURE_NAMES = (
    "linear_bias",
    "degree",
    "coupling_sum",
    "abs_coupling_sum",
    "positive_coupling_sum",
    "negative_coupling_sum",
)


@dataclass(frozen=True)
class QuboNodeFeature:
    index: int
    name: str
    kind: str
    source: str
    logical_name: str | None
    values: tuple[float, ...]

    def as_record(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "kind": self.kind,
            "source": self.source,
            "logical_name": self.logical_name,
            "features": list(self.values),
        }


@dataclass(frozen=True)
class QuboEdgeFeature:
    source: int
    target: int
    coefficient: float

    def as_record(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "coefficient": self.coefficient,
        }


@dataclass(frozen=True)
class QuboGraphFeatures:
    feature_names: tuple[str, ...]
    nodes: tuple[QuboNodeFeature, ...]
    edges: tuple[QuboEdgeFeature, ...]

    def to_training_record(self, label_bitstring: Iterable[int] | None = None) -> dict:
        labels = None if label_bitstring is None else [int(bit) for bit in label_bitstring]
        return {
            "num_nodes": len(self.nodes),
            "feature_names": list(self.feature_names),
            "node_features": [node.as_record() for node in self.nodes],
            "edges": [edge.as_record() for edge in self.edges],
            "labels": labels,
        }


class QuboGraphFeatureExtractor:
    def extract(self, model: QuboModel) -> QuboGraphFeatures:
        linear = [0.0] * model.num_variables
        coupling_sum = [0.0] * model.num_variables
        abs_coupling_sum = [0.0] * model.num_variables
        positive_coupling_sum = [0.0] * model.num_variables
        negative_coupling_sum = [0.0] * model.num_variables
        degree = [0.0] * model.num_variables
        edges: list[QuboEdgeFeature] = []

        for (left, right), coefficient in model.qubo.items():
            if left == right:
                linear[left] += coefficient
                continue
            edges.append(QuboEdgeFeature(source=left, target=right, coefficient=coefficient))
            for index in (left, right):
                degree[index] += 1.0
                coupling_sum[index] += coefficient
                abs_coupling_sum[index] += abs(coefficient)
                if coefficient >= 0:
                    positive_coupling_sum[index] += coefficient
                else:
                    negative_coupling_sum[index] += coefficient

        nodes = []
        for bit in model.registry.bits:
            nodes.append(
                QuboNodeFeature(
                    index=bit.index,
                    name=bit.name,
                    kind=bit.kind,
                    source=bit.source,
                    logical_name=bit.logical_name,
                    values=(
                        linear[bit.index],
                        degree[bit.index],
                        coupling_sum[bit.index],
                        abs_coupling_sum[bit.index],
                        positive_coupling_sum[bit.index],
                        negative_coupling_sum[bit.index],
                    ),
                )
            )
        return QuboGraphFeatures(feature_names=FEATURE_NAMES, nodes=tuple(nodes), edges=tuple(edges))

    def to_training_record(self, model: QuboModel, label_bitstring: Iterable[int] | None = None) -> dict:
        return self.extract(model).to_training_record(label_bitstring)


@dataclass(frozen=True)
class VariableFixingPlan:
    fixed_bits: tuple[tuple[int, int, float], ...]
    free_bits: tuple[int, ...]
    ranked_bits: tuple[tuple[int, float, float], ...]
    confidence_threshold: float

    @property
    def fixed_assignment(self) -> dict[int, int]:
        return {index: value for index, value, _confidence in self.fixed_bits}

    def as_record(self) -> dict:
        return {
            "confidence_threshold": self.confidence_threshold,
            "fixed_bits": [
                {"index": index, "value": value, "confidence": confidence}
                for index, value, confidence in self.fixed_bits
            ],
            "free_bits": list(self.free_bits),
            "ranked_bits": [
                {"index": index, "score": score, "probability_one": probability}
                for index, score, probability in self.ranked_bits
            ],
        }


@dataclass(frozen=True)
class BitProbability:
    index: int
    score: float
    probability_one: float

    @property
    def confidence(self) -> float:
        return max(self.probability_one, 1.0 - self.probability_one)

    def as_record(self) -> dict:
        return {
            "index": self.index,
            "score": round(self.score, 6),
            "probability_one": round(self.probability_one, 6),
            "confidence": round(self.confidence, 6),
        }


class BitProbabilityModel(Protocol):
    name: str

    def predict_probabilities(self, graph: QuboGraphFeatures) -> tuple[BitProbability, ...]:
        raise NotImplementedError


@dataclass(frozen=True)
class WarmStartPrediction:
    model_name: str
    bit_probabilities: tuple[BitProbability, ...]
    threshold_candidate: tuple[int, ...]
    fixing_plan: VariableFixingPlan

    @property
    def ranked_bits(self) -> tuple[tuple[int, float], ...]:
        return tuple((item.index, item.score) for item in self.bit_probabilities)

    def as_record(self) -> dict:
        return {
            "model_name": self.model_name,
            "bit_probabilities": [item.as_record() for item in self.bit_probabilities],
            "threshold_candidate": list(self.threshold_candidate),
            "variable_fixing_plan": self.fixing_plan.as_record(),
        }


class WarmStartInferencePipeline:
    def __init__(self, model: BitProbabilityModel):
        self.model = model

    def predict(
        self,
        graph: QuboGraphFeatures,
        *,
        confidence_threshold: float = 0.85,
    ) -> WarmStartPrediction:
        probabilities = tuple(
            sorted(
                self.model.predict_probabilities(graph),
                key=lambda item: (-item.score, item.index),
            )
        )
        probability_by_index = {item.index: item.probability_one for item in probabilities}
        threshold_candidate = tuple(
            1 if probability_by_index.get(index, 0.0) >= 0.5 else 0
            for index in range(len(graph.nodes))
        )
        return WarmStartPrediction(
            model_name=getattr(self.model, "name", self.model.__class__.__name__),
            bit_probabilities=probabilities,
            threshold_candidate=threshold_candidate,
            fixing_plan=_fixing_plan_from_probabilities(
                probabilities,
                confidence_threshold=confidence_threshold,
            ),
        )


@dataclass(frozen=True)
class LinearWarmStartPolicy:
    weights: tuple[float, ...] = (-1.0, 0.0, -0.25, -0.05, -0.10, 0.10)
    threshold: float = 0.0
    name: str = "linear_warm_start"

    def __post_init__(self) -> None:
        if len(self.weights) != len(FEATURE_NAMES):
            raise ValueError(f"weights must have {len(FEATURE_NAMES)} entries")

    def score(self, node: QuboNodeFeature) -> float:
        return sum(weight * value for weight, value in zip(self.weights, node.values))

    def rank(self, graph: QuboGraphFeatures) -> tuple[tuple[int, float], ...]:
        scored = [(node.index, self.score(node)) for node in graph.nodes]
        return tuple(sorted(scored, key=lambda item: (-item[1], item[0])))

    def predict_probabilities(self, graph: QuboGraphFeatures) -> tuple[BitProbability, ...]:
        return tuple(
            BitProbability(index=index, score=score, probability_one=_sigmoid(score))
            for index, score in self.rank(graph)
        )

    def probabilities(self, graph: QuboGraphFeatures) -> tuple[tuple[int, float, float], ...]:
        return tuple(
            (item.index, item.score, item.probability_one)
            for item in self.predict_probabilities(graph)
        )

    def threshold_candidate(self, graph: QuboGraphFeatures) -> tuple[int, ...]:
        scores = {index: score for index, score in self.rank(graph)}
        return tuple(1 if scores[index] >= self.threshold else 0 for index in range(len(graph.nodes)))

    def suggest_fixing(
        self,
        graph: QuboGraphFeatures,
        *,
        confidence_threshold: float = 0.85,
    ) -> VariableFixingPlan:
        if not 0.5 < confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in (0.5, 1.0]")

        return _fixing_plan_from_probabilities(
            self.predict_probabilities(graph),
            confidence_threshold=confidence_threshold,
        )


@dataclass(frozen=True)
class LearningGuidedTrainingExample:
    problem_name: str
    label_source: str
    record: dict
    objective_value: float | None
    is_feasible: bool | None
    diagnostics: dict
    warnings: tuple[str, ...] = ()

    def as_record(self) -> dict:
        return {
            "problem_name": self.problem_name,
            "label_source": self.label_source,
            "objective_value": self.objective_value,
            "is_feasible": self.is_feasible,
            "diagnostics": self.diagnostics,
            "warnings": list(self.warnings),
            "qubo_graph": self.record,
        }

    def to_json_line(self) -> str:
        return json.dumps(self.as_record(), ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class LogisticWarmStartModel:
    feature_names: tuple[str, ...] = FEATURE_NAMES
    weights: tuple[float, ...] = (0.0,) * len(FEATURE_NAMES)
    bias: float = 0.0
    feature_means: tuple[float, ...] = (0.0,) * len(FEATURE_NAMES)
    feature_scales: tuple[float, ...] = (1.0,) * len(FEATURE_NAMES)
    name: str = "logistic_warm_start"

    def __post_init__(self) -> None:
        width = len(self.feature_names)
        if len(self.weights) != width:
            raise ValueError("weights must match feature_names")
        if len(self.feature_means) != width or len(self.feature_scales) != width:
            raise ValueError("feature normalization vectors must match feature_names")

    @classmethod
    def fit_training_records(
        cls,
        records: Sequence[dict | LearningGuidedTrainingExample],
        *,
        epochs: int = 60,
        learning_rate: float = 0.05,
        l2: float = 0.0005,
    ) -> "LogisticWarmStartModel":
        rows = _labeled_feature_rows(records)
        if not rows:
            raise ValueError("cannot fit warm-start model without labeled graph records")
        width = len(rows[0][0])
        means = tuple(sum(features[index] for features, _label in rows) / len(rows) for index in range(width))
        scales = []
        for index, mean in enumerate(means):
            variance = sum((features[index] - mean) ** 2 for features, _label in rows) / len(rows)
            scale = sqrt(variance)
            scales.append(scale if scale > 1e-12 else 1.0)

        weights = [0.0] * width
        bias = 0.0
        for _epoch in range(max(1, epochs)):
            for features, label in rows:
                normalized = [
                    (features[index] - means[index]) / scales[index]
                    for index in range(width)
                ]
                score = bias + sum(weight * value for weight, value in zip(weights, normalized))
                probability = _sigmoid(score)
                error = probability - label
                bias -= learning_rate * error
                for index, value in enumerate(normalized):
                    weights[index] -= learning_rate * (error * value + l2 * weights[index])

        return cls(
            weights=tuple(round(weight, 12) for weight in weights),
            bias=round(bias, 12),
            feature_means=tuple(round(value, 12) for value in means),
            feature_scales=tuple(round(value, 12) for value in scales),
        )

    def predict_probabilities(self, graph: QuboGraphFeatures) -> tuple[BitProbability, ...]:
        predictions = []
        for node in graph.nodes:
            normalized = [
                (value - mean) / scale
                for value, mean, scale in zip(node.values, self.feature_means, self.feature_scales)
            ]
            score = self.bias + sum(weight * value for weight, value in zip(self.weights, normalized))
            predictions.append(
                BitProbability(
                    index=node.index,
                    score=score,
                    probability_one=_sigmoid(score),
                )
            )
        return tuple(sorted(predictions, key=lambda item: (-item.score, item.index)))

    def as_record(self) -> dict:
        return {
            "model_type": self.name,
            "feature_names": list(self.feature_names),
            "weights": list(self.weights),
            "bias": self.bias,
            "feature_means": list(self.feature_means),
            "feature_scales": list(self.feature_scales),
        }

    @classmethod
    def from_record(cls, record: dict) -> "LogisticWarmStartModel":
        return cls(
            feature_names=tuple(record.get("feature_names", FEATURE_NAMES)),
            weights=tuple(float(value) for value in record["weights"]),
            bias=float(record.get("bias", 0.0)),
            feature_means=tuple(float(value) for value in record.get("feature_means", (0.0,) * len(FEATURE_NAMES))),
            feature_scales=tuple(float(value) for value in record.get("feature_scales", (1.0,) * len(FEATURE_NAMES))),
            name=str(record.get("model_type", "logistic_warm_start")),
        )


class LearningGuidedDatasetBuilder:
    def __init__(
        self,
        *,
        qubo_builder: QuboBuilder | None = None,
        extractor: QuboGraphFeatureExtractor | None = None,
        label_backend: SamplerBackend | None = None,
        label_config: SamplerConfig | None = None,
    ):
        self.qubo_builder = qubo_builder or QuboBuilder()
        self.extractor = extractor or QuboGraphFeatureExtractor()
        self.label_backend = label_backend or ExactSolverBackend()
        self.label_config = label_config or SamplerConfig(return_top_k=1)

    def build_example(self, problem: OptimizationProblem) -> LearningGuidedTrainingExample:
        model = self.qubo_builder.build(problem)
        label_bitstring: tuple[int, ...] | None = None
        label_source = "unlabeled"
        objective_value: float | None = None
        is_feasible: bool | None = None
        warnings: list[str] = []

        try:
            result = self.label_backend.solve(model, self.label_config)
        except ValueError as exc:
            warnings.append(f"label_backend_skipped:{exc}")
        else:
            sample = result.best_feasible() or result.best_raw_energy_sample
            if sample is not None:
                label_bitstring = sample.bitstring
                label_source = result.backend_name
                objective_value = sample.objective_value
                is_feasible = sample.is_feasible

        return LearningGuidedTrainingExample(
            problem_name=problem.name,
            label_source=label_source,
            record=self.extractor.to_training_record(model, label_bitstring),
            objective_value=objective_value,
            is_feasible=is_feasible,
            diagnostics=model.diagnostics(),
            warnings=tuple(warnings),
        )

    def build(self, problems: Sequence[OptimizationProblem]) -> tuple[LearningGuidedTrainingExample, ...]:
        return tuple(self.build_example(problem) for problem in problems)

    def write_jsonl(
        self,
        problems: Sequence[OptimizationProblem],
        path: str | Path,
    ) -> tuple[LearningGuidedTrainingExample, ...]:
        examples = self.build(problems)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "".join(example.to_json_line() + "\n" for example in examples),
            encoding="utf-8",
        )
        return examples


class LearningGuidedSamplerBackend(SamplerBackend):
    name = "learning_guided"

    def __init__(
        self,
        *,
        extractor: QuboGraphFeatureExtractor | None = None,
        policy: BitProbabilityModel | None = None,
    ):
        self.extractor = extractor or QuboGraphFeatureExtractor()
        self.policy = policy or LinearWarmStartPolicy()
        self.pipeline = WarmStartInferencePipeline(self.policy)

    def sample(self, model: QuboModel, config: SamplerConfig | None = None) -> RawSampleSet:
        started = perf_counter()
        resolved = config or SamplerConfig()
        graph = self.extractor.extract(model)
        prediction = self.pipeline.predict(graph)
        ranked = prediction.ranked_bits
        fixing_plan = prediction.fixing_plan
        policy_candidates = _policy_candidates(
            ranked,
            prediction.threshold_candidate,
            num_variables=model.num_variables,
            max_candidates=max(1, resolved.num_reads),
            fixing_plan=fixing_plan,
        )
        logical_candidates = _logical_greedy_candidates(
            model,
            ranked,
            max_candidates=max(1, resolved.num_reads),
        )
        candidates = _dedupe_candidates([*logical_candidates, *policy_candidates])[: max(1, resolved.num_reads)]
        improved = [
            _local_improve(model, candidate, max_sweeps=max(0, resolved.num_sweeps))
            for candidate in candidates
        ]
        return RawSampleSet.from_samples(
            improved,
            source_backend=self.name,
            energy_fn=model.energy,
            timing={"sample_ms": (perf_counter() - started) * 1000.0},
            backend_metadata={
                "feature_names": list(graph.feature_names),
                "num_edges": len(graph.edges),
                "policy": prediction.model_name,
                "candidate_count": len(candidates),
                "logical_candidate_count": len(logical_candidates),
                "ml_role": "warm_start_variable_ranking",
                "warm_start_prediction": prediction.as_record(),
                "variable_fixing_plan": fixing_plan.as_record(),
            },
        )


def _policy_candidates(
    ranked: tuple[tuple[int, float], ...],
    threshold_candidate: tuple[int, ...],
    *,
    num_variables: int,
    max_candidates: int,
    fixing_plan: VariableFixingPlan | None = None,
) -> list[tuple[int, ...]]:
    candidates: list[tuple[int, ...]] = []

    def add(candidate: Iterable[int]) -> None:
        bitstring = tuple(int(bit) for bit in candidate)
        if bitstring not in candidates:
            candidates.append(bitstring)

    add([0] * num_variables)
    add(threshold_candidate)
    if fixing_plan is not None:
        add(_candidate_from_fixed_bits(num_variables, fixing_plan.fixed_assignment))
    for selected_count in range(1, num_variables + 1):
        bitstring = [0] * num_variables
        for index, _score in ranked[:selected_count]:
            bitstring[index] = 1
        if fixing_plan is not None:
            for index, value in fixing_plan.fixed_assignment.items():
                bitstring[index] = value
        add(bitstring)
        if len(candidates) >= max_candidates:
            break
    if len(candidates) < max_candidates:
        add([1] * num_variables)
    return candidates[:max_candidates]


def _logical_greedy_candidates(
    model: QuboModel,
    ranked: tuple[tuple[int, float], ...],
    *,
    max_candidates: int,
) -> list[tuple[int, ...]]:
    logical_binary_names = [
        name
        for name, spec in model.problem.variables.items()
        if spec.kind == "binary"
    ]
    if not logical_binary_names:
        return []

    one_hot_groups = _one_hot_groups(model)
    grouped = {name for group in one_hot_groups for name in group}
    free_binary_names = [name for name in logical_binary_names if name not in grouped]
    score_by_name = _score_by_logical_name(model, ranked)
    free_binary_names.sort(key=lambda name: (-score_by_name.get(name, 0.0), name))

    candidates: list[tuple[int, ...]] = []
    for assignment in _base_logical_assignments(model, one_hot_groups):
        add_logical_candidate(model, candidates, assignment)
        current = dict(assignment)
        current_objective = model.problem.evaluate_objective(current)
        for name in free_binary_names:
            if current.get(name, 0) == 1:
                continue
            trial = dict(current)
            trial[name] = 1
            if not model.check_constraints(trial).is_feasible:
                continue
            trial_objective = model.problem.evaluate_objective(trial)
            if _objective_improves(trial_objective, current_objective, model.problem.sense):
                current = trial
                current_objective = trial_objective
                add_logical_candidate(model, candidates, current)
        if len(candidates) >= max_candidates:
            break
    return candidates[:max_candidates]


def add_logical_candidate(
    model: QuboModel,
    candidates: list[tuple[int, ...]],
    logical_assignment: dict[str, int],
) -> None:
    bitstring = model.bitstring_from_logical(logical_assignment)
    if bitstring not in candidates:
        candidates.append(bitstring)


def _base_logical_assignments(
    model: QuboModel,
    one_hot_groups: tuple[tuple[str, ...], ...],
) -> Iterable[dict[str, int]]:
    lower_bound_assignment = {
        name: int(model.problem.variable_bounds(name)[0])
        for name in model.problem.variables
    }
    for name, spec in model.problem.variables.items():
        if spec.kind == "binary":
            lower_bound_assignment[name] = 0

    if not one_hot_groups:
        yield lower_bound_assignment
        return

    for choices in product(*one_hot_groups):
        assignment = dict(lower_bound_assignment)
        for group in one_hot_groups:
            for name in group:
                assignment[name] = 0
        for name in choices:
            assignment[name] = 1
        yield assignment


def _one_hot_groups(model: QuboModel) -> tuple[tuple[str, ...], ...]:
    groups: list[tuple[str, ...]] = []
    for constraint in model.problem.constraints:
        if (
            constraint.constraint_type == "exactly_one"
            and constraint.sense == "=="
            and abs(constraint.rhs - 1.0) <= 1e-9
            and all(abs(value - 1.0) <= 1e-9 for value in constraint.linear.values())
        ):
            groups.append(tuple(constraint.linear))
    return tuple(groups)


def _score_by_logical_name(
    model: QuboModel,
    ranked: tuple[tuple[int, float], ...],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for index, score in ranked:
        logical_name = model.registry.bits[index].logical_name
        if logical_name is not None:
            scores[logical_name] = max(score, scores.get(logical_name, score))
    return scores


def _objective_improves(next_value: float, current_value: float, sense: str) -> bool:
    if sense == "maximize":
        return next_value > current_value + 1e-9
    return next_value < current_value - 1e-9


def _dedupe_candidates(candidates: Iterable[tuple[int, ...]]) -> list[tuple[int, ...]]:
    deduped: list[tuple[int, ...]] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _local_improve(model: QuboModel, bitstring: tuple[int, ...], *, max_sweeps: int) -> tuple[int, ...]:
    state = list(bitstring)
    current_energy = model.energy(state)
    for _sweep in range(max_sweeps):
        improved = False
        for index in range(model.num_variables):
            state[index] = 1 - state[index]
            next_energy = model.energy(state)
            if next_energy < current_energy:
                current_energy = next_energy
                improved = True
            else:
                state[index] = 1 - state[index]
        if not improved:
            break
    return tuple(state)


def _candidate_from_fixed_bits(num_variables: int, fixed_assignment: dict[int, int]) -> tuple[int, ...]:
    bitstring = [0] * num_variables
    for index, value in fixed_assignment.items():
        bitstring[index] = value
    return tuple(bitstring)


def _fixing_plan_from_probabilities(
    probabilities: Iterable[BitProbability],
    *,
    confidence_threshold: float,
) -> VariableFixingPlan:
    if not 0.5 < confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be in (0.5, 1.0]")
    fixed: list[tuple[int, int, float]] = []
    free: list[int] = []
    ranked_bits: list[tuple[int, float, float]] = []
    for item in probabilities:
        confidence = item.confidence
        if confidence >= confidence_threshold:
            fixed.append((item.index, 1 if item.probability_one >= 0.5 else 0, round(confidence, 6)))
        else:
            free.append(item.index)
        ranked_bits.append((item.index, round(item.score, 6), round(item.probability_one, 6)))
    return VariableFixingPlan(
        fixed_bits=tuple(fixed),
        free_bits=tuple(free),
        ranked_bits=tuple(ranked_bits),
        confidence_threshold=confidence_threshold,
    )


def _labeled_feature_rows(
    records: Sequence[dict | LearningGuidedTrainingExample],
) -> list[tuple[tuple[float, ...], int]]:
    rows: list[tuple[tuple[float, ...], int]] = []
    for record in records:
        payload = record.as_record() if isinstance(record, LearningGuidedTrainingExample) else record
        graph = payload.get("qubo_graph", payload)
        labels = graph.get("labels")
        nodes = graph.get("node_features", [])
        if labels is None or len(labels) != len(nodes):
            continue
        for node, label in zip(nodes, labels):
            features = tuple(float(value) for value in node["features"])
            rows.append((features, int(label)))
    return rows


def _sigmoid(value: float) -> float:
    if value >= 50:
        return 1.0
    if value <= -50:
        return 0.0
    return 1.0 / (1.0 + exp(-value))
