# 开发需求文档：QUBO / Ising 通用建模底座

更新日期：2026-05-12

## 1. 文档目标

本需求文档面向开发人员，定义一个通用建模模块：把混合整数带约束优化问题中的二进制变量、 bounded integer 变量、线性/二次目标、等式/不等式约束转换为 QUBO、Ising 或 BQM 表示，供后续 simulated annealing、quantum annealing、QAOA、hybrid decomposition 等路线复用。

第一阶段不绑定具体业务场景，只实现通用模型层和可验证的小规模样例。

## 2. 精读论文与可开发结论

### 2.1 Glover, Kochenberger, Du 2018：QUBO 建模教程

**核心结论**：QUBO 可以作为组合优化的统一中间表示。标准形式是最小化 `x^T Q x`，其中 `x` 是 0/1 变量，线性项可以放在 `Q` 的对角线上，二次项放在非对角位置。最大化问题可以通过目标函数取负转为最小化。

**对开发的直接要求**：

- 建模层必须支持 sparse QUBO，而不是只支持 dense matrix。
- 线性项要统一写入 diagonal，即 `q_ii += linear_i`。
- 二次项要明确采用 upper-triangular 还是 symmetric 约定，避免能量计算重复。
- 需要保留 constant offset，虽然它不影响 argmin，但影响不同求解器能量对齐和测试断言。
- 约束通过 penalty 加到目标函数中；hard constraint 的 penalty 必须足够大，soft constraint 可以使用较小权重。

**基础罚项库**：

- `x + y <= 1`：`P * x * y`
- `x + y >= 1`：`P * (1 - x - y + x*y)`
- `x + y = 1`：`P * (1 - x - y + 2*x*y)`
- `x <= y`：`P * (x - x*y)`
- `x = y`：`P * (x + y - 2*x*y)`
- `sum(x_i) = b`：`P * (sum(x_i) - b)^2`
- `A x = b`：`P * ||A x - b||^2`
- `A x <= b`：引入 binary slack 后转为等式。

**风险结论**：penalty 不是越大越好。过大会压制原目标函数差异，导致采样器只看约束项；过小会产生不可行最优解。因此模块必须输出 penalty 诊断，而不是只返回 QUBO。

### 2.2 Lucas 2014：NP 问题的 Ising 形式

**核心结论**：大量 NP-hard / NP-complete 问题可以映射成 Ising Hamiltonian。Ising 形式使用 `s_i in {-1,+1}`，经典能量通常写为 `H(s) = -sum J_ij s_i s_j - sum h_i s_i`。QUBO 和 Ising 本质上是同一类二次无约束离散优化的两种变量表示。

**对开发的直接要求**：

- 必须实现 `qubo_to_ising` 和 `ising_to_qubo`。
- 每个编码方案要记录 logical variables、auxiliary variables、ancilla/spin 数量。
- 诊断器要报告三个硬件/求解风险：变量数、连接密度、系数尺度范围。
- 对图类、分配类、路径类问题，优先利用问题结构直接构造二次项，而不是先做泛化 NP 归约。

**关键工程风险**：

- 直接映射可能引入大量辅助变量。
- 高连接度 QUBO 在量子退火硬件上需要 minor embedding，实际 qubit 消耗可能远高于逻辑变量数。
- penalty 系数和目标系数之间若出现大尺度差异，会降低硬件和模拟采样器的有效分辨率。

### 2.3 Dattani 2019：高阶项二次化

**核心结论**：真实建模中可能出现三阶或更高阶伪布尔项，例如 `x_i*x_j*x_k`。QUBO 只接受二次项，因此需要 quadratization。二次化可以通过 deduction、substitution、auxiliary variables、positive/negative monomial reduction 等方式完成，目标通常是保持 ground state，同时尽量减少辅助变量和非局部连接。

**对开发的直接要求**：

- 第一版只实现一个稳健的通用二次化策略：对子表达式 `y = x_i * x_j` 引入辅助变量 `y`，并添加 AND 约束 penalty。
- 需要支持重复子表达式复用，避免每个高阶项都新建辅助变量。
- 需要区分两种正确性目标：
  - ground-state preserving：最优解集合保持正确。
  - full-spectrum preserving：所有能量层级保持一致。第一版只要求 ground-state preserving。
- 二次化后要输出 auxiliary variable 映射，方便解码时隐藏辅助变量。

**建议第一版 AND penalty**：

要约束 `y = x_i * x_j`，可以加入：

```text
P * (x_i*x_j - 2*x_i*y - 2*x_j*y + 3*y)
```

该罚项在 0/1 变量上对合法组合为 0，对非法组合为正，且保持二次形式。

### 2.4 De Santis et al. 2024：优化 QUBO 公式与减少 slack 变量

**核心结论**：标准 binary slack 方法在不等式约束较多或约束范围较大时会引入大量 slack variables，严重限制 NISQ/退火设备可处理的问题规模。该论文提出 iterative quadratic polynomial 和 master-satellite 方法，目标是减少 slack variables，并利用共享变量约束之间的结构。

**对开发的直接要求**：

- 第一版保留标准 binary slack 作为默认实现。
- 需求中预留 advanced penalty backend，用于后续实现 IQP / master-satellite。
- 建模诊断必须统计 slack variables 占比；如果 slack 占比过高，需要给出重构建议。
- 对局部约束，即约束只涉及少量共同变量，应允许使用枚举式 penalty synthesis：列出满足/违反的 assignment，再尝试拟合二次罚项。

**暂不在第一版实现的内容**：

- 自动搜索最少 slack 的 IQP。
- master-satellite 约束分层。
- 非线性非整数约束的无近似罚项合成。

这些内容应作为路线 2 的高级约束处理需求继续精读。

## 3. 模块边界

### 3.1 本模块负责

- 变量注册与编码。
- 目标函数构造。
- 基础约束罚项构造。
- bounded integer 变量二进制展开。
- 不等式约束 binary slack 展开。
- 高阶项二次化。
- QUBO / Ising / BQM 互转。
- 解码与约束检查。
- 建模诊断。

### 3.2 本模块不负责

- 具体业务数据解析。
- 求解器内部算法，例如 SA、QAOA、D-Wave 采样。
- 大规模 decomposition。
- 复杂 infeasible solution repair。
- 针对某一行业场景的专用模型。

这些会分别进入后续 solver、hybrid、scenario benchmark 文档。

## 4. 核心数据结构需求

### 4.1 `VariableRegistry`

用于统一管理变量。

字段建议：

- `name`: 变量名，例如 `x_3`、`slack_capacity_1_0`、`aux_and_x1_x2`。
- `index`: 内部整数索引。
- `type`: `binary`、`integer_encoded`、`slack`、`auxiliary`。
- `source`: 来源描述，例如 `logical`、`constraint:capacity_1`、`quadratization:x1*x2`。
- `decode_rule`: 从 bit 值恢复原变量的规则。

需求：

- 变量名必须稳定，支持可重复构建。
- 辅助变量和 slack 变量不能暴露给业务输出，除非 debug 模式。
- 支持通过原始变量名查找编码 bit 列表。

### 4.2 `QuadraticExpression`

统一表示常数项、线性项、二次项。

字段建议：

- `offset: float`
- `linear: dict[var, coeff]`
- `quadratic: dict[(var_i, var_j), coeff]`
- `sense: minimize | maximize`

需求：

- 自动合并同类项。
- 对二次项 key 进行规范化，例如始终 `(min(i,j), max(i,j))`。
- 支持 `add_linear`、`add_quadratic`、`add_square_linear_form`。
- 支持表达式加法、乘以 scalar、展开平方。

### 4.3 `Constraint`

统一描述约束。

字段建议：

- `name`
- `expression`
- `sense`: `==`、`<=`、`>=`
- `rhs`
- `hardness`: `hard`、`soft`
- `penalty_weight`
- `encoding`: `square`、`binary_slack`、`known_pairwise`、`custom`

需求：

- 每条约束必须能计算 violation。
- 每条约束必须能解释自己引入了哪些 penalty terms 和变量。
- hard constraint 若未提供权重，需要调用 penalty advisor 给出默认权重。

### 4.4 `QuboModel`

最终输出的求解器输入。

字段建议：

- `qubo`: sparse upper-triangular dict。
- `offset`
- `variables`
- `objective_terms`
- `constraint_terms`
- `diagnostics`

需求：

- 能导出为：
  - dense matrix
  - sparse tuple list
  - `dimod.BinaryQuadraticModel`
  - Qiskit Optimization `QuadraticProgram` 可接受的结构
- 能计算任意 bitstring 的 energy。
- 能解码 bitstring 为 logical solution。

## 5. 变量编码需求

### 5.1 Binary variable

原始 0/1 变量直接注册为 logical binary。

### 5.2 Bounded integer variable

若 `z in [L, U]`，第一版使用 binary expansion：

```text
z = L + sum(2^k * b_k) + remainder * b_last
```

需求：

- 自动计算 bit 数。
- 当 `U - L + 1` 不是 2 的幂时，最后一个 bit 可使用 remainder 权重，减少无效编码。
- 解码后必须检查是否越界。

### 5.3 Slack variable

对于 `a^T x <= b`，引入 `s >= 0`：

```text
a^T x + s = b
```

对 `s` 做 binary expansion。

需求：

- 自动估计 slack 上界。
- 支持用户手动覆盖 slack 上界。
- 如果 slack 上界过大，应在 diagnostics 中给出警告。

### 5.4 Auxiliary variable

用于高阶项二次化，例如 `y = x_i*x_j`。

需求：

- 自动复用相同 AND 子表达式。
- 解码时默认隐藏。
- diagnostics 中统计数量和来源。

## 6. QUBO 构造流程

推荐实现流程：

```text
input problem spec
  -> register logical variables
  -> encode bounded integers
  -> build objective expression
  -> normalize objective to minimization
  -> convert high-order objective terms to quadratic
  -> for each constraint:
       choose penalty encoding
       add slack / auxiliary variables if needed
       add penalty expression
  -> canonicalize quadratic expression
  -> export QUBO/BQM/Ising
  -> run diagnostics
```

第一版必须保证任意小规模问题可以用 brute force 验证 QUBO 最优解和原问题最优解一致。

## 7. Penalty 权重需求

### 7.1 默认策略

如果用户没有提供 penalty，默认使用目标函数变化上界：

```text
P = penalty_scale * (sum(abs(linear_i)) + sum(abs(quadratic_ij)) + 1)
```

建议 `penalty_scale = 2` 起步。

### 7.2 分约束权重

支持每条约束单独设置权重：

- hard constraint：必须大于任何违反约束可能带来的目标收益。
- soft constraint：允许用户给较小权重。
- priority constraint：支持按优先级自动放大。

### 7.3 权重诊断

模型构造后必须输出：

- `max_abs_objective_coeff`
- `max_abs_penalty_coeff`
- `coefficient_range`
- `estimated_min_violation_penalty`
- `objective_bound`
- `penalty_dominance_warning`

若 penalty 系数相对目标过大，应提示可能导致采样器分辨率变差；若过小，应提示可能导致不可行解。

## 8. QUBO 与 Ising 互转

### 8.1 变量关系

采用：

```text
x_i = (1 + s_i) / 2
s_i = 2*x_i - 1
```

### 8.2 输出形式

Ising 输出：

```text
E(s) = offset + sum(h_i * s_i) + sum(J_ij * s_i * s_j)
```

需求：

- 与 QUBO energy 对同一 assignment 保持一致。
- 单元测试覆盖随机 QUBO 的能量等价。
- 注意不同库对 Ising 符号约定不同，adapter 层必须记录 convention。

## 9. 高阶项二次化需求

### 9.1 支持范围

第一版支持任意 monomial：

```text
c * x_1 * x_2 * ... * x_k, k > 2
```

通过迭代引入 AND 辅助变量降阶。

### 9.2 示例

```text
c * x1*x2*x3
```

转换为：

```text
aux_y12 = x1*x2
c * aux_y12*x3
P_and * (x1*x2 - 2*x1*aux_y12 - 2*x2*aux_y12 + 3*aux_y12)
```

### 9.3 验收要求

- 对所有 0/1 assignment，合法辅助变量下能量等价。
- 对非法辅助变量，能量至少增加 `P_and` 的正罚项。
- 小规模 brute force 后，logical 最优解集合与原始高阶模型一致。

## 10. 求解前诊断需求

每次构建 QUBO 后输出 diagnostics。

必须包含：

- logical variables 数量。
- slack variables 数量。
- auxiliary variables 数量。
- total binary variables 数量。
- linear terms 数量。
- quadratic couplers 数量。
- QUBO density。
- coefficient min/max/ratio。
- constraint penalty breakdown。
- estimated brute-force feasibility for small n。
- recommended solver route。

推荐规则：

- `n_total <= 25`：允许 brute force 验证。
- `n_total <= 80`：优先 simulated annealing / OpenJij。
- `n_total > 80`：建议 decomposition 或 hybrid。
- slack 占比超过 40%：建议重构约束或使用路线 2 的高级 penalty。
- density 超过 30%：提示量子退火硬件 embedding 风险。

## 11. 解码与可行性检查

### 11.1 解码

输入 bitstring，输出：

- logical variable assignment。
- integer variable value。
- objective value without penalties。
- penalty energy。
- total QUBO energy。
- constraint status。

### 11.2 可行性检查

每条约束输出：

- `name`
- `lhs`
- `sense`
- `rhs`
- `violation`
- `is_satisfied`
- `penalty_contribution`

### 11.3 样本排序

求解器返回多个 sample 时，排序优先级：

1. feasible 优先于 infeasible。
2. feasible 内按原始 objective 排序。
3. infeasible 内按总 violation，再按 QUBO energy 排序。

## 12. 最小可行版本

### 12.1 必须实现

- `VariableRegistry`
- `QuadraticExpression`
- `Constraint`
- `QuboModel`
- binary variable 注册
- bounded integer binary expansion
- linear / quadratic objective
- equality penalty：`P*(lhs-rhs)^2`
- inequality binary slack
- known pairwise penalties
- high-order monomial quadratization
- QUBO energy evaluation
- QUBO -> Ising
- decode solution
- constraint checker
- diagnostics
- brute force verifier

### 12.2 可以延后

- IQP / master-satellite。
- domain-wall encoding。
- automatic symbolic simplification。
- advanced penalty tuning。
- hardware minor embedding。
- Qiskit / D-Wave / OpenJij adapters。
- infeasible solution repair。

这些由后续路线文档继续定义。

## 13. 建议 API

```python
problem = OptimizationProblem(sense="minimize")

x = problem.add_binary_var("x")
y = problem.add_binary_var("y")
z = problem.add_integer_var("z", lower=0, upper=7)

problem.set_objective(linear={"x": -3, "y": 2}, quadratic={("x", "y"): 4})
problem.add_constraint({"x": 1, "y": 1, "z": 2}, sense="<=", rhs=5, name="capacity")

builder = QuboBuilder(config=QuboBuilderConfig(default_penalty="auto"))
qubo_model = builder.build(problem)

diagnostics = qubo_model.diagnostics()
samples = brute_force_solve(qubo_model)
decoded = qubo_model.decode(samples[0])
```

## 14. 测试需求

### 14.1 单元测试

- linear objective 正确写入 diagonal。
- quadratic objective 正确写入 off-diagonal。
- max problem 取负后结果一致。
- pairwise penalties truth table 正确。
- equality square 展开正确。
- inequality slack 上界和 bit 数正确。
- bounded integer 解码正确。
- AND auxiliary penalty truth table 正确。
- QUBO -> Ising 能量等价。

### 14.2 集成测试

每个测试用例都要求原问题 brute force 与 QUBO brute force 最优 logical solution 一致。

建议样例：

- two-variable at-most-one。
- exact-one selection。
- small knapsack。
- weighted vertex cover。
- set partitioning。
- graph coloring 3-node toy case。
- cubic objective with auxiliary variable。

### 14.3 回归测试输出

对每个样例保存：

- 原始最优解。
- QUBO 最优 bitstring。
- decoded logical solution。
- objective value。
- penalty energy。
- diagnostics snapshot。

## 15. 开发优先级

### P0

- Sparse QUBO 数据结构。
- 基础变量注册与目标函数。
- equality / inequality penalty。
- 解码与约束检查。
- brute force verifier。

### P1

- bounded integer。
- high-order quadratization。
- QUBO / Ising 互转。
- diagnostics。

### P2

- BQM adapter。
- penalty advisor。
- benchmark 样例库。

### P3

- IQP / master-satellite 预研。
- domain-wall / unbalanced penalty。
- decomposition hook。

## 16. 主要风险与规避

**风险 1：penalty 过小导致不可行解成为 QUBO 最优解。**  
规避：默认 penalty 基于目标函数上界，所有小规模样例用 brute force 验证可行性。

**风险 2：penalty 过大导致系数范围过宽，采样器表现变差。**  
规避：输出 coefficient range warning，并支持 penalty sweep。

**风险 3：slack variables 过多导致变量数爆炸。**  
规避：诊断 slack 占比，路线 2 中实现 unbalanced penalty、domain-wall、IQP/MS 等替代方案。

**风险 4：高阶项二次化引入过多辅助变量。**  
规避：复用 AND 子表达式，统计 auxiliary 来源，优先重写模型减少高阶项。

**风险 5：QUBO 与 Ising 符号约定混乱。**  
规避：在 adapter 中显式记录 convention，并做能量等价测试。

## 17. 参考文献

Glover, F., Kochenberger, G., & Du, Y. (2018). *A tutorial on formulating and using QUBO models*.

Lucas, A. (2014). Ising formulations of many NP problems. *Frontiers in Physics, 2*, 5. https://doi.org/10.3389/fphy.2014.00005

Dattani, N. (2019). *Quadratization in discrete optimization and quantum mechanics*. arXiv:1901.04405.

De Santis, D., Tirone, S., Marmi, S., & Giovannetti, V. (2024). *Optimized QUBO formulation methods for quantum computing*. arXiv:2406.07681.
