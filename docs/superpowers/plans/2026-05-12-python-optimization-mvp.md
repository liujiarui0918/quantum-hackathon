# Python Optimization MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python optimization framework with runnable footholds for all six requirement routes.

**Architecture:** `modeling` compiles logical optimization problems into `QuboModel`; `constraints` handles compiler plans, repair, sweeps, and feasible-subspace metadata; `solvers` consume QUBOs and return ranked decoded samples; `solvers.qaoa` and `solvers.constrained_qaoa` cover local quantum algorithm demos; `hybrid` covers mixed binary/continuous scaffolding; `benchmarks` compares backends across toy cases. Cloud quantum backends are deliberately optional follow-ups.

**Tech Stack:** Python 3.12, standard library, pytest, setuptools editable install.

---

### Task 1: Project Skeleton And Red Tests

**Files:**
- Create: `pyproject.toml`
- Modify: `.gitignore`
- Create: `tests/test_modeling_qubo.py`
- Create: `tests/test_constraints_postprocess.py`
- Create: `tests/test_solvers_and_benchmarks.py`

- [x] Add Python packaging metadata with `src` layout and pytest config.
- [x] Ignore `.venv`, Python caches, and editable-install metadata.
- [x] Write failing tests for modeling, constraints, solvers, and benchmark behavior.
- [x] Run `.\.venv\Scripts\python.exe -m pytest` and confirm failure is caused by missing public API.

### Task 2: Modeling Core

**Files:**
- Create: `src/quantum_hackathon/modeling/problem.py`
- Create: `src/quantum_hackathon/modeling/variables.py`
- Create: `src/quantum_hackathon/modeling/expressions.py`
- Create: `src/quantum_hackathon/modeling/qubo.py`
- Create: `src/quantum_hackathon/modeling/verify.py`
- Create: `src/quantum_hackathon/modeling/__init__.py`

- [x] Implement `OptimizationProblem`, variable specs, and constraint specs.
- [x] Implement linear and quadratic expression helpers with canonical sparse keys.
- [x] Implement variable registry for binary, bounded integer, slack, and auxiliary bits.
- [x] Implement `QuboBuilder`, `QuboModel`, decode, diagnostics, Ising conversion, and brute-force helper.
- [x] Run modeling tests and fix failures.

### Task 3: Solver And Postprocessing Layer

**Files:**
- Create: `src/quantum_hackathon/solvers/base.py`
- Create: `src/quantum_hackathon/solvers/postprocess.py`
- Create: `src/quantum_hackathon/solvers/exact.py`
- Create: `src/quantum_hackathon/solvers/random.py`
- Create: `src/quantum_hackathon/solvers/simulated_annealing.py`
- Create: `src/quantum_hackathon/solvers/__init__.py`

- [x] Implement `SamplerConfig`, `RawSampleSet`, `SolverResult`, and backend interface.
- [x] Implement feasibility-first `SolutionPostprocessor`.
- [x] Implement exact enumeration with a 25-bit default safety threshold.
- [x] Implement seed-reproducible random sampling.
- [x] Implement local simulated annealing using a geometric beta schedule.
- [x] Run solver tests and fix failures.

### Task 4: Benchmarks And Public API

**Files:**
- Create: `src/quantum_hackathon/benchmarks/cases.py`
- Create: `src/quantum_hackathon/benchmarks/runner.py`
- Create: `src/quantum_hackathon/benchmarks/__init__.py`
- Create: `src/quantum_hackathon/__init__.py`

- [x] Add exactly-one and small knapsack toy cases.
- [x] Implement `AnnealingBenchmarkRunner` and `BenchmarkReport`.
- [x] Export public MVP API from package root.
- [x] Run all tests.

### Task 5: Verification And Review

**Files:**
- Review all new Python source and tests.

- [x] Run full pytest suite after documentation changes.
- [x] Inspect `git diff --stat` and `git status --short`.
- [x] Perform code review focused on correctness, API consistency, and missing tests.
- [x] Fix blocking findings and rerun tests.

### Task 6: Route 2 Constraint Quality Layer

**Files:**
- Create: `src/quantum_hackathon/constraints/specs.py`
- Create: `src/quantum_hackathon/constraints/compiler.py`
- Create: `src/quantum_hackathon/constraints/repair.py`
- Create: `src/quantum_hackathon/constraints/sweep.py`
- Create: `src/quantum_hackathon/constraints/__init__.py`
- Create: `tests/test_constraint_route.py`

- [x] Implement compiler plans and feasible-subspace metadata export.
- [x] Implement unbalanced inequality compilation without slack.
- [x] Implement at-most-one, one-hot, and cardinality repair helpers.
- [x] Implement penalty sweep metrics and recommended weight selection.
- [x] Run route-specific tests.

### Task 7: Route 4 QAOA/VQA Local Simulator

**Files:**
- Create: `src/quantum_hackathon/solvers/qaoa/*`
- Create: `tests/test_qaoa_route.py`

- [x] Implement cost Hamiltonian builder with QUBO energy equivalence.
- [x] Implement statevector and shot simulator backends.
- [x] Implement simple p=1 optimizer and initializers.
- [x] Implement `QaoaRunner` with postprocessed samples.
- [x] Run route-specific tests.

### Task 8: Route 5 Constrained Mixer/Warm-Start Metadata

**Files:**
- Create: `src/quantum_hackathon/solvers/constrained_qaoa/*`
- Create: `tests/test_constrained_qaoa_route.py`

- [x] Implement feasible subspace, initial state, mixer metadata, warm-start probability handling, and recursive reduction metadata.
- [x] Implement constrained runner fallback using exact QUBO solve for local demo.
- [x] Run route-specific tests.

### Task 9: Route 6 Hybrid MILP/MIQP Scaffold

**Files:**
- Create: `src/quantum_hackathon/hybrid/*`
- Create: `tests/test_hybrid_route.py`

- [x] Implement hybrid problem model, decomposition, relaxation heuristic, rounding, and relax-round-repair.
- [x] Implement warm-start metadata output and fix-and-optimize skeleton.
- [x] Run route-specific tests.

### Task 10: Six-Route Integration

**Files:**
- Modify: `src/quantum_hackathon/__init__.py`
- Modify: `src/quantum_hackathon/solvers/__init__.py`
- Create: `tests/test_six_routes_integration.py`

- [x] Export key public APIs for all routes.
- [x] Add a single integration test touching routes 1-6.
- [x] Run full pytest suite.
