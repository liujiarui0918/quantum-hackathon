# 源代码包 README

队伍：平步青云  
赛道：混合整数优化问题赛道  
推荐运行目录：源码包根目录

## 环境

- Python `>=3.10`
- 运行依赖：`numpy`, `scipy`, `matplotlib`
- 测试依赖：`pytest`
- 可选量子模拟：主办方 `qiskit` 容器或本地安装 `qiskit-aer`

安装：

```bash
python -m pip install -e ".[dev]"
```

## 一键测试

```bash
python -m pytest -q
```

当前本地完整验证结果：`54 passed`。

## 运行官方小规模样例

样例 A：

```bash
python -m quantum_hackathon.miqp_cli \
  --input "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz" \
  --output results/miqp_sample_A_route7.json \
  --solution-npz results/miqp_sample_A_solution.npz \
  --exact-binary-limit 15 \
  --max-block-size 12 \
  --candidate-limit 64
```

样例 B：

```bash
python -m quantum_hackathon.miqp_cli \
  --input "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_B.npz" \
  --output results/miqp_sample_B_route7.json \
  --solution-npz results/miqp_sample_B_solution.npz \
  --exact-binary-limit 16 \
  --max-block-size 20 \
  --candidate-limit 128 \
  --max-iterations 5 \
  --seeds 3,7,11,19
```

Windows PowerShell 中同样可以运行，只需保持路径引号。

## 输出文件

- `*_route7.json`：完整诊断，包括实例信息、参考最优、seed portfolio、best solution、block、warm-start、cut advice、连续子问题解。
- `*_solution.npz`：提交友好的数组结果，包含 `x`, `y`, `objective`, `feasible`。

结果汇总：

```bash
python scripts/render_miqp_results.py \
  results/miqp_sample_A_route7.json \
  results/miqp_sample_B_route7.json \
  --output results/miqp_route7_summary.md
```

横向基线与论文图片：

```bash
python scripts/miqp_baseline_study.py \
  --inputs \
  "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz" \
  "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_B.npz" \
  --output-dir baseline_study \
  --route7-json-dir results \
  --random-reads 96 \
  --sa-reads 48 \
  --sa-sweeps 80 \
  --qaoa-block-size 10 \
  --qaoa-shots 160 \
  --meta-population 24 \
  --meta-iterations 8
```

该命令会生成：

- `baseline_study/miqp_baseline_study.csv`
- `baseline_study/miqp_baseline_study.md`
- `baseline_study/figures/*.png`

block selector 权重与聚类消融：

```bash
python scripts/miqp_selector_ablation.py \
  --inputs \
  "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz" \
  "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_B.npz" \
  --output-dir selector_ablation \
  --max-block-size 16 \
  --max-iterations 2 \
  --candidate-limit 48
```

明早真实数据到达后的自动赛马入口：

```bash
python scripts/miqp_auto_sota.py \
  --inputs "path/to/real_1.npz" "path/to/real_2.npz" \
  --output-dir results/auto_sota \
  --seeds 3,7,11,19 \
  --max-lp-evals 800
```

route7++ 训练数据与非神经线性 block scorer（可选，不作为最终默认主线）：

```bash
python scripts/miqp_trace_blocks.py \
  --inputs \
  "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz" \
  "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_B.npz" \
  --output-jsonl results/route7pp/block_traces.jsonl \
  --results-dir results/route7pp/runs \
  --block-pool \
  --blocks-per-iteration 3 \
  --candidate-budget-per-block 64

python scripts/miqp_train_block_model.py \
  --inputs results/route7pp/block_traces.jsonl \
  --output models/block_selector_model.json
```

可选生成 MIQP-like synthetic 数据：

```bash
python scripts/miqp_synthetic_suite.py \
  --output-dir data/miqp_synthetic \
  --manifest data/miqp_synthetic/manifest.json \
  --count 32
```

## 关键目录

```text
src/quantum_hackathon/miqp/
  model.py      MIQP 数据结构、目标函数、约束检查
  loader.py     官方 .npz 读取器
  route7.py     MIQP-aware block selector / warm-start / cut advisor

src/quantum_hackathon/solvers/qaoa/
  hamiltonian.py  QUBO -> Ising
  runner.py       QAOA 参数搜索与采样
  backends.py     本地模拟器与 Qiskit Aer backend

scripts/
  render_miqp_results.py  结果表格渲染脚本
  miqp_baseline_study.py  横向基线、资源画像与论文插图生成脚本
  miqp_selector_ablation.py  block selector 权重与聚类策略消融脚本
  miqp_trace_blocks.py  route7++ block trace/训练数据采集
  miqp_synthetic_suite.py  MIQP-like synthetic .npz 生成器
  miqp_train_block_model.py  非神经线性 block scorer 训练
  miqp_auto_sota.py  多配置赛马并选择每个实例的最高可行解

tests/
  test_miqp_route7.py     MIQP 路线专用测试
  test_*                  其余七条路线与集成测试

results/
  已同步的 route7、baseline study 与 selector ablation 结果副本

submission/results/
  已复现实验结果

submission/baseline_study/
  横向基线结果、CSV/Markdown 表格和论文插图

submission/selector_ablation/
  selector 消融结果、CSV/Markdown 表格和插图
```

## 算法摘要

本方案不把连续变量 `y` 离散化进大 QUBO。固定二进制变量 `x` 后，连续子问题是 LP：

```text
maximize h^T y
subject to G y <= b - A x
           y >= 0
```

路线 7 / route7++ 的主循环为：

```text
score variables -> generate block pool -> warm-start probabilities
-> block QUBO / Ising -> exact / learning-guided / SA / QAOA-compatible candidates
-> 1-swap / 2-swap / destroy-repair / local branch candidates
-> repair Bx <= b' -> LP cache -> solve LP for y
-> objective, cut advice, trace records -> next block
```

量子部分体现在 block QUBO 可转为 Ising Hamiltonian，并接入 QAOA/Aer/退火 backend。提交版本默认使用可复现的 exact、simulated annealing、learning-guided 和小 block QAOA-compatible backend；若评审环境提供真实量子 backend 或 Aer GPU，可在同一 block 接口替换执行层。
