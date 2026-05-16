# Learning-Guided Pretraining Preparation Design

## Background

The hackathon server exposes four 64 GB MetaX C500X GPUs and a `qiskit` container with `qiskit-aer` GPU support. The final problem data is not available yet, so tonight's work should not assume the final distribution. The useful preparation is to build a complete learning-guided optimization pipeline that can consume either synthetic problems tonight or real task instances tomorrow.

The current route 7 implementation already exports QUBO graph features and uses a hand-written linear warm-start policy. It needs to grow into a data and model pipeline:

```text
synthetic or real optimization problem
-> QUBO model
-> QUBO graph training record
-> exact / annealing / hybrid label
-> trainable or external warm-start model
-> bit probabilities
-> variable ranking
-> fixing plan and candidate generation
-> route 7 sampler
```

This document defines the development requirements for that pipeline.

## Goals

1. Generate synthetic optimization instances that are close enough to likely hackathon structures to exercise the seven algorithm routes.
2. Build QUBO graph datasets with labels produced by exact enumeration for small cases and heuristic solvers for medium cases.
3. Include hybrid MILP/MIQP-style samples where binary warm-start labels come from the hybrid relax-round-repair route.
4. Replace the hard-coded route 7 policy dependency with a pluggable warm-start model interface.
5. Provide a dependency-free baseline model that can be trained tonight and swapped for a GPU neural model later.
6. Provide a CLI that writes JSONL datasets, a summary JSON, and a serialized warm-start model.
7. Keep the core pipeline runnable without PyTorch, TensorFlow, JAX, or Paddle, because the current container does not include those packages.

## Non-Goals

- Do not install or require a deep learning framework tonight.
- Do not claim the synthetic model is final competition performance.
- Do not run long GPU training jobs before the final task distribution is known.
- Do not couple route 7 to one neural network implementation.
- Do not mutate remote system configuration outside `/qiskit/quantum-hackathon`.

## Synthetic Problem Families

The generator should cover multiple QUBO graph shapes and constraint patterns so the model sees more than one toy distribution.

### 1. One-Hot Selection

Purpose: assignment-style decisions, route 2 feasible subspace metadata, route 5 constrained mixer preparation.

Structure:

- Binary variables `sel_{group}_{choice}`.
- Exactly one choice per group.
- Linear profit/cost terms.
- Optional quadratic conflict or synergy between choices from adjacent groups.

Expected labels:

- Small cases: exact solver.
- Medium cases: simulated annealing if encoded QUBO exceeds exact threshold.

### 2. Knapsack / Bounded Sum

Purpose: inequality penalties, slack-bit behavior, annealing baseline.

Structure:

- Binary item variables.
- Maximize profit under capacity, represented as minimize negative profit.
- `sum(weight_i * x_i) <= capacity`.

Expected labels:

- Small cases: exact solver.
- Medium cases: simulated annealing.

### 3. Portfolio-Style Selection

Purpose: quadratic risk terms plus cardinality/budget constraints.

Structure:

- Binary asset variables.
- Objective combines return and pairwise risk/correlation.
- Constraint `sum(x_i) == k` or `sum(cost_i * x_i) <= budget`.

Expected labels:

- Exact for small asset counts.
- Simulated annealing for medium asset counts.

### 4. Unit Commitment / Dispatch Skeleton

Purpose: power-domain binary commitment structure before real data arrives.

Structure:

- Binary `on_{unit}_{period}` variables.
- Per-period demand constraints `sum(capacity_u * on_{u,t}) >= demand_t`.
- Linear operating costs and optional switching quadratic terms.

Expected labels:

- Mostly annealing for medium cases because demand inequalities create slack bits.

### 5. Production / Scheduling Assignment

Purpose: machine and time assignment patterns.

Structure:

- Binary `job_{job}_slot_{slot}` variables.
- Exactly one slot per job.
- Slot capacity constraints.
- Quadratic conflict penalties for incompatible adjacent jobs or shared resources.

Expected labels:

- Exact for small cases.
- Annealing for medium cases.

### 6. Unconstrained Graph Cut / Conflict Partition

Purpose: dense pure-QUBO graph shape without constraint slack.

Structure:

- Binary partition variables.
- Objective minimizes the negative cut value.
- Quadratic couplers encode graph edge weights.

Expected labels:

- Exact for small graphs.
- Annealing for medium graphs.

### 7. Hybrid Linked Dispatch Samples

Purpose: route 6 output as warm-start labels for binary open/close variables.

Structure:

- Binary open variables.
- Continuous flow/dispatch variables.
- Linking constraints `flow <= capacity * open`.
- Demand constraints.

Expected labels:

- Use `HybridOptimizer(strategy="relax_round_repair")`.
- Export binary labels for the companion binary QUBO graph.
- Label source should be `hybrid_relax_round_repair`.

## Dataset Schema

Each JSONL row should use the existing `LearningGuidedTrainingExample` shape:

```json
{
  "problem_name": "synthetic_knapsack_0001",
  "label_source": "exact",
  "objective_value": -21.0,
  "is_feasible": true,
  "diagnostics": {
    "logical_variables": 8,
    "encoded_bits": 12,
    "quadratic_couplers": 18
  },
  "warnings": [],
  "qubo_graph": {
    "num_nodes": 12,
    "feature_names": ["linear_bias", "..."],
    "node_features": [
      {
        "index": 0,
        "name": "x0",
        "kind": "binary",
        "source": "logical:x0",
        "logical_name": "x0",
        "features": [1.0, 2.0, 0.5]
      }
    ],
    "edges": [
      {"source": 0, "target": 1, "coefficient": 2.0}
    ],
    "labels": [1, 0, 1]
  }
}
```

Summary JSON should include:

- number of examples
- counts by family
- counts by label source
- min/max/average QUBO bit count
- output paths
- training model metadata
- warnings

## Label Selection Policy

For ordinary `OptimizationProblem` samples:

1. Build QUBO using `QuboBuilder`.
2. If `model.num_variables <= exact_max_bits`, label with `ExactSolverBackend`.
3. Otherwise label with `SimulatedAnnealingBackend`.
4. If exact refuses or another solver fails, fall back to annealing and record a warning.
5. Keep labels even if heuristic labels are not globally optimal; source metadata must be honest.

For `HybridOptimizationProblem` samples:

1. Solve with `HybridOptimizer`.
2. Extract binary variable assignments.
3. Build a companion binary-only `OptimizationProblem`.
4. Convert that companion problem into a QUBO graph.
5. Use the hybrid binary solution as the label bitstring.

## Warm-Start Model Interface

Route 7 should depend on a small model protocol, not a concrete class.

Required behavior:

```text
model.predict_probabilities(graph) -> per-bit probability_one records
```

The inference pipeline should then derive:

- `bit_probabilities`
- ranked bits by confidence / probability
- threshold candidate
- `VariableFixingPlan`

This makes three implementations possible:

1. Current rule-based `LinearWarmStartPolicy`.
2. Dependency-free trainable logistic baseline.
3. Future GNN/RL model backed by PyTorch or another MetaX-compatible framework.

## Dependency-Free Baseline Model

Tonight's baseline should be a small logistic model trained on node features:

- Input: per-node QUBO graph features.
- Output: probability that the corresponding bit is `1`.
- Training: deterministic batch or online logistic regression in pure Python.
- Serialization: JSON file with feature names, weights, bias, feature means, and scales.

This is intentionally not the final neural network. Its value is to prove the training, serialization, inference, ranking, and fixing-plan path.

## CLI Requirements

Add a CLI entry point:

```bash
python -m quantum_hackathon.pretraining_cli \
  --output data/pretraining/qubo_graphs.jsonl \
  --summary data/pretraining/summary.json \
  --model-output data/pretraining/warm_start_model.json \
  --small-per-family 2 \
  --medium-per-family 2 \
  --hybrid-count 2 \
  --seed 7
```

The CLI should:

1. Generate synthetic ordinary and hybrid samples.
2. Label them.
3. Write JSONL records.
4. Train the dependency-free warm-start model when labeled records exist.
5. Write model JSON.
6. Write summary JSON.
7. Print a compact completion summary.

## Acceptance Criteria

- Synthetic generation is deterministic for a fixed seed.
- At least six ordinary families and one hybrid family can be generated.
- Dataset builder writes valid JSONL records with labels.
- Label sources include exact and simulated annealing when sizes cross the exact threshold.
- Hybrid examples produce `hybrid_relax_round_repair` labels.
- Route 7 can run with the default linear policy and with the trained logistic model interface.
- CLI writes dataset, summary, and model files.
- Full pytest suite passes locally and inside the `qiskit` container.
- Remote server implementation lands under `/qiskit/quantum-hackathon`.

## Operational Plan For Tonight

1. Implement the synthetic generators.
2. Implement the pretraining dataset builder and hybrid companion labeling.
3. Add the warm-start model protocol and inference pipeline.
4. Add logistic baseline training and JSON serialization.
5. Add CLI and tests.
6. Upload to the `qiskit` container.
7. Run the CLI with a small count to prove end-to-end output.
8. Run pytest remotely.

## Tomorrow's Real-Data Plan

When the final problem arrives:

1. Write an importer from the real problem format into `OptimizationProblem` or `HybridOptimizationProblem`.
2. Compare real QUBO diagnostics to synthetic distributions.
3. Generate synthetic neighbors around the real dimensions and constraints.
4. Relabel small/medium variants using exact, annealing, QAOA, and hybrid routes.
5. Retrain or fine-tune the warm-start model.
6. Use its bit probabilities for variable fixing, QAOA warm-start states, and annealing candidate seeds.
7. Benchmark against exact where possible and against annealing/hybrid on larger cases.
