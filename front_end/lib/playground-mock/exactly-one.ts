import type {
  PlaygroundScript,
  PlaygroundTimedEvent,
} from '@/lib/playground-types';
import { PLAYGROUND_TIMING, MOCK_BENCHMARK_TOTAL_MS, QAOA_EXECUTION_BACKEND, CONSTRAINED_QAOA_ROUTE } from '@/lib/playground-mock/timing';
import { buildOpenQuestionEvents } from '@/lib/playground-mock/open-questions';

const T = PLAYGROUND_TIMING;

export const EXACTLY_ONE_SCRIPT: PlaygroundScript = {
  scenario: 'exactly_one',
  title: 'Exactly One Selection (exactly_one)',
  description: '5 个候选里只能选 1 个，怎么挑收益最大',
  events: [
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'understand', message: '正在分析互斥选择需求...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-codex-search-1', tool: 'codex.search', title: '搜索代码库', summary: '搜索互斥选择案例', simulated: true, input: { query: 'exactly one selection constraint', scope: 'src/' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-codex-search-1', tool: 'codex.search', simulated: true, output: { matches: ['src/quantum_hackathon/benchmarks/cases.py'], summary: '找到 exactly_one_selection 案例，含 one-hot 约束' } } },
    { delay_ms: T.summary, event: { type: 'summary', phase: 'understand', message: '需求已明确：N 选 1 互斥约束，最大化收益', highlights: ['exactly-one constraint (one-hot)', '5 binary candidates', 'maximize selection value'] } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'load_problem', message: '加载互斥选择问题并构建 QUBO...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-modeling-build-qubo', tool: 'modeling.build_qubo', title: '构建 QUBO 模型', summary: '编译互斥选择为 QUBO', simulated: true, input: { problem: 'exactly_one_selection', sense: 'maximize', penalty_weights: { pick_exactly_one: 15.0 } } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-modeling-build-qubo', tool: 'modeling.build_qubo', simulated: true, output: { num_logical_variables: 5, total_binary_variables: 5, slack_variables: 0, auxiliary_variables: 0, linear_terms: 5, quadratic_couplers: 10, density: 1.0, coefficient_ratio: 12.0, warnings: [] } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'compile_constraints', message: '编译互斥约束与可行子空间...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-constraints-compile', tool: 'constraints.compile', title: '编译约束', summary: '转化 exactly-one 为罚函数', simulated: true, input: { constraints: ['pick_exactly_one'], strategy: 'unbalanced_penalty' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-constraints-compile', tool: 'constraints.compile', simulated: true, output: { compiled: 1, penalty_terms_added: 1, pick_exactly_one: { type: 'exactly_one', penalty_weight: 15.0 } } } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-constraints-subspace', tool: 'constraints.export_feasible_subspace', title: '导出可行子空间', summary: '识别 one-hot 可行子空间', simulated: true, input: { constraint_type: 'exactly_one' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-constraints-subspace', tool: 'constraints.export_feasible_subspace', simulated: true, output: { one_hot_groups: [[0, 1, 2, 3, 4]], constraints_covered: ['pick_exactly_one'], constraints_not_covered: [], subspace_size: '5 qubits in one-hot group', note: 'Full problem captured by one-hot subspace' } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'benchmark', message: '执行求解器 benchmark...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-solvers-exact', tool: 'solvers.solve_exact', title: 'Exact 枚举求解', summary: '全空间枚举', simulated: true, input: { max_bits: 25, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-solvers-exact', tool: 'solvers.solve_exact', simulated: true, output: { status: 'ran', backend: 'exact', feasible_sample_ratio: 0.03125, samples_returned: 32, best_feasible: { bitstring: '00010', objective_value: 9.0, is_feasible: true, source_backend: 'exact' }, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact } } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-solvers-sa', tool: 'solvers.solve_sa', title: '模拟退火求解', summary: '随机局部搜索', simulated: true, input: { num_reads: 60, num_sweeps: 150, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-solvers-sa', tool: 'solvers.solve_sa', simulated: true, output: { status: 'ran', backend: 'simulated_annealing', feasible_sample_ratio: 0.20, samples_returned: 60, best_feasible: { bitstring: '00010', objective_value: 9.0, is_feasible: true, source_backend: 'simulated_annealing' }, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'qaoa', message: '构建 QAOA 量子线路...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-qaoa-run', tool: 'qaoa.run_local_simulator', title: 'QAOA 本地模拟器', summary: '标准 X-mixer ansatz', simulated: true, input: { ansatz: 'standard_qaoa_x_mixer', execution_backend: QAOA_EXECUTION_BACKEND, num_qubits: 5, layers: 1, shots: 200, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-qaoa-run', tool: 'qaoa.run_local_simulator', simulated: true, output: { status: 'ran', backend: 'qaoa_shot_simulator', execution_backend: QAOA_EXECUTION_BACKEND, num_qubits: 5, layers: 1, feasible_sample_ratio: 0.12, best_feasible: { bitstring: '00010', objective_value: 9.0, is_feasible: true }, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator } } },

    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'constrained_qaoa', message: '分析 constrained QAOA 可行子空间与 XY mixer...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-cqaoa-analyze', tool: 'constrained_qaoa.analyze_subspace', title: 'Constrained QAOA 子空间分析', summary: 'one-hot 可行子空间 + XY mixer', simulated: true, input: { constraint_type: 'exactly_one', mixer: 'one_hot_xy' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-cqaoa-analyze', tool: 'constrained_qaoa.analyze_subspace', simulated: true, output: { status: 'ran', route: CONSTRAINED_QAOA_ROUTE, subspace: { num_qubits: 5, one_hot_groups: [[0, 1, 2, 3, 4]] }, constraints_covered: ['pick_exactly_one'], constraints_not_covered: [], mixer: { name: 'one_hot_xy', preserves_feasibility: true, edge_count: 10, two_qubit_term_count: 10, transition_graph_connected: true }, warm_start: { available: true, probability_distribution: 'from_relaxation', note: 'warm-start metadata MVP only' }, best_feasible: { bitstring: '00010', objective_value: 9.0, is_feasible: true }, total_ms: MOCK_BENCHMARK_TOTAL_MS.constrained_qaoa_metadata_mvp } } },

    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-benchmark-compare', tool: 'benchmarks.compare_routes', title: 'Benchmark 对比', summary: '汇总各求解器结果', simulated: true, input: { scenarios: ['exact', 'simulated_annealing', 'qaoa_shot_simulator', 'constrained_qaoa_metadata_mvp'] } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-benchmark-compare', tool: 'benchmarks.compare_routes', simulated: true, output: { rows: [
      { solver: 'exact', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.03125, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact },
      { solver: 'simulated_annealing', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.20, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing },
      { solver: 'qaoa_shot_simulator', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.12, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator },
      { solver: 'constrained_qaoa_metadata_mvp', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.25, total_ms: MOCK_BENCHMARK_TOTAL_MS.constrained_qaoa_metadata_mvp },
    ] } } },

    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'exactly-gemini-review', tool: 'gemini.review', title: '方案审查', summary: '审查最终方案', simulated: true, input: { review_target: 'best_solution', check_feasibility: true } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'exactly-gemini-review', tool: 'gemini.review', simulated: true, output: { verdict: 'pass', feasible: true, objective_value: 9.0, notes: '最优可行解确认，恰好选择 1 个候选' } } },

    { delay_ms: T.summary, event: { type: 'summary', phase: 'final', message: '所有路线收敛到同一最优解，constrained QAOA 子空间全覆盖', highlights: ['objective_value = 9.0', 'exactly-one fully covered by subspace', 'XY mixer preserves feasibility', 'warm-start metadata MVP reported'] } },
    { delay_ms: T.final, event: { type: 'final', simulated: true, best_solution: { bitstring: '00010', bits: [0, 0, 0, 1, 0], logical_solution: { cand_0: 0, cand_1: 0, cand_2: 0, cand_3: 1, cand_4: 0 }, objective_value: 9.0, qubo_energy: -9.0, penalty_energy: 0.0, is_feasible: true, total_violation: 0.0, num_occurrences: 1, source_backend: 'exact', constraint_violations: [] }, benchmark: { rows: [
      { solver: 'exact', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.03125, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact },
      { solver: 'simulated_annealing', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.20, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing },
      { solver: 'qaoa_shot_simulator', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.12, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator },
      { solver: 'constrained_qaoa_metadata_mvp', status: 'ran', best_feasible_objective: 9.0, best_feasible_bitstring: '00010', feasible_sample_ratio: 0.25, total_ms: MOCK_BENCHMARK_TOTAL_MS.constrained_qaoa_metadata_mvp },
    ] }, qaoa_backend: QAOA_EXECUTION_BACKEND } },

    ...buildOpenQuestionEvents('exactly_one').map(
      (q): PlaygroundTimedEvent => ({ delay_ms: T.open_question, event: q }),
    ),

    { delay_ms: T.done, event: { type: 'done', message: '方案分析完成' } },
  ],
};
