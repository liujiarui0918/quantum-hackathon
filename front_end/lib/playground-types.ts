export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = { readonly [key: string]: JsonValue };

export type PlaygroundScenarioId = 'sample_assignment' | 'small_knapsack' | 'exactly_one';

export type PlaygroundToolName =
  | 'modeling.build_qubo'
  | 'constraints.compile'
  | 'constraints.export_feasible_subspace'
  | 'solvers.solve_exact'
  | 'solvers.solve_sa'
  | 'qaoa.run_local_simulator'
  | 'constrained_qaoa.analyze_subspace'
  | 'hybrid.relax_round_repair'
  | 'benchmarks.compare_routes'
  | 'codex.search'
  | 'gemini.review';

export type PlaygroundPhase =
  | 'understand' | 'load_problem' | 'build_qubo' | 'compile_constraints'
  | 'benchmark' | 'qaoa' | 'constrained_qaoa' | 'final' | 'open_questions';

export type PlaygroundBestSolution = {
  bitstring: string;
  bits: number[];
  logical_solution: Record<string, 0 | 1>;
  objective_value: number;
  qubo_energy: number;
  penalty_energy: number;
  is_feasible: boolean;
  total_violation: number;
  num_occurrences: number;
  source_backend: string;
  constraint_violations: JsonObject[];
};

export type PlaygroundBenchmarkRow = {
  solver: string;
  status: 'ran' | 'skipped';
  best_feasible_objective: number | null;
  best_feasible_bitstring: string | null;
  feasible_sample_ratio: number | null;
  total_ms: number;
};

export type PlaygroundThinkingEvent = {
  type: 'thinking'; phase: PlaygroundPhase; message: string;
};
export type PlaygroundToolCallEvent = {
  type: 'tool_call';
  call_id: string;
  tool: PlaygroundToolName;
  title: string;
  summary: string;
  simulated: true;
  input: JsonObject;
};
export type PlaygroundToolResultEvent = {
  type: 'tool_result';
  call_id: string;
  tool: PlaygroundToolName;
  simulated: true;
  output: JsonObject;
};
export type PlaygroundSummaryEvent = {
  type: 'summary';
  phase: PlaygroundPhase;
  message: string;
  highlights: string[];
};
export type PlaygroundFinalEvent = {
  type: 'final';
  simulated: true;
  best_solution: PlaygroundBestSolution;
  benchmark: { rows: PlaygroundBenchmarkRow[] };
  qaoa_backend: string;
};
export type PlaygroundOpenQuestionEvent = {
  type: 'open_question';
  category: 'constraint_coverage' | 'hardware' | 'scale' | string;
  title: string;
  description: string;
};
export type PlaygroundDoneEvent = { type: 'done'; message: string };
export type PlaygroundErrorEvent = { type: 'error'; code: string; message: string };

export type PlaygroundEvent =
  | PlaygroundThinkingEvent
  | PlaygroundToolCallEvent
  | PlaygroundToolResultEvent
  | PlaygroundSummaryEvent
  | PlaygroundFinalEvent
  | PlaygroundOpenQuestionEvent
  | PlaygroundDoneEvent
  | PlaygroundErrorEvent;

export type PlaygroundTimedEvent = { delay_ms: number; event: PlaygroundEvent };

export type PlaygroundScript = {
  scenario: PlaygroundScenarioId;
  title: string;
  description: string;
  events: PlaygroundTimedEvent[];
};

export type PlaygroundStreamRequest = { prompt: string };