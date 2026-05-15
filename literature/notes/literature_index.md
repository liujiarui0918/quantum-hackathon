# 文献索引：混合整数约束优化 + 量子/量子启发算法

整理日期：2026-05-11

## 00 综述与全局视角

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/00_surveys_overviews/blekos_2024_qaoa_variants_review.pdf` | QAOA 及变体综述 | QAOA 结构、变体分类、适用问题 | 选 QAOA 路线时作为总参考 |
| `../papers/00_surveys_overviews/cerezo_2021_variational_quantum_algorithms_review.pdf` | VQA 综述 | barren plateau、优化器、噪声、可训练性 | 解释 near-term 量子算法局限 |
| `../papers/00_surveys_overviews/phillipson_bausch_2021_quantum_annealing_industry_review.pdf` | 工业量子退火综述 | 真实行业问题如何映射到退火 | 写应用价值和方案背景 |
| `../papers/00_surveys_overviews/sharma_2026_quantum_annealing_combinatorial_optimization_review.pdf` | 量子退火组合优化综述 | 退火算法和组合优化问题族 | 准备退火路线话术 |
| `../papers/00_surveys_overviews/hawashin_2026_variational_annealing_quantum_combinatorial_optimization_review.pdf` | 变分/退火量子优化综述 | QAOA、VQA、annealing 的横向对比 | 比赛时快速解释路线选择 |

## 01 QUBO / Ising 建模

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/01_qubo_ising_formulations/glover_kochenberger_du_2018_qubo_tutorial.pdf` | QUBO 教程 | 常见约束如何变成二次罚项 | 必读，直接生成建模模板 |
| `../papers/01_qubo_ising_formulations/lucas_2014_ising_formulations_np_problems.pdf` | NP 问题 Ising 形式 | TSP、cover、partition 等典型映射 | 遇到路径/调度类题可参考 |
| `../papers/01_qubo_ising_formulations/dattani_2019_quadratization_discrete_optimization_quantum_mechanics.pdf` | 高阶项二次化 | 高阶目标/约束如何降到 QUBO | 处理复杂目标函数备用 |
| `../papers/01_qubo_ising_formulations/desantis_2024_optimized_qubo_formulation_methods.pdf` | QUBO 公式优化 | 变量数、耦合数、penalty 规模优化 | 减少 qubit/变量消耗 |

## 02 QAOA / VQA 算法

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/02_qaoa_vqa_algorithms/farhi_goldstone_gutmann_2014_qaoa.pdf` | QAOA 原始论文 | cost Hamiltonian、mixer、参数层数 p | 标准 QAOA 基线 |
| `../papers/02_qaoa_vqa_algorithms/farhi_goldstone_gutmann_2014_qaoa_bounded_occurrence_constraint.pdf` | QAOA 约束满意问题 | Max-E3LIN2 等示例 | 解释 QAOA 处理组合问题 |
| `../papers/02_qaoa_vqa_algorithms/hadfield_2019_quantum_alternating_operator_ansatz.pdf` | Quantum Alternating Operator Ansatz | constrained mixer、可行空间内演化 | 约束很多时比罚函数更有说服力 |
| `../papers/02_qaoa_vqa_algorithms/zhou_2020_qaoa_performance_mechanism.pdf` | QAOA 性能机制 | 参数初始化、优化 landscape、实现细节 | 避免只写“套 QAOA” |
| `../papers/02_qaoa_vqa_algorithms/moll_2018_quantum_optimization_variational_algorithms_near_term.pdf` | 近端设备变分优化 | 硬件限制、变分工作流 | 写技术方案边界 |
| `../papers/02_qaoa_vqa_algorithms/egger_2021_warm_starting_quantum_optimization.pdf` | Warm-start QAOA | 用连续松弛解初始化 QAOA | 有 MILP/MIQP 松弛解时优先考虑 |
| `../papers/02_qaoa_vqa_algorithms/bravyi_2020_obstacles_variational_quantum_optimization_rqaoa.pdf` | R-QAOA / 变分优化障碍 | 递归变量消元、对称性困难 | 做量子启发增强路线 |

## 03 约束处理与编码

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/03_constraints_and_encodings/hen_spedalieri_2016_quantum_annealing_constrained_optimization.pdf` | 约束量子退火 | 如何保持或惩罚约束 | 解释“可行解优先” |
| `../papers/03_constraints_and_encodings/montanez_barrera_2022_unbalanced_penalization_inequality_constraints.pdf` | 不等式约束非平衡罚项 | 不等式不用大量 slack 的方法 | 处理容量、预算、风险上限 |
| `../papers/03_constraints_and_encodings/montanez_barrera_2023_unbalanced_penalization_dwave.pdf` | D-Wave 上的不等式罚项 | 实机/退火器上的 penalty 表现 | 写工程落地风险 |
| `../papers/03_constraints_and_encodings/chancellor_2019_domain_wall_encoding.pdf` | domain-wall 编码 | 多值离散变量编码 | 比 one-hot 省变量的备选方案 |
| `../papers/03_constraints_and_encodings/chen_2021_domain_wall_encoding_performance.pdf` | domain-wall 性能 | 编码对退火性能影响 | 选择编码方式时参考 |
| `../papers/03_constraints_and_encodings/fuchs_2022_constrained_mixers_qaoa.pdf` | constrained mixers | 保持约束的 mixer 构造 | QAOA 可行空间搜索 |
| `../papers/03_constraints_and_encodings/bucher_2026_iterative_warm_start_xy_mixers.pdf` | warm-start + XY mixer | 组合约束下的 warm-start mixer | 适合投资组合/cardinality 约束 |

## 04 MILP / MIQP 与量子混合框架

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/04_milp_miqp_hybrid/braine_2021_mixed_binary_optimization_transaction_settlement.pdf` | mixed-binary optimization | 真实混合二进制问题如何拆分 | 参考“经典分解 + 量子子问题” |
| `../papers/04_milp_miqp_hybrid/gambella_2021_multiblock_admm_mixed_binary_optimization.pdf` | ADMM + 量子退火 | 分块、连续/离散变量分离 | 混合整数变量很多时备用 |
| `../papers/04_milp_miqp_hybrid/brown_2022_copositive_mixed_binary_quadratic_ising_solvers.pdf` | MBQP 到 Ising solver | 二次混合二进制优化 | MIQP 类赛题参考 |

## 05 电力机组组合

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/05_power_unit_commitment/koretsky_2021_qaoa_unit_commitment.pdf` | QAOA 求 unit commitment | 开关机变量、发电成本、负荷约束 | 电力方向首读 |
| `../papers/05_power_unit_commitment/mahroo_2022_hybrid_quantum_classical_unit_commitment.pdf` | 混合量子-经典 unit commitment | 经典优化和量子模块分工 | 工程方案参考 |
| `../papers/05_power_unit_commitment/hong_2025_qubit_efficient_quantum_annealing_stochastic_unit_commitment.pdf` | qubit-efficient stochastic UC | 节省 qubit 的建模方式 | 数据规模较大时参考 |
| `../papers/05_power_unit_commitment/zhou_2025_problem_structure_informed_qaoa_unit_commitment.pdf` | 结构感知 QAOA for UC | 利用 UC 问题结构设计 ansatz | 写“问题结构适配量子算法” |

## 06 工业排产 / Scheduling

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/06_scheduling/venturelli_2015_quantum_annealing_job_shop_scheduling.pdf` | 量子退火 job-shop | 时间索引变量、precedence、machine constraint | 排产方向首读 |
| `../papers/06_scheduling/schworm_2023_multi_objective_quantum_annealing_flexible_job_shop.pdf` | 多目标 flexible job shop | 多目标和柔性机器选择 | 排产扩展 |
| `../papers/06_scheduling/lopez_ruiz_2025_non_variational_quantum_job_shop_scheduling.pdf` | 非变分量子 job shop | 不走经典 QAOA 的替代路线 | 算法创新备选 |
| `../papers/06_scheduling/sawamura_2025_quantum_classical_hybrid_multi_objective_job_shop.pdf` | 量子-经典多目标 job shop | 多目标权衡、混合流程 | 展示结果图参考 |

## 07 物流路径 / VRP

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/07_logistics_vrp/feld_2019_hybrid_cvrp_quantum_annealer.pdf` | CVRP 混合量子退火 | clustering + routing 的混合思路 | 物流方向首读 |
| `../papers/07_logistics_vrp/tambunan_2022_quantum_annealing_vrp_weighted_segment.pdf` | VRP weighted segment | 路段变量和权重设计 | 路径成本建模 |
| `../papers/07_logistics_vrp/qubit_efficient_quantum_algorithms_vrp_2023.pdf` | qubit-efficient VRP | 节省 qubit 的路径编码 | 变量数过大时参考 |
| `../papers/07_logistics_vrp/holliday_2025_quantum_annealing_vrp_time_windows.pdf` | VRPTW 量子退火 | 时间窗约束 | 有时间窗题时参考 |
| `../papers/07_logistics_vrp/azfar_2025_qaoa_vehicle_routing.pdf` | QAOA for VRP | QAOA 路径问题表达 | 想走 QAOA 物流路线时参考 |

## 08 金融投资组合

| 文件 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| `../papers/08_finance_portfolio/sakuler_2023_real_world_portfolio_quantum_annealing.pdf` | 真实投资组合量子退火 | 风险-收益、约束、真实数据 | 金融方向首读 |
| `../papers/08_finance_portfolio/chen_2023_portfolio_qaoa_hard_constraint_binary_encoding.pdf` | hard-constraint QAOA portfolio | 约束保持编码 | cardinality/预算约束参考 |
| `../papers/08_finance_portfolio/yao_2023_fermionic_qaoa_portfolio.pdf` | fermionic QAOA portfolio | 固定资产数约束 | 可行空间搜索参考 |
| `../papers/08_finance_portfolio/morapakula_2025_end_to_end_portfolio_quantum_annealing.pdf` | end-to-end portfolio QA | 从数据到解的完整流程 | Demo 管线参考 |
| `../papers/08_finance_portfolio/mancilla_2026_constrained_portfolio_qaoa_xy_mixers.pdf` | QAOA + XY mixers portfolio | XY mixer 保持约束 | 金融 MIQP + QAOA 路线 |

## 09 Learning-Guided Optimization / 神经网络辅助优化

| 资料 | 主题 | 杰瑞重点看什么 | 比赛用途 |
| --- | --- | --- | --- |
| Bengio et al., https://arxiv.org/abs/1811.06128 | ML for combinatorial optimization survey | construction / improvement / branching / surrogate 的分类 | 解释为什么神经网络是优化流程助手，不是最优性保证器 |
| Gasse et al., https://arxiv.org/abs/1906.01629 | GNN 学 MILP branching | 变量-约束二部图、branching score | route 7 的 constraint-variable graph 设计 |
| Nair et al., https://arxiv.org/abs/2012.13349 | Neural Diving / Neural Branching | partial assignment、固定变量、缩小 MIP | 和 Hybrid fix-and-optimize 对接 |
| Darvariu et al., https://arxiv.org/abs/2404.06492 | Graph RL for combinatorial optimization | repair / local search policy 的 MDP 视角 | 训练 violation repair 和局部搜索动作 |
| Liu et al., https://arxiv.org/abs/2406.02872 | Automated GNN for combinatorial optimization | 图特征、架构搜索、跨问题泛化风险 | P2/P3 的 GNN policy 参考 |
| Egger et al., https://arxiv.org/abs/2009.10095 | Warm-starting quantum optimization | 用经典松弛解初始化 QAOA | 把 ML / relaxation 输出接到 QAOA |

## 10 工具链与官方文档

这些资料不一定是论文，但清哥落地代码会用到。

| 工具 | 官方资料 | 用途 |
| --- | --- | --- |
| Qiskit Optimization | https://qiskit-community.github.io/qiskit-optimization/ | `QuadraticProgram`、MILP/MIQP 建模、QUBO 转换、QAOA/NumPyMinimumEigensolver |
| Qiskit Algorithms | https://qiskit-community.github.io/qiskit-algorithms/ | QAOA、VQE、优化器 |
| D-Wave Ocean SDK | https://docs.dwavequantum.com/ | `dimod.BinaryQuadraticModel`、QUBO/Ising、退火采样器 |
| OpenJij | https://www.openjij.org/ | 本地 simulated annealing / simulated quantum annealing |
| PennyLane QAOA | https://docs.pennylane.ai/ | QAOA circuit 和 differentiable workflow |
| OR-Tools | https://developers.google.com/optimization | 经典基线：MILP、routing、scheduling |
| Pyomo | https://www.pyomo.org/ | 数学规划建模 |

## 比赛时建议的引用组合

如果需要在 PPT 里放 6 个核心参考：

1. Glover, Kochenberger, Du, "A Tutorial on Formulating and Using QUBO Models".
2. Lucas, "Ising formulations of many NP problems".
3. Farhi, Goldstone, Gutmann, "A Quantum Approximate Optimization Algorithm".
4. Hadfield et al., "From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz".
5. Hen, Spedalieri, "Quantum Annealing for Constrained Optimization".
6. Bengio, Lodi, Prouvost, "Machine Learning for Combinatorial Optimization".

如果赛题落到具体场景，再补对应场景首读论文：

- 电力：Koretsky et al., QAOA for unit commitment.
- 排产：Venturelli et al., quantum annealing for job-shop scheduling.
- 物流：Feld et al., hybrid solution method for CVRP using a quantum annealer.
- 金融：Sakuler et al., real-world portfolio optimization with quantum annealing.
