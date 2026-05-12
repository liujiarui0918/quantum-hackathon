export type TaskStatus = 'pending' | 'running' | 'completed';

/** 与表单/文档字段对齐；文档中「最大输出」误写为 minOutput，此处使用 maxOutput */
export interface TaskPayload {
  name: string;
  counts: number;
  period: string;
  targetNeed: number;
  backNeed: number;
  co2Limit: number;
  minOutput: number;
  maxOutput: number;
  changeOimit: number;
  startAndEndTime: string;
  co2Counts: number;
  startCosts: number;
  endCosts: number;
  fuelCosts: number;
}

export interface Task extends TaskPayload {
  id: string;
  status: TaskStatus;
  createdAt: string;
}

export interface ValidationItem {
  key: string;
  label: string;
  pass: boolean;
  reason?: string;
}

export interface UnitResultRow {
  index: number;
  totalPowerMw: number;
  totalCo2Ton: number;
  totalCostYuan: number;
  startCostYuan: number;
  shutdownCostYuan: number;
  fuelCostYuan: number;
  series: { t: string; p: number }[];
}

export interface TaskResultPayload {
  task: Task;
  validations: ValidationItem[];
  units: UnitResultRow[];
}
