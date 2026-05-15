# 路线 5：Constrained Mixer / Warm-start / XY Mixer

Constrained mixer 的核心想法很漂亮：与其让算法到处乱走、走错了再罚，不如一开始就设计只能在合法区域里移动的规则。

这条路线是量子算法部分最有“算法创新味”的一条，但它依赖你已经理解 QUBO、约束和标准 QAOA。

## 从标准 X mixer 的问题开始

标准 QAOA 的 X mixer 允许每个 bit 独立翻转。

对于 exactly-one：

```text
100, 010, 001 是合法状态
000, 110, 101, 011, 111 是非法状态
```

如果从 `100` 出发，X mixer 翻转第 2 个 bit 会到 `110`，非法；翻转第 1 个 bit 会到 `000`，也非法。

这说明标准 X mixer 不理解 exactly-one。

## XY mixer 的直觉

XY mixer 不像 X mixer 那样单独翻 bit。它更像交换：

```text
10 <-> 01
```

在量子写法里，常见局部项是：

```text
X_i X_j + Y_i Y_j
```

直觉上，它把一个 excitation 从位置 `i` 移到位置 `j`。如果一组变量里始终只有一个 1，那么这种交换会保持“只有一个 1”。

所以在 one-hot 约束里：

```text
100 -> 010 -> 001
```

所有移动都合法。

## Feasible subspace

Feasible subspace 是满足某些约束的状态集合。

例如 exactly-one 的可行子空间：

```text
{100, 010, 001}
```

Constrained mixer 的目标是：

```text
如果初始态在 feasible subspace 里，mixer 作用后仍然留在 feasible subspace 里。
```

这样测量结果天然满足被 mixer 覆盖的约束。

## Exactly-k / Fixed Hamming Weight

Exactly-k 是：

```text
sum_i x_i = k
```

也叫固定 Hamming weight。比如投资组合里“必须选 5 只资产”。

XY mixer 很适合这类约束，因为交换 `10 <-> 01` 会保持 1 的总数不变。

这比用 penalty 处理 cardinality 更优雅：算法不会把概率浪费在不满足选 k 个的状态上。

## One-hot assignment

很多赛题有 assignment 结构：

```text
每个任务必须分配给一个机器
每个客户必须由一辆车服务
每个时间槽必须选择一种状态
```

这些都可以写成一组组 one-hot。

对每一组 one-hot，使用组内 XY mixer，就能保持“每组选一个”。

如果还有跨组约束，比如总预算、容量、路径连续性，它们未必被 XY mixer 自动保持，仍然需要 penalty、repair 或 hybrid 处理。

## Warm-start 的直觉

标准 QAOA 常从均匀叠加开始。Warm-start 说：如果经典算法已经给了一个不错的方向，为什么要假装一无所知？

例如连续松弛解给出：

```text
x_a = 0.85
x_b = 0.10
x_c = 0.05
```

这说明 `model_a` 很可能好。Warm-start 可以把初始态或 mixer 参数设计得更偏向这些高置信度选择。

Warm-start 的价值是减少盲目搜索，把经典 relaxation 的信息带进量子线路。

## One-hot warm-start

对 one-hot 组，连续松弛可能给一组概率：

```text
[0.70, 0.20, 0.10]
```

这可以用来构造 weighted initial state，让第一项被测到的概率更高，但不是完全锁死。

比赛里这很适合讲：

```text
我们不是孤立使用量子算法，而是用经典松弛引导量子搜索。
```

## Iterative warm-start

一次 warm-start 不一定够。可以迭代：

```text
1. 经典 relaxation 给初始概率
2. constrained QAOA 采样
3. 根据样本更新置信度或固定部分变量
4. 再运行下一轮
```

这会把路线 5 和路线 6 连接起来：量子模块成为 hybrid workflow 的一部分。

## R-QAOA 的直觉

R-QAOA 是 recursive QAOA。

它的思路不是一次性求完整答案，而是：

```text
1. 跑 QAOA
2. 看变量之间的相关性
3. 固定最确定的变量或变量关系
4. 缩小问题
5. 递归求解
```

例如如果采样里 `x_i` 和 `x_j` 总是相反，就可以固定关系：

```text
x_i = 1 - x_j
```

这是一种量子启发的变量消元方法。

## 比赛时能改哪些地方

选择哪些约束由 mixer 保持

不是所有约束都适合 constrained mixer。先挑 one-hot、exactly-k、fixed Hamming weight 这类结构清楚的约束。

Transition graph

XY mixer 需要定义哪些状态之间可以交换。图太稀，搜索不充分；图太密，线路复杂。

初始态

可以从任意可行解、均匀 feasible state、weighted W-state、classical relaxation warm-start 开始。

未覆盖约束

Mixer 只能保持它覆盖的约束。预算、容量、路径等约束可能仍然需要 penalty 或 repair。

和 standard QAOA 对比

最有说服力的展示是：

```text
penalty QAOA vs constrained mixer QAOA
feasible ratio / best feasible objective / circuit depth
```

## 常见坑

以为 constrained mixer 保持所有约束。

它只保持你设计进去的约束。

初始态不可行。

如果初始态不在 feasible subspace，后面保持也没意义。

Feasible graph 不连通。

如果 mixer 的 transition graph 不能连接所有重要可行状态，算法可能永远到不了某些好解。

线路成本过高。

保持约束可能需要更多门、更复杂的 Trotterization。理论好看，也要看能不能跑。

Warm-start 过度自信。

经典 relaxation 有时会误导。Warm-start 应该引导搜索，不一定完全固定答案。

## 和其他路线的关系

路线 4 给出标准 QAOA 框架。

路线 5 改的是 mixer 和 initial state。

路线 2 负责那些 mixer 没覆盖的约束。

路线 6 可以提供 relaxation warm-start，也可以把 constrained QAOA 放进子问题求解环节。

## 共读任务

请判断下面状态是否能用 XY mixer 保持约束：

```text
约束：x_1 + x_2 + x_3 = 1
合法状态：100, 010, 001
移动：100 <-> 010, 010 <-> 001
```

问题：

1. 所有移动后是否仍然 exactly-one？
2. `100` 能不能到 `001`？
3. 如果不能直接到，但可以通过 `010` 到，这个 transition graph 是否连通？

这个小练习就是 constrained mixer 的核心。

## 延伸阅读

- `literature/requirements/05_constrained_mixer_warm_start_requirements.md`
- Hadfield et al., Quantum Alternating Operator Ansatz
- Fuchs et al., constraint preserving mixers
- Egger et al., warm-starting quantum optimization
- Bravyi et al., R-QAOA
