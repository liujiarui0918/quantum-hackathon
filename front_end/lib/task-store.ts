import { randomUUID } from 'crypto';
import { connectMongo } from '@/lib/mongodb';
import { MiqpResult } from '@/lib/models/miqp-result';
import { MiqpTask } from '@/lib/models/miqp-task';
import type { IterationResultRow, Task, TaskPayload, TaskResultPayload, TaskStatus, ValidationItem } from './types';

const memTasks = new Map<string, Task>();
const completeTimers = new Map<string, ReturnType<typeof setTimeout>>();

function nowIso() {
  return new Date().toISOString();
}

function seedMem() {
  if (memTasks.size > 0) return;
  const base: TaskPayload = {
    name: '演示任务-miqp_sample_A',
    datasetName: 'miqp_sample_A.npz',
    n: 15,
    p: 5,
    m1: 5,
    m2: 1,
    solver: 'hybrid',
    maxQubits: 20,
    subQuboSize: 12,
    maxIterations: 12,
    timeLimitSec: 120,
    penaltyLambda: 8,
  };
  memTasks.set('demo-seed-completed', { id: 'demo-seed-completed', ...base, status: 'completed', createdAt: nowIso() });
  memTasks.set('demo-seed-pending', {
    id: 'demo-seed-pending',
    ...base,
    name: '演示任务-未执行',
    datasetName: 'miqp_sample_B.npz',
    n: 80,
    p: 20,
    m1: 20,
    m2: 4,
    subQuboSize: 18,
    status: 'pending',
    createdAt: nowIso(),
  });
}

function clearTimer(id: string) {
  const t = completeTimers.get(id);
  if (t) clearTimeout(t);
  completeTimers.delete(id);
}

function scheduleComplete(id: string) {
  clearTimer(id);
  const timer = setTimeout(async () => {
    await setTaskStatus(id, 'completed');
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

function normalizeTaskDoc(doc: Record<string, unknown>): Task {
  return {
    id: String(doc.id ?? ''),
    status: (doc.status as TaskStatus) ?? 'pending',
    createdAt: String(doc.createdAt ?? nowIso()),
    name: String(doc.name ?? ''),
    datasetName: String(doc.datasetName ?? ''),
    n: Number(doc.n ?? 0),
    p: Number(doc.p ?? 0),
    m1: Number(doc.m1 ?? 0),
    m2: Number(doc.m2 ?? 0),
    solver: (doc.solver as TaskPayload['solver']) ?? 'hybrid',
    maxQubits: Number(doc.maxQubits ?? 20),
    subQuboSize: Number(doc.subQuboSize ?? 12),
    maxIterations: Number(doc.maxIterations ?? 12),
    timeLimitSec: Number(doc.timeLimitSec ?? 120),
    penaltyLambda: Number(doc.penaltyLambda ?? 8),
  };
}

async function getMongoTasks(): Promise<Task[] | null> {
  const conn = await connectMongo();
  if (!conn) return null;
  const rows = await MiqpTask.find().sort({ createdAt: -1 }).lean().exec();
  return rows.map((x) => normalizeTaskDoc(x as Record<string, unknown>));
}

async function getMongoTask(id: string): Promise<Task | null> {
  const conn = await connectMongo();
  if (!conn) return null;
  const row = await MiqpTask.findOne({ id }).lean().exec();
  if (!row) return null;
  return normalizeTaskDoc(row as Record<string, unknown>);
}

async function setTaskStatus(id: string, status: TaskStatus): Promise<boolean> {
  const conn = await connectMongo();
  if (conn) {
    const r = await MiqpTask.updateOne({ id }, { $set: { status, updatedAt: nowIso() } }).exec();
    return r.matchedCount > 0;
  }
  seedMem();
  const cur = memTasks.get(id);
  if (!cur) return false;
  memTasks.set(id, { ...cur, status });
  return true;
}

export async function listTasks(): Promise<Task[]> {
  const mongoRows = await getMongoTasks();
  if (mongoRows) {
    if (mongoRows.length > 0) return mongoRows;
    return [];
  }
  seedMem();
  return Array.from(memTasks.values()).sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt));
}

export async function getTask(id: string): Promise<Task | null> {
  const mongoRow = await getMongoTask(id);
  if (mongoRow) return mongoRow;
  seedMem();
  return memTasks.get(id) ?? null;
}

export async function createTask(payload: TaskPayload): Promise<Task> {
  const id = randomUUID();
  const createdAt = nowIso();
  const task: Task = { id, ...payload, status: 'pending', createdAt };
  const conn = await connectMongo();
  if (conn) {
    await MiqpTask.create({ ...task, updatedAt: createdAt });
    return task;
  }
  seedMem();
  memTasks.set(id, task);
  return task;
}

export async function updateTask(id: string, payload: TaskPayload): Promise<Task | null> {
  const conn = await connectMongo();
  if (conn) {
    const cur = (await MiqpTask.findOne({ id }).lean().exec()) as Record<string, unknown> | null;
    if (!cur || cur.status !== 'pending') return null;
    await MiqpTask.updateOne({ id }, { $set: { ...payload, updatedAt: nowIso() } }).exec();
    const next = await MiqpTask.findOne({ id }).lean().exec();
    return next ? normalizeTaskDoc(next as Record<string, unknown>) : null;
  }

  seedMem();
  const cur = memTasks.get(id);
  if (!cur || cur.status !== 'pending') return null;
  const next: Task = { ...cur, ...payload, id: cur.id, createdAt: cur.createdAt };
  memTasks.set(id, next);
  return next;
}

export async function executeTask(id: string): Promise<boolean> {
  const task = await getTask(id);
  if (!task || task.status !== 'pending') return false;
  const ok = await setTaskStatus(id, 'running');
  if (ok) scheduleComplete(id);
  return ok;
}

export async function terminateTask(id: string): Promise<boolean> {
  const task = await getTask(id);
  if (!task || task.status !== 'running') return false;
  clearTimer(id);
  return setTaskStatus(id, 'pending');
}

export function buildValidations(task: Task): ValidationItem[] {
  const v = (key: string, label: string, pass: boolean, reason: string): ValidationItem => ({
    key,
    label,
    pass,
    reason: pass ? undefined : reason,
  });

  return [
    v('qubit_limit', '量子比特上限（<=30）', task.maxQubits <= 30, '单次调用超过 30 比特会触发一票否决'),
    v('subqubo_size', 'subQUBO 建议规模（<=20）', task.subQuboSize <= 20, '建议每个 subQUBO 控制在 20 比特以内'),
    v('mixed_constraints', '混合约束维度有效', task.m1 > 0 && task.m1 <= 500, 'm1 需为正且在合理范围'),
    v('binary_constraints', '纯二元约束维度有效', task.m2 >= 0 && task.m2 <= 200, 'm2 需为非负且在合理范围'),
    v('solver_mode', '量子求解模式有效', ['qaoa', 'annealing', 'hybrid'].includes(task.solver), 'solver 需为 qaoa/annealing/hybrid'),
  ];
}

function buildIterations(task: Task): IterationResultRow[] {
  const rnd = mulberry32(hashSeed(task.id, 11));
  const total = Math.max(4, Math.min(40, task.maxIterations));
  const rows: IterationResultRow[] = [];

  let obj = 1000 + task.n * 15 + task.p * 10;
  let bestBound = obj * 1.12;
  let elapsed = 0;
  for (let i = 1; i <= total; i++) {
    const improve = 0.88 + rnd() * 0.06;
    obj *= improve;
    bestBound *= 0.91 + rnd() * 0.05;
    const gapPct = Math.max(0.1, ((obj - bestBound) / Math.max(1, Math.abs(obj))) * 100);
    elapsed += 2 + rnd() * 5;
    rows.push({
      iter: i,
      objective: Math.round(obj * 1000) / 1000,
      bestBound: Math.round(bestBound * 1000) / 1000,
      gapPct: Math.round(Math.abs(gapPct) * 100) / 100,
      feasible: i > 1 || rnd() > 0.25,
      usedQubits: Math.min(task.maxQubits, Math.max(8, task.subQuboSize + Math.floor(rnd() * 4) - 1)),
      elapsedSec: Math.round(elapsed * 100) / 100,
      note: i % 3 === 0 ? '生成新割平面' : undefined,
    });
  }
  return rows;
}

function buildMockResult(task: Task): TaskResultPayload {
  const iterations = buildIterations(task);
  const last = iterations[iterations.length - 1];
  const violations = buildValidations(task).filter((x) => !x.pass).length;
  return {
    task,
    validations: buildValidations(task),
    summary: {
      bestObjective: last.objective,
      bestBound: last.bestBound,
      gapPct: last.gapPct,
      feasible: iterations.some((x) => x.feasible),
      constraintViolationCount: violations,
      usedQubits: Math.max(...iterations.map((x) => x.usedQubits)),
      selectedBinaryCount: Math.max(1, Math.round(task.n * 0.28)),
      activeContinuousCount: Math.max(1, Math.round(task.p * 0.65)),
      totalRuntimeSec: last.elapsedSec,
    },
    iterations,
    artifacts: [],
    notes: '当前为前端演示结果。接入生产后将直接展示 MongoDB 写入的真实结果与示意图。',
  };
}

function parseMongoResultPayload(raw: Record<string, unknown>, task: Task): TaskResultPayload {
  const payload = (raw.payload ?? raw) as Record<string, unknown>;
  const summary = (payload.summary ?? {}) as Record<string, unknown>;
  const validations = Array.isArray(payload.validations) ? (payload.validations as ValidationItem[]) : [];
  const iterations = Array.isArray(payload.iterations) ? (payload.iterations as IterationResultRow[]) : [];
  const artifacts = Array.isArray(payload.artifacts)
    ? (payload.artifacts as Array<Record<string, unknown>>).map((x) => ({
        title: String(x.title ?? '结果图'),
        imageUrl: String(x.imageUrl ?? x.url ?? ''),
        description: x.description ? String(x.description) : undefined,
      }))
    : [];

  return {
    task,
    validations,
    summary: {
      bestObjective: Number(summary.bestObjective ?? 0),
      bestBound: summary.bestBound !== undefined ? Number(summary.bestBound) : undefined,
      gapPct: summary.gapPct !== undefined ? Number(summary.gapPct) : undefined,
      feasible: Boolean(summary.feasible ?? true),
      constraintViolationCount: Number(summary.constraintViolationCount ?? 0),
      usedQubits: Number(summary.usedQubits ?? task.maxQubits),
      selectedBinaryCount: Number(summary.selectedBinaryCount ?? Math.round(task.n * 0.25)),
      activeContinuousCount: Number(summary.activeContinuousCount ?? Math.round(task.p * 0.6)),
      totalRuntimeSec: Number(summary.totalRuntimeSec ?? 0),
    },
    iterations,
    artifacts: artifacts.filter((x) => x.imageUrl),
    notes: payload.notes ? String(payload.notes) : undefined,
  };
}

export type TaskResultLookup =
  | { ok: true; data: TaskResultPayload }
  | { ok: false; reason: 'not_found' | 'not_completed' };

export async function lookupTaskResult(taskId: string): Promise<TaskResultLookup> {
  const task = await getTask(taskId);
  if (!task) return { ok: false, reason: 'not_found' };

  const conn = await connectMongo();
  if (conn) {
    const row = await MiqpResult.findOne({ taskId }).lean().exec();
    if (row) {
      return { ok: true, data: parseMongoResultPayload(row as Record<string, unknown>, task) };
    }
  }

  if (task.status !== 'completed') return { ok: false, reason: 'not_completed' };
  return { ok: true, data: buildMockResult(task) };
}

export function taskStatusZh(status: TaskStatus) {
  if (status === 'pending') return '未执行';
  if (status === 'running') return '执行中';
  return '已完成';
}
