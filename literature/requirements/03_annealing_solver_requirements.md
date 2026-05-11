# 开发需求文档：Quantum Annealing / Simulated Annealing 求解路线

更新日期：2026-05-12

## 1. 文档目标

本需求文档面向开发人员，定义一个可替换的 annealing solver layer：把路线 1/2 生成的 QUBO/BQM/Ising 模型交给本地 simulated annealing、tabu search、exact solver、D-Wave Ocean / D-Wave hybrid solver 等 backend，并统一返回、解码、校验和 benchmark。

第一阶段目标不是证明量子优势，而是让工程系统具备稳定的采样接口、可复现实验配置、可行性优先后处理、与经典 baseline 的公平对比。

## 2. 精读论文与可开发结论

### 2.1 Yarkoni et al. 2022：Quantum annealing 工业应用综述

**核心结论**：量子退火通常以 QUBO/Ising 为输入，实际使用需要经历建模、logical graph 构造、minor embedding、物理采样、chain break 处理和后处理等步骤。当前工业应用中还没有无争议地超过经典启发式的案例，因此工程实现必须保留经典 baseline 和端到端耗时统计。

**对开发的直接要求**：

- Solver 层输入应是 `QuboModel` / `BinaryQuadraticModel`，不能直接接业务数据。
- 需要统一 `SamplerBackend`，D-Wave 只是其中一种 backend。
- D-Wave adapter 必须显式记录 embedding、chain strength、num_reads、annealing_time、postprocess。
- benchmark 要统计 end-to-end time，而不只统计 QPU access time。
- 所有量子/模拟结果都必须经过路线 2 的 feasibility checker 和 logical decoder。

### 2.2 Sharma et al. 2026：Quantum annealing benchmark 与 scalability

**核心结论**：影响量子退火可扩展性的最大因素通常不是裸 qubit 数，而是 encoding、minor embedding、chain break 和物理连接开销。综述强调 benchmark 中常见问题：选择性报告、经典 baseline 弱、忽略 preprocessing overhead。

**对开发的直接要求**：

- diagnostics 必须包括 logical variables、physical variables estimate、coupler density、embedding success、chain length statistics。
- benchmark 必须包括 classical baseline：brute force、小规模 MILP/CP-SAT、greedy、SA、tabu。
- 不允许只报告 best sample；必须报告分布指标，例如 feasible ratio、best/median/mean objective、time-to-target。
- 对 hardware backend，必须记录 embedding 是否复用、embedding 时间、chain break fraction。

### 2.3 Hawashin et al. 2026：近端量子优化成熟度与 benchmark

**核心结论**：quantum annealing 在当前量子优化路径中 operational maturity 较高，适合作为早期工程入口；但实际价值通常来自 hybrid / quantum-inspired pipeline，而不是孤立 QPU 调用。标准化 benchmark 框架有助于把抽象问题与工程场景连接起来。

**对开发的直接要求**：

- 第一版应优先实现本地可跑的 annealing pipeline，再接真实 QPU。
- 需要 benchmark suite，可复用场景论文作为后续实例，但第一阶段用通用 toy/problem-class cases。
- 要区分 solver quality 与 modeling quality：同一 QUBO 交给多个 backend 对比。

### 2.4 Hen & Spedalieri 2016：约束 penalty 对退火的影响

**核心结论**：penalty-based 约束会引入额外 energy scale 和更高连接度，削弱硬件动态范围并加重 embedding 负担。对退火 solver 而言，约束处理不是建模层结束就无关了，而会直接影响采样质量。

**对开发的直接要求**：

- Solver 前必须检查 coefficient range，必要时做 scaling。
- 需要向用户报告 penalty-dominated landscape。
- 对 constrained mixer / driver 可行空间方法，路线 3 只保留接口，不实现量子 driver。

### 2.5 Montanez-Barrera et al. 2023：D-Wave 上 unbalanced penalty 的启示

**核心结论**：unbalanced penalty 在 D-Wave Advantage 与 hybrid solver 上能减少 slack 变量和连接需求，取得比 slack 方法更好的有效解；但它是 heuristic，不保证最优解一定在 ground state。论文还对比了 QPU、hybrid solver、classical solver 和 simulated annealing。

**对开发的直接要求**：

- `SamplesetPostprocessor` 必须支持 feasibility-first ranking。
- annealing backend 不应假设最低能量样本就是业务最优解。
- 对每次 run 保存 top-k samples，后处理时按 logical objective、violation、QUBO energy 多维排序。
- benchmark 需要支持“同一问题不同约束编码”的对比。

## 3. 模块边界

### 3.1 本模块负责

- 统一 solver backend 接口。
- 本地 exact / random / greedy / simulated annealing / tabu baseline。
- D-Wave Ocean adapter 设计。
- solver config 管理。
- sampleset 标准化。
- 后处理：去重、解码、可行性检查、repair、排序。
- benchmark runner。
- 运行日志和可复现实验记录。

### 3.2 本模块不负责

- QUBO 建模与 penalty 构造，沿用路线 1/2。
- QAOA 电路与 classical optimizer，归路线 4。
- constrained mixer，归路线 5。
- MILP block decomposition，归路线 6。

## 4. 核心数据结构需求

### 4.1 `SamplerBackend`

统一接口：

```python
class SamplerBackend:
    name: str
    capabilities: SamplerCapabilities

    def sample(self, model: QuboModel, config: SamplerConfig) -> RawSampleSet:
        ...
```

`SamplerCapabilities` 字段：

- `supports_qubo`
- `supports_ising`
- `supports_bqm`
- `supports_initial_state`
- `supports_reverse_annealing`
- `supports_embedding`
- `is_hardware`
- `max_variables`
- `max_couplers`

### 4.2 `SamplerConfig`

通用字段：

- `seed`
- `num_reads`
- `time_limit`
- `max_samples`
- `return_top_k`
- `scaling`
- `postprocess`

SA 字段：

- `num_sweeps`
- `beta_start`
- `beta_end`
- `schedule`
- `initial_state`
- `restarts`

D-Wave 字段：

- `solver_name`
- `annealing_time`
- `chain_strength`
- `embedding`
- `auto_scale`
- `answer_mode`
- `num_spin_reversal_transforms`
- `label`

### 4.3 `RawSampleSet`

字段：

- `samples`: list of bitstrings/spins。
- `energies`: QUBO/Ising energy。
- `num_occurrences`
- `timing`
- `backend_metadata`
- `warnings`

需求：

- 能从 `dimod.SampleSet` 转换。
- 能保存原始 backend 返回内容的摘要，避免丢失 D-Wave timing/embedding 信息。
- 不直接暴露为最终结果，必须经过 postprocessor。

### 4.4 `DecodedSample`

字段：

- `bitstring`
- `logical_solution`
- `qubo_energy`
- `objective_value`
- `penalty_energy`
- `is_feasible`
- `constraint_violations`
- `num_occurrences`
- `source_backend`
- `repair_info`

排序默认：

1. hard feasible。
2. objective value。
3. soft violation。
4. qubo energy。
5. occurrence count。

## 5. Backend 需求

### 5.1 `ExactSolverBackend`

用途：

- 小规模 correctness oracle。
- 验证 QUBO ground state 与原问题最优可行解是否一致。

限制：

- 默认 `n <= 25`。
- 超过阈值需用户显式允许。

### 5.2 `RandomSamplerBackend`

用途：

- sanity baseline。
- 检查模型是否过于依赖采样器。

需求：

- 支持 uniform random bitstrings。
- 支持按 feasible-subspace 随机采样，例如 exactly-k。

### 5.3 `GreedyLocalSearchBackend`

用途：

- 经典启发式 baseline。
- repair 后 polishing。

需求：

- 支持 1-flip descent。
- 支持 first-improvement / best-improvement。
- 支持 multi-start。

### 5.4 `SimulatedAnnealingBackend`

第一版必须实现或接入现成库。

建议行为：

- 输入 sparse QUBO/BQM。
- 每个 sweep 随机遍历变量并按 Metropolis rule 接受翻转。
- 支持 linear/geometric temperature schedule。
- 支持多 restart。
- 支持 initial_state。

配置默认：

```text
num_reads = 100
num_sweeps = 1000
schedule = geometric
beta_start = auto
beta_end = auto
```

自动 beta 可基于 QUBO 系数尺度估计。

### 5.5 `TabuSearchBackend`

P1/P2。

用途：

- 更强的经典 QUBO baseline。
- 与 SA 比较是否只是普通局部搜索就能解决。

需求：

- 支持 tabu tenure。
- 支持 aspiration criterion。
- 支持 time_limit。

### 5.6 `DWaveSamplerBackend`

P2，可选依赖。

需求：

- 使用 D-Wave Ocean 的 `dimod` / `dwave-system` adapter。
- 支持 `DWaveSampler + EmbeddingComposite`。
- 支持 `LeapHybridSampler` 或 hybrid BQM solver。
- 如果没有 token 或网络，必须优雅跳过，并保留本地 pipeline 可运行。

必须记录：

- logical variable count。
- physical qubit count。
- embedding time。
- chain strength。
- max chain length。
- average chain length。
- chain break fraction。
- qpu_access_time。
- total wall time。

## 6. 求解流程

推荐流程：

```text
QuboModel
  -> pre_solve_diagnostics
  -> optional coefficient scaling
  -> backend.sample()
  -> normalize RawSampleSet
  -> decode logical variables
  -> feasibility check
  -> optional repair
  -> feasibility-first ranking
  -> benchmark metrics
```

### 6.1 Pre-solve diagnostics

必须检查：

- variable count。
- coupler count。
- density。
- coefficient range。
- penalty/objective ratio。
- estimated brute-force eligibility。
- backend compatibility。

若 coefficient range 过大：

- 对本地 SA，允许直接运行但 warning。
- 对 D-Wave，建议 scale 或重构 penalty。

### 6.2 Coefficient scaling

需求：

- 支持把 QUBO 系数缩放到 backend 可接受范围。
- scaling 后保留原始 energy 计算。
- 输出 `scaling_factor` 和精度风险。

### 6.3 Postprocessing

必须执行：

- duplicate aggregation。
- bitstring decode。
- feasibility check。
- objective recomputation without penalties。
- top-k ranking。

可选：

- repair。
- local search polishing。
- constraint-aware resampling。

## 7. Benchmark 需求

### 7.1 Benchmark runner

API 草案：

```python
runner = AnnealingBenchmarkRunner(
    backends=[ExactSolver(), RandomSampler(), SimulatedAnnealer(), TabuSearch()],
    metrics=BenchmarkMetrics.default(),
)

report = runner.run(problem_suite, configs)
report.to_csv("benchmarks/annealing_results.csv")
report.to_markdown("benchmarks/annealing_report.md")
```

### 7.2 必须指标

- best feasible objective。
- best raw QUBO energy。
- best sample feasible。
- feasible sample ratio。
- unique feasible sample count。
- mean / median objective among feasible samples。
- optimality gap if exact known。
- approximation ratio if applicable。
- time to best feasible。
- total runtime。
- preprocessing time。
- sampling time。
- postprocessing time。
- repair success rate。

### 7.3 D-Wave 特有指标

- embedding success。
- embedding time。
- physical qubit count。
- chain break fraction。
- qpu access time。
- qpu programming time。
- qpu sampling time。
- wall-clock time。

### 7.4 公平对比规则

- 同一 QUBO 在多个 backend 上比较。
- 同一原问题在多个 encoding/penalty strategy 上比较。
- 报告所有 preprocessing/postprocessing 时间。
- 固定随机种子。
- 输出完整 config。
- 不只报告 best-of-many，必须报告 reads 和 repeats。

## 8. API 草案

```python
qubo_model = QuboBuilder().build(problem)

solver = AnnealingSolver(
    backend=SimulatedAnnealingBackend(),
    postprocessor=SolutionPostprocessor(enable_repair=True),
)

result = solver.solve(
    qubo_model,
    config=SamplerConfig(
        seed=42,
        num_reads=200,
        num_sweeps=2000,
        return_top_k=20,
    ),
)

best = result.best_feasible()
diagnostics = result.diagnostics
```

D-Wave：

```python
solver = AnnealingSolver(
    backend=DWaveSamplerBackend.from_env(),
    postprocessor=SolutionPostprocessor(enable_repair=True),
)

result = solver.solve(
    qubo_model,
    config=DWaveSamplerConfig(
        num_reads=1000,
        annealing_time=20,
        chain_strength="auto",
        embedding="auto",
    ),
)
```

## 9. 测试需求

### 9.1 单元测试

- QUBO energy evaluation 与 builder 一致。
- SA 单步 delta energy 正确。
- temperature schedule 单调。
- seed 可复现。
- RawSampleSet 去重正确。
- decode 后 objective 不包含 penalty。
- feasibility-first ranking 正确。
- scaling 后 argmin 不变。

### 9.2 集成测试

小规模问题：

- at-most-one。
- exact-one。
- small knapsack。
- graph coloring toy。
- set partitioning。

要求：

- ExactSolver 找到原问题最优。
- SA 在固定 seed/足够 reads 下找到可行解。
- postprocessor 输出 best feasible。
- unbalanced penalty case 中，即便 raw energy 最低样本不可行，ranking 仍能返回可行候选。

### 9.3 回归测试

保存：

- problem spec hash。
- QUBO hash。
- backend config。
- best feasible solution。
- metrics snapshot。

## 10. 开发优先级

### P0

- `SamplerBackend` 接口。
- `SamplerConfig`。
- `RawSampleSet` / `DecodedSample`。
- ExactSolver。
- RandomSampler。
- SimulatedAnnealingBackend。
- postprocessor。
- benchmark metrics。

### P1

- GreedyLocalSearch。
- penalty/encoding comparative benchmark。
- coefficient scaling。
- result persistence。
- local repair integration。

### P2

- TabuSearch。
- D-Wave Ocean adapter。
- embedding diagnostics。
- reverse annealing config 预留。

### P3

- OpenJij adapter。
- parallel tempering。
- population annealing。
- hardware-aware parameter tuning。

## 11. 主要风险与规避

**风险 1：把最低 QUBO energy 当成最终答案。**  
规避：统一 postprocessor，feasibility-first ranking，重算原始 objective。

**风险 2：benchmark 不公平。**  
规避：记录 preprocessing、embedding、sampling、postprocessing 全部耗时；提供 classical baselines。

**风险 3：D-Wave 依赖导致本地不可运行。**  
规避：D-Wave adapter 作为可选 P2，本地 SA/Exact pipeline 必须完整。

**风险 4：Penalty 系数过大导致 SA/QPU 采样质量差。**  
规避：pre-solve coefficient diagnostics，支持 scaling 和 penalty sweep。

**风险 5：硬件 embedding 失败或 chain break 高。**  
规避：输出 embedding diagnostics；提供 domain-wall / decomposition / hybrid 路线建议。

## 12. 参考文献

Yarkoni, S., Raponi, E., Bäck, T., & Schmitt, S. (2022). Quantum annealing for industry applications: Introduction and review. *Reports on Progress in Physics, 85*(10), 104001.

Sharma, R., Katukam, R., & Nagulapally, A. (2026). Quantum annealing for combinatorial optimization: Foundations, architectures, benchmarks, and emerging directions. arXiv:2602.03101.

Hawashin, B., et al. (2026). Variational and annealing quantum approaches to combinatorial optimization: Review and industrial relevance. arXiv:2603.19117.

Hen, I., & Spedalieri, F. M. (2016). Quantum annealing for constrained optimization. *Physical Review Applied, 5*(3), 034007.

Montanez-Barrera, J. A., van den Heuvel, P., Willsch, D., & Michielsen, K. (2023). Improving performance in combinatorial optimization problems with inequality constraints: An evaluation of the unbalanced penalization method on D-Wave Advantage. arXiv:2305.18757.
