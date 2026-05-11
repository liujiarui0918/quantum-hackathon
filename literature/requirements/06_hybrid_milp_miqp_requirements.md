# 开发需求文档：Hybrid MILP / MIQP 分解与量子子问题路线

更新日期：2026-05-12

## 1. 文档目标

本需求文档面向开发人员，定义一条稳健的 hybrid optimization 路线：把通用混合整数优化问题拆成经典连续/松弛/修复模块与量子或量子启发式 binary subproblem 模块。该路线不要求一次性把完整 MILP/MIQP 转成巨大 QUBO，而是让 QUBO/Ising solver 只承担适合它的离散搜索部分。

第一阶段目标是实现一个可跑的 hybrid scaffold：能识别 binary、integer、continuous 变量，构造 classical relaxation，选择或固定变量形成小 QUBO 子问题，调用路线 3 的 solver backend，再用经典 feasibility repair 和 polishing 生成最终候选解。

## 2. 精读论文与可开发结论

### 2.1 Braine et al. 2021：Mixed Binary Optimization 扩展

**核心结论**：很多业务问题不是纯 QUBO，而是 mixed binary optimization，包含 binary decision variables 和 continuous variables；不等式也可能通过 slack/continuous variables 表示。论文提出用 hybrid quantum-classical heuristics 扩展 QUBO 类算法，使其能处理 MBO。

**对开发的直接要求**：

- 输入模型必须支持 continuous variables，不能只支持 binary。
- 需要 `ProblemDecomposer` 判断哪些部分能变成 QUBO，哪些部分应由经典优化器处理。
- 对给定 binary assignment，必须能快速求解 continuous subproblem 或检查可行性。
- 对 inequality/slack，优先由路线 2 的约束层处理；若 slack 是连续变量，则进入 classical subproblem。

### 2.2 Gambella & Simonetto 2021：Multi-block ADMM for MBO

**核心结论**：ADMM 可以把 mixed-binary optimization 拆成 binary unconstrained problem 和 continuous constrained convex subproblem。binary block 可以由 QUBO/quantum algorithms 近似求解；continuous block 可用成熟经典 convex solver。该方法在一般非凸场景仍是 heuristic，但为 hybrid 分解提供了清晰结构。

**对开发的直接要求**：

- 需要实现 `AdmmHybridOptimizer`：
  - binary block update：构造 QUBO 并调用 sampler。
  - continuous block update：调用 classical QP/LP/convex solver。
  - auxiliary/consensus block update。
  - dual update。
  - primal/dual residual stopping。
- binary 子问题求解器可以是 inexact solver，但要记录子问题 gap/energy/feasibility。
- 需要支持 `rho`、`beta`、`max_iter`、`tol`、`rho_update` 等参数。
- ADMM 输出必须标记 heuristic，不承诺全局最优。

### 2.3 Brown et al. 2022/2024：Copositive framework 与 Ising solver 子程序

**核心结论**：直接把复杂优化问题转成 Ising 可能导致变量数、耦合强度和 landscape ill-conditioning。更合理的 hybrid 方法是把 Ising solver 当作一个子程序，与经典优化算法交替工作。论文用 copositive cutting-plane 说明：经典部分可以保持多项式流程，困难集中到 Ising/certificate 子问题；启发式 Ising solver 和完备 classical solver 可以互补。

**对开发的直接要求**：

- 不应把 QUBO solver 设计成唯一求解入口；它是 `DiscreteOracle`。
- 每个子问题要允许 fallback：先 SA/QPU 快速找 certificate/candidate，失败时可用 exact/MILP 小规模证明。
- benchmark 要区分 deterministic solver 与 stochastic solver，支持 time-to-target / success probability。
- 需要保留 lower bound、upper bound、best feasible incumbent，而不是只存一个 best sample。

### 2.4 Egger et al. 2021：Warm-start from relaxation

**核心结论**：经典 relaxation，例如 QP/SDP/LP relaxation，可以给量子优化提供更好的初始点。对开发而言，这说明 hybrid pipeline 应先算 relaxed solution，再将其用于 rounding、initial_state、variable fixing 或 QAOA warm-start。

**对开发的直接要求**：

- 实现 `RelaxationSolver`，至少支持 continuous relaxation。
- 实现 `RoundingStrategy`，把 relaxed values 转为 binary candidate。
- 对路线 4/5，保留 warm-start metadata：continuous values、rounded solution、confidence scores。
- 对路线 3，本地 SA 可用 relaxed rounding 作为 initial_state。

## 3. 模块边界

### 3.1 本模块负责

- 混合变量问题表示。
- problem decomposition。
- classical relaxation。
- rounding / variable fixing。
- binary subproblem QUBO 构造。
- ADMM / block-coordinate hybrid workflow。
- classical repair / polishing。
- incumbent 和 bound 管理。
- hybrid benchmark。

### 3.2 本模块不负责

- 底层 QUBO 表达，沿用路线 1。
- penalty strategy 细节，沿用路线 2。
- annealing solver 实现，沿用路线 3。
- QAOA 电路实现，归路线 4。
- constrained mixer，归路线 5。

## 4. 核心数据结构需求

### 4.1 `HybridOptimizationProblem`

字段建议：

- `variables`
  - `binary`
  - `integer`
  - `continuous`
- `objective`
  - `linear`
  - `quadratic`
  - `constant`
  - `sense`
- `constraints`
  - linear equality/inequality。
  - variable bounds。
  - optional quadratic constraints P2。
- `metadata`

需求：

- 支持从路线 1 的 `OptimizationProblem` 升级而来。
- 对 integer variables 可选择 binary encoding 或作为 classical integer fallback。
- 能导出 LP/QP relaxation。
- 能在固定一部分变量后生成 reduced problem。

### 4.2 `ProblemDecomposition`

字段建议：

- `binary_block_vars`
- `continuous_block_vars`
- `integer_encoded_vars`
- `linking_constraints`
- `pure_binary_terms`
- `pure_continuous_terms`
- `cross_terms`
- `recommended_strategy`

`recommended_strategy` 取值：

- `direct_qubo`
- `relax_round_repair`
- `fix_and_optimize`
- `admm`
- `block_coordinate`
- `classical_only`

### 4.3 `HybridState`

用于迭代算法：

- `iteration`
- `binary_assignment`
- `continuous_solution`
- `auxiliary_variables`
- `dual_variables`
- `rho`
- `objective_value`
- `constraint_violation`
- `best_feasible_incumbent`
- `lower_bound`
- `upper_bound`
- `history`

需求：

- 每次迭代可序列化。
- 支持中断恢复。
- 支持 debug 输出子问题 QUBO 和 continuous subproblem。

## 5. 核心算法需求

### 5.1 Relax-Round-Repair Pipeline

这是第一版最稳路线。

流程：

```text
original MILP/MIQP
  -> continuous relaxation
  -> solve LP/QP relaxation
  -> round binary variables
  -> repair constraints
  -> polish continuous variables with binary fixed
  -> local search on selected binary neighborhood
```

需求：

- `RelaxationSolver` 支持 scipy/OR-Tools/cvxpy 可选后端。
- `RoundingStrategy` 支持：
  - threshold rounding。
  - randomized rounding。
  - top-k rounding for cardinality。
  - objective-aware rounding。
- repair 使用路线 2 的 repair module。
- polish 时固定 binary，求解 continuous LP/QP。

### 5.2 Fix-and-Optimize with QUBO Subproblems

流程：

```text
incumbent solution
  -> select binary neighborhood S
  -> fix variables outside S
  -> build small QUBO over S
  -> sample candidates
  -> decode and repair
  -> continuous polish
  -> update incumbent
```

需求：

- `NeighborhoodSelector`：
  - random。
  - high reduced-cost。
  - high violation contribution。
  - uncertain relaxed values near 0.5。
  - graph/coupler locality。
- 子问题大小受 solver backend 限制，例如 `max_subproblem_bits=40`。
- 每个子问题输出改进值和接受/拒绝原因。

### 5.3 ADMM Hybrid Optimizer

适用：

- binary 与 continuous 有 linking constraints。
- 目标可拆为 binary quadratic + continuous convex。

标准流程：

```text
initialize x, z, y, lambda
for k in 1..max_iter:
    x_k = solve_binary_qubo_block(z, y, lambda, rho)
    z_k = solve_continuous_convex_block(x_k, y, lambda, rho)
    y_k = update_auxiliary_or_consensus(x_k, z_k)
    lambda_k = lambda_{k-1} + rho * residual(x_k, z_k, y_k)
    update incumbent
    stop if primal_residual <= eps_primal and dual_residual <= eps_dual
```

需求：

- binary block 必须调用路线 1/3 的 QUBO builder + sampler。
- continuous block 必须可替换 solver。
- 支持 inexact binary solve：取 top-k sample 逐一评估。
- 每轮必须保存 residual、objective、best feasible。
- 若 residual 长期不下降，触发 rho update 或 restart。

### 5.4 Copositive / Cutting-plane 子程序 P3

第一版不实现完整 copositive framework，但保留接口：

```python
class DiscreteOracle:
    def find_violated_certificate(self, oracle_problem, config) -> OracleResult:
        ...
```

用途：

- 先用 SA/QPU 找 violated certificate。
- 找不到时 fallback 到 exact/MILP verifier。
- 把启发式 solver 和完备 solver 组合进同一 classical algorithm。

## 6. Classical Solver Adapter

### 6.1 必须支持

- scipy optimize / scipy milp（若环境可用）。
- OR-Tools CP-SAT P1。
- cvxpy P1/P2。

### 6.2 Adapter 接口

```python
class ClassicalSolver:
    def solve_relaxation(self, problem, config) -> RelaxationResult:
        ...

    def solve_fixed_binary(self, problem, binary_assignment, config) -> PolishingResult:
        ...
```

### 6.3 输出

- status。
- objective。
- variable values。
- dual values if available。
- runtime。
- infeasibility certificate if available。

## 7. Warm-start 与 Variable Fixing

### 7.1 Relaxation confidence

对 relaxed binary value `r_i in [0,1]`：

```text
confidence_i = abs(r_i - 0.5) * 2
```

规则：

- `confidence_i >= 0.9`：可考虑固定。
- `confidence_i <= 0.2`：优先放入 QUBO neighborhood。

### 7.2 Initial state

输出给路线 3：

- `initial_bitstring`
- `initial_pool`
- `variable_bias`

输出给路线 4/5：

- `continuous_relaxation_values`
- `warm_start_angles`
- `one_hot_group_probabilities`

## 8. Incumbent 与 Bounds

Hybrid solver 必须维护：

- `best_feasible_solution`
- `best_feasible_objective`
- `best_infeasible_candidate`
- `lower_bound`
- `upper_bound`
- `gap`
- `bound_source`

说明：

- 对纯启发式流程，lower bound 可能只有 relaxation bound。
- 对 stochastic QUBO solver，必须保存 success probability 和 repeats。
- 如果无法证明 bound，字段标记为 `unknown`，不能伪装成 optimality certificate。

## 9. API 草案

```python
problem = HybridOptimizationProblem()
problem.add_binary_vars("x", n)
problem.add_continuous_vars("y", m, lower=0.0)
problem.set_objective(linear=..., quadratic=...)
problem.add_linear_constraints(...)

decomposition = ProblemDecomposer().analyze(problem)

solver = HybridOptimizer(
    strategy="relax_round_repair",
    relaxation_solver=ScipyRelaxationSolver(),
    discrete_solver=SimulatedAnnealingBackend(),
    repairer=ConstraintRepairer(),
)

result = solver.solve(problem, HybridConfig(seed=42, time_limit=60))
best = result.best_feasible_solution
```

ADMM：

```python
solver = AdmmHybridOptimizer(
    discrete_solver=SimulatedAnnealingBackend(),
    continuous_solver=CvxpySolver(),
)

result = solver.solve(
    problem,
    AdmmConfig(rho=10.0, max_iter=50, eps_primal=1e-4, eps_dual=1e-4),
)
```

## 10. Diagnostics

必须输出：

- binary variable count。
- continuous variable count。
- integer variable count。
- linking constraint count。
- objective block structure。
- relaxation status。
- relaxed objective。
- rounded objective。
- repaired objective。
- polish status。
- subproblem QUBO sizes。
- subproblem solver metrics。
- total runtime。
- incumbent history。
- feasibility history。

ADMM 额外输出：

- primal residual。
- dual residual。
- rho history。
- binary block energy。
- continuous block objective。
- consensus violation。

## 11. 测试需求

### 11.1 单元测试

- variable block classification。
- fixed-variable reduced problem 构造。
- relaxation bound 正确。
- threshold/top-k/randomized rounding。
- fixed-binary continuous polish。
- neighborhood selector。
- ADMM residual 计算。
- incumbent update。

### 11.2 集成测试

建议样例：

- small binary knapsack with continuous slack。
- mixed binary quadratic toy problem。
- portfolio-like MIQP toy。
- facility-selection with continuous allocation toy。
- ADMM 两变量块小例子。

验收：

- 小规模可用 brute force + continuous solve 验证最优。
- relax-round-repair 生成可行解。
- fix-and-optimize 能在至少一个样例中改进 incumbent。
- ADMM 输出 residual history，不崩溃，并返回 best feasible 或明确 infeasible。

## 12. Benchmark 需求

对比对象：

- classical-only relaxation + rounding。
- classical local search。
- direct QUBO。
- relax-round-repair。
- fix-and-optimize。
- ADMM hybrid。

指标：

- best feasible objective。
- optimality gap if known。
- relaxation gap。
- feasibility rate。
- repair success。
- subproblem count。
- average QUBO size。
- total runtime。
- time split：relaxation / QUBO sampling / continuous polish / repair。
- stochastic success probability。

## 13. 开发优先级

### P0

- `HybridOptimizationProblem`
- `ProblemDecomposer`
- continuous relaxation。
- threshold/top-k rounding。
- fixed-binary polish。
- relax-round-repair pipeline。
- diagnostics。

### P1

- randomized/objective-aware rounding。
- neighborhood selector。
- fix-and-optimize QUBO subproblem。
- incumbent manager。
- benchmark runner。

### P2

- ADMM hybrid optimizer。
- rho update / restart。
- OR-Tools/cvxpy adapters。
- warm-start metadata export。

### P3

- copositive/cutting-plane oracle interface。
- exact fallback oracle。
- advanced bound management。
- automatic decomposition strategy selection。

## 14. 主要风险与规避

**风险 1：直接 QUBO 化导致规模和系数失控。**  
规避：先 decomposition；只把小 binary subproblem 交给 QUBO solver。

**风险 2：Hybrid heuristic 没有全局最优保证。**  
规避：显式标记 guarantee level；维护 relaxation bound 和 incumbent；小规模用 exact 校验。

**风险 3：连续子问题不可行。**  
规避：fixed-binary polish 返回 infeasible certificate；触发 repair 或重新选择 neighborhood。

**风险 4：ADMM residual 不收敛。**  
规避：rho update、restart、max_iter、fallback 到 relax-round-repair。

**风险 5：stochastic 子求解器结果不稳定。**  
规避：固定 seed、多 reads、记录 success probability、必要时 exact fallback。

## 15. 参考文献

Braine, L., Egger, D. J., Glick, J., & Woerner, S. (2021). Quantum algorithms for mixed binary optimization applied to transaction settlement. *IEEE Transactions on Quantum Engineering, 2*, 1-8.

Gambella, C., & Simonetto, A. (2021). Multi-block ADMM heuristics for mixed-binary optimization on classical and quantum computers. *IEEE Transactions on Quantum Engineering, 2*, 1-22.

Brown, R., Bernal Neira, D. E., Venturelli, D., & Pavone, M. (2024). A copositive framework for analysis of hybrid Ising-classical algorithms. arXiv:2207.13630.

Egger, D. J., Mareček, J., & Woerner, S. (2021). Warm-starting quantum optimization. *Quantum, 5*, 479.
