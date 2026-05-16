import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { buildPythonCommand, runOnJumpHost } from '@/lib/jump-host';
import { markTaskRunning, prepareExecuteTask } from '@/lib/task-store';

type Ctx = { params: Promise<{ id: string }> };

export async function POST(_: Request, ctx: Ctx) {
  await connectMongo().catch(() => null);
  const { id } = await ctx.params;
  console.log('[execute] request task id:', id);

  const prepared = await prepareExecuteTask(id);
  console.log('[execute] prepare result:', prepared.ok ? 'ok' : 'failed');
  if (!prepared.ok || !prepared.execParam) {
    console.log('[execute] missing execParam or task not pending');
    return NextResponse.json({ error: 'cannot_execute' }, { status: 400 });
  }

  try {
    console.log('[execute] build and run command');
    const cmd = buildPythonCommand(prepared.execParam, id);
    const { stdout, stderr } = await runOnJumpHost(cmd);
    console.log('[execute] remote done, stdout length:', stdout?.length ?? 0, 'stderr length:', stderr?.length ?? 0);

    await new Promise((resolve) => setTimeout(resolve, 5000));

    const marked = await markTaskRunning(id);
    console.log('[execute] mark running:', marked ? 'ok' : 'failed');
    if (!marked) {
      return NextResponse.json({ error: 'cannot_mark_running', stdout, stderr }, { status: 409 });
    }

    return NextResponse.json({ ok: true, execParam: prepared.execParam, stdout, stderr });
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'ssh_execute_failed';
    console.log('[execute] error:', msg);
    return NextResponse.json({ error: 'ssh_execute_failed', message: msg }, { status: 500 });
  }
}
