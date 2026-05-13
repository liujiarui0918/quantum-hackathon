import mongoose from 'mongoose';

/** 测试集合 `test_data`：业务字段 id / user / type */
const testDataSchema = new mongoose.Schema(
  {
    id: { type: String, required: true },
    user: { type: String, required: true },
    type: { type: String, required: true },
  },
  { collection: 'test_data' },
);

testDataSchema.index({ id: 1 }, { unique: true });

export const TestData = mongoose.models.TestData ?? mongoose.model('TestData', testDataSchema);
