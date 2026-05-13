import mongoose from 'mongoose';

/**
 * MongoDB：在 `MONGODB_URI` 存在时建立连接（供如 /api/test-data 等路由使用）。
 * Docker root 认证示例：
 * mongodb://admin:123456@127.0.0.1:27017/quantum_hackathon?authSource=admin
 */
const globalForMongoose = globalThis as unknown as {
  mongooseConn: typeof mongoose | null;
  mongoosePromise: Promise<typeof mongoose> | null;
};

export async function connectMongo(): Promise<typeof mongoose | null> {
  const uri = process.env.MONGODB_URI;
  if (!uri) return null;

  if (globalForMongoose.mongooseConn) return globalForMongoose.mongooseConn;
  if (!globalForMongoose.mongoosePromise) {
    globalForMongoose.mongoosePromise = mongoose.connect(uri).then(() => mongoose);
  }
  globalForMongoose.mongooseConn = await globalForMongoose.mongoosePromise;
  return globalForMongoose.mongooseConn;
}
