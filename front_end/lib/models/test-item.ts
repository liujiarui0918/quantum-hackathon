import mongoose from 'mongoose';

/** 测试集合 `test_items`：业务字段 id / name / type（文档仍会有 MongoDB 的 _id） */
const testItemSchema = new mongoose.Schema(
  {
    id: { type: String, required: true },
    name: { type: String, required: true },
    type: { type: String, required: true },
  },
  { collection: 'test_items' },
);

testItemSchema.index({ id: 1 }, { unique: true });

export const TestItem = mongoose.models.TestItem ?? mongoose.model('TestItem', testItemSchema);
