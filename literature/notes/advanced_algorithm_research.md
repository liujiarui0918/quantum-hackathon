# 高级算法路线调研：量子优化 + 学习驱动优化

更新日期：2026-05-15

## 结论

现有六条路线已经覆盖量子优化比赛的主干：QUBO / Ising、约束处理、退火、QAOA、constrained mixer、Hybrid MILP / MIQP。它不是“只有两个算法”，而是围绕两个量子求解家族构建的一套建模和工程体系。

但它仍有一个明显进步空间：缺少学习驱动优化层。

推荐新增路线 7：Learning-Guided Optimization / 神经网络辅助混合优化。

这条路线不把神经网络当成“直接保证最优”的求解器，而是让它学习以下环节：

- warm-start：预测高质量初始解或概率分布。
- variable fixing：识别高置信度变量并缩小子问题。
- branching：在 branch-and-bound 或 fix-and-optimize 中选变量。
- repair / local search policy：学习哪个修复动作更可能提升 incumbent。
- solver parameter scheduling：给 SA、QAOA、constrained mixer 提供参数或初态建议。

4 张 64GB 沐曦 GPU 的价值主要在这里：训练 GNN/RL/神经启发式模型，批量评估大量实例，或做 QAOA / statevector / shot simulation 加速。它不自动带来最优性证明；最优性仍要靠 exact solver、MILP/MIQP bound、brute force 小样例或 benchmark gap。

## 为什么不是再找一个“更高级量子算法”替代 QAOA/退火

近端优化路线里，QAOA 和退火仍是主干。更高级的量子路线通常是它们的变体或增强：

- warm-start QAOA：用经典松弛解引导量子线路。
- constrained / XY mixer：把约束写进可行空间演化。
- R-QAOA：通过采样相关性递归固定变量。
- multi-angle QAOA：给 Hamiltonian 不同项分配更多参数。
- counterdiabatic / digitized-counterdiabatic QAOA：加入近似绝热捷径项提升固定深度表现。
- gradually changing unitaries：把 QAOA 参数看作离散绝热调度。

这些很适合写成 P2/P3 算法亮点，但比赛工程上仍需依赖 QUBO、约束、Hybrid 和 benchmark。

## 对我们方案的升级建议

### 1. 保留六条路线，新增第七路线

新增路线：

```text
路线 7：Learning-Guided Optimization / 神经网络辅助混合优化
```

定位：

```text
把 QUBO / MILP / MIQP 表示成图，训练 GNN/RL/神经策略，辅助 warm-start、变量固定、branching、repair 和参数调度。
```

这条路线和现有六条的关系：

- 接路线 1：QUBO 图就是神经网络输入。
- 接路线 2：约束 violation / repair success 可以作为训练信号。
- 接路线 3：学习生成退火 warm-start 或候选解。
- 接路线 4：学习 QAOA 参数、初态、候选 bitstring。
- 接路线 5：学习 constrained mixer 的初始可行态或 transition graph。
- 接路线 6：学习哪些变量固定、哪些变量进入 QUBO 子问题。

### 2. 代码层新增 learning-guided backend

当前实现已新增一个轻量版本：

```text
QUBO -> graph features -> linear warm-start policy -> local improvement -> SolverResult
```

它不是最终深度学习模型，而是数据接口和求解接口：

- `QuboGraphFeatureExtractor`：导出 node features / edges / labels，可喂给 GNN。
- `LearningGuidedDatasetBuilder`：把问题批量导出为 JSONL 训练样本，小规模用 exact label，中规模可换成 SA / hybrid incumbent。
- `VariableFixingPlan`：把 policy 概率转成 fixed bits / free bits，供 hybrid fix-and-optimize 或小 QUBO 子问题使用。
- `LearningGuidedSamplerBackend`：作为 solver backend 参与 benchmark。
- `LinearWarmStartPolicy`：占位基线，后续可替换为 PyTorch/GNN 策略。

### 3. 4 张 64GB GPU 的推荐用法

P0：不用训练，先跑 learning-guided baseline。

P1：生成训练数据。

- 小规模问题用 exact solver 生成标签。
- 中规模问题用 SA / hybrid / repair 生成 pseudo-label。
- 记录 QUBO 图、约束图、best feasible bitstring、violation、repair trace。

P2：训练 GNN warm-start policy。

- 输入：QUBO graph 或 bipartite constraint-variable graph。
- 输出：每个 binary variable 取 1 的概率、固定置信度、branching score。
- 用法：生成 partial assignment，然后交给 SA / QAOA / fix-and-optimize。

P3：训练 RL repair / local search policy。

- 状态：当前解、constraint violation、objective gap。
- 动作：flip variable、swap assignment、drop/add item、repair operator selection。
- 奖励：objective improvement、violation reduction、incumbent improvement。

## 关键文献

1. Bengio, Lodi, Prouvost, Machine Learning for Combinatorial Optimization: a Methodological Tour d'Horizon, 2018. https://arxiv.org/abs/1811.06128
2. Gasse et al., Exact Combinatorial Optimization with Graph Convolutional Neural Networks, 2019. https://arxiv.org/abs/1906.01629
3. Nair et al., Solving Mixed Integer Programs Using Neural Networks, 2020. https://arxiv.org/abs/2012.13349
4. Darvariu, Hailes, Musolesi, Graph Reinforcement Learning for Combinatorial Optimization, 2024. https://arxiv.org/abs/2404.06492
5. Liu et al., Combinatorial Optimization with Automated Graph Neural Networks, 2024. https://arxiv.org/abs/2406.02872
6. Chandarana et al., Digitized-counterdiabatic quantum approximate optimization algorithm, 2021. https://arxiv.org/abs/2107.02789
7. Kremenetski et al., QAOA beyond low depth with gradually changing unitaries, 2023. https://arxiv.org/abs/2305.04455
8. Falla, Safro, Constrained Counterdiabatic QAOA for Portfolio Optimization, 2026. https://arxiv.org/abs/2605.06858
9. Liang et al., Quantum Annealing Inspired Algorithms for Combinatorial Optimization Problems, 2026. https://arxiv.org/abs/2602.03101
