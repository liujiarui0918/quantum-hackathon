'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { buildSchedulingResult, createDemoSchedulingTasks, emptySchedulingPayload } from '@/lib/mock-production';
import type { SchedulingResultPayload } from '@/lib/production-types';
import styles from './result.module.css';

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

export default function ProductionTaskResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [data, setData] = useState<SchedulingResultPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const raw = sessionStorage.getItem(`production-result:${taskId}`);
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as SchedulingResultPayload;
        setData(parsed);
        setErr(null);
        return;
      } catch {
        // ignore and fallback
      }
    }

    const demo = createDemoSchedulingTasks().find((t) => t.id === taskId);
    const fallbackTask =
      demo ??
      ({
        id: taskId,
        ...emptySchedulingPayload(),
        name: `演示任务-${taskId.slice(0, 8)}`,
        status: 'completed',
        createdAt: new Date().toISOString(),
      } as const);
    setData(buildSchedulingResult(fallbackTask));
    setErr(null);
  }, [taskId]);

  const title = useMemo(() => '工业排产调度 - 结果页', []);
  if (!taskId) return null;

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.pageTitle}>{title}</div>
      {err ? <div className={styles.error}>{err}</div> : null}
      {!data && !err ? <div className="muted">加载中…</div> : null}

      {data ? (
        <div className={styles.stack}>
          <section className={styles.section}>
            <div className={styles.sectionTitle}>任务信息 / 约束校验</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>任务名称</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.name}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>订单数</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.orderCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>机器数</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.machineCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>时域</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.horizonHours}h</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>交期紧度</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.dueTightness}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>优先订单占比</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{Math.round(data.task.priorityOrderRatio * 100)}%</span></div>
            </div>
            <div className={styles.legend} style={{ marginTop: 10 }}>
              {data.validations.map((v) => (
                <span key={v.key} style={{ marginRight: 14 }}>
                  <span className={v.pass ? 'pass' : 'fail'}>{v.pass ? '通过' : '不通过'}</span>
                  <span className="muted"> {v.label}</span>
                </span>
              ))}
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>目标函数拆解</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>总订单</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.totalOrders}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>准时交付</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.onTimeOrders}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>延期订单</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.delayedOrders}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>总延期</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.totalDelayHours}h</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>换线次数</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.switchCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>总空闲</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.idleHours}h</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>延期成本</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.delayCost}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>换线成本</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.switchCost}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>空闲成本</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.idleCost}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>目标值</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.objectiveScore}</span></div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>机器排程甘特（简化）</div>
            <div style={{ display: 'grid', gap: 10 }}>
              {data.machineTimelines.map((m) => (
                <div key={m.machineId} className={styles.infoCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <strong>{m.machineId}</strong>
                    <span className="muted">利用率 {pct(m.utilization)} / 换线 {m.switchCount}</span>
                  </div>
                  <div style={{ position: 'relative', border: '1px solid rgba(110,203,255,0.2)', borderRadius: 8, height: 30, overflow: 'hidden', background: 'rgba(6,12,28,0.35)' }}>
                    {m.items.map((it, idx) => {
                      const left = `${(it.start / data.task.horizonHours) * 100}%`;
                      const width = `${Math.max(1, (it.duration / data.task.horizonHours) * 100)}%`;
                      return (
                        <div
                          key={it.orderId + idx}
                          title={`${it.orderId} ${it.start}h-${it.end}h`}
                          style={{
                            position: 'absolute',
                            left,
                            top: 3,
                            width,
                            height: 24,
                            borderRadius: 4,
                            border: it.switched ? '1px solid rgba(255, 183, 77, 0.85)' : '1px solid rgba(61,255,206,0.55)',
                            background: it.switched ? 'rgba(255, 183, 77, 0.22)' : 'rgba(61,255,206,0.2)',
                            overflow: 'hidden',
                            fontSize: 10,
                            lineHeight: '22px',
                            textAlign: 'center',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {it.orderId}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>订单分配明细</div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>订单</th>
                    <th>机器</th>
                    <th>序位</th>
                    <th>开始</th>
                    <th>结束</th>
                    <th>交期</th>
                    <th>延期</th>
                    <th>换线</th>
                  </tr>
                </thead>
                <tbody>
                  {data.assignments.map((a) => (
                    <tr key={a.orderId + a.machineId + a.sequence}>
                      <td>{a.orderId}</td>
                      <td>{a.machineId}</td>
                      <td>{a.sequence}</td>
                      <td>{a.start}h</td>
                      <td>{a.end}h</td>
                      <td>{a.due}h</td>
                      <td className={a.lateness > 0 ? 'fail' : 'pass'}>{a.lateness}h</td>
                      <td>{a.switched ? '是' : '否'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
