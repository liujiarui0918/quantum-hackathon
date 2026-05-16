import type { DatasetExecParams } from './dataset-exec-config';

export type TaskStatus = 'pending' | 'running' | 'completed';

export interface TaskPayload {
  name: string;
  datasetName: string;
  n: number;
  p: number;
  m1: number;
  m2: number;
  solver: 'qaoa' | 'annealing' | 'hybrid';
  maxQubits: number;
  subQuboSize: number;
  maxIterations: number;
  timeLimitSec: number;
  penaltyLambda: number;
}

export type TaskExecParam = DatasetExecParams;

export interface Task extends TaskPayload {
  id: string;
  status: TaskStatus;
  createdAt: string;
  execParam?: TaskExecParam | null;
  result?: unknown;
}

export interface ValidationItem {
  key: string;
  label: string;
  pass: boolean;
  reason?: string;
}

export interface IterationResultRow {
  iter: number;
  objective: number;
  bestBound?: number;
  gapPct?: number;
  feasible: boolean;
  usedQubits: number;
  elapsedSec: number;
  note?: string;
}

export interface ArtifactItem {
  title: string;
  imageUrl: string;
  description?: string;
}

export interface TaskResultSummary {
  bestObjective: number;
  bestBound?: number;
  gapPct?: number;
  feasible: boolean;
  constraintViolationCount: number;
  usedQubits: number;
  selectedBinaryCount: number;
  activeContinuousCount: number;
  totalRuntimeSec: number;
}

export interface TaskResultPayload {
  task: Task;
  validations: ValidationItem[];
  summary: TaskResultSummary;
  iterations: IterationResultRow[];
  artifacts: ArtifactItem[];
  notes?: string;
}
