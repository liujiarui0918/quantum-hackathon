import json
from pathlib import Path
from tempfile import TemporaryDirectory

from quantum_hackathon import (
    LearningGuidedSamplerBackend,
    LogisticWarmStartModel,
    PretrainingDatasetBuilder,
    QuboGraphFeatureExtractor,
    QuboBuilder,
    SamplerConfig,
    SyntheticProblemGenerator,
    WarmStartInferencePipeline,
)
from quantum_hackathon.pretraining_cli import main as pretraining_main


def test_synthetic_problem_generator_is_deterministic_and_covers_expected_families():
    first = SyntheticProblemGenerator(seed=11).generate_suite(
        small_per_family=1,
        medium_per_family=1,
        hybrid_count=1,
    )
    second = SyntheticProblemGenerator(seed=11).generate_suite(
        small_per_family=1,
        medium_per_family=1,
        hybrid_count=1,
    )

    assert [(spec.family, spec.size, spec.problem.name, spec.metadata) for spec in first] == [
        (spec.family, spec.size, spec.problem.name, spec.metadata) for spec in second
    ]
    assert {spec.family for spec in first} == {
        "one_hot_selection",
        "knapsack",
        "portfolio",
        "unit_commitment",
        "scheduling_assignment",
        "graph_cut",
        "hybrid_dispatch",
    }


def test_pretraining_dataset_builder_labels_exact_annealing_and_hybrid_examples():
    specs = SyntheticProblemGenerator(seed=3).generate_suite(
        small_per_family=1,
        medium_per_family=1,
        hybrid_count=1,
    )
    build = PretrainingDatasetBuilder(
        exact_max_bits=8,
        annealing_config=SamplerConfig(seed=3, num_reads=8, num_sweeps=8),
    ).build(specs)

    label_sources = {example.label_source for example in build.examples}
    assert "exact" in label_sources
    assert "simulated_annealing" in label_sources
    assert "hybrid_relax_round_repair" in label_sources
    assert build.summary["families"]["hybrid_dispatch"] == 1
    assert all(example.record["labels"] is not None for example in build.examples)


def test_logistic_warm_start_model_plugs_into_route_7_sampler():
    specs = SyntheticProblemGenerator(seed=5).generate_suite(
        small_per_family=1,
        medium_per_family=0,
        hybrid_count=0,
    )
    build = PretrainingDatasetBuilder(
        exact_max_bits=12,
        annealing_config=SamplerConfig(seed=5, num_reads=6, num_sweeps=6),
    ).build(specs)
    warm_start_model = LogisticWarmStartModel.fit_training_records(
        build.examples,
        epochs=5,
        learning_rate=0.03,
    )
    target_problem = specs[0].problem
    qubo_model = QuboBuilder().build(target_problem)

    graph = QuboGraphFeatureExtractor().extract(qubo_model)
    prediction = WarmStartInferencePipeline(warm_start_model).predict(graph)
    assert len(prediction.bit_probabilities) == qubo_model.num_variables
    assert len(prediction.threshold_candidate) == qubo_model.num_variables

    result = LearningGuidedSamplerBackend(policy=warm_start_model).solve(
        qubo_model,
        SamplerConfig(seed=5, num_reads=6, num_sweeps=4),
    )
    assert result.best_raw_energy_sample is not None
    assert result.diagnostics["policy"] == "logistic_warm_start"


def test_pretraining_cli_writes_dataset_summary_and_model():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        dataset = root / "graphs.jsonl"
        summary = root / "summary.json"
        model = root / "model.json"

        exit_code = pretraining_main(
            [
                "--output",
                str(dataset),
                "--summary",
                str(summary),
                "--model-output",
                str(model),
                "--small-per-family",
                "1",
                "--medium-per-family",
                "0",
                "--hybrid-count",
                "1",
                "--annealing-reads",
                "4",
                "--annealing-sweeps",
                "4",
                "--epochs",
                "3",
                "--seed",
                "13",
            ]
        )

        assert exit_code == 0
        assert dataset.exists()
        assert summary.exists()
        assert model.exists()
        summary_payload = json.loads(summary.read_text(encoding="utf-8"))
        model_payload = json.loads(model.read_text(encoding="utf-8"))
        assert summary_payload["num_examples"] == 7
        assert summary_payload["families"]["hybrid_dispatch"] == 1
        assert model_payload["model_type"] == "logistic_warm_start"
        assert len(dataset.read_text(encoding="utf-8").splitlines()) == 7
