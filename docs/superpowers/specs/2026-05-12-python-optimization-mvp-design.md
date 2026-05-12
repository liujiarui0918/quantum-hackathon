# Python Optimization MVP Design

## Scope

Build a local Python MVP for the hackathon optimization track. The implementation covers runnable local footholds for all six requirement routes:

- generic `OptimizationProblem` modeling for binary and bounded integer variables
- sparse QUBO construction with equality and inequality penalty support
- binary slack variables for inequalities
- high-order binary monomial quadratization through AND auxiliaries
- QUBO energy evaluation, logical decode, feasibility checking, and diagnostics
- QUBO to Ising conversion with energy equivalence
- constraint compiler plans, feasible-subspace metadata, unbalanced inequality strategy, basic repair, and penalty sweep
- exact, random, and simulated annealing solver backends
- feasibility-first sample postprocessing
- local statevector and shot-based QAOA simulator
- constrained QAOA metadata, one-hot/fixed-Hamming-weight XY mixer diagnostics, warm-start probabilities, and recursive reduction metadata
- hybrid MILP/MIQP scaffold with decomposition, relaxation, rounding, and relax-round-repair
- toy benchmark cases and benchmark metrics

D-Wave, IBM Quantum, Qiskit/Aer, real hardware transpilation, and production-grade continuous solvers are intentionally optional follow-ups. The package remains runnable without cloud credentials.

## Architecture

The package lives under `src/quantum_hackathon`.

`modeling` owns problem representation, encoded variables, expressions, QUBO compilation, Ising conversion, decode, feasibility checks, and brute-force verification. It does not call solver algorithms except through the small `brute_force_solve` helper.

`solvers` owns backend interfaces, raw sample representation, postprocessing, exact enumeration, random sampling, and local simulated annealing. Solvers consume `QuboModel`; they do not know business-level modeling details.

`constraints` owns compiler plans, feasible-subspace metadata export, unbalanced penalty compilation, basic repair, and penalty sweep utilities.

`solvers.qaoa` owns a small local QAOA simulator and optimizer layer.

`solvers.constrained_qaoa` owns constrained mixer metadata, warm-start probability handling, constrained-runner fallback, and recursive reduction metadata.

`hybrid` owns mixed binary/continuous problem scaffolding, decomposition, relaxation, rounding, and relax-round-repair.

`benchmarks` owns toy problem factories and a runner that builds QUBOs, executes multiple backends, and emits comparable metrics.

## Data Flow

1. User creates an `OptimizationProblem`.
2. `QuboBuilder` encodes variables, compiles objectives and constraints, and returns a `QuboModel`.
3. A solver backend samples bitstrings from the QUBO.
4. `SolutionPostprocessor` decodes samples, recomputes original objective values, checks constraints, and ranks feasible samples first.
5. `AnnealingBenchmarkRunner` repeats this flow over problem suites and backends.

## Local Simulation Versus Quantum Cloud

The P0 implementation does not require a quantum cloud account. `ExactSolverBackend` is a small-scale correctness oracle, `RandomSamplerBackend` is a sanity baseline, and `SimulatedAnnealingBackend` is a local classical heuristic for QUBO sampling.

Quantum cloud integrations should be optional adapters added later:

- D-Wave Ocean adapter for quantum annealing and hybrid BQM solvers
- Qiskit/Aer local simulator for QAOA
- IBM Quantum hardware adapter when credentials are available

The core pipeline must remain runnable without those services.

## Testing

The initial suite verifies:

- exactly-one QUBO optimum matches the original logical optimum
- bounded integer encoding and inequality slack compile correctly
- QUBO and Ising energies are equivalent over all bitstrings
- cubic binary monomials are quadratized with hidden auxiliary variables
- feasibility checks report lhs, violation, and satisfaction
- postprocessing ranks feasible samples ahead of lower-energy infeasible samples
- exact, random, simulated annealing, and benchmark APIs work

## Known Limits

- Inequalities use binary slack only; unbalanced penalties are follow-up work.
- High-order quadratization currently supports direct binary-variable monomials.
- Exact enumeration refuses models larger than 25 binary variables.
- Simulated annealing is a simple local implementation, not a tuned industrial solver.
