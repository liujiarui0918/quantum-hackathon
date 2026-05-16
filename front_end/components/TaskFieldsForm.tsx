'use client';

import type { ReactNode } from 'react';
import type { TaskPayload } from '@/lib/types';
import styles from './task-form.module.css';

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={className ? `${styles.field} ${className}` : styles.field}>
      <span className={styles.label}>{label}</span>
      {children}
    </label>
  );
}

export function TaskFieldsForm({
  value,
  onChange,
  readOnly,
}: {
  value: TaskPayload;
  onChange: (next: TaskPayload) => void;
  readOnly?: boolean;
}) {
  const ro = readOnly ?? false;
  const patch = (p: Partial<TaskPayload>) => onChange({ ...value, ...p });

  const applyDatasetPreset = (datasetName: string) => {
    if (datasetName === 'miqp_sample_A.npz' || datasetName === 'miqp_test_1.npz') {
      patch({ datasetName, n: 15, p: 5, m1: 5, m2: 1, subQuboSize: 12, maxQubits: 20 });
      return;
    }
    if (datasetName === 'miqp_sample_B.npz' || datasetName === 'miqp_test_3.npz') {
      patch({ datasetName, n: 80, p: 20, m1: 20, m2: 4, subQuboSize: 18, maxQubits: 24 });
      return;
    }
    if (datasetName === 'miqp_test_2.npz') {
      patch({ datasetName, n: 40, p: 10, m1: 10, m2: 2, subQuboSize: 16, maxQubits: 22 });
      return;
    }
    if (datasetName === 'miqp_test_4.npz') {
      patch({ datasetName, n: 120, p: 30, m1: 30, m2: 6, subQuboSize: 20, maxQubits: 28 });
      return;
    }
    if (datasetName === 'miqp_test_5.npz') {
      patch({ datasetName, n: 150, p: 50, m1: 50, m2: 10, subQuboSize: 20, maxQubits: 30 });
      return;
    }
    patch({ datasetName });
  };

  return (
    <div className={styles.grid}>
      <section className={styles.section}>
        <h3 className={styles.h3}>任务标识</h3>
        <Field label="任务名称（name）">
          <input className={styles.input} value={value.name} disabled={ro} onChange={(e) => patch({ name: e.target.value })} placeholder="请输入任务名称" />
        </Field>
        <Field label="数据集文件（datasetName）" className={styles.fieldSpaced}>
          <select className={styles.select} value={value.datasetName} disabled={ro} onChange={(e) => applyDatasetPreset(e.target.value)}>
            <option value="miqp_sample_A.npz">miqp_sample_A.npz</option>
            <option value="miqp_sample_B.npz">miqp_sample_B.npz</option>
            <option value="miqp_test_1.npz">miqp_test_1.npz</option>
            <option value="miqp_test_2.npz">miqp_test_2.npz</option>
            <option value="miqp_test_3.npz">miqp_test_3.npz</option>
            <option value="miqp_test_4.npz">miqp_test_4.npz</option>
            <option value="miqp_test_5.npz">miqp_test_5.npz</option>
          </select>
        </Field>
      </section>

      <section className={styles.section}>
        <h3 className={styles.h3}>问题规模</h3>
        <div className={styles.row4}>
          <Field label="二元变量 n"><input className={styles.input} type="number" value={value.n} disabled={ro} onChange={(e) => patch({ n: Number(e.target.value) })} /></Field>
          <Field label="连续变量 p"><input className={styles.input} type="number" value={value.p} disabled={ro} onChange={(e) => patch({ p: Number(e.target.value) })} /></Field>
          <Field label="混合约束 m1"><input className={styles.input} type="number" value={value.m1} disabled={ro} onChange={(e) => patch({ m1: Number(e.target.value) })} /></Field>
          <Field label="纯二元约束 m2"><input className={styles.input} type="number" value={value.m2} disabled={ro} onChange={(e) => patch({ m2: Number(e.target.value) })} /></Field>
        </div>
      </section>

      
    </div>
  );
}

export function emptyTaskPayload(): TaskPayload {
  return {
    name: '',
    datasetName: 'miqp_sample_A.npz',
    n: 15,
    p: 5,
    m1: 5,
    m2: 1,
    solver: 'hybrid',
    maxQubits: 20,
    subQuboSize: 12,
    maxIterations: 12,
    timeLimitSec: 120,
    penaltyLambda: 8,
  };
}
