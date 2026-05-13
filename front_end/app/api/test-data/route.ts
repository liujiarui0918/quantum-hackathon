import { NextResponse } from 'next/server';
import { connectMongo } from '@/lib/mongodb';
import { TestData } from '@/lib/models/test-data';

/**
 * GET /api/test-data
 * 读取集合 `test_data` 全部文档，返回字段 id、user、type。
 *
 * 与 info.md 中 Docker 启动方式（root 用户 admin/123456）对应时，.env.local 示例：
 * — 数据在 admin 库：mongodb://admin:123456@127.0.0.1:27017/admin?authSource=admin
 * — 数据在 quantum_hackathon 库：mongodb://admin:123456@127.0.0.1:27017/quantum_hackathon?authSource=admin
 *
 * 插入示例数据（mongosh，库名与上面一致）：
 * mongosh "mongodb://admin:123456@127.0.0.1:27017/admin?authSource=admin" --eval '
 * db.test_data.insertMany([
 *   { id: "1", user: "alice", type: "alpha" },
 *   { id: "2", user: "bob", type: "beta" }
 * ])'
 */
export async function GET() {
  if (!process.env.MONGODB_URI) {
    return NextResponse.json(
      {
        error: 'missing_env',
        message:
          '请在 front_end/.env.local 中设置 MONGODB_URI（Docker root 示例见本文件注释）',
      },
      { status: 503 },
    );
  }

  try {
    const conn = await connectMongo();
    if (!conn) {
      return NextResponse.json({ error: 'no_connection', message: '未能连接 MongoDB' }, { status: 503 });
    }
    const rows = await TestData.find().sort({ id: 1 }).lean().exec();
    const data = rows.map((doc) => ({
      id: doc.id,
      user: doc.user,
      type: doc.type,
    }));
    return NextResponse.json({ data });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'unknown_error';
    return NextResponse.json({ error: 'query_failed', message }, { status: 500 });
  }
}
