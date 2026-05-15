# 路线 4：QAOA / VQA 标准量子门模型

QAOA 是量子门模型里最常见的组合优化算法路线。它的核心不是“量子电脑自动给答案”，而是构造一个带参数的量子线路，让低能 bitstring 出现概率更高，再用经典优化器调这些参数。

第一遍学 QAOA，要抓住三个东西：cost Hamiltonian、mixer、classical optimizer。

## QAOA 在做什么

QUBO 给每个 bitstring 一个能量。

QAOA 希望准备一个量子态，使得测量时更容易测到低能 bitstring。

它不是直接输出一个确定解，而是输出一个概率分布：

```text
00110: 0.21
10100: 0.17
00111: 0.09
...
```

然后我们从测量结果里解码、检查约束、挑 best feasible solution。

## 标准 QAOA 结构

QAOA 的状态一般写成：

```text
|psi(gamma, beta)>
  = product_l exp(-i beta_l H_M) exp(-i gamma_l H_C) |+>^n
```

你不用被公式吓到。它只有三层意思：

`|+>^n`

一开始让所有 bitstring 大致均匀叠加。可以理解成“所有候选解先都在场”。

`H_C`

Cost Hamiltonian。它来自 QUBO/Ising，负责给不同 bitstring 加上和成本有关的相位。

`H_M`

Mixer Hamiltonian。它负责在 bitstring 之间混合，让概率流动起来。

`gamma` 和 `beta`

可调参数。经典优化器会不断试参数，观察期望能量，寻找更好的概率分布。

## Cost Hamiltonian

如果 QUBO 是：

```text
E(x) = c + sum_i q_i x_i + sum_ij q_ij x_i x_j
```

转成 Ising 后，就可以构造 cost Hamiltonian：

```text
H_C = C + sum_i h_i Z_i + sum_ij J_ij Z_i Z_j
```

`Z_i` 可以理解成读取第 `i` 个 qubit 的 0/1 信息。某个 bitstring 的能量越低，我们越希望它最后被测出来的概率越高。

## Mixer 是什么

标准 QAOA 常用 X mixer：

```text
H_M = sum_i X_i
```

它的直觉是：每个 bit 都可以翻转。所以标准 X mixer 会在整个 `2^n` 搜索空间里移动。

这很通用，但也有问题：它会移动到非法状态。例如 exactly-one 问题里，从 `100` 翻一个 bit 可能变成 `110` 或 `000`，都不合法。

所以标准 QAOA 常常还需要 penalty 来处理约束。路线 5 的 constrained mixer，就是在改 mixer。

## VQA 是更大的框架

VQA 是 Variational Quantum Algorithm，QAOA 是 VQA 的一个特化版本。

VQA 的共同流程：

```text
1. 设计参数化量子线路 ansatz
2. 在量子后端运行线路
3. 测量得到样本或期望值
4. 经典优化器根据结果更新参数
5. 重复直到预算耗尽或收敛
```

近端量子算法的典型样子就是这种量子-经典闭环。

## p 层是什么意思

QAOA 的 `p` 是交替层数：

```text
p = 1: cost -> mixer
p = 2: cost -> mixer -> cost -> mixer
...
```

`p` 越大，表达能力通常越强，但线路越深、参数越多、优化更难、噪声更重。

比赛里不要默认“p 越大越好”。小规模 demo 可以比较：

```text
p = 1, 2, 3
```

记录 best feasible objective、feasible ratio、optimizer evaluations、runtime。

## Classical optimizer 的角色

QAOA 的参数不是量子设备自己学出来的。经典优化器负责试参数。

常见优化器：

- COBYLA
- Nelder-Mead
- SPSA
- gradient-based methods
- multi-start random search

QAOA 的难点之一就是参数地形可能很不友好：有局部最优、shot noise、barren plateau、参数周期性。

所以参数初始化也很重要。随机初始化是 baseline；更好的方法包括 linear ramp、warm-start parameters、复用小规模问题参数。

## Measurement 和后处理

QAOA 最后测量会得到 counts：

```text
00101: 120
00111: 84
10101: 31
...
```

后处理步骤和退火很像：

```text
counts
  -> bitstrings
  -> QUBO energy
  -> decode
  -> feasibility check
  -> original objective
  -> best feasible
```

不要只报告期望能量。比赛里最终要的是可解释的业务解。

## QAOA 适合什么

小规模组合优化 demo。

QAOA 的 qubit 数和线路深度限制很明显，所以它适合拿小实例做算法展示。

和 classical baseline 对比。

比如 exact small case、random、SA、standard QAOA、constrained QAOA。

展示量子结构。

如果你能解释 cost layer、mixer、测量分布，而不是只说“调用 QAOA”，评委会更容易相信你懂模型。

## 比赛时能改哪些地方

Cost Hamiltonian

QUBO 建得好不好，会直接影响 QAOA。

Mixer

标准 X mixer 是 baseline。问题有 exactly-one 或 fixed-k 结构时，可以改成 XY mixer 或 problem-specific mixer。

Initial state

从均匀叠加开始不是唯一选择。可以用 feasible initial state 或 warm-start state。

参数初始化

random、linear ramp、warm-start、multi-start 都可以比较。

Optimizer

不同 optimizer 对 shot noise 和局部最优的表现不同。

后处理

QAOA 输出的是概率分布。repair、可行性优先排序、local improvement 都有空间。

## 常见坑

把 QAOA 当成大规模万能 solver。

当前近端环境下，QAOA 更适合小规模算法展示和结构对比。

忽略 constraints。

标准 X mixer 会走到非法状态。约束如果只靠 penalty，penalty 质量仍然决定可行性。

只看期望能量。

期望能量低不代表测量样本里有高质量可行解。要看 best feasible 和 feasible ratio。

参数优化预算不公平。

和 SA 比较时，要说明 shots、optimizer evaluations、runtime。否则对比不公平。

线路深度过深。

真实硬件或 noisy simulator 上，深线路可能被噪声毁掉。

## 和其他路线的关系

路线 1 把原问题变成 cost Hamiltonian。

路线 2 决定 penalty 形式和可行性检查。

路线 3 可以作为 QAOA 的经典/退火 baseline。

路线 5 是 QAOA 的结构升级：改 mixer、改 initial state、改 feasible subspace。

路线 6 可以先把大问题拆成小 QUBO，再用 QAOA 求子问题。

## 共读任务

用一句话回答：

```text
QAOA 的 cost layer 在奖励什么？mixer layer 又在允许什么？
```

如果能答出“cost layer 来自目标能量，mixer layer 决定搜索空间里的移动方式”，你就抓住了 QAOA 的骨架。

## 延伸阅读

- `literature/requirements/04_qaoa_vqa_requirements.md`
- Farhi, Goldstone, Gutmann, QAOA original paper
- Zhou et al., QAOA performance and parameter mechanisms
- Cerezo et al., VQA review

