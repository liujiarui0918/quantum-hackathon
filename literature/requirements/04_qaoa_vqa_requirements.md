# 开发需求文档：QAOA / VQA 标准量子门模型路线

更新日期：2026-05-12

## 1. 文档目标

本需求文档面向开发人员，定义一套标准 QAOA / VQA 求解模块：把路线 1/2 生成的 QUBO、BQM 或 Ising Hamiltonian 转换为参数化量子线路，通过 classical optimizer 优化参数，测量得到 bitstring，再交给统一 decoder、feasibility checker 和 postprocessor。

第一阶段目标是可运行、可复现、可验证的小规模 pipeline，而不是承诺量子优势。该路线应作为量子门模型展示层和算法实验层，优先服务 hackathon demo、论文复现实验和后续 constrained mixer 路线。

## 2. 精读论文与可开发结论

### 2.1 Farhi, Goldstone, Gutmann 2014：标准 QAOA

**核心结论**：QAOA 使用 `p` 层交替结构。每层包含 cost unitary 和 mixer unitary，参数为 `gamma_1...gamma_p` 与 `beta_1...beta_p`。量子线路制备参数态后，在 computational basis 测量得到 bitstring，并用 classical optimizer 根据测量估计的期望值更新参数。

**对开发的直接要求**：

- QAOA runner 必须显式暴露 `p`、`gamma`、`beta`、`shots`、`optimizer`、`seed`。
- cost Hamiltonian 必须从路线 1 的 QUBO/Ising/BQM 统一构造，不能在 QAOA 模块重新写业务模型。
- 初始态默认使用 `|+>^n`，对应标准 X mixer。
- 每次 parameter evaluation 必须返回：
  - estimated expectation。
  - raw measurement counts。
  - decoded top samples。
  - objective without penalties。
  - constraint status。
- 小规模问题必须提供 statevector exact expectation，用于对 shot-based estimator 做 sanity check。

**工程注意**：

- QAOA 论文常以最大化目标表述，本系统统一以 minimization 为默认。若 backend 或 benchmark 需要 maximization，必须在 adapter 层显式翻转符号。
- QAOA 的输出不是一个确定解，而是一组 measurement samples；最终答案必须由 postprocessor 排序筛选。

### 2.2 Farhi et al. 2014 bounded occurrence CSP：低深度与局部结构

**核心结论**：在固定 `p`、bounded degree / bounded occurrence 问题中，QAOA 的 expectation 可利用局部子图结构分析。对工程而言，这说明 QAOA circuit depth 与 cost Hamiltonian 的 locality、coupler graph 和 `p` 直接相关。

**对开发的直接要求**：

- Hamiltonian diagnostics 必须报告 interaction graph degree、term locality、two-qubit term 数量。
- circuit diagnostics 必须报告：
  - qubit count。
  - QAOA depth estimate。
  - two-qubit gate count。
  - circuit width。
  - 是否需要硬件 transpilation。
- 对 dense QUBO，必须提示 QAOA cost layer 会产生大量 ZZ gates，可能不适合 NISQ。

### 2.3 Moll et al. 2018：近端量子优化与硬件约束

**核心结论**：VQA 的价值在于 hybrid quantum-classical loop 和 shallow circuit，但近端设备受 qubit 数、coherence、connectivity、gate error 和 circuit depth 限制。classical optimizer 必须能处理 noisy expectation。

**对开发的直接要求**：

- 第一版必须包含本地 simulator backend，不能依赖真实量子硬件。
- hardware backend 必须是可选依赖，没有 token 或 provider 时优雅跳过。
- optimizer 默认优先选择 derivative-free 方法，例如 COBYLA、Nelder-Mead、SPSA。
- 需要记录 shot noise、optimizer calls、wall time、circuit depth、transpiled depth。
- 支持 error mitigation / measurement mitigation 的接口，但 P0 不强制实现。

### 2.4 Zhou et al. 2020：参数优化机制与初始化

**核心结论**：QAOA 的 outer-loop classical optimization 是关键瓶颈。随机初始化在深层 `p` 时成本很高；更好的参数初始化、参数迁移、linear ramp 或从低 `p` 插值到高 `p` 的策略可以显著减少优化次数。

**对开发的直接要求**：

- `ParameterInitializer` 必须是独立组件。
- P0 支持 random / fixed / user-provided / multi-start。
- P1 支持：
  - linear ramp。
  - p-to-p+1 interpolation。
  - 参数缓存与迁移。
  - warm-start params from route 6 relaxation。
- 每次优化必须保存 parameter trace，包含参数、估计能量、best sample、feasible ratio。
- benchmark 不能只比较最终值，还要比较 optimizer evaluations 和 time-to-best。

### 2.5 Blekos et al. 2024：QAOA variants 综述

**核心结论**：QAOA 已有大量 variants：standard QAOA、warm-start QAOA、recursive QAOA、quantum alternating operator ansatz、constraint-preserving mixer、ADAPT-QAOA、CVaR-QAOA 等。工程实现应该先稳定标准 QAOA，再通过接口支持 variants，而不是把所有变体混在一个类里。

**对开发的直接要求**：

- `QaoaRunner` 只负责标准 X-mixer QAOA。
- constrained mixer、warm-start XY、R-QAOA 归路线 5，但 route 4 需要预留 hook。
- objective estimator 应支持多种 aggregation：
  - mean energy。
  - best sample energy。
  - CVaR P1/P2。
- ansatz、optimizer、estimator、postprocessor 必须解耦，方便替换。

### 2.6 Cerezo et al. 2021：VQA 可训练性、shots 与 barren plateau

**核心结论**：VQA 面临 trainability、accuracy、efficiency 问题。测量只给有限统计估计，optimizer 看到的是 noisy objective；参数化线路可能出现 barren plateau；gradient-based 方法可用 parameter-shift，但 shot cost 高。

**对开发的直接要求**：

- 每个 run 必须记录 shots per evaluation 和 total shots。
- optimizer result 必须包含 statistical uncertainty 或至少包含 repeated evaluation variance。
- 需要 barren plateau 风险诊断：
  - qubit 数过多。
  - `p` 过深。
  - random initialization。
  - observed objective variance 过小。
- P2 支持 parameter-shift gradient，但 P0/P1 以 derivative-free optimizer 为主。

## 3. 模块边界

### 3.1 本模块负责

- 从 QUBO/BQM/Ising 构造 cost Hamiltonian。
- 标准 X-mixer QAOA ansatz。
- statevector / shot-based simulator backend。
- classical optimizer adapter。
- 参数初始化和参数 trace。
- measurement decoding。
- 小规模 exact comparison。
- QAOA benchmark 和 diagnostics。

### 3.2 本模块不负责

- QUBO 建模和 penalty 构造，沿用路线 1/2。
- annealing solver，归路线 3。
- constrained mixer、XY mixer、warm-start XY、R-QAOA，归路线 5。
- hybrid decomposition 和 relaxation，归路线 6。
- 真实硬件账号、provider token 管理。

## 4. 核心数据结构需求

### 4.1 `CostHamiltonian`

字段建议：

- `num_qubits`
- `pauli_terms`: list of `(pauli_string, coeff)`。
- `offset`
- `sense`: `minimize | maximize`
- `source_model_id`
- `variable_mapping`
- `convention`

convention 必须说明：

```text
computational bit x = 0 -> Pauli Z eigenvalue +1
computational bit x = 1 -> Pauli Z eigenvalue -1
x = (1 - Z) / 2
```

如果沿用路线 1 的 Ising spin `s = 2x - 1`，则有：

```text
s = -Z
```

需求：

- 支持从 sparse QUBO 直接构造 Z/ZZ Hamiltonian。
- 支持从 Ising `h, J, offset` 构造 Hamiltonian，并显式处理符号约定。
- 保留 constant offset，用于 energy 对齐和测试。
- 支持计算任意 bitstring 的 classical energy。

### 4.2 `QaoaAnsatzSpec`

字段建议：

- `p`
- `mixer_type`: `x_mixer`
- `initial_state`: `plus_state`
- `parameter_order`: `gamma_beta | beta_gamma`
- `cost_layer_repetitions`
- `mixer_layer_repetitions`

需求：

- 默认参数向量顺序必须稳定，例如：

```python
theta = [gamma_1, ..., gamma_p, beta_1, ..., beta_p]
```

- 构造 circuit 时必须能返回 logical circuit 和 transpiled circuit。
- 支持 dry-run diagnostics，不执行优化也能估算资源。

### 4.3 `QaoaConfig`

字段建议：

- `p`
- `shots`
- `seed`
- `backend`
- `optimizer`
- `max_evals`
- `initialization`
- `multi_start`
- `aggregation`: `mean | cvar | best_sample`
- `return_top_k`
- `enable_postprocessing`

默认建议：

```text
p = 1
shots = 1024
optimizer = COBYLA
max_evals = 100
multi_start = 5
aggregation = mean
return_top_k = 20
```

### 4.4 `ParameterInitializer`

统一接口：

```python
class ParameterInitializer:
    def initialize(self, hamiltonian, ansatz, config) -> list[ParameterSet]:
        ...
```

策略：

- `RandomInitializer`
- `ZeroInitializer`
- `FixedGridInitializer` for p=1。
- `LinearRampInitializer` P1。
- `ParameterTransferInitializer` P1。
- `WarmStartParameterInitializer` P2。

需求：

- 所有随机策略必须接受 seed。
- multi-start 返回多个 candidate parameter sets。
- 参数范围要按 QAOA 周期性规范化，例如 gamma/beta wrap。

### 4.5 `QaoaEvaluation`

单次参数评估输出：

- `theta`
- `estimated_energy`
- `energy_std` 或 repeated estimate 方差。
- `shots`
- `counts`
- `top_bitstrings`
- `best_decoded_sample`
- `feasible_ratio`
- `objective_best_feasible`
- `eval_time`

### 4.6 `QaoaResult`

字段建议：

- `best_parameters`
- `best_estimated_energy`
- `best_samples`
- `best_feasible_solution`
- `optimizer_trace`
- `backend_metadata`
- `diagnostics`
- `warnings`

需求：

- 与路线 3 的 solver result 尽量保持同构，便于 benchmark 汇总。
- 必须保存 raw counts 或其 top-k 摘要。
- 必须保存 reproducibility config。

## 5. Hamiltonian 构造需求

### 5.1 从 QUBO 构造

输入：

```text
E(x) = offset + sum_i q_i x_i + sum_{i<j} q_ij x_i x_j
```

使用：

```text
x_i = (1 - Z_i) / 2
x_i x_j = (1 - Z_i - Z_j + Z_i Z_j) / 4
```

输出：

```text
H_C = constant + sum_i h_i Z_i + sum_{i<j} J_ij Z_i Z_j
```

需求：

- 与 `QuboModel.energy(bitstring)` 对齐。
- 支持 coefficient scaling，但 scaling 信息必须可逆。
- 对 minimization，optimizer 最小化 `E[H_C]`；若某库默认最大化，需要在 adapter 翻转。

### 5.2 Cost layer circuit

对每个 Z term：

- `exp(-i gamma h_i Z_i)` 可实现为 `RZ(2 * gamma * h_i)`，具体符号按 framework 校验。

对每个 ZZ term：

- `exp(-i gamma J_ij Z_i Z_j)` 可实现为 `RZZ(2 * gamma * J_ij)` 或 CNOT-RZ-CNOT。

需求：

- adapter 必须用单元测试锁定符号。
- 支持 term grouping / parallel scheduling P1。
- 资源诊断要统计 ZZ terms 和 two-qubit gates。

### 5.3 Mixer layer circuit

标准 X mixer：

```text
H_M = sum_i X_i
U_M(beta) = exp(-i beta H_M)
```

实现：

- 每个 qubit 一个 `RX(2 * beta)` 或按 framework 约定。

需求：

- X mixer 只适合 unconstrained binary search 或 penalty-based QUBO。
- 对 hard one-hot / exactly-k 约束，应在 diagnostics 中提示 route 5 constrained mixer。

## 6. QAOA 求解流程

推荐流程：

```text
QuboModel / IsingModel
  -> CostHamiltonianBuilder
  -> QaoaAnsatzBuilder
  -> pre-run diagnostics
  -> ParameterInitializer
  -> optimizer loop:
       build/bind circuit(theta)
       run backend
       estimate objective from counts/statevector
       decode top samples
       log QaoaEvaluation
  -> final measurement with best theta
  -> postprocess samples:
       decode
       feasibility check
       repair if enabled
       feasibility-first ranking
  -> QaoaResult
```

## 7. Backend 需求

### 7.1 `StatevectorQaoaBackend`

用途：

- 小规模 exact expectation。
- debug Hamiltonian sign。
- optimizer 无 shot noise 的 baseline。

限制：

- 默认 `num_qubits <= 25`，超过阈值需要用户显式允许。

### 7.2 `ShotSimulatorBackend`

用途：

- 模拟真实测量统计。
- 检查 optimizer 对 shot noise 的稳定性。

需求：

- 支持固定 seed。
- 支持 counts 输出。
- 支持重复评估同一参数估计 variance。

### 7.3 `QiskitBackendAdapter` P1

需求：

- 支持 Aer simulator。
- 支持 optional IBM backend。
- 没有依赖时跳过，不影响核心测试。
- 记录 transpiled depth、basis gates、two-qubit count。

### 7.4 其他 backend P2/P3

- PennyLane adapter。
- Cirq adapter。
- hardware provider adapter。

所有 backend 都必须实现：

```python
class QaoaBackend:
    def run(self, circuit, parameters, shots, seed) -> MeasurementResult:
        ...
```

## 8. Optimizer 需求

### 8.1 P0 optimizer

- COBYLA。
- Nelder-Mead。
- Powell。
- SPSA。

### 8.2 P1/P2 optimizer

- gradient descent with parameter-shift。
- Adam。
- Bayesian optimization for low-dimensional p。
- layerwise training。

### 8.3 Optimizer adapter

统一接口：

```python
class ClassicalOptimizer:
    def minimize(self, objective_fn, initial_theta, bounds, config) -> OptimizerResult:
        ...
```

需求：

- 支持 noisy objective。
- 支持 max evaluations / timeout。
- 每次 evaluation 必须可回调写入 trace。
- 对 multi-start，支持并行或顺序运行，结果可比较。

## 9. Measurement 与后处理

### 9.1 Counts 转 samples

输入：

```python
counts = {"0101": 123, "1100": 41}
```

输出：

- bitstring。
- probability。
- count。
- classical energy。
- decoded logical solution。
- feasibility。
- objective without penalties。

### 9.2 排序规则

沿用路线 2/3：

1. hard feasible 优先。
2. feasible 内按原始 objective。
3. infeasible 内按 violation。
4. 再按 QAOA measured energy / probability。

### 9.3 Aggregation

优化目标支持：

- `mean`: 对所有测量样本的 Hamiltonian energy 求均值。
- `best_sample`: 用当前 batch 最好样本，P1。
- `cvar(alpha)`: 只聚合最低能量 alpha 分位样本，P1/P2。

P0 默认 `mean`，但最终解选择必须使用 feasibility-first ranking。

## 10. Diagnostics

每次 run 前输出：

- qubit count。
- cost terms。
- ZZ terms。
- estimated circuit depth。
- estimated two-qubit gates。
- QUBO coefficient range。
- penalty/objective ratio。
- p。
- shots。
- optimizer max_evals。
- expected total circuit executions。
- statevector eligibility。
- exact comparison eligibility。

每次 run 后输出：

- optimizer evaluations。
- total shots。
- best estimated energy。
- best feasible objective。
- feasible sample ratio。
- unique sample count。
- measurement entropy。
- runtime split。
- parameter trace summary。

关键 warnings：

- `dense_cost_layer_warning`: ZZ terms 过多。
- `penalty_dominated_warning`: penalty 系数压制目标。
- `shot_noise_warning`: repeated evaluation variance 高。
- `barren_plateau_risk`: gradient/energy variance 过低。
- `hardware_depth_warning`: transpiled depth 超过 backend 建议阈值。
- `hard_constraint_penalty_warning`: 建议 route 5 constrained mixer。

## 11. API 草案

```python
qubo_model = QuboBuilder().build(problem)

hamiltonian = CostHamiltonianBuilder(
    convention="bit_to_pauli_z"
).from_qubo(qubo_model)

runner = QaoaRunner(
    backend=ShotSimulatorBackend(),
    optimizer=ScipyOptimizer("COBYLA"),
    postprocessor=SolutionPostprocessor(enable_repair=True),
)

result = runner.solve(
    hamiltonian,
    config=QaoaConfig(
        p=2,
        shots=2048,
        seed=42,
        initialization=RandomInitializer(num_starts=5),
        max_evals=150,
        return_top_k=20,
    ),
)

best = result.best_feasible_solution
trace = result.optimizer_trace
```

Statevector exact comparison：

```python
exact = ExactDiagonalization().solve(hamiltonian)
qaoa = QaoaRunner(backend=StatevectorQaoaBackend()).solve(hamiltonian, config)
compare_exact(qaoa, exact)
```

## 12. 测试需求

### 12.1 单元测试

- QUBO -> Hamiltonian energy 等价。
- Ising -> Hamiltonian 符号约定正确。
- single Z term circuit 符号正确。
- ZZ term circuit 符号正确。
- X mixer `RX` 参数约定正确。
- parameter vector encode/decode。
- random initializer seed 可复现。
- counts -> decoded samples 正确。
- feasibility-first ranking 正确。
- optimizer trace 完整。

### 12.2 集成测试

小规模样例：

- 2-qubit MaxCut / MinCut 符号测试。
- at-most-one selection with penalty。
- exactly-one selection with penalty。
- small knapsack。
- graph coloring toy QUBO。

验收：

- statevector backend 的 energy expectation 与手工矩阵计算一致。
- `p=1` QAOA 能产生可行样本。
- fixed seed 下 result 可复现。
- 对小规模问题，best feasible 与 brute force optimum 的 gap 在配置阈值内。
- penalty 太小的构造能通过 diagnostics 或 postprocessor 暴露 infeasible risk。

### 12.3 Benchmark

指标：

- best feasible objective。
- approximation gap if exact known。
- feasible sample ratio。
- unique feasible samples。
- optimizer evaluations。
- total shots。
- time to best feasible。
- circuit depth。
- two-qubit gate count。
- parameter initialization strategy。

对比对象：

- ExactSolver。
- SimulatedAnnealingBackend。
- RandomSampler。
- QAOA p=1/2/3。
- 不同 initializer。

## 13. 开发优先级

### P0

- `CostHamiltonianBuilder`
- `QaoaAnsatzSpec`
- `StatevectorQaoaBackend`
- `ShotSimulatorBackend`
- COBYLA / Nelder-Mead / SPSA adapter。
- random / fixed initializer。
- measurement decoder。
- QAOA result schema。
- diagnostics。
- exact small-instance comparison。

### P1

- Qiskit Aer adapter。
- linear ramp initializer。
- parameter transfer p-to-p+1。
- multi-start benchmark。
- CVaR aggregation。
- circuit resource estimator。

### P2

- parameter-shift gradient。
- hardware backend adapter。
- measurement mitigation hook。
- warm-start parameter hook。
- result persistence and experiment registry。

### P3

- ADAPT-QAOA。
- FALQON。
- hardware-aware transpilation optimizer。
- automatic ansatz variant recommendation。

## 14. 主要风险与规避

**风险 1：Hamiltonian 符号约定错误。**  
规避：固定 `x=(1-Z)/2` convention；所有 QUBO/Hamiltonian/circuit energy 做 truth-table 测试。

**风险 2：把 lowest measured energy 当最终业务解。**  
规避：统一 postprocessor，必须 decode、check feasibility、按原始 objective 排序。

**风险 3：optimizer 被 shot noise 误导。**  
规避：记录 variance；支持 repeated evaluation；默认 derivative-free optimizer；足够 shots 和 multi-start。

**风险 4：QAOA 对 penalty 权重敏感。**  
规避：复用路线 2 penalty diagnostics；必要时切换 route 5 constrained mixer。

**风险 5：dense QUBO 导致线路过深。**  
规避：资源估计；提示 decomposition、sparse reformulation 或 route 6。

**风险 6：barren plateau 或参数优化停滞。**  
规避：限制 P0 问题规模；使用低 p、multi-start、linear ramp 和 parameter transfer。

## 15. 参考文献

Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A quantum approximate optimization algorithm*. arXiv:1411.4028.

Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A quantum approximate optimization algorithm applied to a bounded occurrence constraint problem*. arXiv:1412.6062.

Moll, N., Barkoutsos, P., Bishop, L. S., Chow, J. M., Cross, A., Egger, D. J., Filipp, S., Fuhrer, A., Gambetta, J. M., Ganzhorn, M., Kandala, A., Mezzacapo, A., Muller, P., Riess, W., Salis, G., Smolin, J., Tavernelli, I., & Temme, K. (2018). Quantum optimization using variational algorithms on near-term quantum devices. *Quantum Science and Technology, 3*(3), 030503.

Zhou, L., Wang, S.-T., Choi, S., Pichler, H., & Lukin, M. D. (2020). Quantum approximate optimization algorithm: Performance, mechanism, and implementation on near-term devices. *Physical Review X, 10*(2), 021067.

Blekos, K., Brand, D., Ceschini, A., Chou, C.-H., Li, R.-H., Pandya, K., & Summer, A. (2024). A review on quantum approximate optimization algorithm and its variants. *Physics Reports, 1068*, 1-66.

Cerezo, M., Arrasmith, A., Babbush, R., Benjamin, S. C., Endo, S., Fujii, K., McClean, J. R., Mitarai, K., Yuan, X., Cincio, L., & Coles, P. J. (2021). Variational quantum algorithms. *Nature Reviews Physics, 3*, 625-644.
