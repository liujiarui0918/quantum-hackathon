# 模型与算法路线分类索引

更新日期：2026-05-15

## 目标

本索引把现有文献从“论文主题目录”重新组织为“可开发的模型/算法路线”。分类口径以通用混合整数带约束优化为主，暂不绑定电力、排产、物流、金融等具体业务场景。

开发文档优先服务写代码的人：每条路线都需要沉淀变量编码、目标函数构造、约束处理、求解流程、输入输出接口、测试样例、评估指标和工程风险。

## 分类原则

1. 优先按代码模块职责分类，而不是按论文发表主题分类。
2. 一篇论文可以服务多条路线，但只给一个主归属，避免重复精读。
3. 理论路线论文进入第一轮精读；场景论文作为后续验证样例和 benchmark。
4. 每条路线最后输出一份开发需求文档，放在 `literature/requirements/`。

## 路线 1：QUBO / Ising 通用建模底座

**开发目标**：实现从 0/1 变量、 bounded integer 变量、线性/二次目标、线性等式/不等式约束到 QUBO / Ising / BQM 的转换器。

**核心论文**：

- `../papers/01_qubo_ising_formulations/glover_kochenberger_du_2018_qubo_tutorial.pdf`
- `../papers/01_qubo_ising_formulations/lucas_2014_ising_formulations_np_problems.pdf`
- `../papers/01_qubo_ising_formulations/dattani_2019_quadratization_discrete_optimization_quantum_mechanics.pdf`
- `../papers/01_qubo_ising_formulations/desantis_2024_optimized_qubo_formulation_methods.pdf`

**主要开发产物**：

- QUBO 数据结构：变量注册表、线性项、二次项、常数项、变量来源映射。
- 约束到罚项的基础转换：pairwise penalty、`(Ax - b)^2`、binary slack。
- QUBO 与 Ising 互转：`x in {0,1}` 与 `s in {-1,+1}`。
- 高阶项二次化：引入辅助变量并保持 ground state。
- 建模诊断器：变量数、辅助变量数、coupler 数、系数范围、约束违背成本。

**首份需求文档**：`../requirements/01_qubo_ising_modeling_requirements.md`

## 路线 2：约束处理、编码与罚函数调参

**开发目标**：解决“有约束问题转成无约束 QUBO 后是否仍能得到可行解”的核心风险，尤其是不等式、容量、预算、唯一性、互斥、选择数量、软约束和硬约束。

**核心论文**：

- `../papers/03_constraints_and_encodings/hen_spedalieri_2016_quantum_annealing_constrained_optimization.pdf`
- `../papers/03_constraints_and_encodings/montanez_barrera_2022_unbalanced_penalization_inequality_constraints.pdf`
- `../papers/03_constraints_and_encodings/montanez_barrera_2023_unbalanced_penalization_dwave.pdf`
- `../papers/03_constraints_and_encodings/chancellor_2019_domain_wall_encoding.pdf`
- `../papers/03_constraints_and_encodings/chen_2021_domain_wall_encoding_performance.pdf`
- `../papers/01_qubo_ising_formulations/desantis_2024_optimized_qubo_formulation_methods.pdf`（路线 1 已首读，路线 2 复用其约束优化部分）

**主要开发产物**：

- 约束类型系统：equality、inequality、at-most-one、exactly-one、cardinality、bounded sum、indicator constraint。
- penalty strategy 接口：balanced square、unbalanced penalty、domain-wall、one-hot、binary slack。
- penalty 权重建议器：基于目标函数收益上界、局部变量影响和约束优先级。
- 可行性检查与 repair：求解后把 infeasible sample 修复为 feasible candidate。
- 约束编码 benchmark：变量数、coupler 数、可行解比例、目标损失。

**计划需求文档**：`../requirements/02_constraint_handling_requirements.md`

## 路线 3：Quantum Annealing / Simulated Annealing 求解路线

**开发目标**：把 QUBO/BQM 接到本地模拟退火、模拟量子退火、tabu search、D-Wave Ocean 等采样器，形成可替换的 solver backend。

**核心论文**：

- `../papers/00_surveys_overviews/phillipson_bausch_2021_quantum_annealing_industry_review.pdf`
- `../papers/00_surveys_overviews/sharma_2026_quantum_annealing_combinatorial_optimization_review.pdf`
- `../papers/03_constraints_and_encodings/hen_spedalieri_2016_quantum_annealing_constrained_optimization.pdf`
- `../papers/03_constraints_and_encodings/montanez_barrera_2023_unbalanced_penalization_dwave.pdf`

**主要开发产物**：

- BQM adapter：统一输出给 `dimod`、OpenJij、自研 SA。
- sampler interface：`sample(bqm, config) -> sampleset`。
- 后处理器：去重、能量排序、约束检查、repair、解码为业务变量。
- 退火参数配置：reads、sweeps、temperature schedule、chain strength、time limit。
- 对比基线：random、greedy、OR-Tools/CP-SAT、小规模 brute force。

**计划需求文档**：`../requirements/03_annealing_solver_requirements.md`

## 路线 4：QAOA / VQA 标准量子门模型路线

**开发目标**：实现标准 QAOA 工作流：QUBO/Ising Hamiltonian -> circuit ansatz -> classical optimizer -> measurement decoding，并形成可运行的小规模 demo。

**核心论文**：

- `../papers/02_qaoa_vqa_algorithms/farhi_goldstone_gutmann_2014_qaoa.pdf`
- `../papers/02_qaoa_vqa_algorithms/farhi_goldstone_gutmann_2014_qaoa_bounded_occurrence_constraint.pdf`
- `../papers/02_qaoa_vqa_algorithms/moll_2018_quantum_optimization_variational_algorithms_near_term.pdf`
- `../papers/02_qaoa_vqa_algorithms/zhou_2020_qaoa_performance_mechanism.pdf`
- `../papers/00_surveys_overviews/blekos_2024_qaoa_variants_review.pdf`
- `../papers/00_surveys_overviews/cerezo_2021_variational_quantum_algorithms_review.pdf`

**主要开发产物**：

- Hamiltonian builder：从 QUBO/BQM 构造 cost Hamiltonian。
- QAOA runner：支持 p 层、参数初始化、optimizer、shot 数、seed。
- 参数策略：random、linear ramp、warm-start params、multi-start。
- 小规模 exact comparison：与 brute force 或 NumPyMinimumEigensolver 对比。
- NISQ 风险日志：qubit 数、depth、barren plateau、噪声和采样误差。

**计划需求文档**：`../requirements/04_qaoa_vqa_requirements.md`

## 路线 5：Constrained Mixer / Warm-start / XY Mixer 可行空间搜索路线

**开发目标**：减少对大罚函数的依赖，让量子/变分算法在满足关键约束的可行空间内演化，适合 cardinality、one-hot、固定选择数量、预算类约束。

**核心论文**：

- `../papers/02_qaoa_vqa_algorithms/hadfield_2019_quantum_alternating_operator_ansatz.pdf`
- `../papers/03_constraints_and_encodings/fuchs_2022_constrained_mixers_qaoa.pdf`
- `../papers/02_qaoa_vqa_algorithms/egger_2021_warm_starting_quantum_optimization.pdf`
- `../papers/03_constraints_and_encodings/bucher_2026_iterative_warm_start_xy_mixers.pdf`
- `../papers/02_qaoa_vqa_algorithms/bravyi_2020_obstacles_variational_quantum_optimization_rqaoa.pdf`

**主要开发产物**：

- 约束感知 ansatz 策略：X mixer、XY mixer、problem-specific mixer。
- 初始态构造器：可行初始解、LP/QP relaxation warm-start、heuristic seed。
- 可行空间采样器：measurement 后理论上保持关键约束。
- R-QAOA / recursive variable fixing：从采样相关性中固定变量。
- 与路线 2 的对比：hard constraint mixer vs penalty-based QUBO。

**计划需求文档**：`../requirements/05_constrained_mixer_warm_start_requirements.md`

## 路线 6：Hybrid MILP / MIQP 分解与量子子问题路线

**开发目标**：把通用混合整数优化拆成经典连续/松弛/repair 模块和量子/量子启发离散子问题模块，形成 hackathon 最稳的工程路线。

**核心论文**：

- `../papers/04_milp_miqp_hybrid/braine_2021_mixed_binary_optimization_transaction_settlement.pdf`
- `../papers/04_milp_miqp_hybrid/gambella_2021_multiblock_admm_mixed_binary_optimization.pdf`
- `../papers/04_milp_miqp_hybrid/brown_2022_copositive_mixed_binary_quadratic_ising_solvers.pdf`
- `../papers/02_qaoa_vqa_algorithms/egger_2021_warm_starting_quantum_optimization.pdf`（路线 5 已首读，路线 6 复用 warm-start 部分）

**主要开发产物**：

- problem decomposer：区分 binary、integer、continuous、linear、quadratic 部分。
- classical relaxation：LP/QP/MILP baseline、continuous relaxation、rounding。
- quantum subproblem builder：固定部分变量后生成小 QUBO。
- ADMM / block-coordinate workflow：交替优化、惩罚更新、收敛判定。
- repair 与 polishing：经典求解器把采样解修复并局部优化。

**计划需求文档**：`../requirements/06_hybrid_milp_miqp_requirements.md`

## 路线 7：Learning-Guided Optimization / 神经网络辅助混合优化路线

**开发目标**：把 QUBO / MILP / MIQP 表示成图或状态序列，训练或接入学习策略来辅助 warm-start、变量固定、branching、repair、local search 和 QAOA/退火参数调度。

**核心论文**：

- Bengio, Lodi, Prouvost, Machine Learning for Combinatorial Optimization: a Methodological Tour d'Horizon. https://arxiv.org/abs/1811.06128
- Gasse et al., Exact Combinatorial Optimization with Graph Convolutional Neural Networks. https://arxiv.org/abs/1906.01629
- Nair et al., Solving Mixed Integer Programs Using Neural Networks. https://arxiv.org/abs/2012.13349
- Darvariu et al., Graph Reinforcement Learning for Combinatorial Optimization. https://arxiv.org/abs/2404.06492
- Liu et al., Combinatorial Optimization with Automated Graph Neural Networks. https://arxiv.org/abs/2406.02872
- Egger et al., Warm-starting quantum optimization. https://arxiv.org/abs/2009.10095

**主要开发产物**：

- QUBO graph exporter：node features、edge coefficients、label bitstring、diagnostics。
- training JSONL builder：小规模 exact label，中规模 SA / hybrid incumbent pseudo-label。
- warm-start policy 接口：输出每个变量取 1 的概率、候选 bitstring 和 QAOA/SA 初始建议。
- variable fixing plan：高置信度变量固定，不确定变量进入 QUBO / QAOA / hybrid 子问题。
- repair / local-search policy scaffold：把 violation reduction 和 objective improvement 作为训练信号。
- benchmark 约束：学习策略必须与 exact、SA、QAOA、hybrid baseline 对比，不承诺最优性。

**计划需求文档**：`../requirements/07_learning_guided_optimization_requirements.md`

## 场景论文：暂作为 benchmark 与案例库

这些论文不进入第一轮理论路线分类的主线精读，但后续可以用来构造测试用例、demo 叙事和对比指标。

**电力机组组合**：

- `../papers/05_power_unit_commitment/koretsky_2021_qaoa_unit_commitment.pdf`
- `../papers/05_power_unit_commitment/mahroo_2022_hybrid_quantum_classical_unit_commitment.pdf`
- `../papers/05_power_unit_commitment/hong_2025_qubit_efficient_quantum_annealing_stochastic_unit_commitment.pdf`
- `../papers/05_power_unit_commitment/zhou_2025_problem_structure_informed_qaoa_unit_commitment.pdf`

**工业排产 / Scheduling**：

- `../papers/06_scheduling/venturelli_2015_quantum_annealing_job_shop_scheduling.pdf`
- `../papers/06_scheduling/schworm_2023_multi_objective_quantum_annealing_flexible_job_shop.pdf`
- `../papers/06_scheduling/lopez_ruiz_2025_non_variational_quantum_job_shop_scheduling.pdf`
- `../papers/06_scheduling/sawamura_2025_quantum_classical_hybrid_multi_objective_job_shop.pdf`

**物流路径 / VRP**：

- `../papers/07_logistics_vrp/feld_2019_hybrid_cvrp_quantum_annealer.pdf`
- `../papers/07_logistics_vrp/tambunan_2022_quantum_annealing_vrp_weighted_segment.pdf`
- `../papers/07_logistics_vrp/qubit_efficient_quantum_algorithms_vrp_2023.pdf`
- `../papers/07_logistics_vrp/holliday_2025_quantum_annealing_vrp_time_windows.pdf`
- `../papers/07_logistics_vrp/azfar_2025_qaoa_vehicle_routing.pdf`

**金融投资组合**：

- `../papers/08_finance_portfolio/sakuler_2023_real_world_portfolio_quantum_annealing.pdf`
- `../papers/08_finance_portfolio/chen_2023_portfolio_qaoa_hard_constraint_binary_encoding.pdf`
- `../papers/08_finance_portfolio/yao_2023_fermionic_qaoa_portfolio.pdf`
- `../papers/08_finance_portfolio/morapakula_2025_end_to_end_portfolio_quantum_annealing.pdf`
- `../papers/08_finance_portfolio/mancilla_2026_constrained_portfolio_qaoa_xy_mixers.pdf`

## 推荐精读顺序

1. 路线 1：QUBO / Ising 通用建模底座。
2. 路线 2：约束处理、编码与罚函数调参。
3. 路线 3：退火类求解器。
4. 路线 6：Hybrid MILP / MIQP 分解。
5. 路线 4：QAOA / VQA 标准路线。
6. 路线 5：Constrained Mixer / Warm-start / XY Mixer。
7. 路线 7：Learning-Guided Optimization / 神经网络辅助混合优化。

这个顺序更适合开发推进：先有统一建模层和约束层，再接求解器；QAOA 与 constrained mixer 可以在小规模样例上补充创新展示；learning-guided 层最后接入，用已有求解结果生成训练信号。
