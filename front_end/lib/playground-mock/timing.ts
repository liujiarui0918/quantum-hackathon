export const QAOA_EXECUTION_BACKEND = 'local_statevector_optimizer_plus_shot_sampler' as const;
export const CONSTRAINED_QAOA_ROUTE = 'constrained_qaoa_metadata_mvp' as const;
export const MOCK_BENCHMARK_TOTAL_MS = {
  exact: 12,
  simulated_annealing: 85,
  qaoa_shot_simulator: 420,
  constrained_qaoa_metadata_mvp: 156,
} as const;
export const PLAYGROUND_TIMING = {
  thinking: 250,
  tool_call: 350,
  tool_result: 500,
  summary: 300,
  final: 400,
  open_question: 200,
  done: 100,
} as const;