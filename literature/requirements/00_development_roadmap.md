# 总体开发路线图：混合整数约束优化的量子/量子启发求解框架

更新日期：2026-05-15

## 1. 文档目标

本文档把 7 类理论路线串成一套可落地的开发计划。读者默认是写代码的人，目标是先做出稳定的通用优化框架，再逐步接入 quantum annealing、QAOA、constrained mixer、hybrid decomposition 和 learning-guided optimization。

当前阶段暂不绑定电力、排产、物流、金融等具体场景。场景论文后续只作为 benchmark 和 demo 数据来源。

## 2. 七条路线的开发定位

### 路线 1：QUBO / Ising 建模底座

文档：`01_qubo_ising_modeling_requirements.md`

定位：所有 solver 的共同输入层。负责变量注册、目标函数、约束罚项、bounded integer 编码、高阶项二次化、QUBO/Ising/BQM 导出、energy evaluation、decode 和 diagnostics。

这是必须最先实现的模块。

### 路线 2：约束处理、编码与罚函数调参

文档：`02_constraint_handling_requirements.md`

定位：保证可行性的核心层。负责 `ConstraintSpec`、penalty strategy、encoding strategy、feasibility checker、sample ranking、repair、penalty sweep 和 feasible-subspace metadata。

这是第二个必须实现的模块，因为没有它，所有量子/模拟求解器都会把 infeasible sample 当成好结果。

### 路线 3：Quantum Annealing / Simulated Annealing 求解路线

文档：`03_annealing_solver_requirements.md`

定位：第一条可跑通的 solver 路线。用 Exact / Random / Greedy / Simulated Annealing / Tabu / D-Wave adapter 统一消费 QUBO/BQM，并输出标准 sampleset。

这是 hackathon 最适合先跑出结果的路线。

### 路线 4：QAOA / VQA 标准量子门模型路线

文档：`04_qaoa_vqa_requirements.md`

定位：标准 gate-model quantum demo 和算法实验层。负责 QUBO/Ising Hamiltonian、standard X-mixer QAOA、classical optimizer、shots、measurement decoding 和 exact small-instance comparison。

适合小规模展示，不适合作为第一条大规模求解主线。

### 路线 5：Constrained Mixer / Warm-start / XY Mixer

文档：`05_constrained_mixer_warm_start_requirements.md`

定位：比标准 QAOA 更有理论亮点的可行空间搜索路线。通过 one-hot / exactly-k / fixed-Hamming-weight 的 constrained mixer 减少 penalty 依赖，并支持 warm-start XY 和 R-QAOA。

这是创新展示路线，依赖路线 2 和路线 4 的接口稳定。

### 路线 6：Hybrid MILP / MIQP 分解与量子子问题

文档：`06_hybrid_milp_miqp_requirements.md`

定位：工程上最稳的扩展路线。把完整混合整数问题拆成 classical relaxation、rounding、repair、continuous polish 和小 QUBO subproblem，让量子/量子启发 solver 只处理离散子问题。

当问题规模变大或含连续变量时，应优先走这条路线，而不是强行 direct QUBO。

### 路线 7：Learning-Guided Optimization / 神经网络辅助混合优化

文档：`07_learning_guided_optimization_requirements.md`

定位：GPU 友好的学习引导层。它把 QUBO / MILP 表示成图，学习 warm-start、变量固定、branching、repair、local search 和 QAOA/退火参数调度。它不替代 exact solver、MILP bound 或 feasibility checker，而是让前面路线更快产生高质量候选解。

## 3. 推荐实现顺序

### 第一阶段：可验证建模闭环

目标：不用任何量子库，也能把小规模原问题转成 QUBO，并用 brute force 验证正确性。

必须完成：

- `VariableRegistry`
- `QuadraticExpression`
- `ConstraintSpec`
- `QuboModel`
- binary variable。
- bounded integer binary expansion。
- equality penalty。
- inequality binary slack。
- QUBO energy evaluation。
- QUBO -> Ising。
- decode。
- feasibility checker。
- brute force verifier。
- diagnostics snapshot。

验收标准：

- small knapsack、exactly-one、at-most-one、set partitioning 等 toy case 中，原问题 brute force 与 QUBO brute force 的最优 logical solution 一致。

### 第二阶段：可跑 solver 闭环

目标：同一 QUBO 可以交给不同 solver，统一返回、解码、排序和 benchmark。

必须完成：

- `SamplerBackend`
- `ExactSolverBackend`
- `RandomSamplerBackend`
- `SimulatedAnnealingBackend`
- `RawSampleSet`
- `DecodedSample`
- `SolutionPostprocessor`
- feasibility-first ranking。
- basic repair。
- benchmark runner。

验收标准：

- 每个 toy case 输出 best feasible solution。
- raw QUBO energy 最低但 infeasible 的样本不会被当成最终答案。
- benchmark 能比较 exact、random、SA 的 best feasible objective、feasible ratio 和 runtime。

### 第三阶段：约束高级策略与 hybrid scaffold

目标：减少 slack 爆炸，并把 direct QUBO 扩展为可处理中等规模问题的 hybrid workflow。

应完成：

- penalty advisor。
- penalty sweep。
- unbalanced inequality penalty。
- one-hot encoding strategy。
- cardinality repair。
- bounded-sum greedy repair。
- `HybridOptimizationProblem`
- `ProblemDecomposer`
- relaxation -> rounding -> repair -> polish pipeline。
- fix-and-optimize small QUBO subproblem。

验收标准：

- 对同一原问题，可以比较 binary slack 与 unbalanced penalty 的变量数、coupler 数、feasible ratio 和 best feasible objective。
- hybrid pipeline 能在含连续变量或较多约束的 toy problem 上返回可行候选解。

### 第四阶段：标准 QAOA 小规模 demo

目标：把 QUBO/Ising 接到 gate-model QAOA，形成小规模可复现实验。

应完成：

- `CostHamiltonianBuilder`
- standard X-mixer ansatz。
- statevector backend。
- shot simulator backend。
- COBYLA / SPSA optimizer adapter。
- random / fixed / multi-start initializer。
- measurement decoder。
- exact diagonalization comparison。

验收标准：

- 2-10 qubit toy case 可跑通。
- Hamiltonian energy 与 QUBO energy truth table 一致。
- QAOA 输出走统一 feasibility checker 和 postprocessor。

### 第五阶段：Constrained Mixer 与 warm-start

目标：实现 one-hot / exactly-k 的可行空间 QAOA，并展示相对 penalty QAOA 的可行率优势。

应完成：

- `FeasibleSubspaceSpec`
- `MixerStrategy`
- one-hot XY mixer。
- fixed-Hamming-weight XY mixer。
- feasible initial state builder。
- transition graph diagnostics。
- weighted W-state P2。
- warm-start XY P2。
- iterative warm-start P2。
- R-QAOA reducer P2。

验收标准：

- noiseless simulator 中，XY mixer 的 covered constraints violation rate 为 0。
- penalty QAOA 与 XY-QAOA 的 feasible ratio、best feasible objective、circuit depth 有可复现实验报告。

### 第六阶段：Learning-Guided Optimization 与 GPU 训练接口

目标：把已有 benchmark 输出变成训练信号，用学习策略给退火、QAOA、constrained mixer 和 hybrid 子问题提供 warm-start 和变量固定建议。

应完成：

- QUBO graph feature exporter。
- training JSONL builder。
- exact / SA / hybrid incumbent label source。
- linear warm-start policy baseline。
- variable fixing plan。
- optional PyTorch/GNN policy adapter。
- repair / local-search policy scaffold。
- QAOA parameter initialization predictor P2。

验收标准：

- 小规模问题能导出带 exact label 的训练样本。
- learning-guided backend 能作为 solver row 进入 demo benchmark。
- 固定变量计划可解释：记录 fixed bits、free bits、概率和置信度。
- 文档明确神经网络是启发式增强，不承诺最优性。

## 4. 推荐代码目录

建议新增代码结构：

```text
src/quantum_hackathon/
  modeling/
    variables.py
    expressions.py
    problem.py
    qubo.py
    ising.py
    quadratization.py
    diagnostics.py
  constraints/
    specs.py
    compiler.py
    penalties.py
    encodings.py
    feasibility.py
    repair.py
  solvers/
    base.py
    postprocess.py
    exact.py
    random.py
    simulated_annealing.py
    learning_guided.py
    tabu.py
    qaoa/
      hamiltonian.py
      ansatz.py
      backends.py
      optimizers.py
      runner.py
    constrained_qaoa/
      subspace.py
      mixers.py
      warm_start.py
      recursive.py
  hybrid/
    problem.py
    decomposition.py
    relaxation.py
    rounding.py
    optimizer.py
  benchmarks/
    cases.py
    runner.py
    metrics.py
tests/
  test_modeling_*.py
  test_constraints_*.py
  test_solvers_*.py
  test_qaoa_*.py
```

如果现有仓库已有代码结构，应优先融入现有目录，不强行照搬。

## 5. 最小公共接口

### 5.1 输入问题接口

```python
problem = OptimizationProblem(sense="minimize")
problem.add_binary_var("x0")
problem.add_integer_var("y", lower=0, upper=7)
problem.set_objective(linear={...}, quadratic={...})
problem.add_constraint(linear={...}, sense="<=", rhs=..., name="capacity")
```

### 5.2 QUBO 构建接口

```python
compiled = ConstraintCompiler(config).compile(problem)
qubo_model = QuboBuilder(config).build(problem, compiled)
diagnostics = qubo_model.diagnostics()
```

### 5.3 Solver 接口

```python
solver = SolverRegistry.create("simulated_annealing")
result = solver.solve(qubo_model, config)
best = result.best_feasible()
```

### 5.4 Result 接口

统一 result 必须包含：

- `best_feasible_solution`
- `best_feasible_objective`
- `best_raw_energy_sample`
- `samples`
- `feasible_ratio`
- `constraint_violations`
- `runtime`
- `diagnostics`
- `config`

## 6. 第一批测试样例

P0 必须覆盖：

- 2-variable at-most-one。
- exactly-one selection。
- exactly-k selection。
- small knapsack。
- set partitioning。
- 3-node graph coloring toy。
- cubic objective quadratization toy。

每个样例保存：

- original optimum。
- QUBO optimum。
- decoded solution。
- objective without penalties。
- penalty energy。
- feasibility report。
- diagnostics snapshot。

## 7. Benchmark 输出字段

建议统一 CSV/JSON 字段：

- `problem_name`
- `route`
- `solver`
- `encoding_strategy`
- `penalty_strategy`
- `logical_variables`
- `encoded_binary_variables`
- `slack_variables`
- `auxiliary_variables`
- `coupler_count`
- `density`
- `coefficient_ratio`
- `best_feasible_objective`
- `best_raw_energy`
- `best_raw_energy_feasible`
- `feasible_sample_ratio`
- `unique_feasible_samples`
- `optimality_gap`
- `preprocess_ms`
- `solve_ms`
- `postprocess_ms`
- `total_ms`
- `seed`

QAOA 额外字段：

- `p`
- `shots`
- `optimizer`
- `optimizer_evals`
- `two_qubit_gate_count`
- `circuit_depth`
- `total_shots`

Hybrid 额外字段：

- `relaxation_status`
- `relaxation_bound`
- `rounding_strategy`
- `repair_success`
- `subproblem_count`
- `average_subproblem_bits`

## 8. 开发任务拆分

### P0：基础正确性

- 建模数据结构。
- QUBO 构造。
- 基础约束 penalty。
- decode / feasibility checker。
- brute force verifier。
- exact / random / SA backend。
- postprocessor。
- toy benchmark。

### P1：可用性和约束质量

- penalty advisor。
- penalty sweep。
- unbalanced inequality。
- one-hot / cardinality support。
- repair。
- benchmark report。
- hybrid relax-round-repair。

### P2：量子展示与高级路线

- standard QAOA。
- Qiskit/Aer adapter。
- constrained QAOA one-hot XY mixer。
- warm-start metadata。
- fix-and-optimize QUBO subproblem。
- result persistence。

### P3：研究增强

- warm-start XY。
- R-QAOA。
- learning-guided warm-start / variable fixing。
- GNN/RL repair policy。
- domain-wall。
- ADMM hybrid。
- D-Wave adapter。
- hardware-aware circuit / embedding diagnostics。

## 9. 关键工程原则

1. 所有 solver 的最终答案都必须经过 decode、feasibility check 和 objective recomputation。
2. 不把 QUBO energy 当业务目标；QUBO energy 包含 penalty 和 offset。
3. 每次模型构建都输出 diagnostics，尤其是变量数、slack 数、coupler 数和 coefficient range。
4. 小规模问题必须先 brute force 验证，再谈量子/启发式效果。
5. D-Wave、IBM Quantum 等硬件依赖必须可选，本地 pipeline 必须完整可运行。
6. benchmark 必须包含 classical baseline，不只展示量子结果。
7. constrained mixer 只覆盖它能保持的硬约束，未覆盖约束仍需 penalty 或 repair。
8. hybrid 路线中，量子/Ising solver 是 discrete oracle，不是整个系统唯一入口。

## 10. 近期建议落地顺序

最短可用路径：

```text
OptimizationProblem
  -> QuboBuilder
  -> ExactSolver + SimulatedAnnealing
  -> SolutionPostprocessor
  -> Benchmark report
```

随后扩展：

```text
ConstraintCompiler
  -> penalty advisor / unbalanced / repair
  -> Hybrid relax-round-repair
  -> standard QAOA
  -> one-hot XY constrained QAOA
```

如果时间只够做一条 demo 主线，建议选择：

```text
QUBO modeling + constraint checker + SA solver + repair + benchmark
```

如果需要展示量子算法创新，再补：

```text
standard QAOA vs constrained XY-QAOA on one-hot toy problem
```
