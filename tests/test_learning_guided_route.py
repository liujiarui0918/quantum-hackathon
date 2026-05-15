from quantum_hackathon import (
    LearningGuidedDatasetBuilder,
    LearningGuidedSamplerBackend,
    LinearWarmStartPolicy,
    QuboBuilder,
    QuboGraphFeatureExtractor,
    SamplerConfig,
)
from quantum_hackathon.benchmarks.cases import exactly_one_selection


def test_qubo_graph_feature_extractor_exports_training_record_schema():
    model = QuboBuilder().build(exactly_one_selection())

    record = QuboGraphFeatureExtractor().to_training_record(model, label_bitstring=(1, 0, 0))

    assert record["num_nodes"] == model.num_variables
    assert record["feature_names"] == [
        "linear_bias",
        "degree",
        "coupling_sum",
        "abs_coupling_sum",
        "positive_coupling_sum",
        "negative_coupling_sum",
    ]
    assert len(record["node_features"]) == model.num_variables
    assert record["labels"] == [1, 0, 0]
    assert any(edge["coefficient"] > 0 for edge in record["edges"])


def test_linear_policy_exports_variable_fixing_plan():
    model = QuboBuilder().build(exactly_one_selection())
    graph = QuboGraphFeatureExtractor().extract(model)

    plan = LinearWarmStartPolicy().suggest_fixing(graph, confidence_threshold=0.55)

    assert plan.confidence_threshold == 0.55
    assert plan.fixed_assignment
    assert set(plan.fixed_assignment).issubset(set(range(model.num_variables)))
    assert plan.as_record()["ranked_bits"][0]["index"] in range(model.num_variables)


def test_dataset_builder_writes_labeled_jsonl(tmp_path):
    target = tmp_path / "learning_guided.jsonl"

    examples = LearningGuidedDatasetBuilder().write_jsonl([exactly_one_selection()], target)

    assert len(examples) == 1
    assert examples[0].label_source == "exact"
    assert examples[0].record["labels"] == [1, 0, 0]
    text = target.read_text(encoding="utf-8")
    assert '"qubo_graph"' in text


def test_learning_guided_sampler_uses_policy_candidates_and_local_improvement():
    model = QuboBuilder().build(exactly_one_selection())

    result = LearningGuidedSamplerBackend().solve(
        model,
        SamplerConfig(seed=3, num_reads=8, num_sweeps=5, return_top_k=8),
    )

    best = result.best_feasible()
    assert best is not None
    assert best.logical_solution == {"x0": 1, "x1": 0, "x2": 0}
    assert result.backend_name == "learning_guided"
    assert result.diagnostics["raw_sample_count"] >= 1
    assert result.config.num_reads == 8
    assert "variable_fixing_plan" in result.diagnostics
