# Quantum Hackathon Literature Pack

这个目录是杰瑞准备阶段的文献库，围绕赛道“量化优化：混合整数带约束优化问题”整理。

## 目录结构

- `papers/00_surveys_overviews`: 综述，适合快速建立全局视角。
- `papers/01_qubo_ising_formulations`: MILP/MIQP 到 QUBO/Ising 的建模资料。
- `papers/02_qaoa_vqa_algorithms`: QAOA、VQA、warm-start、R-QAOA 等算法。
- `papers/03_constraints_and_encodings`: 约束处理、罚函数、domain-wall、constrained mixer。
- `papers/04_milp_miqp_hybrid`: 混合二进制/混合整数优化与量子混合框架。
- `papers/05_power_unit_commitment`: 电力机组组合方向。
- `papers/06_scheduling`: 工业排产、job shop scheduling 方向。
- `papers/07_logistics_vrp`: 物流路径、VRP/CVRP/VRPTW 方向。
- `papers/08_finance_portfolio`: 金融投资组合 MIQP/QUBO 方向。
- `papers/09_tools_docs`: 工具链官方资料索引。
- `notes/literature_index.md`: 中文索引，每篇文献说明用途。
- `notes/jerry_reading_plan.md`: 一周阅读和输出计划。

## 先读哪几篇

如果时间有限，优先读：

1. `papers/01_qubo_ising_formulations/glover_kochenberger_du_2018_qubo_tutorial.pdf`
2. `papers/01_qubo_ising_formulations/lucas_2014_ising_formulations_np_problems.pdf`
3. `papers/02_qaoa_vqa_algorithms/farhi_goldstone_gutmann_2014_qaoa.pdf`
4. `papers/02_qaoa_vqa_algorithms/hadfield_2019_quantum_alternating_operator_ansatz.pdf`
5. `papers/03_constraints_and_encodings/hen_spedalieri_2016_quantum_annealing_constrained_optimization.pdf`
6. 按正式赛题场景选择 `05` 到 `08` 中对应目录。

## 杰瑞需要输出给队友的东西

- 给清哥：变量表、目标函数、约束列表、QUBO/Ising 映射、罚函数权重建议、伪代码、输入输出格式。
- 给龙哥：问题为什么难、搜索空间为什么爆炸、算法路线图、基线对比指标、可视化字段建议。
- 给团队：至少 2 条备选路线，例如“经典基线 + QUBO + 退火采样 + repair”和“QAOA/XY mixer + 经典优化器 + 可行性评估”。
