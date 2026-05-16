# MIQP-Aware Route 7 Plan

## Goal

Upgrade route 7 from a generic learning-guided QUBO warm-start path into an MIQP-aware coordinator that understands the official competition data format:

```text
maximize x^T Q x + c^T x + h^T y
subject to A x + G y <= b
           B x <= b'
           x in {0,1}^n, y >= 0
```

The new route should not try to solve the whole instance as one giant QUBO. Instead it should:

1. Identify a strong binary block.
2. Generate a warm start for that block.
3. Solve the continuous subproblem for a fixed binary assignment.
4. Produce cut advice from the continuous dual / feasibility residuals.
5. Iterate over blocks while keeping every quantum call under the 30-qubit cap and ideally under the 20-bit comfort zone.

## Why This Change

The current generic route 7 is good for:

- QUBO graph feature extraction
- binary warm-start ranking
- candidate generation
- local improvement
- pretraining data generation

But the official MIQP problems are structurally different:

- They include continuous variables that should not be force-encoded into a giant binary space unless the instance is tiny.
- The dense `Q` matrix and the `A/G` coupling make naive whole-problem QUBO conversion scale badly.
- The sample instances already show a 15/5 and 80/20 split, and the hidden test instances scale up to 150/50.

The best path is a hybrid coordinator:

- classical continuous reasoning
- quantum or heuristic search only on a selected binary block
- Benders-like cut advice to guide the next block

## Observed Problem Structure

From the provided samples:

- The true objective is maximization, despite the wording glitch in the document.
- The objective value matches `x^T Q x + c^T x + h^T y`.
- `Q` is dense.
- `A` is dense and negative-valued in the samples.
- `G` is dense and positive-valued in the samples.
- `B` rows look like selection/cardinality style constraints with 0/1 coefficients.

This strongly suggests:

- binary decisions dominate the combinatorial part
- continuous variables are best handled as a linear subproblem after fixing `x`
- route 7 should focus on block selection, warm starts, and cuts rather than full encoding

## Proposed Architecture

### 1. MIQP Import Layer

Read official `.npz` files into a typed instance object containing:

- dimensions `n, p, m1, m2`
- `Q, c, h, A, G, b, B, b_prime`
- optional sample metadata such as `optimal_value`, `x_opt`, `y_opt`

Responsibilities:

- validate shapes
- enforce symmetry of `Q` when needed
- retain original arrays for reporting and diagnostics
- expose derived metadata: density, coefficient ranges, constraint norms

### 2. Binary Block Selector

Choose a binary block of size at most 20 by default, with a hard cap below 30.

Scoring inputs:

- absolute row/column mass from `Q`
- participation in tight binary constraints `B`
- participation in mixed constraints `A`
- marginal objective weight `c`
- coupling to nearby variables with heavy `Q` or `B` overlap

Selection strategy:

- rank variables by a composite score
- grow a block greedily from the highest-scoring seed
- add strong neighbors first
- stop when the block hits the size cap
- keep a frontier of adjacent variables for the next iteration

Desired output:

- selected binary indices
- frontier binary indices
- block score
- rationale / feature summary

### 3. Warm-Start Advisor

Convert MIQP structure into binary probabilities for the selected block.

Inputs:

- instance matrices
- current incumbent assignment
- block selector output
- optional trained route 7 warm-start model

Outputs:

- per-bit probability of 1
- ranked bits by confidence
- fixed bits above a confidence threshold
- a candidate block assignment

Fallback hierarchy:

1. trained warm-start model if available
2. MIQP structural heuristic
3. simple score-to-probability baseline

### 4. Continuous Subproblem Solver

For a fixed binary assignment `x`, solve:

```text
maximize h^T y
subject to G y <= b - A x
           y >= 0
```

This is a linear program and can be solved with SciPy if available.

If feasible:

- return optimal `y`
- return continuous objective contribution
- extract dual multipliers
- produce an optimality cut

If infeasible:

- produce a feasibility advisory with violated rows
- identify the most problematic constraints
- recommend which binary variables contributed most to the violation

### 5. Cut Advisor

When the continuous LP is feasible, derive a Benders-style optimality cut:

```text
theta <= b^T pi - (A^T pi)^T x
```

where `pi` is a dual-feasible multiplier vector from the continuous subproblem.

When the continuous LP is infeasible:

- emit violated constraints
- emit slack magnitudes
- emit penalty suggestions for the next binary block
- carry the result as a feasibility cut advisory even if a mathematically exact ray is not available

This gives the route a real cut loop instead of only a score loop.

### 6. Block Search Loop

The MIQP-aware coordinator should iterate:

1. select block
2. warm-start block
3. solve block candidate set
4. solve continuous subproblem for each candidate
5. keep best feasible solution
6. generate cut advice
7. update scores for the next block

For the selected block:

- use exact search if block size is small enough
- use simulated annealing or local search if the block is larger or dense

This keeps quantum calls small and targeted.

## Route 7 Integration

Route 7 should become the orchestration layer that chooses between:

- classic QUBO learning-guided mode for pure binary instances
- MIQP-aware block mode for `.npz` competition instances

The route should expose:

- `block_selector`
- `warm_start`
- `cut_advisor`
- `continuous_subproblem`
- `best_incumbent`
- `quantum_block_candidates`

## Planned CLI

Add a dedicated MIQP CLI that can:

- load one or more `.npz` files
- solve or approximate them
- write a JSON result file
- optionally export a `.npz` or `.json` solution artifact

The CLI should record:

- selected block(s)
- warm-start summary
- continuous objective contribution
- cut summaries
- feasibility status
- final objective

## Acceptance Criteria

- `.npz` sample files load correctly.
- The solver reproduces the sample `optimal_value` on the provided sample instances or gets very close with a clear diagnostic trail.
- Block selection respects the 20-bit comfort zone and the 30-bit hard cap.
- Warm-start produces ranked probabilities and a fixed-bit plan.
- Continuous LP solving works when SciPy is available and gracefully degrades when it is not.
- Cut advisor produces meaningful Benders-style optimality cuts for feasible subproblems.
- Existing seven-route tests remain green.
- New MIQP-specific tests cover loader, selector, warm start, and cut generation.

## Risks

- Exact dual cut extraction depends on LP solver availability.
- Feasibility cuts for infeasible subproblems are harder to make exact without solver certificates.
- If the hidden instances are very dense, block choice matters more than the warm-start model.
- Over-encoding continuous variables into QUBO would be a regression.

## Recommendation

Do not expand route 7 by just making a bigger QUBO. The highest-value improvement is:

- treat `x` as the quantum/hybrid search surface
- treat `y` as a classical continuous subproblem
- use learned or heuristic block selection
- use Benders-style cut advice to steer the next block

That is the right shape for this competition.
