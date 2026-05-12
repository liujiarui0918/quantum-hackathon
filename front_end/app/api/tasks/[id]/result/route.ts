import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { lookupTaskResult } from '@/lib/task-store';

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_: Request, ctx: Ctx) {
  await connectMongo().catch(() => null);
  const { id } = await ctx.params;
  const r = lookupTaskResult(id);
  if (!r.ok) {
    if (r.reason === 'not_found') {
      return NextResponse.json({ error: 'not_found' }, { status: 404 });
    }
    return NextResponse.json({ error: 'not_completed' }, { status: 409 });
  }
  return NextResponse.json({ data: r.data });
}
