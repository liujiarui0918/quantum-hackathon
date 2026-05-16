import { Schema, model, models } from 'mongoose';

const MiqpResultSchema = new Schema(
  {
    taskId: { type: String, required: true, unique: true, index: true },
    payload: { type: Schema.Types.Mixed, required: true },
    createdAt: { type: String, required: true },
    updatedAt: { type: String, required: true },
  },
  {
    collection: 'miqp_results',
    versionKey: false,
  },
);

export const MiqpResult = models.MiqpResult || model('MiqpResult', MiqpResultSchema);
