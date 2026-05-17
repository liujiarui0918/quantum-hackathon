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

## 堡垒机 / qiskit 容器复现注意事项

本源码包已在题目堡垒机的 `qiskit` Docker 容器中从压缩包干净解压复现。实测环境为 Python `3.12.3`，容器内已有 `numpy`、`scipy` 和 `pytest`，但基础镜像可能没有 `unzip`，也可能没有预装 `matplotlib`。

如果容器中没有 `unzip`，可直接用 Python 标准库解压：

```bash
python -m zipfile -e "混合整数优化问题赛道-平步青云-源代码.zip" /tmp/qh_repro_submit
cd /tmp/qh_repro_submit
```

如果只运行 A/B 样例主求解流程，核心依赖是 `numpy` 与 `scipy`；如果要运行横向 baseline 作图或完整测试，请使用正常安装命令让 `pip` 补齐 `matplotlib`：

```bash
python -m pip install -e ".[dev]"
```

若评审环境中使用了 `--no-deps` 安装，且随后运行 `scripts/miqp_baseline_study.py` 或完整测试时提示缺少 `matplotlib`，执行：

```bash
python -m pip install matplotlib
```

本次堡垒机容器复现结果：`python -m pytest -q` 通过 `56 passed`；重新运行 A/B 样例后，A 得到 `106.094636140193074`，B 得到 `610.266638604722743`，二者均可行且与官方最优值一致。

## 一键测试

```bash
python -m pytest -q
```

当前本地完整验证结果：`56 passed`。

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
  --candidate-limit 192 \
  --max-iterations 8 \
  --seed 11 \
  --block-pool \
  --blocks-per-iteration 3 \
  --candidate-budget-per-block 64 \
  --max-lp-evals 800 \
  --qaoa-max-qubits 0 \
  --weight-objective 0.25 \
  --weight-coupling 0.25 \
  --weight-mixed 0.25 \
  --weight-binary 0.25 \
  --post-polish-rounds 2 \
  --polish-candidate-limit 128
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
  --profile safe \
  --seeds 3,7,11,19 \
  --max-lp-evals 800
```

需要更强但更耗时的赛马时，将 `--profile safe` 改为 `--profile deep`。默认主线仍为非神经 route7++。

五个官方隐藏测试文件到达后的推荐入口：

```bash
mkdir -p data/final_tests
# 将 miqp_test_1.npz ... miqp_test_5.npz 放入 data/final_tests/
python scripts/run_miqp_hidden_demo.py \
  --input-dir data/final_tests \
  --output-dir results/hidden_demo
```

该脚本按规模自动选择参数：

- `miqp_test_1.npz`：`n=15,p=5,m1=5,m2=1`，直接精确枚举二进制部分并求 LP。
- `miqp_test_2.npz`：`n=40,p=10,m1=10,m2=2`，启用 subQUBO 分块与多 seed。
- `miqp_test_3.npz`：`n=80,p=20,m1=20,m2=4`，使用 route7++ block pool，避免随机分块。
- `miqp_test_4.npz`：`n=120,p=30,m1=30,m2=6`，使用 deep profile 和 affinity-cluster。
- `miqp_test_5.npz`：`n=150,p=50,m1=50,m2=10`，扩大 seed/config portfolio，并用 LP 预算控时。

预览计划但不求解：

```bash
python scripts/run_miqp_hidden_demo.py \
  --input-dir data/final_tests \
  --output-dir results/hidden_demo \
  --dry-run
```

## 最终验证数据集结果

本源码包已纳入 2026-05-17 在堡垒机 `qiskit` 容器中得到的五个大规模验证结果。主办方未随验证数据提供标准答案，因此这里不写官方 gap，只报告重算目标值、可行性和约束违反量。最终提交预测文件放在源码包根目录：

- `miqpscale1.npz`
- `miqpscale2.npz`
- `miqpscale3.npz`
- `miqpscale4.npz`
- `miqpscale5.npz`

每个 `miqpscaleX.npz` 均包含 `x`, `y`, `objective`, `feasible` 四个数组字段。诊断版结果保留在 `results/hidden_final/`，包括五个 `miqp_test_X_route7.json`、五个 `miqp_test_X_solution.npz`、`hidden_final_summary.md/json`、`verify_hidden_final.json`、`verify_miqpscale.json` 以及 `figures/sota_loss_curves.png/csv`。

最终结果汇总：

| instance | objective | feasible | config | seed | LP calls | runtime(s) |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| `miqp_test_1` | 157.585995 | True | `route7_safe` | 7 | 28032 | 42.99 |
| `miqp_test_2` | 459.864903 | True | `miqp_test_2_seed23_cluster_boost` | 23 | 1057 | 110.60 |
| `miqp_test_3` | 765.690515 | True | `miqp_test_3_seed23_cluster_boost` | 23 | 1684 | 168.73 |
| `miqp_test_4` | 636.175569 | True | `miqp_test_4_seed23_cluster_boost` | 23 | 1371 | 245.63 |
| `miqp_test_5` | 842.345737 | True | `route7pp_balanced` | 7 | 554 | 85.44 |

用官方大规模验证数据复算提交文件：

```bash
python scripts/verify_hidden_final.py \
  --input-dir "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道大规模得分验证数据" \
  --predictions-dir . \
  --output-json results/hidden_final/verify_miqpscale.json
```

用诊断目录复算：

```bash
python scripts/verify_hidden_final.py \
  --input-dir "量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道大规模得分验证数据" \
  --results-dir results/hidden_final \
  --output-json results/hidden_final/verify_hidden_final.json
```

堡垒机宿主机与 `qiskit` 容器中可使用相同命令。若源码 zip 已上传到宿主机 `/home/infra/.../`，可在宿主机执行：

```bash
docker cp "混合整数优化问题赛道-平步青云-源代码.zip" qiskit:/root/submission_recheck/source.zip
docker exec qiskit bash -lc 'rm -rf /root/submission_recheck/work && python -m zipfile -e /root/submission_recheck/source.zip /root/submission_recheck/work && cd /root/submission_recheck/work && python -m pip install -e ".[dev]" && python -m pytest tests/test_miqp_route7.py tests/test_miqp_sota_scripts.py -q && python scripts/verify_hidden_final.py --input-dir /root/quantum_hackathon_hidden_run/final_tests --results-dir results/hidden_final'
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
  run_miqp_hidden_demo.py  五个官方隐藏测试的规模感知一键运行入口
  miqp_trace_blocks.py  route7++ block trace/训练数据采集
  miqp_synthetic_suite.py  MIQP-like synthetic .npz 生成器
  miqp_train_block_model.py  非神经线性 block scorer 训练
  miqp_auto_sota.py  多配置赛马并选择每个实例的最高可行解
  miqp_plot_sota_curves.py  最终验证集收敛曲线生成
  verify_hidden_final.py  最终 miqpscaleX.npz / hidden_final 结果复算

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
