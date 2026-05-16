import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { createTask, listTasks } from '@/lib/task-store';
import type { TaskPayload } from '@/lib/types';

export async function GET(req: Request) {
  await connectMongo().catch(() => null);
  const url = new URL(req.url);
  const n = url.searchParams.get('n');
  const p = url.searchParams.get('p');
  const m1 = url.searchParams.get('m1');
  const m2 = url.searchParams.get('m2');
  const datasetName = url.searchParams.get('datasetName') ?? undefined;

  const data = await listTasks({
    datasetName,
    n: n ? Number(n) : undefined,
    p: p ? Number(p) : undefined,
    m1: m1 ? Number(m1) : undefined,
    m2: m2 ? Number(m2) : undefined,
  });
  return NextResponse.json({ data });
}

export async function POST(req: Request) {
  await connectMongo().catch(() => null);
  const body = (await req.json()) as TaskPayload;
  const task = await createTask(body);
  return NextResponse.json({ data: task });
}
