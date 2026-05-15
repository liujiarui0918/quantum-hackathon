# 开发需求文档：Learning-Guided Optimization / 神经网络辅助混合优化路线

更新日期：2026-05-15

## 1. 文档目标

本文档定义第七条路线：用机器学习和深度学习辅助混合整数约束优化。它不替代 QUBO、退火、QAOA 或 Hybrid，而是学习求解流程中的策略环节。

本路线服务两个目标：

- 比赛工程：充分使用 4 张 64GB 沐曦 GPU，形成“经典深度学习 + 量子/量子启发优化”的可讲方案。
- 算法改进：让神经网络参与 warm-start、变量固定、branching、repair、参数调度和候选解生成。

## 2. 精读论文与可开发结论

### 2.1 Bengio et al. 2018：ML for Combinatorial Optimization

可开发结论：

- ML 不应只被看作端到端 solver，也可以学习启发式、搜索策略和局部决策。
- 要区分 construction policy、improvement policy、branching policy 和 surrogate model。
- 每个学习模型都必须和 baseline、可行性检查、泛化测试绑定。

### 2.2 Gasse et al. 2019：GNN for Branching

可开发结论：

- MILP 可以表示成变量-约束二部图。
- GNN 可学习 branching score，辅助 branch-and-bound。
- 我们的 `HybridOptimizationProblem` 后续应导出 constraint-variable graph。

### 2.3 Nair et al. 2020：Neural Diving / Neural Branching

可开发结论：

- Neural Diving 学 partial assignment，把剩余变量交给 MIP solver。
- Neural Branching 学变量选择，减少 branch-and-bound tree。
- 对我们来说，对应 `FixAndOptimize` 的变量选择和 QUBO 子问题选择。

### 2.4 Graph RL for CO 2024

可开发结论：

- 图强化学习适合学习 constructive / repair / local-search policy。
- 比赛中可以把 repair operator selection 建成 MDP：状态是当前 violation 和 objective，动作是 flip/drop/swap。

### 2.5 AutoGNP 2024

可开发结论：

- QUBO 和 MILP 都可以作为 GNN 输入图。
- 后续可以用自动图网络搜索，但 P0 不做架构搜索；先固定特征和接口。

### 2.6 Counterdiabatic / advanced QAOA

可开发结论：

- 更高级量子算法不是完全新入口，而是 QAOA ansatz 增强。
- P2/P3 可支持 multi-angle、counterdiabatic terms、warm-start parameters。
- ML 可学习这些参数或选择 ansatz，而不是直接替换 QAOA。

## 3. 模块边界

### 3.1 本模块负责

- QUBO graph feature extraction。
- 可导出的训练样本 schema。
- learning-guided warm-start backend。
- variable ranking / partial assignment scaffold。
- 与 benchmark runner、demo CLI 的接入。
- GPU 训练路线文档和数据契约。

### 3.2 本模块不负责

- 默认安装 PyTorch 或真实深度学习框架。
- 保证神经网络输出最优解。
- 替代 exact solver / MILP solver 的 bound。
- 替代 QAOA 或退火求解器。

## 4. 核心数据结构需求

### 4.1 `QuboGraphFeatures`

字段：

- `feature_names`
- `nodes`
- `edges`

Node feature 至少包含：

- `linear_bias`
- `degree`
- `coupling_sum`
- `abs_coupling_sum`
- `positive_coupling_sum`
- `negative_coupling_sum`

Edge feature 至少包含：

- `source`
- `target`
- `coefficient`

### 4.2 Training record

输出 JSON-like record：

```text
{
  "num_nodes": int,
  "feature_names": [...],
  "node_features": [...],
  "edges": [...],
  "labels": [0, 1, ...] or null
}
```

标签来源：

- 小规模 exact optimum。
- 中规模 best feasible incumbent。
- repair 后可行解。
- 多 solver ensemble 投票。

### 4.3 `LearningGuidedSamplerBackend`

职责：

- 读取 QUBO graph features。
- 用 policy 生成候选 bitstrings。
- 对候选做 local improvement。
- 输出标准 `SolverResult`。

P0 policy：

- `LinearWarmStartPolicy`，作为可解释 baseline。

P1/P2 policy：

- PyTorch GNN。
- RL repair policy。
- QAOA parameter predictor。

### 4.4 `VariableFixingPlan`

字段：

- `fixed_bits`：高置信度 bit，包含 index、value、confidence。
- `free_bits`：保留给 QUBO / QAOA / Hybrid 子问题的不确定 bit。
- `ranked_bits`：policy score 和 probability，便于解释和调试。

用途：

- 给 `FixAndOptimize` 或小 QUBO 子问题提供固定变量。
- 给 QAOA / 退火提供更小的搜索空间和 warm-start 候选。
- 在 benchmark 中记录哪些变量由学习策略建议固定。

### 4.5 `LearningGuidedDatasetBuilder`

职责：

- 批量构建 QUBO graph 训练样本。
- 小规模问题使用 exact solver 标签。
- 中规模问题可替换为 SA / hybrid / repair incumbent 标签。
- 输出 JSONL，方便后续接 PyTorch / GNN / RL 训练脚本。

## 5. 求解流程

```text
OptimizationProblem
  -> QUBO
  -> graph features
  -> warm-start / variable ranking policy
  -> candidate bitstrings or partial assignments
  -> SA / QAOA / fix-and-optimize / repair
  -> decode + feasibility check
  -> benchmark
```

## 6. GPU 使用计划

### P0

不依赖 GPU，先跑 learning-guided backend。

### P1

用 GPU 批量训练 GNN warm-start policy。

训练数据：

- QUBO node/edge features。
- labels from exact / SA / hybrid incumbent。
- violation 和 objective 作为辅助目标。

### P2

训练 RL repair policy。

状态：

- 当前 bitstring。
- objective value。
- constraint violation vector。
- 最近 repair action。

动作：

- flip variable。
- swap variables。
- drop/add item。
- select repair operator。

奖励：

- violation reduction。
- objective improvement。
- incumbent improvement。

### P3

学习 QAOA / constrained QAOA 参数：

- 初始 `gamma/beta`。
- multi-start 分布。
- mixer / ansatz choice。
- warm-start state weights。

## 7. 测试需求

P0 必须覆盖：

- QUBO graph features 数量和字段正确。
- training record 可 JSON 序列化。
- learning-guided backend 可输出标准 `SolverResult`。
- 在 `exactly_one_selection` 上能找到可行候选。
- demo CLI report 包含 learning-guided row。

P1/P2 扩展测试：

- dataset split deterministic。
- no label leakage。
- policy output shape 与变量数一致。
- GPU unavailable 时回退 CPU 或跳过训练。

## 8. 主要风险与规避

风险：神经网络被误说成保证最优。

规避：所有文档统一表述为 heuristic / warm-start / policy learning；最优性必须由 exact/bound/benchmark 证明。

风险：训练数据太少导致泛化差。

规避：先做同分布问题族；跨场景只做迁移实验，不做夸大承诺。

风险：GPU 环境不稳定。

规避：核心 demo 不强依赖 GPU；GPU 训练作为可选增强。

风险：模型复杂但无收益。

规避：每个学习模型必须和 random、greedy、SA、QAOA、hybrid baseline 对比。
