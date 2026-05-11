# 开发需求文档：约束处理、编码与罚函数调参

更新日期：2026-05-12

## 1. 文档目标

本需求文档面向开发人员，定义通用混合整数约束优化中的“约束处理层”。它位于路线 1 的 QUBO / Ising 建模底座之上，负责把 equality、inequality、cardinality、one-hot、mutual exclusion、bounded sum、soft constraint 等约束转成可求解的 QUBO/BQM/Ising 表示，或为后续 constrained mixer / hybrid solver 提供结构化约束信息。

第一阶段不绑定具体业务场景，目标是让写代码的人能实现一套稳定的约束模块：可以选择编码策略、自动生成 penalty、诊断变量爆炸和系数范围、检查样本可行性、对 infeasible sample 做排序和基础 repair。

## 2. 精读论文与可开发结论

### 2.1 Hen & Spedalieri 2016：约束保持 driver 的启发

**核心结论**：传统 penalty-based 方法会把约束平方后加入目标函数，但这通常带来 all-to-all connectivity、额外 energy scale、硬件动态范围缩小和 minor embedding 负担。作者提出构造与约束对易的 driver Hamiltonian，使演化限制在可行子空间内，从而避免 penalty 项。

**对开发的直接要求**：

- 约束模块不能只输出 QUBO penalty，还要保留机器可读的 `ConstraintSpec`，供路线 5 的 constrained mixer 或路线 6 的 hybrid decomposition 使用。
- diagnostics 必须报告 penalty 引入的 coupler 数、系数尺度、约束项与原目标项的比例。
- 对 cardinality / one-hot / fixed-Hamming-weight 类约束，应标记 `preservable_by_mixer=true`，方便后续使用 XY mixer 或其他 feasible-subspace 方法。
- 对硬约束，不能默认相信 penalty 一定足够；构建后必须支持小规模 brute force 验证 ground state 是否可行。

**边界说明**：本路线第一版仍以 penalty/QUBO 编码为主；constraint-preserving driver 与 mixer 的电路实现归路线 5。但本模块必须提供足够的约束元数据。

### 2.2 Montanez-Barrera et al. 2022/2023：Unbalanced penalization

**核心结论**：不等式约束常用 binary slack 转为等式，但 slack variables 会增加 qubit 数、搜索空间和连接数。Unbalanced penalization 不引入 slack，通过非对称罚函数让违反不等式的一侧惩罚更强，可以显著降低资源消耗。其代价是 ground-state guarantee 弱于严格 slack 方法，最优可行解可能位于 near-ground-state，而不是总在 ground state。

**建议实现公式**：

对 `a^T x <= b`，定义 residual：

```text
h(x) = b - a^T x
```

采用二次 unbalanced penalty：

```text
penalty(x) = -lambda1 * h(x) + lambda2 * h(x)^2
```

其中 `lambda1 > 0`、`lambda2 > 0`，违反约束时 `h(x) < 0`，线性项与二次项共同抬高能量；满足约束但 slack 较大时可能产生非零能量，因此它是 heuristic encoding。

**对开发的直接要求**：

- `UnbalancedInequalityPenalty` 必须作为独立策略，不能替代默认 slack penalty。
- 解排序不能只按 QUBO energy。必须先过滤/标记 feasibility，再按原始 objective 排序。
- 对 unbalanced penalty 输出风险标记：`ground_state_not_guaranteed=true`。
- 参数 `lambda1`、`lambda2` 必须可配置，支持 grid search / sweep。
- benchmark 必须比较：
  - slack variable 数量。
  - total binary variables。
  - coupler 数。
  - feasible sample ratio。
  - best feasible objective。
  - best QUBO energy 是否可行。

### 2.3 Chancellor 2019：Domain-wall encoding

**核心结论**：离散变量不一定只能用 binary encoding 或 one-hot encoding。Domain-wall encoding 用 `N-1` 个 qubit 表示 `N` 个取值，利用一维 Ising chain 中 domain wall 的位置编码离散值。它可以用 two-body Ising terms 表达任意两个离散变量之间的相互作用，并且变量内部只需要线性连接来保持有效编码。

**对开发的直接要求**：

- 需要抽象 `EncodingStrategy`，至少覆盖 `binary`、`one_hot`、`domain_wall` 三类。
- 对 domain-wall 的实现要区分两层：
  - variable core：保证编码 bitstring 是合法 domain-wall 状态。
  - value interaction：把特定离散取值的一元/二元代价映射到 qubit 项。
- 由于实现复杂，domain-wall 建议放 P2/P3，但数据结构必须从第一版预留。
- 对任意离散变量 `v in {0, ..., N-1}`，编码策略需要返回：
  - `bits`
  - `decode(bits) -> value`
  - `validity_penalty`
  - `value_indicator(value)`
  - `pairwise_value_interaction(value_i, value_j, coeff)`

### 2.4 Chen, Stollenwerk, Chancellor 2021：Domain-wall 性能评估

**核心结论**：在 quantum annealing 实验中，domain-wall encoding 相比 one-hot 在多个问题和指标上表现更好，通常减少 broken chains，提高正确 decode 的比例；但优势与问题结构相关，小规模容易问题上差距不明显。

**对开发的直接要求**：

- 不能硬编码“one-hot 永远默认最好”。应由 `EncodingAdvisor` 根据变量取值数、交互结构、求解器 backend 选择编码。
- diagnostics 要输出 `encoding_comparison`，至少估计每种编码的变量数、变量内部 coupler 数、跨变量 coupler 数和有效状态比例。
- 对 D-Wave / hardware-aware backend，应把 domain-wall 的 embedding 风险作为单独指标。

### 2.5 Fuchs et al. 2022 与 Bucher et al. 2026：与 constrained mixer 的接口边界

**核心结论**：QAOA 中处理约束有两条路：一是 penalty，二是构造保持可行子空间的 mixer。Penalty 方法简单但可能输出不可行解，对权重敏感；constrained mixer 能从可行初态出发并保持在可行子空间，但 mixer 设计、电路分解和 Trotterization 成本更复杂。Warm-start XY mixer 进一步说明：初态、mixer topology 和约束子空间必须对齐，否则会破坏收敛性质。

**对开发的直接要求**：

- 约束模块要能导出 `FeasibleSubspaceSpec`：
  - fixed Hamming weight。
  - one-hot groups。
  - exactly-k groups。
  - feasible state list for small custom constraints。
  - initial feasible assignment。
- 对路线 5，不应只传 QUBO；必须传结构化约束和编码映射。
- 对硬件噪声或近似求解器导致的 infeasible measurement，仍需要本模块的 feasibility checker 和 repair。

## 3. 模块边界

### 3.1 本模块负责

- 约束类型系统。
- 变量编码策略选择。
- penalty strategy 选择和构造。
- penalty 权重建议、扫描和诊断。
- slack / auxiliary variable 管理。
- feasible-subspace 元数据导出。
- 样本可行性检查、排序、基础 repair。
- 编码策略 benchmark。

### 3.2 本模块不负责

- QUBO sparse matrix 的底层表达，沿用路线 1。
- 退火器、QAOA、D-Wave 的求解实现。
- constrained mixer 电路构造。
- 大规模 MILP decomposition。
- 具体行业模型解析。

## 4. 核心数据结构需求

### 4.1 `ConstraintSpec`

字段建议：

- `name`
- `expression`: `LinearExpression | QuadraticExpression`
- `sense`: `== | <= | >=`
- `rhs`
- `constraint_type`: `equality | inequality | cardinality | one_hot | at_most_one | at_least_one | bounded_sum | indicator | custom`
- `hardness`: `hard | soft`
- `priority`: integer 或 enum。
- `variables`
- `metadata`

需求：

- 每条约束必须能独立计算 `lhs`、`violation`、`is_satisfied`。
- 必须支持 `normalize()`，例如把 `>=` 转成 `<=` 或标准 residual。
- 必须保留原始约束文本/结构，方便 debug 和导出。

### 4.2 `ConstraintEncodingPlan`

字段建议：

- `constraint_name`
- `strategy`: `square_penalty | binary_slack | unbalanced | known_pairwise | one_hot | domain_wall | custom_table | mixer_only`
- `penalty_weight`
- `introduced_variables`
- `introduced_terms`
- `expected_min_penalty_gap`
- `guarantee`: `exact_ground_state | heuristic_near_ground | feasible_subspace_only`
- `warnings`

需求：

- 每个 plan 要能解释“为什么选择这个策略”。
- 每个 plan 要可序列化为 JSON，方便 benchmark 和日志。
- strategy 选择结果必须可被用户覆盖。

### 4.3 `EncodingStrategy`

统一接口：

```python
class EncodingStrategy:
    name: str

    def encode_variable(self, var_spec) -> EncodedVariable:
        ...

    def decode(self, bits) -> Any:
        ...

    def validity_penalty(self, weight) -> QuadraticExpression:
        ...

    def indicator(self, value) -> QuadraticExpression:
        ...

    def diagnostics(self) -> EncodingDiagnostics:
        ...
```

第一版必须实现：

- `BinaryEncoding`
- `BoundedIntegerBinaryEncoding`
- `OneHotEncoding`
- `BinarySlackEncoding`

第二阶段实现：

- `DomainWallEncoding`
- `UnaryEncoding`
- `CustomDiscreteEncoding`

### 4.4 `PenaltyStrategy`

统一接口：

```python
class PenaltyStrategy:
    name: str

    def supports(self, constraint: ConstraintSpec) -> bool:
        ...

    def build(self, constraint, variables, config) -> PenaltyBuildResult:
        ...

    def guarantee(self) -> PenaltyGuarantee:
        ...
```

策略清单：

- `SquareEqualityPenalty`: `P * (lhs - rhs)^2`
- `BinarySlackInequalityPenalty`: `lhs + s = rhs`
- `KnownPairwisePenalty`: at-most-one、exactly-one、implication、equivalence 等 truth-table penalty。
- `UnbalancedInequalityPenalty`: 不引入 slack 的 heuristic inequality penalty。
- `CustomTruthTablePenalty`: 小变量局部约束的枚举拟合。
- `NoPenaltyFeasibleSubspace`: 标记给 constrained mixer 使用。

## 5. 约束类型与默认策略

### 5.1 Equality

形式：

```text
a^T x = b
```

默认策略：

```text
P * (a^T x - b)^2
```

适用范围：

- 变量数较少或 coupler 密度可接受。
- hard equality。
- one-hot / exactly-k 也可先用该策略实现。

风险：

- 展开后变量两两相连，可能形成 dense QUBO。
- 系数范围随 `a_i*a_j` 放大。

### 5.2 Inequality

形式：

```text
a^T x <= b
```

默认策略：

```text
a^T x + s = b, s >= 0
P * (a^T x + s - b)^2
```

slack 上界：

```text
s_max = b - min_possible(a^T x)
```

需求：

- 自动处理负系数。
- 若 `s_max < 0`，约束在变量边界内不可行，构建时直接报错。
- 若 slack bit 数过大，输出 `slack_blowup_warning`。

### 5.3 At-most-one

形式：

```text
sum_i x_i <= 1
```

默认 pairwise penalty：

```text
P * sum_{i<j} x_i*x_j
```

需求：

- 不需要 slack。
- 对 group size 很大时 coupler 数为 `O(n^2)`，需要 warning。
- 如果用于 one-hot 的上半部分，和 at-least-one 组合为 exactly-one。

### 5.4 Exactly-one / One-hot

形式：

```text
sum_i x_i = 1
```

默认策略：

```text
P * (sum_i x_i - 1)^2
```

展开后：

```text
P * (1 - sum_i x_i + 2 * sum_{i<j} x_i*x_j)
```

替代策略：

- one-hot encoding 作为变量编码。
- domain-wall encoding。
- constrained mixer 的 XY mixer。

### 5.5 Cardinality / Exactly-k

形式：

```text
sum_i x_i = k
```

默认策略：

```text
P * (sum_i x_i - k)^2
```

需求：

- 标记为 `fixed_hamming_weight=k`。
- 对 QAOA 可导出 XY mixer 约束元数据。
- repair 可以通过翻转若干 bit 使 Hamming weight 回到 k。

### 5.6 Bounded sum

形式：

```text
L <= a^T x <= U
```

默认策略：

- 拆成 `a^T x >= L` 与 `a^T x <= U`。
- 分别使用 slack 或 unbalanced penalty。

需求：

- 如果 `a_i` 全非负，可用更紧的 residual bound。
- 允许 `bounded_sum` 专用 repair：移除或加入变量直到回到范围内。

### 5.7 Indicator constraint

形式：

```text
y = 1 -> a^T x <= b
```

第一版建议：

- 不做自动 big-M QUBO 展开。
- 支持用户显式展开或作为 `custom constraint`。

第二阶段：

- 实现 binary indicator 的 big-M penalty。
- 对小规模局部 indicator 做 truth-table penalty synthesis。

## 6. Penalty 权重需求

### 6.1 默认权重估计

默认 penalty 应基于目标函数可能收益上界：

```text
objective_bound = sum(abs(linear_i)) + sum(abs(quadratic_ij)) + abs(offset)
P_default = scale * (objective_bound + 1)
```

建议：

- `scale=2` 作为起步。
- hard constraint 使用 `scale>=2`。
- soft constraint 由用户提供权重或使用较低 scale。

### 6.2 局部影响上界

对只涉及部分变量的约束，可以估计局部目标收益：

```text
local_bound(C) = sum(abs(linear_i for i in C.vars))
               + sum(abs(quadratic_ij if i or j in C.vars))
```

约束默认权重：

```text
P_C = scale * (local_bound(C) + 1)
```

需求：

- 提供 `global_bound` 和 `local_bound` 两种 advisor。
- 如果局部估计低于实际可能违反收益，应允许用户强制 `strict_global=true`。

### 6.3 Penalty sweep

必须提供自动扫描工具：

```python
results = penalty_sweep(
    problem,
    constraints=["capacity"],
    weights=[1, 2, 5, 10, 20, 50, 100],
    solver="bruteforce_or_sa",
)
```

输出：

- best feasible objective。
- best total energy。
- feasibility rate。
- average violation。
- coefficient range。
- recommended weight。

### 6.4 Unbalanced 参数调优

对 `UnbalancedInequalityPenalty`，支持：

- `lambda1`
- `lambda2`
- `lambda0` for equality 或组合场景。

调参策略：

- 小规模 brute force：要求 top-k energy 中包含原问题最优可行解。
- 中规模 sampling：要求 feasible sample ratio 与 best feasible objective 达到阈值。
- 不把“QUBO ground state 必可行”作为硬验收，除非参数扫描实际验证通过。

## 7. Feasibility Checker

### 7.1 输入输出

输入：

- bitstring。
- decoded logical assignment。
- original constraints。

输出：

```python
ConstraintCheckResult(
    name="capacity",
    lhs=12,
    sense="<=",
    rhs=10,
    violation=2,
    is_satisfied=False,
    penalty_energy=40,
)
```

总结果：

- `is_feasible`
- `num_violated`
- `total_violation_l1`
- `total_violation_l2`
- `hard_violation_count`
- `soft_violation_score`

### 7.2 样本排序规则

求解器返回样本后统一排序：

1. hard feasible 优先。
2. hard feasible 内按原始 objective 排序。
3. hard infeasible 内按 hard violation，再按原始 objective，再按 QUBO energy。
4. soft constraint violation 作为 tie-breaker 或业务自定义评分。

该排序对 unbalanced penalty 尤其重要，因为最优可行解不一定是 QUBO ground state。

## 8. Repair 需求

### 8.1 基础 repair 接口

```python
class RepairStrategy:
    def supports(self, constraints, assignment) -> bool:
        ...

    def repair(self, assignment, objective, constraints, config) -> RepairResult:
        ...
```

输出：

- repaired assignment。
- changed variables。
- original objective。
- repaired objective。
- feasibility before/after。
- repair reason。

### 8.2 必须实现的 repair

P1：

- `CardinalityRepair`: 对 exactly-k，按目标边际收益加入/移除变量。
- `AtMostOneRepair`: group 内保留收益最高或成本最低的一个 bit。
- `OneHotRepair`: 若全 0，选择局部目标最优 bit；若多 1，保留最优 bit。
- `BoundedSumGreedyRepair`: 对 `a^T x <= b`，按 value/weight 或局部目标损失移除变量。

P2：

- `LocalSearchRepair`: 在 repaired 解附近做 1-flip / 2-flip local search。
- `MILPPolishRepair`: 调用 OR-Tools/CP-SAT 或 scipy/milp 对小邻域修复。

### 8.3 Repair 约束

- repair 不能修改辅助变量和 slack 变量作为最终逻辑输出；它应直接操作 logical variables，再重新 encode。
- 每次 repair 都必须重新跑 feasibility checker。
- repair 后 objective 可能变差，必须显式记录。

## 9. Encoding Advisor

### 9.1 输入

- discrete variable cardinality。
- 是否需要任意 pairwise interaction。
- 是否有自然数值顺序。
- 求解器 backend：SA、QA、QAOA、hybrid。
- hardware constraints：connectivity、coefficient range、qubit budget。

### 9.2 输出

```python
EncodingRecommendation(
    variable="color[v3]",
    recommended="domain_wall",
    alternatives=["one_hot", "binary"],
    estimated_bits={"binary": 2, "one_hot": 4, "domain_wall": 3},
    estimated_couplers={...},
    reason="arbitrary pairwise discrete interactions and QA backend",
)
```

### 9.3 初始规则

- 纯数值 bounded integer，且目标/约束只依赖线性数值：优先 binary encoding。
- 离散类别变量，且需要 one-of-N：优先 one-hot，N 大时提示 domain-wall。
- 任意两个离散变量取值之间有 pairwise table cost：one-hot 或 domain-wall 优于 binary。
- QA/D-Wave backend 且 one-hot group 很大：建议评估 domain-wall。
- QAOA constrained mixer 需要 one-hot 或 fixed-Hamming-weight 结构：保留 one-hot 元数据，不急于压缩为 binary。

## 10. Diagnostics

每次 build 后必须输出：

- total logical variables。
- total encoded binary variables。
- slack variables。
- auxiliary variables。
- variables by encoding strategy。
- constraints by type。
- constraints by penalty strategy。
- introduced couplers per constraint。
- QUBO density before/after constraints。
- max/min coefficient。
- coefficient ratio。
- objective_bound。
- penalty_weight per constraint。
- estimated_min_violation_penalty。
- feasible-subspace metadata availability。
- warnings。

关键 warnings：

- `slack_blowup_warning`: slack bit 占比超过 30%。
- `dense_constraint_warning`: 单条约束引入 coupler 超过阈值。
- `penalty_too_small_risk`: penalty 小于目标收益上界。
- `penalty_too_large_risk`: penalty 与目标系数比例过大。
- `unbalanced_ground_state_warning`: unbalanced penalty 不保证 ground state 可行。
- `mixer_candidate`: 该约束适合路线 5 的 constrained mixer。

## 11. API 草案

```python
problem = OptimizationProblem(sense="minimize")
x = problem.add_binary_vars("x", 10)

problem.set_objective(linear={f"x[{i}]": -profits[i] for i in range(10)})
problem.add_constraint(
    linear={f"x[{i}]": weights[i] for i in range(10)},
    sense="<=",
    rhs=capacity,
    name="capacity",
    constraint_type="bounded_sum",
    hardness="hard",
)

config = ConstraintCompilerConfig(
    default_inequality_strategy="binary_slack",
    allow_unbalanced=True,
    penalty_advisor="local_bound",
    enable_repair=True,
)

compiled = ConstraintCompiler(config).compile(problem)
qubo = QuboBuilder().build(problem, compiled)
samples = sampler.sample(qubo)
ranked = SolutionPostprocessor(compiled).rank(samples)
best = ranked.best_feasible()
```

Unbalanced 使用：

```python
config = ConstraintCompilerConfig(
    strategy_overrides={
        "capacity": UnbalancedPenaltyConfig(lambda1=0.5, lambda2=2.0)
    },
    ranking="feasibility_first",
)
```

导出给 constrained mixer：

```python
subspace = compiled.export_feasible_subspace()
qaoa = ConstrainedQaoaRunner(cost_hamiltonian, subspace)
```

## 12. 测试需求

### 12.1 单元测试

- equality square 展开 truth table。
- at-most-one penalty truth table。
- exactly-one penalty truth table。
- binary slack 上界计算，覆盖正/负系数。
- unbalanced penalty residual 方向正确。
- one-hot encode/decode。
- domain-wall encode/decode P2。
- feasibility checker 对所有 sense 正确。
- penalty advisor 在简单目标上给出足够权重。
- sample ranking 对 unbalanced near-ground case 可把 feasible 解排前。

### 12.2 集成测试

每个测试都对小规模原问题 brute force，并验证：

- 原问题最优可行解。
- QUBO ground state 是否可行。
- 若使用 unbalanced，则 top-k 是否包含最优可行解。
- repair 前后 feasibility 和 objective。

建议样例：

- 3 变量 at-most-one。
- 4 变量 exactly-one。
- exactly-k selection。
- small knapsack。
- bounded sum with negative coefficients。
- one-hot color assignment toy case。
- custom truth-table constraint。

### 12.3 Benchmark

对每个约束策略输出 CSV/JSON：

- problem name。
- strategy。
- logical variable count。
- encoded binary count。
- slack count。
- auxiliary count。
- coupler count。
- density。
- coefficient ratio。
- feasible sample ratio。
- best feasible objective。
- best energy feasibility。
- repair success rate。

## 13. 开发优先级

### P0

- `ConstraintSpec`
- `ConstraintEncodingPlan`
- equality square penalty。
- inequality binary slack。
- known pairwise penalties。
- penalty advisor。
- feasibility checker。
- sample ranking。
- diagnostics。

### P1

- one-hot encoding strategy。
- cardinality/exactly-k 专用支持。
- penalty sweep。
- basic repair。
- unbalanced inequality penalty。
- benchmark 输出。

### P2

- encoding advisor。
- domain-wall encode/decode。
- custom truth-table penalty synthesis。
- feasible-subspace export。
- local search repair。

### P3

- domain-wall 任意 value interaction 完整实现。
- constrained mixer 自动联动。
- MILP polish repair。
- hardware-aware embedding estimator。

## 14. 主要风险与规避

**风险 1：Penalty 权重错误导致不可行解能量最低。**  
规避：默认使用目标收益上界；小规模 brute force 验证；支持 penalty sweep；排序始终 feasibility-first。

**风险 2：Slack variables 导致变量数爆炸。**  
规避：统计 slack 占比；对大 slack 上界建议 unbalanced、domain-wall、decomposition 或 constrained mixer。

**风险 3：Unbalanced penalty 不保证 ground state 对应原问题最优。**  
规避：标记 heuristic guarantee；top-k feasible ranking；必须配合 feasibility checker 和参数扫描。

**风险 4：One-hot 约束产生 dense couplers。**  
规避：group size warning；评估 domain-wall；对 QAOA 保留 one-hot group 结构以启用 XY mixer。

**风险 5：Domain-wall 实现复杂且结构依赖强。**  
规避：先实现接口和诊断，P2/P3 再实现完整 mapping；保留 one-hot fallback。

**风险 6：Repair 改善可行性但破坏目标质量。**  
规避：记录 repair delta；repair 后局部搜索；最终报告 repair 前后 objective。

## 15. 参考文献

Hen, I., & Spedalieri, F. M. (2016). Quantum annealing for constrained optimization. *Physical Review Applied, 5*(3), 034007.

Montanez-Barrera, J. A., Willsch, D., Maldonado-Romo, A., & Michielsen, K. (2024). Unbalanced penalization: A new approach to encode inequality constraints of combinatorial problems for quantum optimization algorithms. arXiv:2211.13914.

Montanez-Barrera, J. A., van den Heuvel, P., Willsch, D., & Michielsen, K. (2023). Improving performance in combinatorial optimization problems with inequality constraints: An evaluation of the unbalanced penalization method on D-Wave Advantage. arXiv:2305.18757.

Chancellor, N. (2019). Domain wall encoding of discrete variables for quantum annealing and QAOA. *Quantum Science and Technology, 4*(4), 045004.

Chen, J., Stollenwerk, T., & Chancellor, N. (2021). Performance of domain-wall encoding for quantum annealing. arXiv:2102.12224.

Fuchs, F. G., Lye, K. O., Nilsen, H. M., Stasik, A. J., & Sartor, G. (2022). Constraint preserving mixers for the quantum approximate optimization algorithm. *Algorithms, 15*(6), 202.

Bucher, D., Janetschek, M., Poppel, M., Stein, J., Linnhoff-Popien, C., & Feld, S. (2026). Constrained quantum optimization via iterative warm-start XY-mixers. arXiv:2604.02083.
