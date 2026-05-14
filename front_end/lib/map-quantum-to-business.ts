import type {
  QuantumVisualization,
  ScenarioConstraint,
  ScenarioVariable,
} from './quantum-api-types';
import type {
  TaskResultPayload,
  Task,
  ValidationItem,
  UnitResultRow,
} from './types';
import type { PlaygroundBenchmarkRow } from './playground-types';

// ---------------------------------------------------------------------------
// mapVisualizationToTaskResultPayload
// ---------------------------------------------------------------------------

export function mapVisualizationToTaskResultPayload(
  vis: QuantumVisualization,
  taskId: string,
): Partial<TaskResultPayload> {
  const now = new Date().toISOString();

  const task: Task = {
    id: taskId,
    name: vis.scenario.scenario_id,
    status: 'completed',
    createdAt: now,
    counts: 0,
    period: '',
    targetNeed: 0,
    backNeed: 0,
    co2Limit: 0,
    minOutput: 0,
    maxOutput: 0,
    changeOimit: 0,
    startAndEndTime: '',
    co2Counts: 0,
    startCosts: 0,
    endCosts: 0,
    fuelCosts: 0,
  };

  const validations: ValidationItem[] = vis.scenario.constraints.map(
    (c: ScenarioConstraint): ValidationItem => ({
      key: c.name,
      label: c.name,
      pass: c.is_satisfied,
      reason: c.is_satisfied
        ? undefined
        : `violation ${c.violation}: ${c.lhs} ${c.sense} ${c.rhs}`,
    }),
  );

  const units: UnitResultRow[] = vis.scenario.variables
    .filter((v: ScenarioVariable) => v.selected)
    .map(
      (_v: ScenarioVariable, idx: number): UnitResultRow => ({
        index: idx,
        totalPowerMw: 0,
        totalCo2Ton: 0,
        totalCostYuan: 0,
        startCostYuan: 0,
        shutdownCostYuan: 0,
        fuelCostYuan: 0,
        series: [],
      }),
    );

  return { task, validations, units };
}

// ---------------------------------------------------------------------------
// extractBestSolution
// ---------------------------------------------------------------------------

export interface BestSolutionDisplay {
  objective_value: number | null;
  is_feasible: boolean | null;
  bitstring: string | null;
  source_backend: string | null;
  total_violation: number | null;
}

export function extractBestSolution(
  vis: QuantumVisualization,
): BestSolutionDisplay {
  const sol = vis.quantum.best_solution;
  if (!sol) {
    return {
      objective_value: null,
      is_feasible: null,
      bitstring: null,
      source_backend: null,
      total_violation: null,
    };
  }
  return {
    objective_value: sol.objective_value,
    is_feasible: sol.is_feasible,
    bitstring: sol.bitstring,
    source_backend: sol.source_backend,
    total_violation: sol.total_violation,
  };
}

// ---------------------------------------------------------------------------
// extractBenchmarkRows
// ---------------------------------------------------------------------------

export function extractBenchmarkRows(
  vis: QuantumVisualization,
): PlaygroundBenchmarkRow[] {
  return vis.quantum.benchmark_rows;
}

// ---------------------------------------------------------------------------
// extractQaoaStatus
// ---------------------------------------------------------------------------

export interface QaoaStatusDisplay {
  status: 'ran' | 'skipped';
  backend: string | undefined;
  circuit_layers: number | undefined;
  optimizer_trace_length: number | undefined;
}

export function extractQaoaStatus(
  vis: QuantumVisualization,
): QaoaStatusDisplay {
  const q = vis.quantum.qaoa;
  return {
    status: q.status,
    backend: q.backend,
    circuit_layers: q.circuit?.layers,
    optimizer_trace_length: q.optimizer?.trace_length,
  };
}

// ---------------------------------------------------------------------------
// extractConstrainedQaoaStatus
// ---------------------------------------------------------------------------

export interface ConstrainedQaoaStatusDisplay {
  status: 'ran' | 'skipped';
  diagnostics: Record<string, unknown> | undefined;
  warnings: string[] | undefined;
}

export function extractConstrainedQaoaStatus(
  vis: QuantumVisualization,
): ConstrainedQaoaStatusDisplay {
  return {
    status: vis.quantum.constrained_qaoa.status,
    diagnostics: vis.quantum.constrained_qaoa.diagnostics,
    warnings: vis.quantum.constrained_qaoa.warnings,
  };
}
