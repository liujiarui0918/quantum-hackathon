# 量子黑客松 MIQP 赛题项目复盘演讲稿

预计总时长：100 分钟左右，另留 20 分钟讨论。  
整体结构按照“项目全景、赛题建模、算法主线、实验结果、工程边界、后续研究”展开。

## 第 1 页：标题页，约 1 分钟

各位老师、同学好，今天我汇报这次量子黑客松混合整数优化赛道的工作。汇报题目是“从七条量子优化路线到 QBB-MIQP 混合求解器”。今天不会只讲一个最终分数，而是把整个项目从赛题理解、方法选择、代码实现、结果验证到后续研究问题完整复盘一遍。  

这次项目的核心其实是一个取舍：我们没有把整个混合整数二次规划硬塞进一个巨大的量子线路，而是把量子或量子启发搜索放在最关键的二进制变量块上，再用经典 LP 对连续变量做精确补全和验证。

## 第 2 页：赛题入口，约 3 分钟

先看这次黑客松赛题本身。官方问题不是一个纯 QUBO，而是混合整数二次规划：二进制变量 \(x\) 进入二次目标，连续变量 \(y\) 进入线性目标，同时还有 \(Ax+Gy\le b\) 和 \(Bx\le b'\) 两类约束。  

这页我想先把问题结构说清楚。\(x\) 是组合爆炸的来源，也是量子、退火和局部搜索比较适合处理的部分；但 \(y\) 是连续变量，强行把它离散化会把变量规模和精度问题一起放大。约束也不能只靠一个很大的罚函数解决，因为罚函数太小会不可行，太大又会淹没原始目标。  

所以后面整场汇报围绕三个问题展开：哪些部分适合量子或量子启发搜索，哪些部分应该交给经典 LP 做精确补全和验证，以及最后的结果如何复算、追溯和解释。

## 第 3 页：目录，约 2 分钟

今天分六部分。第一部分先审阅项目，讲仓库里到底完成了哪些东西。第二部分讲赛题建模，尤其是为什么这题不能直接全量 QUBO 化。第三部分是算法主线，也就是 QBB-MIQP。第四部分讲实验结果，包括公开样例、baseline、消融和隐藏验证。第五部分讲工程实现、复现链路和讨论。最后附录保留关键命令、结果文件和参考材料。

过渡到第一部分：先不急着讲公式，我们先看这个项目到底是一套什么东西。

## 第 4 页：一、项目审阅，约 30 秒

这一部分的目标是把仓库“摊开”。因为这次项目不是一个单脚本，而是从学习材料、算法模块、实验脚本、前后端到提交包都有内容。先把全景讲清楚，后面大家会更容易理解为什么最终主线收束到 QBB-MIQP。

## 第 5 页：仓库全景，约 3 分钟

仓库可以分成几类。`src/quantum_hackathon/` 是核心算法包，里面有建模、约束、求解器、QAOA、hybrid 和 MIQP route7。`tests/` 是回归测试，覆盖从 toy QUBO 到 route7 的主要链路。  

`learning_guides/` 是七条算法路线的学习讲义，有 PDF 和 LaTeX；`literature/` 是论文、路线分类和开发需求。`scripts/` 是比赛后期非常关键的部分，负责 baseline study、selector 消融、隐藏集批量求解、结果渲染和验证。  

`results/` 和 `submission/` 是证据仓库：结果 JSON、CSV、图片、最终提交 PDF、源码 zip 和预测文件都在那里。前后端是演示和任务管理层，不是最终结果可信性的唯一来源。

## 第 6 页：项目从宽到窄的收束，约 3 分钟

项目早期是宽探索，准备了七条路线：QUBO/Ising 建模、约束处理、退火、QAOA、constrained mixer、hybrid 分解和 learning-guided optimization。  

真正拿到官方 MIQP 赛题以后，我们发现它不是一个纯二进制 QUBO 问题，而是带连续变量、带混合线性约束、带纯二进制约束的 MIQP。于是项目收束到 Route 7 / QBB-MIQP。  

这里不是说前面的路线浪费了。它们都变成了最终主线的底座：QUBO/Ising 是 block 表示，QAOA 是小 block backend，退火是候选生成器，约束处理是 repair 和 feasibility check，hybrid 分解是主干。

## 第 7 页：交付物状态，约 2 分钟

这页讲交付状态。求解说明 PDF 已经在 `submission/` 里，源码 zip 也已经生成。公开 A/B 样例有完整 JSON 和 NPZ 结果，隐藏五个验证实例也有 `miqpscale1.npz` 到 `miqpscale5.npz`。  

横向 baseline 和 selector 消融也都做了，这点很重要，因为它让我们可以回答“是不是只是碰巧跑得好”。前端和后端可以演示，但我会把它们定位为工程表面，不把它们当作算法结论的核心证据。

## 第 8 页：代码审阅：核心可信链路，约 3 分钟

可信链路是从官方 `.npz` 输入开始，读成 `MiqpInstance`，然后做 block selection，生成 subQUBO 候选，经过 repair，再固定 \(x\) 求连续 LP，最后输出 objective、feasibility、NPZ 和 JSON。  

这个链路有三个关键点。第一，每个结果都能追溯到 seed、config、候选数和 LP 调用数。第二，提交的 `miqpscale*.npz` 可以由验证脚本重新计算目标和约束。第三，测试不是只跑一个 demo，而是覆盖 route7、SOTA 脚本和预训练管线。

## 第 9 页：工程表面：前端和服务，约 2 分钟

工程上还有两个表面。FastAPI 服务是核心包的薄封装，主要服务小规模 demo，提供健康检查、示例问题和同步求解接口。Next.js 前端提供任务创建、执行、结果查看，以及 MIQP 任务字段。  

但我会把前端放在“系统化交付”位置，而不是算法结果的主要依据。隐藏集最终结论依赖的是命令行脚本、结果 JSON、验证脚本和提交文件。

## 第 10 页：可信边界，约 3 分钟

这页很重要，因为组会里很容易被问“你们到底做到了什么，没做到什么”。可以明确说的是：项目实现了可复现的量子/量子启发混合优化框架；QAOA、QUBO、Ising、退火、learning-guided、hybrid 分解都有代码落点；最终最佳 MIQP 结果来自 block portfolio、repair 和 LP 验真闭环。  

不能过度宣称的是：没有调用真实 QPU；隐藏集没有官方最优，所以不报告 hidden gap；block-QAOA 单独并不是击败经典启发式的原因。真正有效的是完整混合闭环。

## 第 11 页：二、赛题建模，约 30 秒

接下来进入赛题建模。这一部分要讲清楚一个核心判断：这题的关键不是“会不会写成 QUBO”，而是“哪些东西不该写成 QUBO”。如果这个判断错了，后面无论 QAOA 还是退火都会被规模和罚函数拖垮。

## 第 12 页：官方问题形式，约 4 分钟

官方问题可以写成最大化 \(x^\top Qx+c^\top x+h^\top y\)，约束包括 \(Ax+Gy\le b\)、\(Bx\le b'\)、\(x\) 是 0/1 变量，\(y\ge 0\)。  

这里有三个结构。第一，\(x\) 是组合爆炸来源，也是量子、退火和局部搜索最适合处理的部分。第二，\(y\) 是连续变量，但固定 \(x\) 后它就是一个线性规划。第三，\(A,G,B\) 决定可行域，也决定 block 选择难度。  

所以这不是一个“所有变量都二进制化”的问题，而是一个天然适合 hybrid decomposition 的问题。

## 第 13 页：实例规模，约 2 分钟

公开 A 很小，15 个二进制变量、5 个连续变量。公开 B 已经有 80 个二进制变量、20 个连续变量。隐藏 5 达到 150 个二进制变量、50 个连续变量。  

这意味着全局枚举从 B 开始已经不可行。即便只看二进制空间，\(2^{80}\) 和 \(2^{150}\) 都不是可以直接处理的规模。更不用说如果把连续变量离散化，变量数还会继续爆炸。

## 第 14 页：为什么不能直接全量 QUBO，约 4 分钟

直接全量 QUBO 有三类问题。第一是连续变量离散化，每个 \(y_j\) 如果用 \(r\) 位表示，就会增加 \(pr\) 个 bit。精度越高，qubit 越多。第二是全局二进制空间本身已经巨大，B 是 \(2^{80}\)，隐藏 5 是 \(2^{150}\)。第三是罚函数失真，penalty 太小会得到不可行解，penalty 太大又会淹没原始目标，量子线路只是在追惩罚。  

所以我们的设计原则是：连续变量留给 LP，量子或启发式资源集中在二进制变量的高价值 block。

## 第 15 页：固定 x 后的连续子问题，约 4 分钟

固定 \(x\) 之后，连续子问题是最大化 \(h^\top y\)，约束是 \(Gy\le b-Ax, y\ge 0\)。这就是标准 LP。  

这一步的价值非常大：它不牺牲连续变量精度；可以直接用成熟 LP 求解器；还能得到可行性、原始目标和对偶信息。  

也就是说，量子层不需要解决全部问题。它只需要给出有价值的离散候选 \(x\)，剩下的 \(y\) 和最终验证交给 LP。

## 第 16 页：成功标准，约 2 分钟

我们的成功标准有五个。可行性必须由约束报告和验证脚本确认。目标值必须用原始 MIQP 目标函数重算，不能用 QUBO energy 代替。复现需要 seed、config、runtime、LP calls 和 JSON 结果。量子相关性体现在 block QUBO 可以转 Ising 并接 QAOA 或退火 backend。工程稳定性体现在测试、CLI、提交包和容器复算路径完整。  

这五个标准保证项目不是一个孤立 notebook，而是一套可审计的求解链路。

## 第 17 页：一句话对照，约 2 分钟

这一页用对照总结。我们不采用全量 MIQP 到全量 QUBO，不采用连续变量粗粒度二进制化，不只看 QUBO energy，也不让单个量子线路直接产出最终解。  

我们采用的是 MIQP 到 binary block 加 continuous LP，小 block QUBO/Ising 候选生成，repair 加 LP 加原始目标排序，以及 seed/config portfolio 赛马。

## 第 18 页：三、算法主线，约 30 秒

下面进入 QBB-MIQP。它的全称是 Quantum Block-Benders for MIQP。名字里的两个关键词很重要：Block 说明我们只搜索变量块，Benders 说明连续子问题和 cut advice 是闭环的一部分。

## 第 19 页：QBB-MIQP 总览，约 4 分钟

这张图是整个方法的工作流。现在图放大展示，便于看清从左到右的闭环。左侧是从实例结构出发，选择二进制 block；中间把 block 转成 QUBO 或 Ising，交给 exact、退火、learning-guided 或 QAOA-compatible backend；右侧是候选 \(x\) 的 repair、连续 LP 补全和 cut advice。  

可以把它理解成一个循环：选择 block，构造 block QUBO，生成候选 \(x\)，修复 \(Bx\le b'\)，求 LP 得到 \(y\)，再用真实目标和 cut 反馈下一轮。  

这个循环是最终成绩的核心。

## 第 20 页：block 子问题，约 4 分钟

这里给出 block 子问题的数学形式。当前 incumbent 是 \(\bar{x}\)，我们选择变量集合 \(S\)，只让 \(z=x_S\) 变化。block 内目标是 \(z^\top Q_{SS}z+\ell_S^\top z+\text{const}\)。  

因为大部分 QUBO backend 是最小化，我们把最大化目标取负，并加上对 \(B\) 约束违反的惩罚。代码里 `build_block_binary_problem()` 负责抽取这个子问题，并复用已有 QUBO builder 和 solver 接口。  

注意这里的 block 不是随便切的，它需要保留强耦合结构。

## 第 21 页：变量打分，约 4 分钟

变量打分由四部分组成：目标边际、Q 耦合、混合约束参与度和纯二进制约束压力。  

目标边际衡量变量自身贡献；Q 耦合衡量它和其他变量的二次关系；mixed 衡量它对连续 LP 可行域的影响；binary 衡量它在 \(Bx\le b'\) 中的压力。  

这四个分量共同回答一个问题：哪个变量值得进入下一次小 block 搜索？这也是我们和随机切块最大的不同。

## 第 22 页：block selector，约 3 分钟

项目里有 greedy selector 和 affinity cluster 两类策略。greedy 从最高分变量开始，再按邻居耦合和约束关联加入变量。它简单、稳定、可解释。affinity cluster 更重视强耦合变量簇，对稠密 Q 可能更好，但实验上不是总是占优。  

最终 route7++ 不是押注一个 selector，而是生成 block pool，包括 default、balanced、Q-heavy、constraint-heavy、cluster、cut-guided 和 destroy-repair。

## 第 23 页：warm-start 与 fixing plan，约 4 分钟

warm-start advisor 根据当前 incumbent 的边际收益 \(m=c+\operatorname{diag}(Q)+2Q\bar{x}\)，再结合约束释放量和二进制压力，生成每个 bit 取 1 的倾向。  

高置信变量可以固定，低置信变量留给 block backend 搜索。这里要说明，当前 probability 更多是 ranking 或 fixing signal，不是经过严格校准的概率。后续如果有更多真实标签，可以训练 learned selector 或 GNN 来替代这部分。

## 第 24 页：候选生成 portfolio，约 4 分钟

候选来源有很多。小 block 用 exact solver，中等 block 用 simulated annealing 或 learning-guided sampler。小而密的目标 block 可以转成 Ising 后接 QAOA-compatible backend。针对 cardinality 或选择约束，有 XY proxy 和 swap 候选。还有 destroy-repair、local branch 和最后的 post polish。  

这就是 portfolio 的含义：不赌单一 backend，而是让多个候选生成器在统一的 repair、LP 和目标重算框架下竞争。

## 第 25 页：QAOA 在这里扮演什么角色，约 4 分钟

QAOA 的基本形式是把 QUBO 转成 Ising Hamiltonian，然后交替施加 cost unitary 和 mixer unitary。项目里实现了标准 X-mixer QAOA 的小规模路线。  

但在这个赛题里，QAOA 不跑全局 80 或 150 bit 问题。它只跑小 block，作为候选生成器。  

QAOA 的作用不是替代整个 MIQP solver，而是在高价值离散子空间中提供量子候选；最终可行性和目标仍由经典层验证。

## 第 26 页：repair 和 augment，约 4 分钟

repair 是当 \(Bx>b'\) 时删除低价值 active bit，保证纯二进制约束不明显违反。augment 是 route7++ 的增强：repair 后如果容量没有用满，就尝试加入高价值变量。  

这在 B 类约束里很重要。因为单纯 repair 往往过度保守，把一些本来可以保留的收益删掉。augment 通过二次边际、线性收益和 warm-start 信号，尝试把可行容量重新用起来。  

所有这些候选仍然要交给 LP 检查，不能直接成为最终答案。

## 第 27 页：连续 LP 与 cut advice，约 4 分钟

连续 LP 的对偶可以给出 cut advice。直观地说，LP 不只是告诉我们这个 \(x\) 对应的 \(y\) 是什么，也告诉我们哪些二进制变量让连续可行域变紧，哪些变量改变连续收益。  

当前实现里，cut advice 不是强行加入主问题的正式 Benders cut，而是作为下一轮 block 选择和候选排序的结构信号。这样 QBB-MIQP 就从单纯 local search 变成了 MIQP-aware coordinator。

## 第 28 页：预算控制，约 3 分钟

预算控制是工程上能不能跑完的关键。`max_block_size` 控制每次送入 QUBO/Ising backend 的 bit 数；`candidate_limit` 控制候选数量；`max_lp_evals` 控制连续 LP 调用，是最重要的时间阀门；`blocks_per_iteration` 控制每轮探索宽度；`post_polish_rounds` 控制最后精修。  

同时 LP cache 会避免重复 \(x\) 被多次求解，这对多 seed 和多配置赛马很重要。

## 第 29 页：route7++ 主循环，约 4 分钟

这一页把前面的模块串起来。先初始化 warm start 并 repair；生成 block pool；对每个 block 构造 subQUBO 或 objective-only QAOA block；组合 exact、SA、learning-guided、QAOA-compatible、swap、destroy-repair 候选；然后候选排序、去重、repair、augment；再用 LP cache 求连续子问题；最后更新 incumbent，写入 block trace、cut advice 和诊断。  

主循环之后还有受控 polish。隐藏 test 4 的结果表明 polish 阶段确实可能带来关键提升。

## 第 30 页：Auto SOTA profile，约 2 分钟

为了比赛当天快速运行，脚本里有 quick、safe、deep 三种 profile。quick 用来冒烟，safe 是默认主线，deep 是时间充足时加大配置和 polish。  

最终提交策略是每个实例跑多个配置，只取最高可行目标值。不默认启用神经模型，因为 A/B 真实标签太少，临时训练模型容易过拟合。

## 第 31 页：核心代码地图，约 3 分钟

核心代码集中在几个文件。`model.py` 定义 MIQP 数据结构、目标函数和约束报告；`loader.py` 读取官方 `.npz`；`route7.py` 是主算法，包括 selector、warm-start、LP、cut、候选组合和 polish；`miqp_cli.py` 是单实例入口；`miqp_auto_sota.py` 是多配置赛马；`run_miqp_hidden_demo.py` 是隐藏五例入口；`verify_hidden_final.py` 是最终验证。  

代码主线可以从 `MiqpAwareRoute7Solver.solve()` 和 `_solve_block_heuristic()` 两个入口展开。

## 第 32 页：正确性守门，约 3 分钟

最终答案有三道门。第一，二进制约束，检查 \(Bx\le b'\)。第二，连续可行性，固定 \(x\) 后求 LP，检查 \(Ax+Gy\le b\)。第三，目标重算，用原始 MIQP 目标函数，不用 QUBO energy。  

这点对量子优化尤其重要，因为 raw energy 最低的样本可能只是 penalty 结构里的好样本，不一定是业务可行解。

## 第 33 页：与七条路线的关系，约 3 分钟

这页把前期七条路线和最终主线对应起来。QUBO/Ising 是底座；约束处理是守门；退火是 backend；QAOA 是 backend 和展示；constrained mixer 的思想进入 XY proxy；hybrid MIQP 是主干；learning-guided 是增强接口。  

所以最终不是抛弃前期工作，而是把它们嵌入到一个最适合赛题结构的主线里。

## 第 34 页：四、实验结果，约 30 秒

接下来讲结果。这里我会分四层证据：公开 A/B、横向 baseline、selector 消融、隐藏验证。公开样例证明上限，隐藏验证证明链路，baseline 和消融证明这不是只讲故事。

## 第 35 页：公开 A/B 总表，约 3 分钟

公开 A 的目标值是 106.094636，与官方最优一致。公开 B 的目标值是 610.266639，也与官方最优一致。  

A 的意义是小规模下可以用 exact 加 LP 验证建模正确。B 的意义更大，因为 80 个二进制变量不能全枚举，但 QBB-MIQP 通过 block heuristic 达到官方最优。这说明结构化分块和 LP 验真闭环确实有效。

## 第 36 页：横向 baseline 结论，约 4 分钟

B 样例上，marginal greedy 目标值 544.475466，gap 约 10.78%。genetic repair LP 是很强的传统启发式，目标值 565.761894，gap 7.29%。block SA 是 492.115433，block QAOA 是 488.070768，gap 大约 20%。  

QBB-MIQP 达到 610.266639，gap 0%。  

这里的结论不是“QAOA 单独打败经典方法”，而是“MIQP-aware block portfolio 加 LP repair 的完整闭环打败了这些 baseline”。

## 第 37 页：A/B gap 与 B 样例目标值，约 2 分钟

左图是跨样例 gap，QBB-MIQP 在 A/B 都是 0%。右图是 B 样例不同方法的目标值，虚线是官方最优。  

这两张图适合快速展示结果：我们的点不只是高，而且与 reference 对齐。

## 第 38 页：为什么 block 重要，约 3 分钟

这张热图展示的是 B 样例选中的 block 的 \(Q_{SS}\) 耦合。可以看到变量关系不是均匀噪声，而是有局部强耦合结构。  

如果 block 切错，小量子线路或退火 backend 看到的只是低价值局部问题，生成的候选自然不会好。所以 QBB-MIQP 的优势首先来自“把搜索表面选准”，不是来自单次更深线路。

## 第 39 页：selector 消融，约 3 分钟

selector 消融告诉我们两件事。第一，A 太小，对权重不敏感，各策略都能到最优。第二，B 对 selector 明显敏感，balanced greedy 在短预算下较好，但 cluster 并不稳定占优。  

这支持我们的最终策略：不主观固定一组权重，而是用多 profile 赛马，让不同结构假设在验证目标值上竞争。

## 第 40 页：质量-时间和资源画像，约 3 分钟

左图是 B 样例的质量-时间前沿，QBB-MIQP 用更多时间和 LP 评估换来 0% gap。右图是资源画像，block-QAOA 控制在 10 qubit，QBB-MIQP 主搜索使用 20-bit block 和 768 次候选评估。  

这说明它不是最快的 baseline，但在比赛目标中，受控预算下拿到更高可行目标值更重要。

## 第 41 页：隐藏验证总表，约 3 分钟

隐藏五例全部可行。目标值分别是 157.585995、459.864903、765.690515、636.175569 和 842.345737。  

LP 调用数差异比较大，test 1 因为小规模 exact 枚举，LP 调用 28032；test 2 到 test 5 是 block profile，调用在几百到一千多。runtime 从 42 秒到 245 秒不等。  

这里再次强调，隐藏集没有官方最优值，所以只报告可行目标和重算结果。

## 第 42 页：隐藏验证可行性，约 2 分钟

这页是验证脚本重算的约束违反量。stored objective 和 recomputed objective 的差都是 0。mixed max violation 最大约 \(6.94\times 10^{-12}\)，binary max violation 全部为 0。  

这些数值在 LP 容差范围内，说明提交 NPZ 不是只保存了一个看起来可行的字段，而是真的能被原始约束重算。

## 第 43 页：隐藏验证收敛曲线，约 3 分钟

这张图的纵轴是相对最终 incumbent 的剩余 loss，横轴是 LP 调用进度。test 2、test 3、test 5 较早收敛到最终结果；test 4 在 polish 阶段继续提升。  

这说明 post polish 不是装饰，它在一些实例上确实贡献了解质量。也说明 route7++ 的收益来自多个阶段叠加，而不是单一候选生成器。

## 第 44 页：容器复现与测试，约 2 分钟

源码包在 qiskit 容器中完成复现，记录的测试结果是 56 passed。A/B 样例在容器中重新运行后，A 为 106.094636140193074，B 为 610.266638604722743。  

这点对比赛很重要，因为结果不是本地某个临时环境才能跑，而是在主办方容器链路里验证过。

## 第 45 页：结果文件的可追溯性，约 2 分钟

这一页给出结果文件地图。A/B 的 route7 JSON、baseline study CSV、selector ablation CSV、hidden final summary、verify_miqpscale JSON 都在 `results/` 里。`submission/` 里是最终提交材料。  

如果老师或同学想追某个数字，基本都能从这些文件找到源头。

## 第 46 页：五、工程与讨论，约 30 秒

最后一部分是讨论，重点放在工程可信性、量子模块定位、learning-guided 路线选择、最优性声明边界、代码风险和下一步研究。

## 第 47 页：材料与复现入口，约 2 分钟

这一页列出材料和复现入口。第一，求解说明 PDF 包含数学建模和 workflow 图。第二，`results/miqp_route7_summary.md` 展示 A/B 最优。第三，hidden final summary 展示五例可行。第四，`route7.py` 对应 QBB-MIQP 主循环。  

前端任务页面属于工程演示补充，核心算法结论仍以脚本、结果文件和验证器为准。

## 第 48 页：量子模块定位，约 3 分钟

我的回答是：量子性体现在 QUBO/Ising 建模、block QAOA 线路、QAOA-compatible backend、退火/量子启发采样接口，以及 constrained mixer 和 warm-start 的设计。  

但是最终工程选择是把它们放在小 block 上，而不是全局硬跑。因为近端量子设备和 statevector 模拟都不适合全局 80 到 150 bit 问题。  

所以量子层在这里是 discrete oracle，是候选生成器，不是整个优化器。

## 第 49 页：Learning-guided 路线定位，约 3 分钟

项目已经为 learning-guided 做了准备：有 QUBO graph exporter、JSONL dataset builder、warm-start model interface、非神经线性 block scorer 和 synthetic suite。  

但最终没有默认启用神经模型，因为真实标签只有 A/B，数据太少。临场 synthetic 数据可能和隐藏分布偏移，神经模型容易过拟合，还可能拖慢提交链路。  

所以比赛提交阶段，我们选择更稳健的非神经 route7++。这不是否定 learning-guided，而是把它放到赛后研究路线。

## 第 50 页：最优性与可行性声明，约 2 分钟

公开 A/B 可以说达到官方最优，因为有 reference。A 还能用 exact 加 LP 支撑小规模验证。B 不能全枚举，但目标值与官方最优一致，所以报告 0% gap。  

隐藏五例不能说最优，因为官方没有给最优值。我们只能报告可行解、重算目标和约束违反量。  

准确表述是：公开样例达到官方最优，隐藏验证集给出可复算可行解。

## 第 51 页：代码质量审阅：做得好的地方，约 2 分钟

代码做得好的地方包括：模块边界比较清楚，输出可追溯性强，算法文档和代码能对应，测试覆盖不是只有玩具 demo，边界表述也比较诚实。  

特别是结果保留 JSON、CSV、Markdown、图片和 NPZ，这对复盘和答辩非常有帮助。

## 第 52 页：代码质量审阅：后续要补的地方，约 3 分钟

后续要补的地方也要诚实讲。第一，远程执行配置需要完全环境变量化和脱敏，避免任何凭据进入源码。第二，`route7.py` 已经很大，后续应拆成 selector、candidate、LP、polish 和 trace 模块。第三，前端任务流和核心 CLI 边界还可以再收敛。第四，隐藏集没有 reference，需要补 synthetic 或 perturbed benchmark 做鲁棒性分析。第五，QAOA backend 还需要更系统的深度、shots 和 warm-start 消融。

## 第 53 页：当前限制，约 3 分钟

当前限制包括：没有真实 QPU 调用；隐藏集没有最优值；block selector 仍是启发式；warm-start 概率没有严格校准；route7 单文件较重。  

这些限制不会推翻现有结果，但决定了后续研究该往哪里走。尤其是 learned selector 和 constrained mixer，可以把当前“有效工程启发式”继续推进成更系统的研究贡献。

## 第 54 页：最值得继续做的研究，约 4 分钟

我认为后续最值得做六件事。第一，用 block trace 学习 selector，目标可以是单位 LP 调用提升量。第二，把 LP 对偶 cut 更深地融入 block 生成和候选排序。第三，做 QAOA 系统消融，比较 depth、shots、warm-start 和不同 block。第四，把 XY proxy 升级成完整 constrained mixer ansatz。第五，围绕官方维度生成分布邻近 synthetic MIQP，做鲁棒 benchmark。第六，把 route7++ 从比赛脚本整理成可复用研究框架。

## 第 55 页：可以留给导师讨论的问题，约 3 分钟

这页是我希望组会上可以讨论的问题。比如 block selector 能不能和 Benders cut 形成更标准的理论框架？哪些 \(Q,A,B,G\) 特征最适合做 learned selector？QAOA block oracle 的评价指标应该是 energy、可行候选比例，还是 LP 后的最终 objective？如果接真实硬件，应该优先跑哪些 block？这个框架是否能迁移到 unit commitment、portfolio 或 routing？  

这些问题能把项目从一次 hackathon 延伸到后续课题研究。

## 第 56 页：最终收束，约 2 分钟

最后总结。本项目的核心贡献，是把一个看似可以直接 QUBO 化的量子优化赛题，重构成了一个可复现、可解释、可验证的 MIQP-aware 量子-经典混合求解框架。  

工程价值是代码、测试、容器复现和提交包完整；算法价值是 block-QUBO、LP、repair、cut 的闭环有效；研究价值是为 learned selector、constrained mixer 和 QAOA block oracle 留出了清晰接口。  

最后一句话：不赌全局大线路，只打最关键的二进制块。谢谢大家。

## 附录页讲法

附录用于补充复现命令和数字来源。

### 附录：复现命令，约 2 分钟

公开样例可以通过 A/B 的 CLI 参数复现。B 的核心参数包括 max block size 20、block pool、每轮多个 block、LP budget 800 和 post polish。公开样例结果不是手填的，是 CLI 可以重跑的。

### 附录：隐藏验证，约 2 分钟

隐藏验证通过 `run_miqp_hidden_demo.py` 和 `verify_hidden_final.py` 复算。一个负责批量求解，一个负责从提交 NPZ 或诊断 JSON 重新计算 objective 和 feasibility。

### 附录：实验图表，约 2 分钟

baseline 和消融图来自 `miqp_baseline_study.py` 与 `miqp_selector_ablation.py`。这些脚本生成 CSV、Markdown 和论文插图。

### 附录：最终数字，约 1 分钟

如果需要快速报数字，就用这页。公开 A/B 都是 0% gap；隐藏五例目标值分别是 157.586、459.865、765.691、636.176、842.346；最大 mixed violation 约 \(6.94\times 10^{-12}\)，binary violation 全为 0；容器测试记录是 56 passed。

