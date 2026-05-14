import type {
  PlaygroundOpenQuestionEvent,
  PlaygroundScenarioId,
} from '@/lib/playground-types';

export const COMMON_OPEN_QUESTIONS: readonly PlaygroundOpenQuestionEvent[] = [
  {
    type: 'open_question',
    category: 'constraint_coverage',
    title: '约束覆盖范围有限',
    description:
      '当前 constrained QAOA 子空间仅覆盖 exactly-one 类约束，resource_budget 等不等式约束仍依赖罚函数编码，未被可行子空间或 XY mixer 直接保持。',
  },
  {
    type: 'open_question',
    category: 'hardware',
    title: 'QAOA 当前为本地模拟',
    description:
      '所有 QAOA 卡片的 execution_backend 为 local_statevector_optimizer_plus_shot_sampler，运行在本地 CPU 上对量子线路进行经典模拟，未接入真实量子硬件或云服务。',
  },
  {
    type: 'open_question',
    category: 'scale',
    title: '样例规模较小',
    description:
      '本演示问题约 5 个逻辑变量、8 个 QUBO bits，仅用于展示建模、编译、采样与后处理链路；实际生产规模需要走 Hybrid relax-round-repair 或经典 MILP/MIQP 路线。',
  },
];

export function buildOpenQuestionEvents(
  scenario: PlaygroundScenarioId,
): PlaygroundOpenQuestionEvent[] {
  const base: PlaygroundOpenQuestionEvent[] = COMMON_OPEN_QUESTIONS.map((q) => ({ ...q }));
  if (scenario === 'small_knapsack') {
    base.push({
      type: 'open_question',
      category: 'hybrid',
      title: 'Hybrid 路线仍是 scaffold',
      description:
        'hybrid.relax_round_repair 当前为分解、relaxation、rounding、repair 与 fix-and-optimize 的工程脚手架，尚未接入外部 MILP/MIQP 求解器作为可选后端。',
    });
  } else if (scenario === 'exactly_one') {
    base.push({
      type: 'open_question',
      category: 'metadata',
      title: 'warm-start 仅为元数据',
      description:
        '当前 constrained QAOA 的 warm-start 概率与 recursive reduction 输出主要是元数据 MVP，尚未驱动完整可行子空间采样器或递归化简执行流程。',
    });
  }
  return base;
}
