import { randomUUID } from 'crypto';
import type { Task, TaskPayload, TaskResultPayload, TaskStatus, UnitResultRow, ValidationItem } from './types';

const tasks = new Map<string, Task>();
const completeTimers = new Map<string, ReturnType<typeof setTimeout>>();

function nowIso() {
  return new Date().toISOString();
}

function seed() {
  if (tasks.size > 0) return;
  const base: TaskPayload = {
    name: '演示任务-华东电网',
    counts: 3,
    period: '24小时',
    targetNeed: 1200,
    backNeed: 200,
    co2Limit: 800,
    minOutput: 45,
    maxOutput: 320,
    changeOimit: 12,
    startAndEndTime: '30分钟',
    co2Counts: 0.85,
    startCosts: 4500,
    endCosts: 1200,
    fuelCosts: 380,
  };
  // 固定 ID：避免 dev 热更新/进程重启后种子任务 UUID 变化，导致结果页链接失效
  const t1: Task = {
    id: 'demo-seed-completed',
    ...base,
    name: '演示任务-华东电网',
    status: 'completed',
    createdAt: nowIso(),
  };
  const t2: Task = {
    id: 'demo-seed-pending',
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

export function listTasks(): Task[] {
  seed();
  return Array.from(tasks.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getTask(id: string): Task | null {
  seed();
  return tasks.get(id) ?? null;
}

export function createTask(payload: TaskPayload): Task {
  seed();
  const task: Task = {
    id: randomUUID(),
    ...payload,
    status: 'pending',
    createdAt: nowIso(),
  };
  tasks.set(task.id, task);
  return task;
}

export function updateTask(id: string, payload: TaskPayload): Task | null {
  seed();
  const cur = tasks.get(id);
  if (!cur || cur.status !== 'pending') return null;
  const next: Task = { ...cur, ...payload, id: cur.id, createdAt: cur.createdAt };
  tasks.set(id, next);
  return next;
}

export function executeTask(id: string): boolean {
  seed();
  const cur = tasks.get(id);
  if (!cur || cur.status !== 'pending') return false;
  tasks.set(id, { ...cur, status: 'running' });
  scheduleComplete(id);
  return true;
}

export function terminateTask(id: string): boolean {
  seed();
  const cur = tasks.get(id);
  if (!cur || cur.status !== 'running') return false;
  clearTimer(id);
  tasks.set(id, { ...cur, status: 'pending' });
  return true;
}

function statusLabelZh(s: TaskStatus) {
  if (s === 'pending') return '未执行';
  if (s === 'running') return '执行中';
  return '已完成';
}

export function buildValidations(task: Task): ValidationItem[] {
  const v = (key: string, label: string, pass: boolean, reason: string): ValidationItem => ({
    key,
    label,
    pass,
    reason: pass ? undefined : reason,
  });

  const targetPass = task.targetNeed >= 200 && task.targetNeed <= 12000;
  const backPass = task.backNeed >= 50 && task.backNeed <= 2000;
  const co2Pass = task.co2Limit >= 100 && task.co2Limit <= 5000;
  const minMaxPass = task.maxOutput > task.minOutput && task.minOutput >= 10 && task.maxOutput <= 600;
  const rampPass = task.changeOimit >= 5 && task.changeOimit <= 20;
  const timePass = ['15分钟', '30分钟', '60分钟'].includes(task.startAndEndTime);
  const co2RatePass = task.co2Counts >= 0.6 && task.co2Counts <= 1.2;
  const startCostPass = task.startCosts >= 2000 && task.startCosts <= 10000;
  const endCostPass = task.endCosts >= 500 && task.endCosts <= 2000;
  const fuelPass = task.fuelCosts >= 200 && task.fuelCosts <= 600;

  return [
    v('targetNeed', '目标负荷需求', targetPass, '需处于 200~12000 MW 且与备用容量协调'),
    v('backNeed', '备用容量上限', backPass, '需处于 50~2000 MW'),
    v('co2Limit', '碳排放限额', co2Pass, '需处于 100~5000 吨/天'),
    v('minOutput', '最小出力', minMaxPass, '最小/最大出力区间不合法或未满足 10~600 MW'),
    v('maxOutput', '最大出力', minMaxPass, '最大出力须大于最小出力'),
    v('changeOimit', '爬坡限制', rampPass, '需处于 5~20 MW/min'),
    v('startAndEndTime', '启停时间', timePass, '需为 15/30/60 分钟之一'),
    v('co2Counts', '碳排放量', co2RatePass, '需处于 0.6~1.2 吨CO2/MWh'),
    v('startCosts', '启动成本', startCostPass, '需处于 2000~10000 元'),
    v('endCosts', '关停成本', endCostPass, '需处于 500~2000 元'),
    v('fuelCosts', '燃料成本', fuelPass, '需处于 200~600 元/MWh'),
  ];
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

function buildUnitRows(task: Task): UnitResultRow[] {
  const n = Math.max(1, Math.min(12, Math.floor(task.counts)));
  const rows: UnitResultRow[] = [];
  for (let i = 0; i < n; i++) {
    const h = hashSeed(task.id, i + 1);
    const rnd = mulberry32(h);
    const series: { t: string; p: number }[] = [];
    const hours = task.period === '48小时' ? 48 : 24;

    // 机组启停：每台 1~3 个开机波段，每个波段从 0 升到峰值再降到 0
    const pulses = Math.min(3, Math.max(1, 1 + Math.floor(rnd() * 3)));
    const p = new Array<number>(hours).fill(0);
    let cursor = 0;
    for (let k = 0; k < pulses && cursor < hours - 2; k++) {
      const remainPulses = pulses - k;
      const remainHours = hours - cursor;
      const minNeed = remainPulses * 3;
      if (remainHours < minNeed) break;

      const idleMax = Math.max(0, Math.min(5, remainHours - minNeed));
      const idle = Math.floor(rnd() * (idleMax + 1));
      cursor += idle;
      if (cursor >= hours - 2) break;

      const remainHours2 = hours - cursor;
      const minNeed2 = (remainPulses - 1) * 3;
      const maxLen = Math.max(3, Math.min(10, remainHours2 - minNeed2));
      const len = 3 + Math.floor(rnd() * (maxLen - 2));

      const peakBase = task.minOutput + (task.maxOutput - task.minOutput) * (0.55 + rnd() * 0.4);
      for (let j = 0; j < len && cursor + j < hours; j++) {
        const x = len <= 1 ? 0 : j / (len - 1); // 0..1
        // 三角波包络：0 -> 1 -> 0
        const tri = x <= 0.5 ? x * 2 : (1 - x) * 2;
        const envelope = Math.pow(Math.max(0, tri), 0.9);
        const jitter = 1 + (rnd() - 0.5) * 0.08;
        const val = Math.max(0, Math.min(task.maxOutput, peakBase * envelope * jitter));
        p[cursor + j] = Math.max(p[cursor + j], val);
      }
      cursor += len;
    }

    for (let t = 0; t < hours; t++) {
      const val = p[t] < 1 ? 0 : p[t];
      series.push({ t: `${t + 1}h`, p: Math.round(val * 10) / 10 });
    }

    const totalPowerMw = Math.round(series.reduce((s, x) => s + x.p, 0) * 10) / 10;
    const avgMw = totalPowerMw / series.length;
    const energyMwh = (avgMw * series.length) / 1; // 简化：按小时均值近似 MWh
    const totalCo2Ton =
      Math.round(((energyMwh * task.co2Counts) / 1000) * 1000) / 1000;

    let startCount = 0;
    let shutdownCount = 0;
    for (let t = 0; t < series.length; t++) {
      const prevOn = t > 0 ? series[t - 1].p > 0 : false;
      const curOn = series[t].p > 0;
      if (!prevOn && curOn) startCount += 1;
      if (prevOn && !curOn) shutdownCount += 1;
    }

    const startCostYuan = Math.round(startCount * task.startCosts * (0.95 + rnd() * 0.1));
    const shutdownCostYuan = Math.round(shutdownCount * task.endCosts * (0.95 + rnd() * 0.1));
    const fuelCostYuan = Math.round(energyMwh * task.fuelCosts * (0.96 + rnd() * 0.08));
    const totalCostYuan = startCostYuan + shutdownCostYuan + fuelCostYuan;
    rows.push({
      index: i + 1,
      totalPowerMw,
      totalCo2Ton,
      totalCostYuan,
      startCostYuan,
      shutdownCostYuan,
      fuelCostYuan,
      series,
    });
  }
  return rows;
}

export type TaskResultLookup =
  | { ok: true; data: TaskResultPayload }
  | { ok: false; reason: 'not_found' | 'not_completed' };

export function lookupTaskResult(taskId: string): TaskResultLookup {
  const task = getTask(taskId);
  if (!task) return { ok: false, reason: 'not_found' };
  if (task.status !== 'completed') return { ok: false, reason: 'not_completed' };
  return {
    ok: true,
    data: {
      task,
      validations: buildValidations(task),
      units: buildUnitRows(task),
    },
  };
}

export function buildTaskResult(taskId: string): TaskResultPayload | null {
  const r = lookupTaskResult(taskId);
  return r.ok ? r.data : null;
}

export function taskStatusZh(status: TaskStatus) {
  return statusLabelZh(status);
}
