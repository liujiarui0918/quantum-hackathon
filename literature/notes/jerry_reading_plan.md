# 杰瑞准备阶段阅读计划

目标不是把论文都精读完，而是形成比赛当天能直接调用的建模和算法材料。

## Day 1: 建立共同语言

阅读：

- `../papers/01_qubo_ising_formulations/glover_kochenberger_du_2018_qubo_tutorial.pdf`
- `../papers/01_qubo_ising_formulations/lucas_2014_ising_formulations_np_problems.pdf`
- `../papers/00_surveys_overviews/blekos_2024_qaoa_variants_review.pdf`

输出：

- MILP / MIQP / QUBO / Ising / QAOA / 量子退火的一页中文解释。
- QUBO 标准形式：`min x^T Q x, x in {0,1}^n`。
- Ising 变量替换：`x = (1 + z) / 2` 或 `z = 2x - 1`，注意符号约定。

## Day 2: QUBO 转换模板

阅读：

- `../papers/01_qubo_ising_formulations/glover_kochenberger_du_2018_qubo_tutorial.pdf`
- `../papers/01_qubo_ising_formulations/desantis_2024_optimized_qubo_formulation_methods.pdf`
- `../papers/03_constraints_and_encodings/montanez_barrera_2022_unbalanced_penalization_inequality_constraints.pdf`

输出给清哥：

- 等式约束罚函数模板：`A * (sum_i x_i - b)^2`。
- one-hot 约束模板：`A * (sum_j x_ij - 1)^2`。
- 不等式约束处理方案：松弛变量、unbalanced penalization、repair 三选一。
- 惩罚项调参原则：先保证可行，再优化目标；记录 penalty sweep。

## Day 3: QAOA / 变分算法路线

阅读：

- `../papers/02_qaoa_vqa_algorithms/farhi_goldstone_gutmann_2014_qaoa.pdf`
- `../papers/02_qaoa_vqa_algorithms/zhou_2020_qaoa_performance_mechanism.pdf`
- `../papers/02_qaoa_vqa_algorithms/egger_2021_warm_starting_quantum_optimization.pdf`
- `../papers/02_qaoa_vqa_algorithms/hadfield_2019_quantum_alternating_operator_ansatz.pdf`

输出：

- 标准 QAOA 流程图：构造 cost Hamiltonian、mixer、参数优化、采样、解码、评估。
- 何时用 standard X mixer，何时用 constrained mixer / XY mixer。
- warm-start 适合的场景：有连续松弛解、MILP/MIQP 小规模基线、或者启发式初解。

## Day 4: 退火和约束处理

阅读：

- `../papers/03_constraints_and_encodings/hen_spedalieri_2016_quantum_annealing_constrained_optimization.pdf`
- `../papers/03_constraints_and_encodings/chancellor_2019_domain_wall_encoding.pdf`
- `../papers/03_constraints_and_encodings/fuchs_2022_constrained_mixers_qaoa.pdf`

输出：

- 量子退火 / 模拟退火 / simulated quantum annealing 的区别。
- 离散多值变量编码方式：one-hot、binary、domain-wall。
- 非法解处理策略：罚函数、约束保持 mixer、后处理 repair。

## Day 5: 四类场景快速建模

按比赛可能方向选择阅读：

- 电力机组组合：`../papers/05_power_unit_commitment`
- 工业排产：`../papers/06_scheduling`
- 物流路径：`../papers/07_logistics_vrp`
- 投资组合：`../papers/08_finance_portfolio`

输出：

- 每个场景一张建模卡片：变量、目标、约束、典型 QUBO 项、可视化方式。
- 每个场景至少准备一个小规模样例，方便清哥本地 demo。

## Day 6: 工程接口

阅读：

- `literature_index.md` 里的工具链部分。
- Qiskit Optimization / D-Wave Ocean / OpenJij 官方文档。

输出给清哥：

- `problem.json` 输入字段草案。
- `result.json` 输出字段草案：`objective_value`、`feasible`、`constraint_violations`、`runtime_ms`、`solution`、`baseline`。
- solver 接口草案：`solve(problem, method, params) -> result`。

## Day 7: 队内模拟

目标：

- 选一个小型场景完整跑通：建模、基线、QUBO、采样、repair、结果展示。
- 杰瑞负责检查公式和结果合法性。
- 清哥负责一键运行。
- 龙哥负责把结果图做成评委能看懂的材料。

最终交付：

- `赛题知识卡片.md`
- `QUBO建模模板.md`
- `算法路线候选.md`
- `四类场景建模卡片.md`
