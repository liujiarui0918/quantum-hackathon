# 路线 3：Quantum Annealing / Simulated Annealing 求解

退火路线的核心直觉很朴素：把 QUBO 看成一片高低不平的能量地形，然后想办法走到低谷。

它不是最炫的路线，但通常是比赛里最先跑通、最容易做 benchmark、最适合作为稳定 baseline 的路线。

## 能量地形

QUBO 给每个 bitstring 一个能量：

```text
E(00001), E(00010), E(10110), ...
```

如果变量有 `n` 个，可能的 bitstring 有 `2^n` 个。小问题可以 brute force，全枚举。大一点就不行。

退火算法做的事是：

```text
不枚举所有状态，而是在状态空间里移动，尽量找到低能状态。
```

## Simulated Annealing

模拟退火来自一个物理类比：高温时系统可以乱跳，低温时系统逐渐稳定。

算法过程可以这样理解：

```text
1. 随机给一个 bitstring
2. 随机翻转一个或几个 bit
3. 如果能量下降，接受
4. 如果能量上升，也有一定概率接受
5. 随着温度下降，越来越不愿意接受变差移动
6. 重复很多次
```

为什么要接受变差移动？因为如果永远只接受变好移动，很容易卡在局部最优。高温阶段允许“先走烂路”，是为了跨过小山丘。

## Quantum Annealing

量子退火的直觉也是找低能态，但移动机制更像从一个容易制备的量子系统，慢慢变成目标问题 Hamiltonian。

粗略写成：

```text
H(t) = A(t) * H_initial + B(t) * H_problem
```

开始时 `H_initial` 强，系统容易准备。结束时 `H_problem` 强，系统希望落在问题的低能态。

实际设备比如 D-Wave 会把问题嵌入硬件图上，用物理过程采样低能状态。

第一遍学习不用神化“量子”。你先记住：

```text
Quantum annealing 也是吃 QUBO/BQM，也会输出 samples，也需要解码和可行性检查。
```

## BQM 是什么

BQM 是 Binary Quadratic Model，可以容纳 QUBO 或 Ising 表达。

```text
binary variables: x_i in {0,1}
spin variables:   s_i in {-1,+1}
linear bias:      h_i 或 q_i
quadratic bias:   J_ij 或 q_ij
offset:           常数项
```

很多退火工具链围绕 BQM 工作。对你来说，BQM 就是“可交给 sampler 的二次能量模型”。

## 退火路线的完整流程

一条健康退火流程是：

```text
原问题
  -> QUBO/BQM
  -> coefficient scaling
  -> sampler
  -> raw samples
  -> decode
  -> feasibility check
  -> repair / local search
  -> best feasible solution
  -> benchmark report
```

注意 sampler 只是中间一环。真正的结果来自后处理。

## 常见 backend

Exact solver

全枚举。只能处理很小的问题，但它是验证 QUBO 正确性的金标准。

Random sampler

随机采样。看起来很弱，但必须有。它能告诉你算法是不是真的比瞎猜好。

Greedy local search

不断做局部改进。简单、快、可作为强 baseline。

Simulated annealing

用温度调度跳出局部最优。比赛里非常实用。

Tabu search

记录近期访问过的状态，避免来回震荡。

D-Wave sampler

真实量子退火器或云端混合 solver。需要关注嵌入、chain strength、硬件连通性和可用资源。

## 参数旋钮

reads

独立采样次数。更多 reads 通常提高找到好解的机会，但耗时更长。

sweeps

每次退火内部尝试更新的步数。太少不充分，太多可能收益递减。

temperature schedule

温度怎么从高到低。降太快容易卡住，降太慢耗时。

seed

随机种子。比赛 benchmark 必须固定或记录 seed。

coefficient scaling

把 QUBO 系数缩到 sampler 可处理范围。缩放不能改变最优解的相对关系，但会影响数值稳定。

chain strength

D-Wave 嵌入时使用。太弱链会断，太强会淹没问题本身。

## 退火不懂业务约束

这是路线 3 最重要的一句话：

```text
退火器只采样低能状态，不知道业务合法性。
```

如果 penalty 写得不好，退火器会很认真地找到一个非法低能解。

所以退火结果必须报告：

- best raw energy sample
- best raw energy sample 是否可行
- best feasible sample
- feasible ratio
- repair 后目标
- 和 exact / random / greedy 的对比

## 比赛时能改哪些地方

更好的 QUBO

退火表现常常不是 sampler 决定的，而是 QUBO 地形决定的。约束编码、系数缩放、变量设计都能改。

退火参数

reads、sweeps、schedule、seed、initial state 都能调。不要只跑默认参数。

后处理

去重、repair、local search、可行性优先排序，往往比换一个 sampler 更有用。

分块求解

大问题可以分块退火，或者用 hybrid 流程不断生成小 QUBO。

Benchmark

用 random、greedy、exact small case 做基线。没有基线，退火结果很难说服评委。

## 常见坑

只展示最好一次。

采样算法有随机性，要展示多次统计或固定 seed。

把 infeasible 当最优。

raw energy 最低不等于原问题最优。

没有缩放诊断。

系数范围太大时，求解器可能看不清小项。

过度承诺 quantum advantage。

比赛里更稳的说法是：这是 quantum / quantum-inspired 求解路线，并与经典基线对比。

忽略硬件嵌入。

真实量子退火器有连通性限制。逻辑变量可能需要多个物理 qubit 链接起来。

## 和其他路线的关系

路线 1 给退火器输入。

路线 2 决定退火样本是否容易可行。

路线 6 可以把大 MILP/MIQP 拆成小 QUBO，再交给退火器。

路线 4 和路线 5 是另一类量子门模型求解路线，可以和退火做横向对比。

## 共读任务

想象我们对 `sample_problem.json` 跑 simulated annealing。

你需要设计结果表格的字段：

- raw bitstring
- raw QUBO energy
- decoded solution
- original objective
- feasible
- violation detail
- repaired solution

如果结果表能把这些字段讲清楚，退火路线就不会变成黑箱。

## 延伸阅读

- `literature/requirements/03_annealing_solver_requirements.md`
- Phillipson & Bausch, quantum annealing industry review
- D-Wave Ocean 文档中的 BQM / sampler 概念

