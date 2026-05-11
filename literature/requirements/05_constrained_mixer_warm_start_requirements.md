# 开发需求文档：Constrained Mixer / Warm-start / XY Mixer 可行空间搜索路线

更新日期：2026-05-12

## 1. 文档目标

本需求文档面向开发人员，定义一套约束保持的 QAOA 扩展模块：让量子线路从可行初态出发，并通过 constrained mixer、XY mixer、warm-start mixer、recursive variable fixing 等机制尽量在可行空间内搜索，减少对大罚函数的依赖。

第一阶段不绑定具体业务场景，重点覆盖通用结构：one-hot、exactly-one、exactly-k、fixed Hamming weight、互斥选择组和小规模自定义可行状态集合。该路线依赖路线 1 的 Hamiltonian 建模、路线 2 的结构化约束元数据、路线 4 的 QAOA runner，以及路线 6 的 relaxation / warm-start metadata。

## 2. 精读论文与可开发结论

### 2.1 Hadfield et al. 2019：Quantum Alternating Operator Ansatz

**核心结论**：标准 QAOA 的 X mixer 会在整个 bitstring 空间中演化，因此硬约束通常只能通过 penalty 加到 cost Hamiltonian。Quantum Alternating Operator Ansatz 把 mixer 设计提升为核心模块：mixer 应保持 feasible subspace，并在可行解之间提供足够的连通性。

**对开发的直接要求**：

- 必须从路线 2 接收 `FeasibleSubspaceSpec`，不能只接 QUBO。
- constrained mixer 要声明两个性质：
  - `preserves_feasibility`: 从可行态出发不会离开可行空间。
  - `connects_feasible_states`: 可行态图连通或至少给出连通性诊断。
- 初始态必须是可行态或可行态叠加。
- one-hot 编码虽然 qubit 多，但对 mixer 编译更简单；binary encoding 不应默认用于 constrained mixer。
- 对每个 mixer，需要同时提供 abstract transition graph 和 circuit implementation metadata。

### 2.2 Fuchs et al. 2022：Constraint preserving mixers

**核心结论**：penalty QAOA 可能输出不可行解，并且对 penalty 权重非常敏感。constrained mixer 可以把演化限制在可行基态张成的子空间内，但 mixer 的 Trotterization、basis gate decomposition 和 transition connectivity 会影响实际性能。

**对开发的直接要求**：

- `MixerStrategy` 必须能描述 feasible basis states 或可行态生成规则。
- 对小可行空间，可通过 feasible state list 构造 transition matrix。
- 对 one-hot / fixed Hamming weight，优先使用结构化 XY mixer，而不是枚举所有可行态。
- Trotterized mixer 必须有连通性检查；不能假设 Hamiltonian 连通就代表分解后的 circuit 也连通。
- diagnostics 必须记录 mixer gate count、CX count、Trotter repetitions 和 transition graph connectivity。

### 2.3 Egger, Mareček, Woerner 2021：Warm-start QAOA

**核心结论**：classical relaxation 可给 QAOA 提供更好的初始分布。标准 warm-start QAOA 用 continuous relaxation solution `c_i in [0,1]` 生成 biased single-qubit initial state，并调整 mixer Hamiltonian，使初态是 mixer 的 ground state。对开发而言，warm-start 不只是传入一个 bitstring，而是一组概率、角度、regularization 和 mixer 变更。

**对开发的直接要求**：

- 需要 `WarmStartStateSpec`，至少支持：
  - continuous relaxation values。
  - rounded bitstring。
  - per-variable probability。
  - clipping epsilon。
  - confidence score。
- 对标准 unconstrained QAOA，warm-start 初态和 mixer 必须成对构造。
- 当 `c_i` 接近 0 或 1 时，必须使用 epsilon clipping，避免 qubit 被锁死而无法探索。
- route 6 的 relaxation solver 应能导出本路线需要的 warm-start metadata。

### 2.4 Bucher et al. 2026：Iterative warm-start XY mixers

**核心结论**：XY mixer 可以保持 one-hot / Hamming-weight 约束，但直接把 warm-start bias 放到初态上会破坏“初态是 mixer ground state”的对齐性质。warm-start XY 需要根据 one-hot 概率分布同步构造初态和 mixer。论文还强调硬件噪声仍会产生 infeasible measurement，因此 repair/postprocessing 仍不可省略。

**对开发的直接要求**：

- 对 one-hot group 的 warm-start，输入应是 group 内概率分布 `P_i`，不是独立 Bernoulli 概率。
- warm-start XY mixer 需要校验：
  - `P_i >= 0`
  - `sum_i P_i = 1`
  - clipping 后仍保持归一化。
- 必须记录 initial-state / mixer alignment。
- 支持 iterative warm-start：从上一轮 samples 更新 group probability，再重新运行 QAOA。
- 即便 mixer 理论上保持可行性，硬件或模拟近似导致的 infeasible samples 仍要交给路线 2 repair。

### 2.5 Bravyi et al. 2020：R-QAOA 与相关性舍入

**核心结论**：R-QAOA 用 QAOA 估计变量相关性，然后递归加入变量相关/反相关约束，消去变量，直到剩余问题足够小再用经典算法求解。它不是 mixer，而是一种 hybrid variable fixing / problem reduction 策略。

**对开发的直接要求**：

- `RecursiveQaoaReducer` 应作为独立组件，不放进 `MixerStrategy`。
- 需要从 measurement 或 expectation 中估计 `corr(i,j)=<Z_i Z_j>`。
- 每次消元要保存：
  - eliminated variable。
  - kept variable。
  - relation: same / opposite。
  - confidence。
  - energy offset update。
  - reverse decode map。
- 剩余变量数小于阈值 `n_cutoff` 后调用 exact solver / SA / MILP fallback。
- 对高阶项或复杂约束，变量消元可能增加项阶数，必须调用路线 1 quadratization 或拒绝该 reduction。

## 3. 模块边界

### 3.1 本模块负责

- constrained ansatz / mixer 策略接口。
- feasible initial state 构造。
- one-hot / exactly-k / fixed-Hamming-weight XY mixer。
- warm-start state 与 warm-start mixer metadata。
- iterative warm-start loop。
- R-QAOA variable reduction。
- constrained QAOA diagnostics。
- 与路线 2 feasibility checker / repair 联动。

### 3.2 本模块不负责

- 基础 QUBO / Ising 构造，沿用路线 1。
- penalty strategy 和 repair 具体实现，沿用路线 2。
- 标准 X-mixer QAOA runner，沿用路线 4。
- relaxation 求解，沿用路线 6。
- 真实硬件 provider 细节。

## 4. 核心数据结构需求

### 4.1 `FeasibleSubspaceSpec`

由路线 2 导出，本路线消费。

字段建议：

- `subspace_type`: `one_hot_groups | exactly_k | fixed_hamming_weight | feasible_state_list | custom`
- `groups`: list of variable groups。
- `k`: exactly-k 或 Hamming weight。
- `logical_to_qubit_map`
- `encoding`: `one_hot | binary | domain_wall | custom`
- `initial_feasible_assignment`
- `feasible_state_count`
- `constraints_covered`
- `constraints_not_covered`

需求：

- 必须区分“被 mixer 保持的硬约束”和“仍需 penalty/repair 的约束”。
- 对多个 group，明确 group 是否 disjoint。非 disjoint group 第一版不支持 XY mixer 自动处理。
- 可序列化为 JSON，便于 QAOA experiment registry 复现。

### 4.2 `MixerStrategy`

统一接口：

```python
class MixerStrategy:
    name: str

    def supports(self, subspace: FeasibleSubspaceSpec) -> bool:
        ...

    def build_mixer(self, subspace, config) -> MixerBuildResult:
        ...

    def build_initial_state(self, subspace, warm_start=None) -> InitialStateSpec:
        ...

    def diagnostics(self) -> MixerDiagnostics:
        ...
```

策略清单：

- `XMixerStrategy`: route 4 标准路线。
- `OneHotXYMixerStrategy`
- `FixedHammingWeightXYMixerStrategy`
- `FeasibleStateGraphMixerStrategy` P2。
- `WarmStartXYMixerStrategy` P2。
- `CustomMixerStrategy` P3。

### 4.3 `MixerBuildResult`

字段建议：

- `mixer_hamiltonian_terms`
- `mixer_circuit_template`
- `transition_graph`
- `preserves_feasibility`
- `connectivity_status`
- `covered_constraints`
- `requires_initial_state`
- `trotterization`
- `resource_estimate`
- `warnings`

### 4.4 `InitialStateSpec`

字段建议：

- `state_type`: `basis_state | plus_state | w_state | weighted_w_state | custom_circuit`
- `basis_assignment`
- `group_probabilities`
- `state_prep_circuit`
- `depth_estimate`
- `is_feasible`
- `is_mixer_ground_state`

需求：

- 若 `is_feasible=false`，constrained QAOA runner 必须拒绝执行。
- warm-start XY 必须检查 `is_mixer_ground_state=true` 或给出 alignment warning。

### 4.5 `WarmStartStateSpec`

字段建议：

- `source`: `relaxation | rounded_solution | samples | user`
- `continuous_values`
- `group_probabilities`
- `rounded_assignment`
- `epsilon`
- `confidence`
- `iteration`
- `metadata`

需求：

- 对 independent binary warm-start，概率是 per bit。
- 对 one-hot group warm-start，概率是 group 内 categorical distribution。
- clipping 后必须重新归一化。

### 4.6 `RecursiveReductionState`

用于 R-QAOA：

- `current_model`
- `elimination_history`
- `reverse_decode_map`
- `energy_offset`
- `current_num_variables`
- `correlation_estimates`
- `cutoff`

## 5. 支持的约束与默认 mixer

### 5.1 One-hot / Exactly-one

形式：

```text
sum_{i in G} x_i = 1
```

默认 mixer：

- `OneHotXYMixerStrategy`

初始态：

- equal W-state：

```text
|W_G> = 1/sqrt(|G|) * sum_i |e_i>
```

或 weighted W-state P2：

```text
|W_P> = sum_i sqrt(P_i) |e_i>
```

需求：

- 每个 one-hot group 使用 group 内 XY mixer。
- 多个 disjoint one-hot groups 的初态是各 group W-state 的 tensor product。
- 如果 group 共享变量，P0/P1 不自动支持，转 penalty 或 custom mixer。

### 5.2 Exactly-k / Fixed Hamming Weight

形式：

```text
sum_i x_i = k
```

默认 mixer：

- `FixedHammingWeightXYMixerStrategy`

初始态：

- 任一 Hamming weight k 的 basis state P0。
- equal superposition over weight-k states P2。

需求：

- P0 可从一个可行 bitstring 出发，用 XY mixer 在固定 Hamming-weight sector 内搜索。
- 需要 transition graph connectivity 检查，确保 chosen topology 能连接所有 weight-k feasible states。
- 对 ring topology 与 full topology 输出不同 gate count。

### 5.3 At-most-one

形式：

```text
sum_i x_i <= 1
```

默认建议：

- 如果允许 all-zero，固定 Hamming weight mixer 不直接适用。
- P0 继续使用 penalty / repair。
- P2 可引入 extended one-hot：增加 dummy variable，把 `<=1` 转为 `exactly-one`。

### 5.4 Bounded sum / knapsack inequality

形式：

```text
a^T x <= b
```

默认建议：

- P0/P1 不做通用 constrained mixer。
- 使用路线 2 unbalanced/slack penalty 或路线 6 decomposition。
- 若小规模可枚举 feasible states，可用 `FeasibleStateGraphMixerStrategy` P2。

### 5.5 Custom feasible state list

适用：

- 小规模局部约束。
- 业务子结构可枚举。

需求：

- 输入 feasible bitstrings list。
- 构造 transition graph。
- 检查 graph connected。
- 若 feasible state count 太大，拒绝并建议结构化 mixer。

## 6. Mixer 构造需求

### 6.1 XY mixer

基础两 qubit hopping term：

```text
X_i X_j + Y_i Y_j
```

性质：

- 保持 Hamming weight。
- 对 one-hot group，保持 exactly-one。
- 对 exactly-k group，保持固定 k。

需求：

- 支持 topology：
  - `complete`
  - `ring`
  - `line`
  - `hardware_graph`
- 支持 decomposition metadata：
  - native XY gate。
  - CNOT/RZ decomposition。
  - iSWAP-like native gate P2。
- 输出 gate count 和 depth estimate。

### 6.2 Trotterization

需求：

- 支持 `trotter_steps`。
- 支持 even/odd edge partition。
- 对分解后的 transition graph 做连通性测试。
- 如果 Trotterization 破坏连通性，输出 warning 或自动增加 mixer repetition。

### 6.3 Mixer transition graph

每个 mixer 都要能生成抽象图：

- nodes: feasible basis states 或 compressed states。
- edges: mixer 可达 transition。

诊断：

- connected components。
- diameter。
- degree distribution。
- isolated states。
- coverage of feasible states。

对大规模 fixed-Hamming-weight 可用组合公式估计，不必枚举所有节点。

## 7. Warm-start 需求

### 7.1 标准 binary warm-start

输入：

```text
c_i in [0,1]
```

初态：

```text
sqrt(1-c_i)|0> + sqrt(c_i)|1>
```

需求：

- 使用 epsilon clipping：

```text
c_i <- min(max(c_i, epsilon), 1 - epsilon)
```

- 构造与初态对齐的 mixer。
- 如果只设置初态、不设置 warm-start mixer，输出 warning。

### 7.2 One-hot warm-start

输入：

```text
P_G = [P_1, ..., P_k], sum(P_i)=1
```

初态：

```text
|W_P> = sum_i sqrt(P_i)|e_i>
```

需求：

- 概率来自 route 6 relaxation / prior solution / previous samples。
- 对每个 group 单独归一化。
- 支持 epsilon smoothing：

```text
P_i <- (1 - k*epsilon) * P_i + epsilon
```

然后重新归一化。

### 7.3 Warm-start XY mixer

需求：

- 与 weighted W-state 对齐。
- 记录 `initial_state_mixer_alignment=true`。
- 如果 backend 只支持 standard XY mixer，则允许 fallback，但必须标记 `alignment_broken=true`。
- P2 实现完整 warm-start XY Hamiltonian；P1 可先只实现 weighted initial state + warning。

### 7.4 Iterative warm-start

流程：

```text
initial probabilities from relaxation or uniform
for t in 1..T:
    build weighted initial state and mixer
    run constrained QAOA
    postprocess samples
    update probabilities from elite feasible samples
return best feasible solution
```

概率更新策略：

- elite top-k frequency。
- softmax of objective。
- exponential moving average。
- CVaR-weighted update P2。

需求：

- 每轮保存 probability history。
- 防止概率塌缩到 0/1，使用 smoothing。
- 每轮后必须输出 feasible ratio 和 best feasible objective。

## 8. R-QAOA / Recursive Variable Fixing 需求

### 8.1 输入

- Ising/QUBO cost model。
- 可选约束元数据。
- QAOA runner。
- cutoff `n_cutoff`。
- correlation threshold。

### 8.2 单步 reduction

流程：

```text
run QAOA on current model
estimate correlations <Z_i Z_j>
select pair with max |corr|
impose relation:
    Z_j = sign(corr) * Z_i
substitute and eliminate Z_j
update energy offset
record reverse mapping
```

需求：

- 支持 pairwise Ising P1。
- 对 QUBO 先转换到 Ising。
- 对消元后出现的高阶项，调用 quadratization 或拒绝。
- 如果 max correlation 低于阈值，可停止递归或改用 fallback。

### 8.3 终止与回代

终止：

- `num_variables <= n_cutoff`
- max recursion reached。
- correlation confidence too low。
- time limit reached。

剩余问题：

- exact solver。
- SA。
- MILP fallback。

回代：

- 根据 elimination history 恢复所有变量。
- 重新计算 original objective。
- 跑 feasibility checker。

## 9. Constrained QAOA 求解流程

推荐流程：

```text
OptimizationProblem
  -> route 2 ConstraintCompiler exports FeasibleSubspaceSpec
  -> route 1 CostHamiltonianBuilder builds cost Hamiltonian without covered hard penalties
  -> MixerStrategy selected from subspace
  -> InitialStateBuilder creates feasible initial state
  -> ConstrainedQaoaRunner:
       build phase separator
       build constrained mixer layers
       optimize parameters
       measure
  -> route 2 postprocess:
       feasibility check for all constraints
       repair if needed
       rank feasible samples
```

关键原则：

- 被 mixer 覆盖的硬约束不应再加大 penalty，避免重复扭曲目标。
- 未被 mixer 覆盖的硬约束仍可使用 penalty 或后处理。
- 所有最终样本都必须检查完整原始约束。

## 10. Diagnostics

必须输出：

- covered hard constraints。
- uncovered hard constraints。
- feasible subspace type。
- group count。
- group sizes。
- initial state type。
- initial state feasibility。
- mixer type。
- mixer topology。
- preserves feasibility。
- transition graph connected。
- circuit depth estimate。
- two-qubit gate count。
- Trotter steps。
- warm-start alignment。
- probability smoothing epsilon。
- feasible sample ratio。
- infeasible sample count after measurement。

关键 warnings：

- `unsupported_shared_group_warning`: one-hot groups 共享变量。
- `transition_graph_disconnected`: mixer 无法连通全部可行解。
- `initial_state_infeasible`: 初态不满足 hard constraints。
- `alignment_broken`: warm-start 初态不是 mixer ground state。
- `trotter_connectivity_warning`: 分解后缺失 transition。
- `noise_infeasible_warning`: 理论保持可行但测量/硬件结果不可行。

## 11. API 草案

Constrained QAOA：

```python
compiled = ConstraintCompiler().compile(problem)
subspace = compiled.export_feasible_subspace()

hamiltonian = CostHamiltonianBuilder().from_problem(
    problem,
    exclude_constraints=subspace.constraints_covered,
)

mixer = OneHotXYMixerStrategy(topology="ring")

runner = ConstrainedQaoaRunner(
    backend=ShotSimulatorBackend(),
    optimizer=ScipyOptimizer("COBYLA"),
    mixer_strategy=mixer,
    postprocessor=SolutionPostprocessor(enable_repair=True),
)

result = runner.solve(
    hamiltonian,
    subspace=subspace,
    config=ConstrainedQaoaConfig(p=2, shots=2048, seed=42),
)
```

Warm-start one-hot：

```python
warm = WarmStartStateSpec(
    source="relaxation",
    group_probabilities={
        "color[v0]": [0.7, 0.2, 0.1],
        "color[v1]": [0.1, 0.6, 0.3],
    },
    epsilon=0.02,
)

mixer = WarmStartXYMixerStrategy(topology="complete")
result = runner.solve(hamiltonian, subspace=subspace, warm_start=warm, config=config)
```

R-QAOA：

```python
reducer = RecursiveQaoaReducer(
    qaoa_runner=QaoaRunner(...),
    cutoff=20,
    min_abs_correlation=0.2,
    fallback_solver=ExactSolverBackend(),
)

result = reducer.solve(ising_model, config=RecursiveQaoaConfig(p=1, shots=4096))
solution = result.decode_full_assignment()
```

## 12. 测试需求

### 12.1 单元测试

- `FeasibleSubspaceSpec` disjoint group 检查。
- one-hot W-state bitstrings 全部 Hamming weight 1。
- XY mixer 保持 Hamming weight。
- fixed-Hamming-weight topology connectivity。
- weighted probability clipping 和归一化。
- initial-state / mixer alignment flag。
- Trotter edge partition 不丢边。
- R-QAOA pair elimination energy offset 正确。
- reverse decode map 正确。

### 12.2 集成测试

建议样例：

- 3-bit exactly-one selection。
- 4-bit exactly-k selection。
- two one-hot groups with quadratic cost。
- small graph coloring one-hot toy。
- penalty QAOA vs XY-QAOA 对比。
- warm-start one-hot 概率偏置测试。
- R-QAOA small Ising graph。

验收：

- constrained mixer 在 noiseless simulator 中测量样本全部满足 covered constraints。
- 若加入未覆盖约束，postprocessor 能识别违反。
- warm-start XY 不破坏 one-hot feasibility。
- iterative warm-start 至少记录多轮 probability history。
- R-QAOA 回代后的 full assignment 与 reduced problem energy 对齐。

### 12.3 Benchmark

指标：

- best feasible objective。
- feasible sample ratio。
- covered-constraint violation rate。
- uncovered-constraint violation rate。
- probability of sampling optimum if known。
- circuit depth。
- two-qubit gate count。
- optimizer evaluations。
- total shots。
- time to best feasible。

对比对象：

- penalty QAOA + X mixer。
- one-hot XY-QAOA。
- warm-start XY-QAOA。
- SA / exact baseline。
- R-QAOA vs standard QAOA on small Ising。

## 13. 开发优先级

### P0

- `FeasibleSubspaceSpec` consumer。
- `MixerStrategy` 接口。
- `InitialStateSpec`。
- one-hot group validation。
- basic XY mixer metadata。
- constrained runner 与 route 4 runner 的接口打通。
- full feasibility postprocessing。

### P1

- executable one-hot XY mixer circuit。
- fixed-Hamming-weight XY mixer。
- transition graph diagnostics。
- ring / complete topology。
- penalty QAOA vs constrained QAOA benchmark。

### P2

- weighted W-state。
- warm-start XY mixer。
- iterative warm-start loop。
- feasible-state-list mixer。
- R-QAOA pairwise Ising reducer。

### P3

- custom mixer synthesis。
- shared-variable constraint mixer。
- hardware-native XY gate compilation。
- CVaR iterative warm-start。
- high-order R-QAOA with quadratization integration。

## 14. 主要风险与规避

**风险 1：初态不可行导致 constrained mixer 失效。**  
规避：runner 启动前强制检查 initial state feasibility。

**风险 2：mixer 保持可行但不可连通。**  
规避：transition graph connectivity diagnostics；必要时换 topology 或增加 mixer repetitions。

**风险 3：warm-start 只改初态破坏 mixer alignment。**  
规避：`InitialStateSpec.is_mixer_ground_state` 必填；不对齐则 warning 或拒绝严格模式。

**风险 4：covered constraints 和 penalty 重复计算。**  
规避：CostHamiltonianBuilder 接收 `exclude_constraints`，文档化哪些约束由 mixer 覆盖。

**风险 5：硬件噪声产生 infeasible samples。**  
规避：所有结果仍走 route 2 feasibility checker 和 repair。

**风险 6：R-QAOA 消元使模型复杂化。**  
规避：P1 只支持 pairwise Ising；高阶项交给路线 1 quadratization 或停止 reduction。

## 15. 参考文献

Hadfield, S., Wang, Z., O'Gorman, B., Rieffel, E. G., Venturelli, D., & Biswas, R. (2019). From the quantum approximate optimization algorithm to a quantum alternating operator ansatz. *Algorithms, 12*(2), 34.

Fuchs, F. G., Lye, K. O., Nilsen, H. M., Stasik, A. J., & Sartor, G. (2022). Constraint preserving mixers for the quantum approximate optimization algorithm. *Algorithms, 15*(6), 202.

Egger, D. J., Mareček, J., & Woerner, S. (2021). Warm-starting quantum optimization. *Quantum, 5*, 479.

Bucher, D., Janetschek, M., Poppel, M., Stein, J., Linnhoff-Popien, C., & Feld, S. (2026). Constrained quantum optimization via iterative warm-start XY-mixers. arXiv:2604.02083.

Bravyi, S., Kliesch, A., Koenig, R., & Tang, E. (2020). Obstacles to state preparation and variational optimization from symmetry protection. *Physical Review Letters, 125*(26), 260505.
