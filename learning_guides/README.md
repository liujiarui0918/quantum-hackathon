# 七条模型路线学习讲义

这组材料是给比赛前共读用的，不是代码复现说明。

建议阅读顺序：

1. `00_seven_routes_big_picture.md`
2. `01_qubo_ising_modeling.md`
3. `02_constraint_handling.md`
4. `03_annealing_solver.md`
5. `06_hybrid_milp_miqp.md`
6. `04_qaoa_vqa.md`
7. `05_constrained_mixer_warm_start.md`
8. `07_learning_guided_optimization.md`

为什么路线 6 放在路线 4、5 前面：比赛题通常先要求一个能稳定求解的工程方案，再要求量子算法亮点。Hybrid 分解能帮你判断哪些变量交给经典求解，哪些变量变成小 QUBO 子问题；理解这个以后，再看 QAOA 和 constrained mixer，会更知道它们应该插在哪里。

为什么路线 7 放在最后：神经网络辅助优化要建立在建模、约束、求解和 benchmark 都稳定之后。GPU 适合训练 warm-start、变量固定、repair 和参数调度策略，但不能替代 exact/bound/feasibility check。

PDF 版本生成到 `learning_guides/pdf/`，LaTeX 中间稿生成到 `learning_guides/tex/`。

本地重新生成：

```powershell
python scripts\build_learning_guides.py
```

生成脚本使用 MiKTeX / XeLaTeX 编译，适合中文正文和数学公式排版。旧的 HTML 打印链路已移除。
