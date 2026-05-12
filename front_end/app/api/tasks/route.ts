import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { createTask, listTasks } from '@/lib/task-store';
import type { TaskPayload } from '@/lib/types';

export async function GET() {
  await connectMongo().catch(() => null);
  return NextResponse.json({ data: listTasks() });
}

export async function POST(req: Request) {
  await connectMongo().catch(() => null);
  const body = (await req.json()) as TaskPayload;
  const task = createTask(body);
  return NextResponse.json({ data: task });
}
