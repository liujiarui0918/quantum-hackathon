import { readFile } from 'fs/promises';
import path from 'path';
import { NextResponse } from 'next/server';

type Ctx = { params: Promise<{ path: string[] }> };

const MIME_BY_EXT: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
};

export async function GET(_: Request, ctx: Ctx) {
  const { path: segs } = await ctx.params;
  const name = Array.isArray(segs) ? segs.join('/') : '';
  if (!name || name.includes('/') || name.includes('..')) {
    return NextResponse.json({ error: 'invalid_name' }, { status: 400 });
  }

  const abs = path.join(process.cwd(), 'app', 'upload_img', name);
  try {
    const data = await readFile(abs);
    const ext = path.extname(name).toLowerCase();
    const mime = MIME_BY_EXT[ext] ?? 'application/octet-stream';
    return new NextResponse(data, {
      status: 200,
      headers: {
        'Content-Type': mime,
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  } catch {
    return NextResponse.json({ error: 'not_found' }, { status: 404 });
  }
}
