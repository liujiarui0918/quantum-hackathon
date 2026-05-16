# 非神经 Route7++ SOTA 优化开发需求

## 背景

当前已验证主线成绩为：

| 样例 | 目标值 | 官方最优 | gap | 状态 |
| --- | ---: | ---: | ---: | --- |
| A | 106.094636 | 106.094636 | 0.00% | 可行且最优 |
| B | 594.648146 | 610.266639 | 2.56% | 可行 |

A 已无优化空间。B 的剩余差距主要来自二进制变量组合搜索仍未充分探索，而不是连续变量求解。当前最稳主线应继续沿 MIQP-aware route7++ 推进：保留连续变量 LP 子问题，用结构化 block、repair、LP cache、cut advice 和 seed/config portfolio 提升二进制搜索质量。

本阶段明确不采用 GNN/RL 作为最终主线。原因是可用真实标签只有 A/B，临场合成数据与真实测试分布可能偏移，神经模型容易过拟合并拖慢提交链路。学习接口只保留为离线消融，不影响默认提交。

## 目标

1. 强化非神经 route7++，在相同或可控预算下提高 B 类中大规模实例的可行目标值。
2. 让 auto SOTA 脚本可以用不同预算 profile 自动赛马，真实数据到达后直接批量运行。
3. 保持所有候选必须经过 `B x <= b'` repair、连续 LP、原始约束报告验证。
4. 保持工程可复现：JSON/NPZ/Markdown 输出完整记录 config、seed、LP 调用数、runtime 和最佳解。

## 非目标

- 不训练 GNN、RL、深度 MLP，也不把神经模型放进默认候选。
- 不宣称真实 QPU 结果；QAOA 仍是小 block 可插拔模拟/接口。
- 不把连续变量 `y` 离散化进全局 QUBO。
- 不做不可控的无限搜索；所有增强都受 `max_lp_evals` 和 `time_limit_sec` 控制。

## 优化方向

### 1. 候选 repair 后主动补满可行容量

当前 `repair_binary_constraints` 只负责在违反 `B` 约束时删 bit。对 `B` 类样例，很多候选在 repair 后可能过于保守，留下可行容量却没有重新加入高价值变量。

新增 `augment_binary_constraints`：

- 输入 repair 后的 `x`、warm-start probability、当前边际收益。
- 在不违反 `B x <= b'` 的前提下，贪心加入 inactive 变量。
- 加入评分综合二次边际收益、线性收益、bit probability。
- 只加入正分变量，避免为了填满容量而引入明显坏变量。
- 作为候选增强，不替代 LP 可行性验证。

验收：

- 对任意返回结果满足 `B x <= b'`。
- CLI/route7++ 默认启用，可通过参数关闭。

### 2. 候选排序从“生成顺序”改为“二进制代理收益排序”

当前候选先生成再截断，预算较小时可能把更有价值的候选挤掉。新增 `_rank_candidates_by_binary_surrogate`：

- 主评分：`binary_objective(candidate) - binary_objective(base)`。
- 辅评分：warm-start probability 与 flip 方向一致性。
- cut 辅助：若有 LP 对偶 cut，优先测试 cut 系数高的变化。
- 保留 base candidate，避免丢失 incumbent 验证和 LP cache 命中。

验收：

- candidate budget 下候选数量不增加失控。
- trace 中保留原 candidate count 和 LP 调用数。

### 3. 最终 incumbent polish

主循环结束后，针对当前最佳可行解做少量受预算控制的局部 polish：

- 生成全局 top-k single flip、1-swap、2-swap、augment 候选。
- 每轮只接受可行且目标更高的解。
- 继续使用同一个 LP cache，避免重复 LP。
- 受 `post_polish_rounds`、`polish_candidate_limit`、`max_lp_evals`、`time_limit_sec` 控制。

验收：

- 默认 solver 行为可控。
- auto_sota 的 deep/profile 配置启用 polish。
- diagnostics 记录 polish rounds、候选数、LP calls、best objective。

### 4. Auto SOTA profile

真实数据到达后最重要的是快速赛马。扩展 `scripts/miqp_auto_sota.py`：

- `--profile quick|safe|deep`。
- quick：少配置、少 seed，用于冒烟。
- safe：当前默认，包含 balanced/cluster/wide/q-heavy/b-heavy 的非神经赛马。
- deep：增加 q-heavy、b-heavy、large-block、polished 配置。
- `--max-configs` 可截断配置，方便时间不足时降级。

验收：

- 默认仍不使用 learned model。
- 输出每个 config/seed 的 objective、gap、runtime、LP calls、polish 统计。
- 每个实例仍只按最高可行目标值选择结果。

### 5. 结果与文档

更新 README/速读文档：

- 主线明确为非神经 route7++。
- GNN/RL 只作为未来方向。
- 给出当前 A/B 成绩和下一步真实数据运行命令。

## 测试计划

1. 单测：
   - `augment_binary_constraints` 不违反 B 约束。
   - route7++ trace 包含 candidate augmentation/polish diagnostics。
   - auto_sota profile 能生成 deep 配置且不包含 learned 配置。
2. 回归：
   - `python -m pytest -q` 全绿。
   - A 样例仍达到 `106.094636`。
3. 打包：
   - 重建 `submission/混合整数优化问题赛道-平步青云-源代码.zip`。
   - 解压后运行关键测试。

## 风险控制

- 若 polish 增强在某实例上没有提升，只会浪费少量受控 LP 预算，不会降低已验证 best solution。
- 若 augment 产生 LP 不可行候选，会被连续子问题过滤，不会进入提交结果。
- 若 deep profile 时间不足，可降级为 safe/quick profile。
