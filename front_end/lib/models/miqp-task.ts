import { Schema, model, models } from 'mongoose';
import type { TaskPayload, TaskStatus } from '@/lib/types';
import type { DatasetExecParams } from '@/lib/dataset-exec-config';

export interface MiqpTaskDoc extends TaskPayload {
  id: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
  execParam?: DatasetExecParams | null;
  result?: unknown;
}

const MiqpTaskSchema = new Schema<MiqpTaskDoc>(
  {
    id: { type: String, required: true, unique: true, index: true },
    status: { type: String, required: true, enum: ['pending', 'running', 'completed'], default: 'pending' },
    createdAt: { type: String, required: true },
    updatedAt: { type: String, required: true },
    execParam: { type: Schema.Types.Mixed, required: false },
    result: { type: Schema.Types.Mixed, required: false },

    name: { type: String, required: true },
    datasetName: { type: String, required: true },
    n: { type: Number, required: true },
    p: { type: Number, required: true },
    m1: { type: Number, required: true },
    m2: { type: Number, required: true },
    solver: { type: String, required: true, enum: ['qaoa', 'annealing', 'hybrid'] },
    maxQubits: { type: Number, required: true },
    subQuboSize: { type: Number, required: true },
    maxIterations: { type: Number, required: true },
    timeLimitSec: { type: Number, required: true },
    penaltyLambda: { type: Number, required: true },
  },
  {
    collection: 'task',
    versionKey: false,
  },
);

export const MiqpTask = models.MiqpTask || model<MiqpTaskDoc>('MiqpTask', MiqpTaskSchema);
