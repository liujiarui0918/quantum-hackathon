import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { TestItem } from '@/lib/models/test-item';

/**
 * GET /api/test-items
 * 返回集合 test_items 中全部文档的 id、name、type。
 *
 * 本地准备数据（任选其一）：
 * 1) mongosh：
 *    use quantum_hackathon
 *    db.test_items.insertMany([
 *      { id: "1", name: "Alpha", type: "demo" },
 *      { id: "2", name: "Beta", type: "demo" },
 *      { id: "3", name: "Gamma", type: "trial" },
 *    ])
 * 2) 配置 .env.local 中 MONGODB_URI=mongodb://127.0.0.1:27017/quantum_hackathon 后启动 next dev
 */
export async function GET() {
  if (!process.env.MONGODB_URI) {
    return NextResponse.json(
      { error: 'missing_env', message: '请在 .env.local 中设置 MONGODB_URI（例如 mongodb://127.0.0.1:27017/quantum_hackathon）' },
      { status: 503 },
    );
  }

  try {
    const conn = await connectMongo();
    if (!conn) {
      return NextResponse.json({ error: 'no_connection', message: '未能连接 MongoDB' }, { status: 503 });
    }
    const rows = await TestItem.find().sort({ id: 1 }).lean().exec();
    const data = rows.map((doc) => ({
      id: doc.id,
      name: doc.name,
      type: doc.type,
    }));
    return NextResponse.json({ data });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'unknown_error';
    return NextResponse.json({ error: 'query_failed', message }, { status: 500 });
  }
}
