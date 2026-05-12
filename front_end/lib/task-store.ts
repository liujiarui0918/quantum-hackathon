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

function buildUnitRows(task: Task): UnitResultRow[] {
  const n = Math.max(1, Math.min(12, Math.floor(task.counts)));
  const rows: UnitResultRow[] = [];
  for (let i = 0; i < n; i++) {
    const h = hashSeed(task.id, i + 1);
    const base = 40 + (h % 180);
    const series: { t: string; p: number }[] = [];
    const hours = task.period === '48小时' ? 48 : 24;
    for (let t = 0; t < hours; t++) {
      const wave = Math.sin((t / 6 + i) * 0.9) * 18;
      const noise = ((h >> (t % 5)) & 7) - 3;
      const p = Math.min(
        task.maxOutput,
        Math.max(task.minOutput, base + wave + noise),
      );
      series.push({ t: `${t + 1}h`, p: Math.round(p * 10) / 10 });
    }
    const totalPowerMw = Math.round(series.reduce((s, x) => s + x.p, 0) * 10) / 10;
    const avgMw = totalPowerMw / series.length;
    const energyMwh = (avgMw * series.length) / 1; // 简化：按小时均值近似 MWh
    const totalCo2Ton =
      Math.round(((energyMwh * task.co2Counts) / 1000) * 1000) / 1000;
    const startCostYuan = Math.round(task.startCosts * (0.85 + (h % 20) / 100));
    const shutdownCostYuan = Math.round(task.endCosts * (0.9 + (h % 15) / 100));
    const fuelCostYuan = Math.round(energyMwh * task.fuelCosts * (0.95 + (h % 10) / 200));
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
