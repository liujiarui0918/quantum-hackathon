import { randomUUID } from 'crypto';
import type {
  MachineTimelineRow,
  SchedulingAssignment,
  SchedulingResultPayload,
  SchedulingSummary,
  SchedulingTask,
  SchedulingTaskPayload,
  SchedulingTaskStatus,
  SchedulingValidationItem,
} from './production-types';

const tasks = new Map<string, SchedulingTask>();
const completeTimers = new Map<string, ReturnType<typeof setTimeout>>();

function nowIso() {
  return new Date().toISOString();
}

function seed() {
  if (tasks.size > 0) return;
  const base: SchedulingTaskPayload = {
    name: '演示任务-汽车零部件周排产',
    orderCount: 24,
    machineCount: 5,
    horizonHours: 72,
    dueTightness: 1.0,
    switchCostPerChange: 220,
    idlePenaltyPerHour: 80,
    priorityOrderRatio: 0.25,
  };
  const t1: SchedulingTask = {
    id: 'demo-production-completed',
    ...base,
    status: 'completed',
    createdAt: nowIso(),
  };
  const t2: SchedulingTask = {
    id: 'demo-production-pending',
    ...base,
    name: '演示任务-未执行',
    status: 'pending',
    createdAt: nowIso(),
  };
  tasks.set(t1.id, t1);
  tasks.set(t2.id, t2);
}

function clearTimer(id: string) {
  const t = completeTimers.get(id);
  if (t) clearTimeout(t);
  completeTimers.delete(id);
}

function scheduleComplete(id: string) {
  clearTimer(id);
  const timer = setTimeout(() => {
    const cur = tasks.get(id);
    if (cur && cur.status === 'running') {
      tasks.set(id, { ...cur, status: 'completed' });
    }
    completeTimers.delete(id);
  }, 6000);
  completeTimers.set(id, timer);
}

function hashSeed(id: string, salt: number) {
  let h = 0;
  const s = id + String(salt);
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

function mulberry32(seed: number) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

export function listSchedulingTasks(): SchedulingTask[] {
  seed();
  return Array.from(tasks.values()).sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt));
}

export function getSchedulingTask(id: string): SchedulingTask | null {
  seed();
  return tasks.get(id) ?? null;
}

export function createSchedulingTask(payload: SchedulingTaskPayload): SchedulingTask {
  seed();
  const task: SchedulingTask = {
    id: randomUUID(),
    ...payload,
    status: 'pending',
    createdAt: nowIso(),
  };
  tasks.set(task.id, task);
  return task;
}

export function updateSchedulingTask(id: string, payload: SchedulingTaskPayload): SchedulingTask | null {
  seed();
  const cur = tasks.get(id);
  if (!cur || cur.status !== 'pending') return null;
  const next: SchedulingTask = { ...cur, ...payload, id: cur.id, createdAt: cur.createdAt };
  tasks.set(id, next);
  return next;
}

export function executeSchedulingTask(id: string): boolean {
  seed();
  const cur = tasks.get(id);
  if (!cur || cur.status !== 'pending') return false;
  tasks.set(id, { ...cur, status: 'running' });
  scheduleComplete(id);
  return true;
}

export function terminateSchedulingTask(id: string): boolean {
  seed();
  const cur = tasks.get(id);
  if (!cur || cur.status !== 'running') return false;
  clearTimer(id);
  tasks.set(id, { ...cur, status: 'pending' });
  return true;
}

export function buildSchedulingValidations(task: SchedulingTask): SchedulingValidationItem[] {
  const v = (key: string, label: string, pass: boolean, reason: string): SchedulingValidationItem => ({
    key,
    label,
    pass,
    reason: pass ? undefined : reason,
  });
  const orderPass = task.orderCount >= 8 && task.orderCount <= 500;
  const machinePass = task.machineCount >= 2 && task.machineCount <= 30;
  const horizonPass = task.horizonHours >= 24 && task.horizonHours <= 336;
  const duePass = task.dueTightness >= 0.6 && task.dueTightness <= 1.4;
  const switchPass = task.switchCostPerChange >= 20 && task.switchCostPerChange <= 5000;
  const idlePass = task.idlePenaltyPerHour >= 10 && task.idlePenaltyPerHour <= 1000;
  const priorityPass = task.priorityOrderRatio >= 0 && task.priorityOrderRatio <= 1;
  return [
    v('orderCount', '订单数量', orderPass, '建议 8~500'),
    v('machineCount', '机器数量', machinePass, '建议 2~30'),
    v('horizonHours', '排程时域', horizonPass, '建议 24~336 小时'),
    v('dueTightness', '交期紧度', duePass, '建议 0.6~1.4'),
    v('switchCostPerChange', '换线成本', switchPass, '建议 20~5000'),
    v('idlePenaltyPerHour', '空闲惩罚', idlePass, '建议 10~1000'),
    v('priorityOrderRatio', '优先订单占比', priorityPass, '建议 0~1'),
  ];
}

function simulateScheduling(task: SchedulingTask): {
  assignments: SchedulingAssignment[];
  machineTimelines: MachineTimelineRow[];
  summary: SchedulingSummary;
} {
  const rnd = mulberry32(hashSeed(task.id, 17));
  const mCount = Math.max(2, Math.min(30, Math.floor(task.machineCount)));
  const oCount = Math.max(8, Math.min(500, Math.floor(task.orderCount)));
  const horizon = Math.max(24, Math.min(336, Math.floor(task.horizonHours)));

  const priorities = new Set<number>();
  for (let i = 0; i < oCount; i++) {
    if (rnd() < task.priorityOrderRatio) priorities.add(i);
  }

  type Order = { id: string; duration: number; due: number; priority: number };
  const orders: Order[] = Array.from({ length: oCount }).map((_, i) => {
    const duration = 1 + Math.floor(rnd() * 8); // 1~8h
    const baseDue = (horizon * (0.3 + rnd() * 0.65)) * task.dueTightness;
    const due = Math.max(duration + 1, Math.min(horizon + 24, Math.round(baseDue)));
    const priority = priorities.has(i) ? 1 : 0;
    return { id: `O${String(i + 1).padStart(3, '0')}`, duration, due, priority };
  });

  // 先高优先+早交期，再短工时（EDD + SPT）
  orders.sort((a, b) => b.priority - a.priority || a.due - b.due || a.duration - b.duration);

  const machineTime = new Array<number>(mCount).fill(0);
  const machineLastFamily = new Array<number>(mCount).fill(-1);
  const machineItems: MachineTimelineRow[] = Array.from({ length: mCount }).map((_, i) => ({
    machineId: `M${i + 1}`,
    busyHours: 0,
    idleHours: 0,
    utilization: 0,
    switchCount: 0,
    items: [],
  }));

  const assignments: SchedulingAssignment[] = [];
  for (let i = 0; i < orders.length; i++) {
    const o = orders[i];
    const family = (i + Math.floor(rnd() * 3)) % 4;
    let bestM = 0;
    let bestScore = Number.POSITIVE_INFINITY;
    for (let m = 0; m < mCount; m++) {
      const switchNeeded = machineLastFamily[m] !== -1 && machineLastFamily[m] !== family;
      const switchSetup = switchNeeded ? 1 : 0; // 1h 换线
      const finish = machineTime[m] + switchSetup + o.duration;
      const lateness = Math.max(0, finish - o.due);
      const score =
        lateness * (o.priority ? 3.5 : 1.8) +
        switchSetup * (task.switchCostPerChange / 100) +
        machineTime[m] * 0.03;
      if (score < bestScore) {
        bestScore = score;
        bestM = m;
      }
    }

    const switchNeeded = machineLastFamily[bestM] !== -1 && machineLastFamily[bestM] !== family;
    if (switchNeeded) {
      machineItems[bestM].switchCount += 1;
      machineTime[bestM] += 1;
    }
    const start = machineTime[bestM];
    const end = start + o.duration;
    const lateness = Math.max(0, end - o.due);
    machineTime[bestM] = end;
    machineLastFamily[bestM] = family;

    const row = machineItems[bestM];
    row.items.push({
      orderId: o.id,
      start,
      end,
      duration: o.duration,
      switched: switchNeeded,
    });
    row.busyHours += o.duration;

    assignments.push({
      orderId: o.id,
      machineId: `M${bestM + 1}`,
      sequence: row.items.length,
      start,
      end,
      due: o.due,
      lateness,
      switched: switchNeeded,
    });
  }

  let totalIdle = 0;
  for (const m of machineItems) {
    const finish = m.items.length > 0 ? m.items[m.items.length - 1].end : 0;
    m.idleHours = Math.max(0, horizon - finish);
    m.utilization = Math.max(0, Math.min(1, m.busyHours / horizon));
    totalIdle += m.idleHours;
  }

  const delayedOrders = assignments.filter((x) => x.lateness > 0);
  const totalDelayHours = delayedOrders.reduce((s, x) => s + x.lateness, 0);
  const switchCount = machineItems.reduce((s, x) => s + x.switchCount, 0);
  const delayCost = Math.round(totalDelayHours * 260);
  const switchCost = Math.round(switchCount * task.switchCostPerChange);
  const idleCost = Math.round(totalIdle * task.idlePenaltyPerHour);
  const objectiveScore = delayCost + switchCost + idleCost;

  const summary: SchedulingSummary = {
    totalOrders: assignments.length,
    onTimeOrders: assignments.length - delayedOrders.length,
    delayedOrders: delayedOrders.length,
    avgDelayHours: delayedOrders.length ? Math.round((totalDelayHours / delayedOrders.length) * 100) / 100 : 0,
    totalDelayHours: Math.round(totalDelayHours * 100) / 100,
    switchCount,
    idleHours: Math.round(totalIdle * 100) / 100,
    objectiveScore,
    delayCost,
    switchCost,
    idleCost,
  };

  assignments.sort((a, b) => a.machineId.localeCompare(b.machineId) || a.sequence - b.sequence);
  return { assignments, machineTimelines: machineItems, summary };
}

export type SchedulingResultLookup =
  | { ok: true; data: SchedulingResultPayload }
  | { ok: false; reason: 'not_found' | 'not_completed' };

export function lookupSchedulingTaskResult(taskId: string): SchedulingResultLookup {
  const task = getSchedulingTask(taskId);
  if (!task) return { ok: false, reason: 'not_found' };
  if (task.status !== 'completed') return { ok: false, reason: 'not_completed' };
  const simulated = simulateScheduling(task);
  return {
    ok: true,
    data: {
      task,
      validations: buildSchedulingValidations(task),
      summary: simulated.summary,
      assignments: simulated.assignments,
      machineTimelines: simulated.machineTimelines,
    },
  };
}

export function schedulingTaskStatusZh(status: SchedulingTaskStatus) {
  if (status === 'pending') return '未执行';
  if (status === 'running') return '执行中';
  return '已完成';
}
