import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { terminateTask } from '@/lib/task-store';

type Ctx = { params: Promise<{ id: string }> };

export async function POST(_: Request, ctx: Ctx) {
  await connectMongo().catch(() => null);
  const { id } = await ctx.params;
  const ok = await terminateTask(id);
  if (!ok) return NextResponse.json({ error: 'cannot_terminate' }, { status: 400 });
  return NextResponse.json({ ok: true });
}
