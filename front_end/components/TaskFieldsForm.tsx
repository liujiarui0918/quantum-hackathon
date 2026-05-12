'use client';

import type { ReactNode } from 'react';
import type { TaskPayload } from '@/lib/types';
import styles from './task-form.module.css';

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className={styles.field}>
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

  return (
    <div className={styles.grid}>
      <section className={styles.section}>
        <h3 className={styles.h3}>任务名称</h3>
        <Field label="任务名称（name）">
          <input
            className={styles.input}
            value={value.name}
            disabled={ro}
            onChange={(e) => patch({ name: e.target.value })}
            placeholder="请输入任务名称"
          />
        </Field>
      </section>

      <section className={styles.section}>
        <h3 className={styles.h3}>基础设置</h3>
        <div className={styles.row2}>
          <Field label="机组数量（counts）">
            <input
              className={styles.input}
              type="number"
              min={1}
              max={24}
              value={value.counts}
              disabled={ro}
              onChange={(e) => patch({ counts: Number(e.target.value) })}
            />
          </Field>
          <Field label="调度时段（period）">
            <select
              className={styles.select}
              value={value.period}
              disabled={ro}
              onChange={(e) => patch({ period: e.target.value })}
            >
              <option value="24小时">24小时</option>
              <option value="48小时">48小时</option>
            </select>
          </Field>
        </div>
      </section>

      <section className={styles.section}>
        <h3 className={styles.h3}>系统约束</h3>
        <div className={styles.row3}>
          <Field label="目标负荷需求（targetNeed，MW）">
            <input
              className={styles.input}
              type="number"
              value={value.targetNeed}
              disabled={ro}
              onChange={(e) => patch({ targetNeed: Number(e.target.value) })}
            />
          </Field>
          <Field label="备用容量上限（backNeed，MW）">
            <input
              className={styles.input}
              type="number"
              value={value.backNeed}
              disabled={ro}
              onChange={(e) => patch({ backNeed: Number(e.target.value) })}
            />
          </Field>
          <Field label="碳排放限额（co2Limit，吨/天）">
            <input
              className={styles.input}
              type="number"
              value={value.co2Limit}
              disabled={ro}
              onChange={(e) => patch({ co2Limit: Number(e.target.value) })}
            />
          </Field>
        </div>
      </section>

      <section className={styles.section}>
        <h3 className={styles.h3}>单机组约束</h3>
        <div className={styles.row2}>
          <Field label="最小输出（minOutput，10-99 MW）">
            <input
              className={styles.range}
              type="range"
              min={10}
              max={99}
              value={value.minOutput}
              disabled={ro}
              onChange={(e) => patch({ minOutput: Number(e.target.value) })}
            />
            <span className={styles.rangeVal}>{value.minOutput} MW</span>
          </Field>
          <Field label="最大输出（maxOutput，100-600 MW）">
            <input
              className={styles.range}
              type="range"
              min={100}
              max={600}
              value={value.maxOutput}
              disabled={ro}
              onChange={(e) => patch({ maxOutput: Number(e.target.value) })}
            />
            <span className={styles.rangeVal}>{value.maxOutput} MW</span>
          </Field>
        </div>

        <div className={styles.row2}>
          <Field label="爬坡限制（changeOimit，5-20 MW/min）">
            <input
              className={styles.range}
              type="range"
              min={5}
              max={20}
              value={value.changeOimit}
              disabled={ro}
              onChange={(e) => patch({ changeOimit: Number(e.target.value) })}
            />
            <span className={styles.rangeVal}>{value.changeOimit} MW/min</span>
          </Field>
          <Field label="启停时间（startAndEndTime）">
            <select
              className={styles.select}
              value={value.startAndEndTime}
              disabled={ro}
              onChange={(e) => patch({ startAndEndTime: e.target.value })}
            >
              <option value="15分钟">15分钟</option>
              <option value="30分钟">30分钟</option>
              <option value="60分钟">60分钟</option>
            </select>
          </Field>
        </div>

        <div className={styles.row2}>
          <Field label="碳排放量（co2Counts，0.6-1.2 吨CO2/MWh）">
            <input
              className={styles.range}
              type="range"
              min={60}
              max={120}
              step={1}
              value={Math.round(value.co2Counts * 100)}
              disabled={ro}
              onChange={(e) => patch({ co2Counts: Number(e.target.value) / 100 })}
            />
            <span className={styles.rangeVal}>{value.co2Counts.toFixed(2)} 吨CO2/MWh</span>
          </Field>
          <Field label="启动成本（startCosts，2000-10000 元）">
            <input
              className={styles.range}
              type="range"
              min={2000}
              max={10000}
              step={50}
              value={value.startCosts}
              disabled={ro}
              onChange={(e) => patch({ startCosts: Number(e.target.value) })}
            />
            <span className={styles.rangeVal}>{value.startCosts} 元</span>
          </Field>
        </div>

        <div className={styles.row2}>
          <Field label="关停成本（endCosts，500-2000 元）">
            <input
              className={styles.range}
              type="range"
              min={500}
              max={2000}
              step={10}
              value={value.endCosts}
              disabled={ro}
              onChange={(e) => patch({ endCosts: Number(e.target.value) })}
            />
            <span className={styles.rangeVal}>{value.endCosts} 元</span>
          </Field>
          <Field label="燃料成本（fuelCosts，200-600 元/MWh）">
            <input
              className={styles.range}
              type="range"
              min={200}
              max={600}
              step={5}
              value={value.fuelCosts}
              disabled={ro}
              onChange={(e) => patch({ fuelCosts: Number(e.target.value) })}
            />
            <span className={styles.rangeVal}>{value.fuelCosts} 元/MWh</span>
          </Field>
        </div>
      </section>
    </div>
  );
}

export function emptyTaskPayload(): TaskPayload {
  return {
    name: '',
    counts: 2,
    period: '24小时',
    targetNeed: 800,
    backNeed: 150,
    co2Limit: 600,
    minOutput: 40,
    maxOutput: 300,
    changeOimit: 10,
    startAndEndTime: '30分钟',
    co2Counts: 0.8,
    startCosts: 4000,
    endCosts: 800,
    fuelCosts: 350,
  };
}
