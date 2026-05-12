# Quantum Hackathon Optimization Demo

本仓库是量子黑客松优化赛道的可复现实验代码包。当前 demo 面向评审运行要求，重点提供：

- 结构化问题输入：JSON 描述变量、目标函数、约束和惩罚权重。
- 可复现求解链路：QUBO/Ising 建模、精确枚举、模拟退火、标准 QAOA 小规模本地模拟。
- 量子线路说明：输出 QAOA cost unitary、mixer unitary 和门数量估计。
- 结果生成：一条命令生成 `result.json` 和 `report.md`。

## Directory Structure

```text
src/quantum_hackathon/
  modeling/              # OptimizationProblem, QUBO/Ising conversion, feasibility checks
  solvers/               # exact, simulated annealing, QAOA, constrained-QAOA metadata route
  constraints/           # constraint encoding, repair, penalty sweep
  benchmarks/            # built-in benchmark cases and report table helpers
  demo.py                # one-click competition demo entrypoint
data/sample_problem.json # sample input instance
tests/                   # regression tests
literature/requirements/ # algorithm route development requirement docs
```

## Environment

- Python: `>=3.10`, locally verified on Python `3.12.10`.
- Runtime dependencies: none outside the Python standard library.
- Test dependency: `pytest>=8.0`.
- Expected hardware: CPU only. The sample problem runs in seconds on a laptop.

Install:

```bash
python -m pip install -e .
```

Install test tools:

```bash
python -m pip install -e ".[dev]"
```

Competition container path from the organizer environment:

```bash
docker exec -it qiskit bash
cd /qiskit/quantum-hackathon
python -m pip install -e .
```

## One-Click Run

```bash
python -m quantum_hackathon.demo \
  --input data/sample_problem.json \
  --output results/result.json \
  --report results/report.md
```

PowerShell equivalent:

```powershell
python -m quantum_hackathon.demo --input data/sample_problem.json --output results/result.json --report results/report.md
```

Run tests:

```bash
python -m pytest -q
```

## CLI Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `--input` | none | JSON problem file. If omitted, `--case` is used. |
| `--case` | `sample` | Built-in case: `sample`, `small_knapsack`, `exactly_one`. |
| `--output` | `results/result.json` | Machine-readable result file. |
| `--report` | `results/report.md` | Human-readable Markdown report. |
| `--seed` | `7` | Random seed for reproducibility. |
| `--sa-reads` | `60` | Simulated annealing reads. |
| `--sa-sweeps` | `150` | Simulated annealing sweeps per read. |
| `--qaoa-p` | `1` | QAOA depth. |
| `--qaoa-shots` | `200` | Shot count for QAOA sampling. |
| `--qaoa-max-qubits` | `12` | Skip local statevector QAOA above this bit count. |
| `--skip-qaoa` | false | Skip QAOA and run only classical baselines. |

## Input Format

`data/sample_problem.json` is the reference schema.

```json
{
  "name": "sample_assignment",
  "sense": "maximize",
  "variables": [
    {"name": "model_a", "kind": "binary"}
  ],
  "objective": {
    "linear": {"model_a": 9.0},
    "quadratic": [
      {"variables": ["model_c", "boost_x"], "coefficient": 1.0}
    ],
    "offset": 0.0
  },
  "constraints": [
    {
      "name": "choose_one_model",
      "linear": {"model_a": 1.0, "model_b": 1.0, "model_c": 1.0},
      "sense": "==",
      "rhs": 1.0,
      "constraint_type": "exactly_one",
      "penalty_weight": 15.0
    }
  ]
}
```

Supported variable types:

- `binary`: direct 0/1 decision variable.
- `integer`: bounded integer encoded internally into binary bits, requiring `lower` and `upper`.

Supported constraints:

- `==`, `<=`, `>=` linear constraints.
- `constraint_type="exactly_one"` is recognized by the constrained-QAOA metadata route.
- `penalty_weight` is optional. If omitted, the QUBO builder selects an automatic scale from the objective bound.

## Output Format

`results/result.json` contains:

- `problem`: input source, sense, logical variables, QUBO bit count, constraints.
- `diagnostics`: QUBO density, coefficient scale, auxiliary/slack bit diagnostics and warnings.
- `best_solution`: bitstring, logical solution, original objective value, feasibility and violations.
- `benchmark.rows`: compact solver comparison table.
- `solvers.exact`: exact enumeration result when QUBO bit count is small enough.
- `solvers.simulated_annealing`: simulated annealing result.
- `qaoa`: standard QAOA simulator result, parameters, optimizer trace summary and circuit description.
- `constrained_qaoa`: feasible-subspace and XY-mixer diagnostics for `exactly_one` constraints.

`results/report.md` is generated from the same payload and can be copied into the final solution document's experiment section.

## Algorithm Routes

1. QUBO/Ising modeling: converts the structured optimization model into a binary quadratic objective with penalty terms.
2. Exact solver: enumerates all QUBO bitstrings for small models, used as a correctness baseline.
3. Simulated annealing: stochastic baseline for reproducibility and larger local runs.
4. Standard QAOA: builds the QUBO-derived Ising Hamiltonian, optimizes `gamma` and `beta`, then samples with a local statevector plus shot simulator.
5. Constrained-QAOA metadata route: detects one-hot feasible subspaces and reports XY-mixer resource diagnostics. In this MVP it does not claim hardware execution; it uses exact or simulated annealing backends to validate the feasible-subspace design.

## Quantum Circuit Implementation

The generated report includes a circuit-level summary:

- Initial state: apply `H` to all qubits.
- Cost layer: apply `exp(-i gamma C)` from QUBO-to-Ising terms, represented by `RZ` gates for `Z_i` terms and `RZZ` gates for `Z_i Z_j` terms.
- Mixer layer: apply `exp(-i beta sum_i X_i)`, represented by `RX` gates.
- Repeat for `p` QAOA layers.

The JSON field `qaoa.quantum_circuit` contains the exact term list and gate-count estimate for the submitted instance.

## Expected Runtime

For `data/sample_problem.json` with default parameters:

- QUBO size: single-digit qubit count after slack encoding.
- Expected runtime: usually under a few seconds on CPU.
- Exact enumeration is automatically skipped if the QUBO model exceeds 25 bits.
- Local statevector QAOA is automatically skipped above `--qaoa-max-qubits`.

## Submission Packaging

Organizer-required names:

- Solution PDF: `赛道-队伍名称-求解说明.pdf`
- Source ZIP: `赛道-队伍名称-源代码.zip`

Suggested source ZIP contents:

- `README.md`
- `pyproject.toml`
- `src/`
- `tests/`
- `data/`
- `literature/requirements/`
- optional presentation/web files in the repository root

Windows PowerShell packaging example:

```powershell
Compress-Archive -Force -Path README.md,pyproject.toml,src,tests,data,literature\requirements,quantum_hackathon_page.html,quantum_hackathon_index.css,quantum_hackathon_index.js,quantum_hackathon_quantum_index.js -DestinationPath "赛道-队伍名称-源代码.zip"
```

Linux packaging example:

```bash
zip -r "赛道-队伍名称-源代码.zip" README.md pyproject.toml src tests data literature/requirements quantum_hackathon_page.html quantum_hackathon_index.css quantum_hackathon_index.js quantum_hackathon_quantum_index.js
```

The solution PDF should include: abstract, problem analysis, mathematical model, quantum algorithm design, quantum circuit implementation, experimental results and visualization.
