import mongoose from 'mongoose';

/**
 * MongoDB 连接占位：配置 MONGODB_URI 后会在首次调用时尝试连接。
 * 当前业务数据仍走内存假数据，不做集合初始化与迁移。
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
