import { randomUUID } from 'crypto';
import { mkdir, writeFile } from 'fs/promises';
import path from 'path';
import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { importTaskResult } from '@/lib/task-store';

type Ctx = { params: Promise<{ id: string }> };

async function saveFiles(files: File[], folder: string): Promise<string[]> {
  const outDir = path.join(process.cwd(), 'app', 'upload_img');
  await mkdir(outDir, { recursive: true });
  const urls: string[] = [];
  for (const f of files) {
    const ext = path.extname(f.name || '') || '.png';
    const fileName = `${folder}-${Date.now()}-${randomUUID()}${ext}`;
    const abs = path.join(outDir, fileName);
    const buf = Buffer.from(await f.arrayBuffer());
    await writeFile(abs, buf);
    urls.push(`/api/upload-img/${fileName}`);
  }
  return urls;
}

export async function POST(req: Request, ctx: Ctx) {
  await connectMongo().catch(() => null);
  const { id } = await ctx.params;
  try {
    const form = await req.formData();
    const rawJson = String(form.get('rawJson') ?? '');
    if (!rawJson) return NextResponse.json({ error: 'missing_raw_json' }, { status: 400 });
    JSON.parse(rawJson);

    const runningFiles = form
      .getAll('runningImages')
      .filter((x): x is File => x instanceof File && x.size > 0);
    const compareFiles = form
      .getAll('compareImages')
      .filter((x): x is File => x instanceof File && x.size > 0);

    const runningUrls = await saveFiles(runningFiles, id);
    const compareUrls = await saveFiles(compareFiles, id);

    const ok = await importTaskResult(id, rawJson, runningUrls, compareUrls);
    if (!ok) return NextResponse.json({ error: 'cannot_import' }, { status: 400 });
    return NextResponse.json({ ok: true, runningUrls, compareUrls });
  } catch {
    return NextResponse.json({ error: 'invalid_json_or_upload' }, { status: 400 });
  }
}
