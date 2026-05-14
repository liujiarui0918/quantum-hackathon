// Reusable types from playground-types
import type {
  PlaygroundBestSolution,
  PlaygroundBenchmarkRow,
  JsonObject,
} from './playground-types';

// ---------------------------------------------------------------------------
// RawResult — matches the full payload returned by demo.run_demo()
// ---------------------------------------------------------------------------

export interface ProblemSummary {
  name: string;
  source: string;
  sense: 'minimize' | 'maximize';
  variables: string[];
  num_logical_variables: number;
  num_qubo_bits: number;
  constraints: string[];
}

export interface RunInfo {
  seed: number;
  python: string;
  platform: string;
  total_ms: number;
}

/** Matches model.diagnostics() output. */
export type Diagnostics = JsonObject;

export interface BenchmarkSection {
  rows: PlaygroundBenchmarkRow[];
  markdown: string;
}

export interface SolverSummary {
  status: 'ran' | 'skipped';
  backend?: string;
  reason?: string;
  best_feasible?: PlaygroundBestSolution | null;
  best_raw_energy_sample?: PlaygroundBestSolution | null;
  feasible_sample_ratio?: number | null;
  samples_returned?: number;
  timing?: JsonObject;
  diagnostics?: Diagnostics;
  config?: JsonObject;
  total_ms?: number;
}

export interface SolverSection {
  exact: SolverSummary;
  simulated_annealing: SolverSummary;
}

export interface QaoaCircuitSummary {
  ansatz: string;
  execution_backend: string;
  num_qubits: number;
  layers: number;
  initial_state: string;
  cost_unitary: {
    description: string;
    z_terms: Record<string, number>;
    zz_terms: Record<string, number>;
  };
  mixer_unitary: {
    description: string;
    x_terms_per_layer: number;
  };
  gate_count_estimate: {
    h: number;
    rz_per_layer: number;
    rzz_per_layer: number;
    rx_per_layer: number;
  };
}

export interface QaoaSummary {
  status: 'ran' | 'skipped';
  reason?: string;
  backend?: string;
  best_feasible?: PlaygroundBestSolution | null;
  best_raw_energy_sample?: PlaygroundBestSolution | null;
  feasible_sample_ratio?: number | null;
  samples_returned?: number;
  best_parameters?: {
    gammas: number[];
    betas: number[];
  };
  optimizer?: {
    trace_length: number;
    best_expected_energy: number | null;
    first_expected_energy: number | null;
    last_expected_energy: number | null;
  };
  diagnostics?: Diagnostics;
  quantum_circuit?: QaoaCircuitSummary;
  total_ms?: number;
}

export interface ConstrainedQaoaSummary {
  status: 'ran' | 'skipped';
  reason?: string;
  route?: string;
  note?: string;
  best_feasible?: PlaygroundBestSolution | null;
  backend?: string;
  feasible_sample_ratio?: number | null;
  diagnostics?: Diagnostics;
  warnings?: string[];
  total_ms?: number;
}

export interface RawResult {
  problem: ProblemSummary;
  run: RunInfo;
  diagnostics: Diagnostics;
  best_solution: PlaygroundBestSolution | null;
  benchmark: BenchmarkSection;
  solvers: SolverSection;
  qaoa: QaoaSummary;
  constrained_qaoa: ConstrainedQaoaSummary;
  output_files?: {
    json: string;
    markdown_report: string;
  };
  report_markdown?: string;
}

// ---------------------------------------------------------------------------
// QuantumVisualization — bi-layer structure returned by backend_service
// ---------------------------------------------------------------------------

export interface QuantumView {
  problem: ProblemSummary;
  best_solution: PlaygroundBestSolution | null;
  benchmark_rows: PlaygroundBenchmarkRow[];
  qaoa: {
    status: 'ran' | 'skipped';
    backend?: string;
    circuit?: QaoaCircuitSummary;
    optimizer?: {
      trace_length: number;
      best_expected_energy: number | null;
      first_expected_energy: number | null;
      last_expected_energy: number | null;
    };
  };
  constrained_qaoa: {
    status: 'ran' | 'skipped';
    diagnostics?: Diagnostics;
    warnings?: string[];
  };
  diagnostics: Diagnostics;
}

export interface ScenarioVariable {
  name: string;
  value: number;
  selected: boolean;
}

export interface ScenarioConstraint {
  name: string;
  lhs: number;
  sense: string;
  rhs: number;
  violation: number;
  is_satisfied: boolean;
}

export interface SampleAssignmentMapping {
  selected_models: string[];
  model_details: Record<string, {
    objective_contribution: number;
    resource_usage: number;
  }>;
}

export interface ScenarioView {
  scenario_id: string;
  mapping_version: number;
  variables: ScenarioVariable[];
  selected_variables: string[];
  constraints: ScenarioConstraint[];
  objective_value: number;
  sample_assignment?: SampleAssignmentMapping;
}

export interface QuantumVisualization {
  quantum: QuantumView;
  scenario: ScenarioView;
}

// ---------------------------------------------------------------------------
// QuantumApiResponse — top-level wrapper from backend_service
// ---------------------------------------------------------------------------

export interface QuantumApiResponse {
  ok: boolean;
  raw_result: RawResult;
  visualization: QuantumVisualization;
}

// ---------------------------------------------------------------------------
// Error shape returned by backend_service on failure
// ---------------------------------------------------------------------------

export interface QuantumApiError {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: JsonObject;
  };
}
