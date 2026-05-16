import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { getTask, updateTask } from '@/lib/task-store';
import type { TaskPayload } from '@/lib/types';

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_: Request, ctx: Ctx) {
  await connectMongo().catch(() => null);
  const { id } = await ctx.params;
  const task = await getTask(id);
  if (!task) return NextResponse.json({ error: 'not_found' }, { status: 404 });
  return NextResponse.json({ data: task });
}

export async function PUT(req: Request, ctx: Ctx) {
  await connectMongo().catch(() => null);
  const { id } = await ctx.params;
  const body = (await req.json()) as TaskPayload;
  const task = await updateTask(id, body);
  if (!task) return NextResponse.json({ error: 'forbidden_or_not_found' }, { status: 400 });
  return NextResponse.json({ data: task });
}
