import { randomUUID } from 'crypto';
import { connectMongo } from '@/lib/mongodb';
import { MiqpTask } from '@/lib/models/miqp-task';
import type { Task, TaskPayload, TaskResultPayload, TaskStatus } from './types';

function nowIso() {
  return new Date().toISOString();
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
    result: (doc.result ?? null) as Task['result'],
  };
}

async function ensureMongo() {
  const conn = await connectMongo();
  if (!conn) throw new Error('MongoDB 未连接');
}

export async function listTasks(): Promise<Task[]> {
  await ensureMongo();
  const rows = await MiqpTask.find().sort({ createdAt: -1 }).lean().exec();
  return rows.map((x) => normalizeTaskDoc(x as Record<string, unknown>));
}

export async function getTask(id: string): Promise<Task | null> {
  await ensureMongo();
  const row = await MiqpTask.findOne({ id }).lean().exec();
  if (!row) return null;
  return normalizeTaskDoc(row as Record<string, unknown>);
}

export async function createTask(payload: TaskPayload): Promise<Task> {
  await ensureMongo();
  const createdAt = nowIso();
  const task: Task = {
    id: randomUUID(),
    ...payload,
    status: 'pending',
    createdAt,
    result: null,
  };
  await MiqpTask.create({ ...task, updatedAt: createdAt });
  return task;
}

export async function updateTask(id: string, payload: TaskPayload): Promise<Task | null> {
  await ensureMongo();
  const cur = (await MiqpTask.findOne({ id }).lean().exec()) as Record<string, unknown> | null;
  if (!cur || cur.status !== 'pending') return null;
  await MiqpTask.updateOne({ id }, { $set: { ...payload, updatedAt: nowIso() } }).exec();
  const next = await MiqpTask.findOne({ id }).lean().exec();
  return next ? normalizeTaskDoc(next as Record<string, unknown>) : null;
}

export async function deleteTask(id: string): Promise<boolean> {
  await ensureMongo();
  const r = await MiqpTask.deleteOne({ id }).exec();
  return r.deletedCount > 0;
}

export async function executeTask(id: string): Promise<boolean> {
  await ensureMongo();
  const cur = (await MiqpTask.findOne({ id }).lean().exec()) as Record<string, unknown> | null;
  if (!cur || cur.status !== 'pending') return false;
  const r = await MiqpTask.updateOne({ id }, { $set: { status: 'running', updatedAt: nowIso() } }).exec();
  return r.matchedCount > 0;
}

export async function terminateTask(id: string): Promise<boolean> {
  await ensureMongo();
  const cur = (await MiqpTask.findOne({ id }).lean().exec()) as Record<string, unknown> | null;
  if (!cur || cur.status !== 'running') return false;
  const r = await MiqpTask.updateOne({ id }, { $set: { status: 'pending', updatedAt: nowIso() } }).exec();
  return r.matchedCount > 0;
}

export async function importTaskResult(
  id: string,
  rawJson: string,
  runningImages: string[],
  compareImages: string[],
): Promise<boolean> {
  await ensureMongo();
  const cur = (await MiqpTask.findOne({ id }).lean().exec()) as Record<string, unknown> | null;
  if (!cur || cur.status !== 'running') return false;
  const parsed = JSON.parse(rawJson) as Record<string, unknown>;
  const merged = {
    ...parsed,
    images: {
      runningInfo: runningImages,
      compareInfo: compareImages,
    },
  };
  const r = await MiqpTask.updateOne({ id }, { $set: { result: merged, updatedAt: nowIso() } }).exec();
  return r.matchedCount > 0;
}

export type TaskResultLookup =
  | { ok: true; data: TaskResultPayload }
  | { ok: false; reason: 'not_found' | 'not_completed' };

export async function lookupTaskResult(taskId: string): Promise<TaskResultLookup> {
  const task = await getTask(taskId);
  if (!task) return { ok: false, reason: 'not_found' };
  if (!task.result) return { ok: false, reason: 'not_completed' };
  return { ok: true, data: task.result as TaskResultPayload };
}
