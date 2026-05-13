export type SchedulingTaskStatus = 'pending' | 'running' | 'completed';

export interface SchedulingTaskPayload {
  name: string;
  orderCount: number;
  machineCount: number;
  horizonHours: number;
  dueTightness: number; // 0.6 ~ 1.4
  switchCostPerChange: number;
  idlePenaltyPerHour: number;
  priorityOrderRatio: number; // 0 ~ 1
}

export interface SchedulingTask extends SchedulingTaskPayload {
  id: string;
  status: SchedulingTaskStatus;
  createdAt: string;
}

export interface SchedulingValidationItem {
  key: string;
  label: string;
  pass: boolean;
  reason?: string;
}

export interface SchedulingAssignment {
  orderId: string;
  machineId: string;
  sequence: number;
  start: number;
  end: number;
  due: number;
  lateness: number;
  switched: boolean;
}

export interface MachineTimelineItem {
  orderId: string;
  start: number;
  end: number;
  duration: number;
  switched: boolean;
}

export interface MachineTimelineRow {
  machineId: string;
  busyHours: number;
  idleHours: number;
  utilization: number;
  switchCount: number;
  items: MachineTimelineItem[];
}

export interface SchedulingSummary {
  totalOrders: number;
  onTimeOrders: number;
  delayedOrders: number;
  avgDelayHours: number;
  totalDelayHours: number;
  switchCount: number;
  idleHours: number;
  objectiveScore: number;
  delayCost: number;
  switchCost: number;
  idleCost: number;
}

export interface SchedulingResultPayload {
  task: SchedulingTask;
  validations: SchedulingValidationItem[];
  summary: SchedulingSummary;
  assignments: SchedulingAssignment[];
  machineTimelines: MachineTimelineRow[];
}
