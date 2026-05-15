export interface QuantumSampleProblemResponse {
  ok: true;
  problem: QuantumProblemPayload;
}

export interface QuantumProblemPayload {
  name?: string;
  sense?: string;
  variables?: Array<{ name: string; kind?: string; [key: string]: unknown }>;
  objective?: Record<string, unknown>;
  constraints?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export interface QuantumSolveRequest {
  problem: QuantumProblemPayload;
  run_options?: QuantumRunOptions;
}

export interface QuantumRunOptions {
  seed?: number;
  sa_reads?: number;
  sa_sweeps?: number;
  top_k?: number;
  qaoa_p?: number;
  qaoa_shots?: number;
  qaoa_max_qubits?: number;
  qaoa_grid_size?: number;
  qaoa_random_trials?: number;
  qaoa_backend?: 'local' | 'aer' | 'aer-gpu' | 'aer-cpu';
  aer_device?: 'CPU' | 'GPU';
  aer_method?: string;
  aer_max_qubits?: number;
  aer_optimization_level?: number;
  skip_qaoa?: boolean;
}

export interface QuantumSolveResponse {
  ok: true;
  raw_result: QuantumRawResult;
  visualization: QuantumVisualization;
}

export interface QuantumApiErrorResponse {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface QuantumRawResult {
  problem?: Record<string, unknown>;
  run?: { seed?: number; [key: string]: unknown };
  diagnostics?: unknown;
  best_solution?: QuantumBestSolution | null;
  benchmark?: { rows?: QuantumBenchmarkRow[]; [key: string]: unknown };
  solvers?: Record<string, unknown>;
  qaoa?: Record<string, unknown>;
  constrained_qaoa?: Record<string, unknown>;
  report_markdown?: string;
  [key: string]: unknown;
}

export interface QuantumVisualization {
  quantum: QuantumView;
  scenario: QuantumScenarioView;
}

export interface QuantumView {
  problem?: {
    name?: string;
    sense?: string;
    num_logical_variables?: number;
    num_qubo_bits?: number;
    constraints?: unknown;
  };
  best_solution?: QuantumBestSolution | null;
  benchmark_rows?: QuantumBenchmarkRow[];
  qaoa?: QuantumQaoaView;
  constrained_qaoa?: QuantumConstrainedQaoaView;
  diagnostics?: unknown;
}

export interface QuantumBestSolution {
  bitstring?: string;
  bits?: number[];
  logical_solution?: Record<string, number | boolean | string | null>;
  objective_value?: number;
  qubo_energy?: number;
  penalty_energy?: number;
  is_feasible?: boolean;
  total_violation?: number;
  num_occurrences?: number;
  source_backend?: string;
  constraint_violations?: QuantumConstraintViolation[];
}

export interface QuantumConstraintViolation {
  name?: string;
  lhs?: number;
  sense?: string;
  rhs?: number;
  violation?: number;
  is_satisfied?: boolean;
}

export interface QuantumBenchmarkRow {
  solver?: string;
  status?: string;
  best_feasible_objective?: number | null;
  best_feasible_bitstring?: string | null;
  feasible_sample_ratio?: number | null;
  total_ms?: number | null;
  [key: string]: unknown;
}

export interface QuantumQaoaView {
  status?: string;
  backend?: string;
  circuit?: {
    ansatz?: string;
    execution_backend?: string;
    num_qubits?: number;
    layers?: number;
    gate_count_estimate?: Record<string, number>;
    [key: string]: unknown;
  };
  optimizer?: {
    trace_length?: number;
    best_expected_energy?: number;
    first_expected_energy?: number;
    last_expected_energy?: number;
    [key: string]: unknown;
  };
}

export interface QuantumConstrainedQaoaView {
  status?: string;
  diagnostics?: {
    route?: string;
    backend?: string;
    feasible_ratio?: number;
    subspace?: Record<string, unknown>;
    mixer?: Record<string, unknown>;
    [key: string]: unknown;
  };
  warnings?: string[];
}

export interface QuantumScenarioView {
  scenario_id?: string;
  mapping_version?: number;
  variables?: Array<{ name: string; value: number | boolean | string | null; selected: boolean }>;
  selected_variables?: string[];
  constraints?: QuantumConstraintViolation[];
  objective_value?: number;
  selected_models?: string[];
  enabled_boosts?: string[];
}
