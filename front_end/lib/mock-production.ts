import type {
  MachineTimelineRow,
  SchedulingAssignment,
  SchedulingResultPayload,
  SchedulingTask,
  SchedulingTaskPayload,
} from './production-types';

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

export function emptySchedulingPayload(): SchedulingTaskPayload {
  return {
    name: '',
    orderCount: 24,
    machineCount: 5,
    horizonHours: 72,
    dueTightness: 1.0,
    switchCostPerChange: 220,
    idlePenaltyPerHour: 80,
    priorityOrderRatio: 0.25,
  };
}

export function createDemoSchedulingTasks(): SchedulingTask[] {
  const now = new Date().toISOString();
  const base = emptySchedulingPayload();
  return [
    { id: 'prod-demo-completed', ...base, name: '演示任务-汽车零部件周排产', status: 'completed', createdAt: now },
    { id: 'prod-demo-pending', ...base, name: '演示任务-未执行', status: 'pending', createdAt: now },
  ];
}

export function buildSchedulingResult(task: SchedulingTask): SchedulingResultPayload {
  const rnd = mulberry32(hashSeed(task.id, 17));
  const mCount = task.machineCount;
  const oCount = task.orderCount;
  const horizon = task.horizonHours;

  type Order = { id: string; duration: number; due: number; priority: number };
  const orders: Order[] = Array.from({ length: oCount }).map((_, i) => {
    const duration = 1 + Math.floor(rnd() * 8);
    const due = Math.max(duration + 1, Math.round((horizon * (0.35 + rnd() * 0.6)) * task.dueTightness));
    const priority = rnd() < task.priorityOrderRatio ? 1 : 0;
    return { id: `O${String(i + 1).padStart(3, '0')}`, duration, due, priority };
  });
  orders.sort((a, b) => b.priority - a.priority || a.due - b.due || a.duration - b.duration);

  const machineTime = new Array<number>(mCount).fill(0);
  const machineFamily = new Array<number>(mCount).fill(-1);
  const machineRows: MachineTimelineRow[] = Array.from({ length: mCount }).map((_, i) => ({
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
    let best = 0;
    let bestScore = Number.POSITIVE_INFINITY;
    for (let m = 0; m < mCount; m++) {
      const switched = machineFamily[m] !== -1 && machineFamily[m] !== family;
      const setup = switched ? 1 : 0;
      const finish = machineTime[m] + setup + o.duration;
      const late = Math.max(0, finish - o.due);
      const score = late * (o.priority ? 3.5 : 1.8) + setup * (task.switchCostPerChange / 100) + machineTime[m] * 0.03;
      if (score < bestScore) {
        bestScore = score;
        best = m;
      }
    }

    const switched = machineFamily[best] !== -1 && machineFamily[best] !== family;
    if (switched) {
      machineRows[best].switchCount += 1;
      machineTime[best] += 1;
    }
    const start = machineTime[best];
    const end = start + o.duration;
    machineTime[best] = end;
    machineFamily[best] = family;
    machineRows[best].busyHours += o.duration;
    machineRows[best].items.push({ orderId: o.id, start, end, duration: o.duration, switched });

    assignments.push({
      orderId: o.id,
      machineId: `M${best + 1}`,
      sequence: machineRows[best].items.length,
      start,
      end,
      due: o.due,
      lateness: Math.max(0, end - o.due),
      switched,
    });
  }

  let totalIdle = 0;
  for (const row of machineRows) {
    const finish = row.items.length ? row.items[row.items.length - 1].end : 0;
    row.idleHours = Math.max(0, horizon - finish);
    row.utilization = row.busyHours / horizon;
    totalIdle += row.idleHours;
  }

  const delayed = assignments.filter((x) => x.lateness > 0);
  const totalDelay = delayed.reduce((s, x) => s + x.lateness, 0);
  const switchCount = machineRows.reduce((s, x) => s + x.switchCount, 0);
  const delayCost = Math.round(totalDelay * 260);
  const switchCost = Math.round(switchCount * task.switchCostPerChange);
  const idleCost = Math.round(totalIdle * task.idlePenaltyPerHour);

  return {
    task,
    validations: [
      { key: 'machine-once', label: '机器一次只能做一个任务', pass: true },
      { key: 'process-order', label: '工序先后关系满足', pass: true },
      { key: 'due-date', label: '交付时间约束可行', pass: delayed.length <= Math.round(oCount * 0.35) },
    ],
    summary: {
      totalOrders: assignments.length,
      onTimeOrders: assignments.length - delayed.length,
      delayedOrders: delayed.length,
      avgDelayHours: delayed.length ? Math.round((totalDelay / delayed.length) * 100) / 100 : 0,
      totalDelayHours: Math.round(totalDelay * 100) / 100,
      switchCount,
      idleHours: Math.round(totalIdle * 100) / 100,
      objectiveScore: delayCost + switchCost + idleCost,
      delayCost,
      switchCost,
      idleCost,
    },
    assignments: assignments.sort((a, b) => a.machineId.localeCompare(b.machineId) || a.sequence - b.sequence),
    machineTimelines: machineRows,
  };
}
