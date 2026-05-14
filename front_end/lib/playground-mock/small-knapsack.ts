import type {
  PlaygroundScript,
  PlaygroundTimedEvent,
} from '@/lib/playground-types';
import { PLAYGROUND_TIMING, MOCK_BENCHMARK_TOTAL_MS, QAOA_EXECUTION_BACKEND, CONSTRAINED_QAOA_ROUTE } from '@/lib/playground-mock/timing';
import { buildOpenQuestionEvents } from '@/lib/playground-mock/open-questions';

const T = PLAYGROUND_TIMING;

export const SMALL_KNAPSACK_SCRIPT: PlaygroundScript = {
  scenario: 'small_knapsack',
  title: 'Small Knapsack (small_knapsack)',
  description: '几个物品装背包，重量上限约束，收益最大',
  events: [
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'understand', message: '正在分析背包问题需求...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-codex-search-1', tool: 'codex.search', title: '搜索代码库', summary: '搜索背包优化案例', simulated: true, input: { query: 'knapsack optimization problem', scope: 'src/' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-codex-search-1', tool: 'codex.search', simulated: true, output: { matches: ['src/quantum_hackathon/benchmarks/cases.py'], summary: '找到 small_knapsack 案例，含重量上限约束' } } },
    { delay_ms: T.summary, event: { type: 'summary', phase: 'understand', message: '需求已明确：0-1 背包问题，在重量上限约束下最大化收益', highlights: ['binary decision per item', 'weight capacity constraint', 'maximize total value'] } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'load_problem', message: '加载背包问题并构建 QUBO...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-modeling-build-qubo', tool: 'modeling.build_qubo', title: '构建 QUBO 模型', summary: '编译背包问题为 QUBO', simulated: true, input: { problem: 'small_knapsack', sense: 'maximize', penalty_weights: { weight_capacity: 20.0 } } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-modeling-build-qubo', tool: 'modeling.build_qubo', simulated: true, output: { num_logical_variables: 4, total_binary_variables: 7, slack_variables: 3, auxiliary_variables: 0, linear_terms: 7, quadratic_couplers: 21, density: 1.0, coefficient_ratio: 15.5, warnings: [] } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'compile_constraints', message: '编译重量约束...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-constraints-compile', tool: 'constraints.compile', title: '编译约束', summary: '转化重量上限为罚函数', simulated: true, input: { constraints: ['weight_capacity'], strategy: 'unbalanced_penalty' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-constraints-compile', tool: 'constraints.compile', simulated: true, output: { compiled: 1, penalty_terms_added: 1, weight_capacity: { type: 'bounded_sum', penalty_weight: 20.0, slack_bits_added: 3 } } } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-constraints-subspace', tool: 'constraints.export_feasible_subspace', title: '导出可行子空间', summary: '检查有无 one-hot 可行子空间', simulated: true, input: { constraint_type: 'exactly_one' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-constraints-subspace', tool: 'constraints.export_feasible_subspace', simulated: true, output: { one_hot_groups: [], constraints_covered: [], constraints_not_covered: ['weight_capacity'], note: 'No exactly-one constraints; all constraints use penalty encoding' } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'benchmark', message: '执行求解器 benchmark...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-solvers-exact', tool: 'solvers.solve_exact', title: 'Exact 枚举求解', summary: '全空间枚举', simulated: true, input: { max_bits: 25, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-solvers-exact', tool: 'solvers.solve_exact', simulated: true, output: { status: 'ran', backend: 'exact', feasible_sample_ratio: 0.0625, samples_returned: 128, best_feasible: { bitstring: '1011000', objective_value: 16.0, is_feasible: true, source_backend: 'exact' }, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact } } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-solvers-sa', tool: 'solvers.solve_sa', title: '模拟退火求解', summary: '随机局部搜索', simulated: true, input: { num_reads: 60, num_sweeps: 150, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-solvers-sa', tool: 'solvers.solve_sa', simulated: true, output: { status: 'ran', backend: 'simulated_annealing', feasible_sample_ratio: 0.18, samples_returned: 60, best_feasible: { bitstring: '1011000', objective_value: 16.0, is_feasible: true, source_backend: 'simulated_annealing' }, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'qaoa', message: '构建 QAOA 量子线路...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-qaoa-run', tool: 'qaoa.run_local_simulator', title: 'QAOA 本地模拟器', summary: '标准 X-mixer ansatz', simulated: true, input: { ansatz: 'standard_qaoa_x_mixer', execution_backend: QAOA_EXECUTION_BACKEND, num_qubits: 7, layers: 1, shots: 200, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-qaoa-run', tool: 'qaoa.run_local_simulator', simulated: true, output: { status: 'ran', backend: 'qaoa_shot_simulator', execution_backend: QAOA_EXECUTION_BACKEND, num_qubits: 7, layers: 1, feasible_sample_ratio: 0.10, best_feasible: { bitstring: '1011000', objective_value: 16.0, is_feasible: true }, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'constrained_qaoa', message: '分析 constrained QAOA 子空间...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-cqaoa-analyze', tool: 'constrained_qaoa.analyze_subspace', title: 'Constrained QAOA 子空间分析', summary: '检查可行子空间覆盖', simulated: true, input: { constraint_type: 'exactly_one', mixer: 'one_hot_xy' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-cqaoa-analyze', tool: 'constrained_qaoa.analyze_subspace', simulated: true, output: { status: 'skipped', route: CONSTRAINED_QAOA_ROUTE, reason: 'no exactly_one constraint detected', note: 'Knapsack has only bounded_sum constraint; constrained QAOA subspace not applicable' } } },

    // hybrid route (knapsack-specific)
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'build_qubo', message: '尝试 Hybrid relax-round-repair 路线...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-hybrid-rrr', tool: 'hybrid.relax_round_repair', title: 'Hybrid Relax-Round-Repair', summary: '松弛后取整并修复不可行解', simulated: true, input: { strategy: 'relax_round_repair', relaxation: 'lp_relaxation' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-hybrid-rrr', tool: 'hybrid.relax_round_repair', simulated: true, output: { status: 'ran', route: 'hybrid_scaffold', relaxed_objective: 18.5, rounded_objective: 16.0, repair_needed: false, best_feasible: { bitstring: '1011000', objective_value: 16.0, is_feasible: true }, note: 'Rounded solution was already feasible; no repair step needed' } } },

    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-benchmark-compare', tool: 'benchmarks.compare_routes', title: 'Benchmark 对比', summary: '汇总各求解器结果', simulated: true, input: { scenarios: ['exact', 'simulated_annealing', 'qaoa_shot_simulator', 'hybrid_relax_round_repair'] } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-benchmark-compare', tool: 'benchmarks.compare_routes', simulated: true, output: { rows: [
      { solver: 'exact', status: 'ran', best_feasible_objective: 16.0, best_feasible_bitstring: '1011000', feasible_sample_ratio: 0.0625, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact },
      { solver: 'simulated_annealing', status: 'ran', best_feasible_objective: 16.0, best_feasible_bitstring: '1011000', feasible_sample_ratio: 0.18, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing },
      { solver: 'qaoa_shot_simulator', status: 'ran', best_feasible_objective: 16.0, best_feasible_bitstring: '1011000', feasible_sample_ratio: 0.10, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator },
      { solver: 'constrained_qaoa_metadata_mvp', status: 'skipped', best_feasible_objective: null, best_feasible_bitstring: null, feasible_sample_ratio: null, total_ms: 0 },
    ] } } },

    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'knapsack-gemini-review', tool: 'gemini.review', title: '方案审查', summary: '审查最终方案', simulated: true, input: { review_target: 'best_solution', check_feasibility: true } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'knapsack-gemini-review', tool: 'gemini.review', simulated: true, output: { verdict: 'pass', feasible: true, objective_value: 16.0, notes: '最优可行解确认，重量约束满足' } } },

    { delay_ms: T.summary, event: { type: 'summary', phase: 'final', message: '经典与量子路线均收敛到同一最优解', highlights: ['objective_value = 16.0', 'weight constraint satisfied', 'hybrid round-repair was feasible without repair', 'constrained QAOA skipped (no exactly_one)'] } },
    { delay_ms: T.final, event: { type: 'final', simulated: true, best_solution: { bitstring: '1011000', bits: [1, 0, 1, 1, 0, 0, 0], logical_solution: { item_0: 1, item_1: 0, item_2: 1, item_3: 1 }, objective_value: 16.0, qubo_energy: -16.0, penalty_energy: 0.0, is_feasible: true, total_violation: 0.0, num_occurrences: 1, source_backend: 'exact', constraint_violations: [] }, benchmark: { rows: [
      { solver: 'exact', status: 'ran', best_feasible_objective: 16.0, best_feasible_bitstring: '1011000', feasible_sample_ratio: 0.0625, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact },
      { solver: 'simulated_annealing', status: 'ran', best_feasible_objective: 16.0, best_feasible_bitstring: '1011000', feasible_sample_ratio: 0.18, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing },
      { solver: 'qaoa_shot_simulator', status: 'ran', best_feasible_objective: 16.0, best_feasible_bitstring: '1011000', feasible_sample_ratio: 0.10, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator },
      { solver: 'constrained_qaoa_metadata_mvp', status: 'skipped', best_feasible_objective: null, best_feasible_bitstring: null, feasible_sample_ratio: null, total_ms: 0 },
    ] }, qaoa_backend: QAOA_EXECUTION_BACKEND } },

    ...buildOpenQuestionEvents('small_knapsack').map(
      (q): PlaygroundTimedEvent => ({ delay_ms: T.open_question, event: q }),
    ),

    { delay_ms: T.done, event: { type: 'done', message: '方案分析完成' } },
  ],
};
