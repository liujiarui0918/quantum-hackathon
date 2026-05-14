# Quantum Hackathon Optimization Demo

本仓库是量子黑客松优化赛道的可复现实验代码包，目标是让评委或队友在比赛容器中用一条命令复现实验结果，并能清楚看到问题如何被量子化建模、如何转成 QUBO/Ising、如何构造 QAOA 量子线路，以及各类求解器的输出结果。

当前版本重点服务两个对象：

- 评审运行：下载代码、安装、执行 demo、查看 `result.json` 和 `report.md`。
- 代码开发：基于已有建模、QUBO、QAOA、约束处理模块继续接入最终赛题数据和改进算法。

## Important Scope

本项目当前不依赖真实量子硬件。主办方材料中只给出了 `qiskit` Docker 容器环境，没有提供真实 QPU backend、token、API key 或作业提交说明。因此本仓库默认实现的是：

```text
优化问题 -> QUBO/Ising -> QAOA 量子线路逻辑 -> 本地 statevector/shot 模拟 -> 结果文件
```

这属于在经典计算机上模拟量子算法执行过程。README 和代码中不会声称已经调用真实量子芯片。如果主办方后续提供真实量子平台账号或 backend 信息，可以在 `src/quantum_hackathon/demo.py` 中增加一个可选硬件提交分支；当前提交包为了可复现性，默认只使用 CPU 本地模拟。

## Quick Start

在仓库根目录执行：

```bash
python -m pip install -e .
python -m quantum_hackathon.demo --input data/sample_problem.json --output results/result.json --report results/report.md
```

Windows PowerShell：

```powershell
python -m pip install -e .
python -m quantum_hackathon.demo --input data/sample_problem.json --output results/result.json --report results/report.md
```

运行成功后会生成：

- `results/result.json`：机器可读结果，包含最优解、QUBO 诊断、各求解器结果、QAOA 线路摘要。
- `results/report.md`：人类可读实验报告，可直接复制到最终“求解说明”文档的实验结果部分。

运行测试：

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Competition Container

主办方环境说明中给出的容器入口是：

```bash
docker exec -it qiskit bash
```

宿主机 `/home/infra/qiskit` 会挂载到容器内 `/qiskit`。建议把仓库放在宿主机：

```text
/home/infra/qiskit/quantum-hackathon
```

然后进入容器运行：

```bash
docker exec -it qiskit bash
cd /qiskit/quantum-hackathon
python -m pip install -e .
python -m quantum_hackathon.demo --input data/sample_problem.json --output results/result.json --report results/report.md
```

沐曦 / `qiskit-aer-maca` 适配运行：

```bash
python -m quantum_hackathon.metax_demo --input data/sample_problem.json --output results/metax_result.json --report results/metax_report.md
```

该入口会保持六条算法路线都可运行，并将标准 QAOA 的最终 shot execution 优先交给 `Qiskit AerSimulator(method="statevector", device="GPU")`。如果容器没有 `qiskit-aer` 或 GPU 后端不可用，会记录 warning 并回退到仓库内置的本地 shot simulator。默认还会额外执行一个 Aer GPU stress circuit，用于确认 `qiskit-aer-maca` 能看到并调度 4 张沐曦卡；可用 `--skip-stress` 跳过。

如果需要测试：

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Environment

| Item | Requirement |
| --- | --- |
| Python | `>=3.10` |
| Local verified version | Python `3.12.10` |
| Runtime dependencies | Python standard library only |
| Test dependency | `pytest>=8.0` |
| Hardware | CPU only |
| Expected sample runtime | Usually under a few seconds |

项目目前没有强制安装 Qiskit Python 包，因为已有 QAOA 路线使用仓库内的轻量 statevector/shot simulator 实现，避免在评审环境里因为外部依赖版本不同导致不可复现。

## Repository Layout

```text
.
├── README.md
├── pyproject.toml
├── data/
│   └── sample_problem.json
├── src/
│   └── quantum_hackathon/
│       ├── demo.py
│       ├── modeling/
│       ├── constraints/
│       ├── solvers/
│       ├── benchmarks/
│       └── hybrid/
├── tests/
├── literature/
│   ├── notes/
│   ├── papers/
│   └── requirements/
├── quantum_hackathon_page.html
├── quantum_hackathon_index.css
├── quantum_hackathon_index.js
└── quantum_hackathon_quantum_index.js
```

Main modules:

| Path | Purpose |
| --- | --- |
| `src/quantum_hackathon/demo.py` | Competition demo CLI. Loads JSON, builds QUBO, runs solvers, writes JSON and Markdown reports. |
| `src/quantum_hackathon/modeling/problem.py` | Structured optimization model: variables, objective, constraints. |
| `src/quantum_hackathon/modeling/qubo.py` | QUBO builder, Ising conversion, decoding, feasibility checks, diagnostics. |
| `src/quantum_hackathon/solvers/exact.py` | Exact enumeration for small QUBO models; correctness baseline. |
| `src/quantum_hackathon/solvers/simulated_annealing.py` | CPU simulated annealing baseline. |
| `src/quantum_hackathon/solvers/qaoa/` | Standard QAOA Hamiltonian, statevector backend, shot sampler, simple optimizer. |
| `src/quantum_hackathon/solvers/constrained_qaoa/` | Feasible-subspace and XY-mixer metadata route for one-hot constraints. |
| `src/quantum_hackathon/constraints/` | Constraint encoding, repair and penalty analysis utilities. |
| `src/quantum_hackathon/benchmarks/` | Built-in small benchmark cases and report table helpers. |
| `data/sample_problem.json` | Reference input schema and sample instance. |
| `tests/` | Unit and integration tests. |
| `literature/requirements/` | Literature-derived development requirement docs for each algorithm route. |

## End-to-End Workflow

The one-click demo performs the following steps:

1. Load a structured optimization instance from JSON or a built-in sample case.
2. Validate variables, objective terms and constraints.
3. Convert the model into a QUBO with penalty terms.
4. Convert QUBO into an Ising Hamiltonian for QAOA.
5. Run exact enumeration if the QUBO bit count is small enough.
6. Run simulated annealing as a stochastic CPU baseline.
7. Run standard QAOA with local statevector optimization and shot sampling if the QUBO bit count is below `--qaoa-max-qubits`.
8. Run constrained-QAOA metadata diagnostics when one-hot constraints are present.
9. Decode bitstrings back to logical variables.
10. Check feasibility against original constraints.
11. Write `result.json` and `report.md`.

## One-Click CLI

Default sample run:

```bash
python -m quantum_hackathon.demo --input data/sample_problem.json --output results/result.json --report results/report.md
```

Use built-in cases:

```bash
python -m quantum_hackathon.demo --case sample
python -m quantum_hackathon.demo --case small_knapsack
python -m quantum_hackathon.demo --case exactly_one
```

Skip QAOA if only checking classical baselines:

```bash
python -m quantum_hackathon.demo --input data/sample_problem.json --skip-qaoa
```

Use more simulated annealing reads and sweeps:

```bash
python -m quantum_hackathon.demo --input data/sample_problem.json --sa-reads 300 --sa-sweeps 800
```

Use deeper QAOA or more shots:

```bash
python -m quantum_hackathon.demo --input data/sample_problem.json --qaoa-p 2 --qaoa-shots 1000
```

CLI parameters:

| Parameter | Default | Description |
| --- | --- | --- |
| `--input` | none | JSON problem file. If omitted, `--case` is used. |
| `--case` | `sample` | Built-in case: `sample`, `small_knapsack`, `exactly_one`. |
| `--output` | `results/result.json` | Machine-readable output path. |
| `--report` | `results/report.md` | Markdown report path. |
| `--seed` | `7` | Random seed for reproducibility. |
| `--sa-reads` | `60` | Simulated annealing independent reads. |
| `--sa-sweeps` | `150` | Annealing sweeps per read. |
| `--top-k` | `20` | Maximum number of top samples kept by solver configs. |
| `--qaoa-p` | `1` | QAOA circuit depth. |
| `--qaoa-shots` | `200` | Number of sampled shots after QAOA parameter search. |
| `--qaoa-max-qubits` | `12` | Skip local statevector QAOA above this QUBO bit count. |
| `--qaoa-grid-size` | `5` | Grid points for p=1 parameter search. |
| `--qaoa-random-trials` | `10` | Extra random parameter trials. |
| `--skip-qaoa` | false | Skip QAOA route. |

## Input Format

The input is a JSON object with four main sections:

| Field | Required | Description |
| --- | --- | --- |
| `name` | no | Human-readable problem name. |
| `sense` | no | `minimize` or `maximize`; default is `minimize`. |
| `variables` | yes | List of variable declarations. |
| `objective` | yes | Linear, quadratic, optional high-order terms and offset. |
| `constraints` | no | List of linear constraints. |

Reference file:

```bash
data/sample_problem.json
```

Minimal example:

```json
{
  "name": "sample_assignment",
  "sense": "maximize",
  "variables": [
    {"name": "model_a", "kind": "binary"},
    {"name": "model_b", "kind": "binary"},
    {"name": "model_c", "kind": "binary"}
  ],
  "objective": {
    "linear": {
      "model_a": 9.0,
      "model_b": 6.0,
      "model_c": 7.0
    },
    "quadratic": [],
    "offset": 0.0
  },
  "constraints": [
    {
      "name": "choose_one_model",
      "linear": {
        "model_a": 1.0,
        "model_b": 1.0,
        "model_c": 1.0
      },
      "sense": "==",
      "rhs": 1.0,
      "constraint_type": "exactly_one",
      "penalty_weight": 15.0
    }
  ]
}
```

Variable schema:

| Field | Required | Description |
| --- | --- | --- |
| `name` | yes | Unique variable name. |
| `kind` | no | `binary` or `integer`; default should be treated as `binary`. |
| `lower` | integer only | Lower bound for integer variables. |
| `upper` | integer only | Upper bound for integer variables. |

Objective schema:

| Field | Type | Description |
| --- | --- | --- |
| `linear` | object | Map from variable name to coefficient. |
| `quadratic` | list or object | Pairwise terms. List form: `{"variables": ["x", "y"], "coefficient": 1.0}`. Object form: `"x,y": 1.0`. |
| `high_order` | list | Optional high-order monomials; currently quadratized for direct binary variables. |
| `offset` | number | Constant objective offset. |

Constraint schema:

| Field | Required | Description |
| --- | --- | --- |
| `name` | no | Constraint name. |
| `linear` | yes | Map from variable name to linear coefficient. |
| `sense` | yes | One of `==`, `<=`, `>=`. |
| `rhs` | yes | Right-hand side value. |
| `constraint_type` | no | Used by specialized routes. `exactly_one` enables one-hot constrained-QAOA diagnostics. |
| `hardness` | no | Informational field; default is `hard`. |
| `penalty_weight` | no | Explicit QUBO penalty. If omitted, auto-scaled from objective bound. |

## Output Format

`results/result.json` is the main machine-readable output. Top-level fields:

| Field | Meaning |
| --- | --- |
| `problem` | Problem metadata, input source, sense, variables, constraints and QUBO bit count. |
| `run` | Seed, Python version, platform and total runtime. |
| `diagnostics` | QUBO size, density, coefficient scale, slack/auxiliary diagnostics and warnings. |
| `best_solution` | Best feasible decoded solution selected across available routes. |
| `benchmark` | Compact comparison rows and Markdown table. |
| `solvers.exact` | Exact enumeration route result or skip reason. |
| `solvers.simulated_annealing` | Simulated annealing route result. |
| `qaoa` | Standard QAOA simulator result, parameters, optimizer summary and circuit description. |
| `constrained_qaoa` | Feasible-subspace and XY-mixer diagnostics for one-hot constraints. |
| `output_files` | Paths of generated output files. |

`best_solution` fields:

| Field | Meaning |
| --- | --- |
| `bitstring` | QUBO bitstring after binary/slack/auxiliary encoding. |
| `bits` | Same bitstring as an integer list. |
| `logical_solution` | Decoded original decision variables. |
| `objective_value` | Objective value in the original optimization sense. |
| `qubo_energy` | QUBO energy after penalties and objective sign conversion. |
| `penalty_energy` | Penalty contribution. |
| `is_feasible` | Whether all original constraints are satisfied. |
| `total_violation` | Sum of constraint violations. |
| `constraint_violations` | Detailed violated constraints, empty if feasible. |

`results/report.md` is a human-readable summary with:

- problem metadata
- best solution JSON block
- solver benchmark table
- QAOA circuit implementation summary
- reproducibility details

## Algorithm Details

### 1. Structured Optimization Model

The model uses binary and bounded integer variables, linear/quadratic objective terms and linear constraints. The original objective can be either minimization or maximization. Maximization is internally converted to minimization by changing the objective sign before QUBO construction.

### 2. QUBO and Ising Conversion

The QUBO builder constructs an energy function:

```text
E(x) = objective(x) + sum_i penalty_i * violation_i(x)^2
```

Equality constraints are encoded as squared penalties. Inequality constraints introduce binary slack variables where needed. Integer variables are encoded into binary bits. The QUBO model can then be converted into an Ising Hamiltonian:

```text
C(z) = offset + sum_i h_i Z_i + sum_{i,j} J_ij Z_i Z_j
```

This Hamiltonian is used by the QAOA route.

### 3. Exact Solver

The exact solver enumerates every bitstring for small QUBO models and is used as a correctness baseline. It automatically refuses models above 25 binary variables to avoid accidental exponential blow-up.

### 4. Simulated Annealing

The simulated annealing route performs seeded stochastic local search on the QUBO energy. It provides a scalable CPU baseline and helps compare the QAOA route with a common heuristic.

### 5. Standard QAOA Route

The QAOA route implements the standard X-mixer ansatz:

```text
|psi_0> = H^n |0...0>
|psi(gamma, beta)> = product_l U_M(beta_l) U_C(gamma_l) |psi_0>
U_C(gamma) = exp(-i gamma C)
U_M(beta) = exp(-i beta sum_i X_i)
```

Implementation details:

- Cost Hamiltonian comes from QUBO-to-Ising conversion.
- `Z_i` terms map to `RZ`-style phase rotations.
- `Z_i Z_j` terms map to `RZZ`-style two-qubit phase rotations.
- Mixer terms map to `RX` rotations.
- Parameters are searched with a simple grid plus random trials.
- The final distribution is sampled with a seeded shot sampler.

The generated `qaoa.quantum_circuit` JSON field records the exact Hamiltonian terms and estimated gate counts for the submitted instance.

### 6. Constrained-QAOA Metadata Route

For constraints marked as `constraint_type="exactly_one"`, the constrained route identifies one-hot feasible subspaces and reports XY-mixer diagnostics:

- one-hot groups
- constraints covered
- constraints not covered
- XY edge count
- two-qubit term count
- whether the transition graph is connected
- whether the mixer preserves feasibility

Current status: this route is an MVP diagnostic and validation path. It does not claim full quantum circuit execution for constrained mixers. Internally it uses exact or simulated annealing backends to validate feasible-subspace behavior while reporting the mixer resource plan.

## Quantum Circuit Implementation

For the standard QAOA route, the effective circuit is:

```text
for each qubit i:
    H(i)

for layer l in 1..p:
    for each Z_i term:
        RZ(i, angle from gamma_l * h_i)
    for each Z_i Z_j term:
        RZZ(i, j, angle from gamma_l * J_ij)
    for each qubit i:
        RX(i, angle from beta_l)

measure all qubits
```

The output report includes:

- ansatz name
- backend type
- number of qubits
- QAOA layer count
- cost-unitary description
- mixer-unitary description
- `RZ`, `RZZ`, `RX` gate-count estimate
- exact `Z` and `ZZ` coefficient lists in JSON

This satisfies the solution document requirement for “量子线路实现” while keeping the implementation reproducible in the supplied container.

## Expected Runtime and Scaling

For `data/sample_problem.json` with default parameters:

| Route | Expected behavior |
| --- | --- |
| QUBO build | milliseconds |
| Exact enumeration | runs because sample has a small QUBO bit count |
| Simulated annealing | usually under a few seconds |
| Standard QAOA local simulator | usually under a few seconds for the sample |
| Constrained-QAOA metadata | milliseconds to seconds |

Scaling notes:

- Exact enumeration is exponential and skipped above 25 QUBO bits.
- Local statevector QAOA is exponential in qubit count and skipped above `--qaoa-max-qubits`.
- Simulated annealing can be used for larger instances by increasing `--sa-reads` and `--sa-sweeps`.
- Inequality constraints may introduce slack bits, increasing the QUBO size.

## Development Guide

Add a new JSON instance:

1. Copy `data/sample_problem.json`.
2. Change `name`, `variables`, `objective` and `constraints`.
3. Run the demo with `--input your_file.json`.

Add a new built-in benchmark:

1. Add a function in `src/quantum_hackathon/benchmarks/cases.py`.
2. Register it in `CASE_BUILDERS` inside `src/quantum_hackathon/demo.py`.
3. Add a test under `tests/`.

Add a new solver:

1. Implement `SamplerBackend.sample()` or a route-specific runner under `src/quantum_hackathon/solvers/`.
2. Decode raw samples through `SolutionPostprocessor`.
3. Add the route to `demo.py` output.
4. Add tests for deterministic behavior and output schema.

Before submitting changes:

```bash
python -m pytest -q
python -m quantum_hackathon.demo --input data/sample_problem.json --output results/result.json --report results/report.md
```

## Troubleshooting

`ModuleNotFoundError: No module named 'quantum_hackathon'`

Run from the repository root after installing:

```bash
python -m pip install -e .
```

`qaoa.status` is `skipped`

The model may exceed `--qaoa-max-qubits`, or `--skip-qaoa` was provided. Increase the threshold only for small enough problems because statevector simulation scales exponentially.

`exact.status` is `skipped`

The QUBO has more than 25 bits. This is expected for larger problems.

Output directory does not exist

The demo creates the parent directories for `--output` and `--report` automatically.

Results differ after changing parameters

Set `--seed` to a fixed value. Stochastic routes depend on the seed, reads, sweeps and shot count.

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
- optional web/presentation files from the repository root

Windows PowerShell packaging example:

```powershell
Compress-Archive -Force -Path README.md,pyproject.toml,src,tests,data,literature\requirements,quantum_hackathon_page.html,quantum_hackathon_index.css,quantum_hackathon_index.js,quantum_hackathon_quantum_index.js -DestinationPath "赛道-队伍名称-源代码.zip"
```

Linux packaging example:

```bash
zip -r "赛道-队伍名称-源代码.zip" README.md pyproject.toml src tests data literature/requirements quantum_hackathon_page.html quantum_hackathon_index.css quantum_hackathon_index.js quantum_hackathon_quantum_index.js
```

The final solution PDF should include:

- abstract
- problem analysis
- mathematical model
- QUBO/Ising transformation
- quantum algorithm design
- quantum circuit implementation
- experimental results and visualization
- innovation points
- comparison with classical or common quantum baselines
- reproducibility instructions
