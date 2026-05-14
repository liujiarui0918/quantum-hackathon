import type {
  PlaygroundScript,
  PlaygroundTimedEvent,
} from '@/lib/playground-types';
import { PLAYGROUND_TIMING, MOCK_BENCHMARK_TOTAL_MS, QAOA_EXECUTION_BACKEND, CONSTRAINED_QAOA_ROUTE } from '@/lib/playground-mock/timing';
import { buildOpenQuestionEvents } from '@/lib/playground-mock/open-questions';

const T = PLAYGROUND_TIMING;

export const SAMPLE_ASSIGNMENT_SCRIPT: PlaygroundScript = {
  scenario: 'sample_assignment',
  title: 'Sample Assignment (sample_assignment)',
  description: '从 model_a/b/c 三个模型里选一个，再决定是否启用 boost_x/boost_y，资源预算不超过 6',
  events: [
    // 1. understand
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'understand', message: '正在分析您的需求：这是一个带约束的组合优化问题...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-codex-search-1', tool: 'codex.search', title: '搜索代码库', summary: '在项目仓库中搜索相关优化案例', simulated: true, input: { query: 'sample_assignment optimization problem', scope: 'src/' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-codex-search-1', tool: 'codex.search', simulated: true, output: { matches: ['data/sample_problem.json', 'src/quantum_hackathon/demo.py'], summary: '找到 sample_assignment 案例，含 exactly-one 约束与 resource_budget 约束' } } },
    { delay_ms: T.summary, event: { type: 'summary', phase: 'understand', message: '需求已明确：从 3 个模型中选 1 个，配合 2 个可选 boost，资源预算 ≤6', highlights: ['3 binary models + 2 boost variables', 'exactly_one constraint on models', 'resource_budget ≤ 6'] } },

    // 2. load_problem + build_qubo
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'load_problem', message: '加载样例问题并构建 QUBO 模型...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-modeling-build-qubo', tool: 'modeling.build_qubo', title: '构建 QUBO 模型', summary: '将优化问题编译为 QUBO 能量函数', simulated: true, input: { problem: 'sample_assignment', sense: 'maximize', penalty_weights: { choose_one_model: 15.0, resource_budget: 20.0 } } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-modeling-build-qubo', tool: 'modeling.build_qubo', simulated: true, output: { num_logical_variables: 5, total_binary_variables: 8, slack_variables: 3, auxiliary_variables: 0, linear_terms: 8, quadratic_couplers: 28, density: 1.0, coefficient_ratio: 20.75, warnings: [], variable_mapping: { model_a: 0, model_b: 1, model_c: 2, boost_x: 3, boost_y: 4, slack_0: 5, slack_1: 6, slack_2: 7 } } } },

    // 3. compile constraints
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'compile_constraints', message: '编译约束并检查可行子空间...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-constraints-compile', tool: 'constraints.compile', title: '编译约束', summary: '将线性约束转化为罚函数项', simulated: true, input: { constraints: ['choose_one_model', 'resource_budget'], strategy: 'unbalanced_penalty' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-constraints-compile', tool: 'constraints.compile', simulated: true, output: { compiled: 2, penalty_terms_added: 2, choose_one_model: { type: 'exactly_one', penalty_weight: 15.0 }, resource_budget: { type: 'bounded_sum', penalty_weight: 20.0, slack_bits_added: 3 } } } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-constraints-subspace', tool: 'constraints.export_feasible_subspace', title: '导出可行子空间', summary: '识别 exactly-one 约束的 one-hot 可行子空间', simulated: true, input: { constraint_type: 'exactly_one' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-constraints-subspace', tool: 'constraints.export_feasible_subspace', simulated: true, output: { one_hot_groups: [[0, 1, 2]], constraints_covered: ['choose_one_model'], constraints_not_covered: ['resource_budget'], subspace_size: '3 of 8 qubits in one-hot groups', note: 'resource_budget uses slack encoding, not subspace-preserving' } } },

    // 4. solvers
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'benchmark', message: '执行各求解器 benchmark...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-solvers-exact', tool: 'solvers.solve_exact', title: 'Exact 枚举求解', summary: '全空间枚举，保证最优', simulated: true, input: { max_bits: 25, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-solvers-exact', tool: 'solvers.solve_exact', simulated: true, output: { status: 'ran', backend: 'exact', feasible_sample_ratio: 0.046875, samples_returned: 256, best_feasible: { bitstring: '00110000', objective_value: 11.0, is_feasible: true, source_backend: 'exact' }, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact } } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-solvers-sa', tool: 'solvers.solve_sa', title: '模拟退火求解', summary: '随机局部搜索 CPU 基线', simulated: true, input: { num_reads: 60, num_sweeps: 150, seed: 7 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-solvers-sa', tool: 'solvers.solve_sa', simulated: true, output: { status: 'ran', backend: 'simulated_annealing', feasible_sample_ratio: 0.15, samples_returned: 60, best_feasible: { bitstring: '00110000', objective_value: 11.0, is_feasible: true, source_backend: 'simulated_annealing' }, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing } } },

    // 5. QAOA
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'qaoa', message: '构建 QAOA 量子线路并运行本地模拟...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-qaoa-run', tool: 'qaoa.run_local_simulator', title: 'QAOA 本地模拟器', summary: '标准 X-mixer ansatz，本地 statevector 优化 + shot 采样', simulated: true, input: { ansatz: 'standard_qaoa_x_mixer', execution_backend: QAOA_EXECUTION_BACKEND, num_qubits: 8, layers: 1, shots: 200, seed: 7, grid_size: 5, random_trials: 10 } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-qaoa-run', tool: 'qaoa.run_local_simulator', simulated: true, output: { status: 'ran', backend: 'qaoa_shot_simulator', execution_backend: QAOA_EXECUTION_BACKEND, num_qubits: 8, layers: 1, best_parameters: { gammas: [0.7854], betas: [0.3927] }, gate_count_estimate: { h: 8, rz_per_layer: 8, rzz_per_layer: 28, rx_per_layer: 8 }, feasible_sample_ratio: 0.08, best_feasible: { bitstring: '00110000', objective_value: 11.0, is_feasible: true }, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator } } },

    // 6. constrained QAOA
    { delay_ms: T.thinking, event: { type: 'thinking', phase: 'constrained_qaoa', message: '分析 constrained QAOA 可行子空间与 XY mixer...' } },
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-cqaoa-analyze', tool: 'constrained_qaoa.analyze_subspace', title: 'Constrained QAOA 子空间分析', summary: '识别 one-hot 可行子空间与 XY mixer 诊断', simulated: true, input: { constraint_type: 'exactly_one', mixer: 'one_hot_xy' } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-cqaoa-analyze', tool: 'constrained_qaoa.analyze_subspace', simulated: true, output: { status: 'ran', route: CONSTRAINED_QAOA_ROUTE, note: 'This route reports feasible-subspace and XY-mixer diagnostics; the current MVP samples the induced model with exact or simulated annealing backends.', subspace: { num_qubits: 5, one_hot_groups: [[0, 1, 2]] }, constraints_covered: ['choose_one_model'], constraints_not_covered: ['resource_budget'], mixer: { name: 'one_hot_xy', preserves_feasibility: true, edge_count: 3, two_qubit_term_count: 3, transition_graph_connected: true }, best_feasible: { bitstring: '00110000', objective_value: 11.0, is_feasible: true }, total_ms: MOCK_BENCHMARK_TOTAL_MS.constrained_qaoa_metadata_mvp } } },

    // 7. benchmark comparison
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-benchmark-compare', tool: 'benchmarks.compare_routes', title: 'Benchmark 对比', summary: '汇总各求解器结果', simulated: true, input: { scenarios: ['exact', 'simulated_annealing', 'qaoa_shot_simulator', 'constrained_qaoa_metadata_mvp'] } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-benchmark-compare', tool: 'benchmarks.compare_routes', simulated: true, output: { rows: [
      { solver: 'exact', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.046875, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact },
      { solver: 'simulated_annealing', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.15, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing },
      { solver: 'qaoa_shot_simulator', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.08, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator },
      { solver: 'constrained_qaoa_metadata_mvp', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.12, total_ms: MOCK_BENCHMARK_TOTAL_MS.constrained_qaoa_metadata_mvp },
    ] } } },

    // 8. gemini review
    { delay_ms: T.tool_call, event: { type: 'tool_call', call_id: 'sample-gemini-review', tool: 'gemini.review', title: '方案审查', summary: '审查最终方案合理性', simulated: true, input: { review_target: 'best_solution', check_feasibility: true } } },
    { delay_ms: T.tool_result, event: { type: 'tool_result', call_id: 'sample-gemini-review', tool: 'gemini.review', simulated: true, output: { verdict: 'pass', feasible: true, objective_value: 11.0, notes: '最优可行解已确认，所有约束满足' } } },

    // 9. summary + final
    { delay_ms: T.summary, event: { type: 'summary', phase: 'final', message: '所有求解器均收敛到同一最优可行解', highlights: ['objective_value = 11.0', 'choose_one_model: model_c = 1', 'resource_budget: 4+2=6 ≤ 6', 'all 4 solvers agree'] } },
    { delay_ms: T.final, event: { type: 'final', simulated: true, best_solution: { bitstring: '00110000', bits: [0, 0, 1, 1, 0, 0, 0, 0], logical_solution: { model_a: 0, model_b: 0, model_c: 1, boost_x: 1, boost_y: 0 }, objective_value: 11.0, qubo_energy: -11.0, penalty_energy: 0.0, is_feasible: true, total_violation: 0.0, num_occurrences: 1, source_backend: 'exact', constraint_violations: [] }, benchmark: { rows: [
      { solver: 'exact', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.046875, total_ms: MOCK_BENCHMARK_TOTAL_MS.exact },
      { solver: 'simulated_annealing', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.15, total_ms: MOCK_BENCHMARK_TOTAL_MS.simulated_annealing },
      { solver: 'qaoa_shot_simulator', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.08, total_ms: MOCK_BENCHMARK_TOTAL_MS.qaoa_shot_simulator },
      { solver: 'constrained_qaoa_metadata_mvp', status: 'ran', best_feasible_objective: 11.0, best_feasible_bitstring: '00110000', feasible_sample_ratio: 0.12, total_ms: MOCK_BENCHMARK_TOTAL_MS.constrained_qaoa_metadata_mvp },
    ] }, qaoa_backend: QAOA_EXECUTION_BACKEND } },

    // 10. open questions
    ...buildOpenQuestionEvents('sample_assignment').map(
      (q): PlaygroundTimedEvent => ({ delay_ms: T.open_question, event: q }),
    ),

    // 11. done
    { delay_ms: T.done, event: { type: 'done', message: '方案分析完成' } },
  ],
};
