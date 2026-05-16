'use client';

import Image from 'next/image';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { buildMockResult, createDemoTasks, emptyTaskPayload } from '@/lib/mock-miqp';
import type { Task, TaskResultPayload } from '@/lib/types';
import styles from './result.module.css';

export default function TaskResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [data, setData] = useState<TaskResultPayload | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const raw = sessionStorage.getItem(`miqp-result:${taskId}`);
    if (raw) {
      try {
        setData(JSON.parse(raw) as TaskResultPayload);
        return;
      } catch {
        // fallback
      }
    }

    const demo = createDemoTasks().find((t) => t.id === taskId);
    const fallbackTask: Task =
      demo ??
      {
        id: taskId,
        ...emptyTaskPayload(),
        name: `演示任务-${taskId.slice(0, 8)}`,
        status: 'completed',
        createdAt: new Date().toISOString(),
      };
    setData(buildMockResult(fallbackTask));
  }, [taskId]);

  const title = useMemo(() => '比赛题结果展示', []);
  if (!taskId) return null;

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.pageTitle}>{title}</div>
      {!data ? <div className="muted">加载中…</div> : null}

      {data ? (
        <div className={styles.stack}>
          <section className={styles.section}>
            <div className={styles.sectionTitle}>任务信息 / 约束校验</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>任务名</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.name}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>数据集</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.datasetName}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>变量规模</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>n={data.task.n}, p={data.task.p}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>约束规模</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>m1={data.task.m1}, m2={data.task.m2}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>求解模式</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.solver}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>比特/分块</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.maxQubits}/{data.task.subQuboSize}</span></div>
            </div>
            <div className={styles.legend}>
              {data.validations.map((v) => (
                <span key={v.key} style={{ marginRight: 12 }}>
                  <span className={v.pass ? 'pass' : 'fail'}>{v.pass ? '通过' : '不通过'}</span>
                  <span className="muted"> {v.label}</span>
                </span>
              ))}
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>求解摘要</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>最优目标</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.bestObjective}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>最优解</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.bestBound ?? '-'}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>Gap</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.gapPct ?? '-'}%</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>可行性</span><span className={styles.infoSep}>：</span><span className={data.summary.feasible ? 'pass' : 'fail'}>{data.summary.feasible ? '可行' : '不可行'}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>违反约束数</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.constraintViolationCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>激活二元变量</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.selectedBinaryCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>激活连续变量</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.activeContinuousCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>总耗时</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.totalRuntimeSec}s</span></div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>迭代过程（示例）</div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>迭代</th>
                    <th>目标值</th>
                    <th>下界</th>
                    <th>Gap%</th>
                    <th>可行</th>
                    <th>比特</th>
                    <th>耗时(s)</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  {data.iterations.map((it) => (
                    <tr key={it.iter}>
                      <td>{it.iter}</td>
                      <td>{it.objective}</td>
                      <td>{it.bestBound ?? '-'}</td>
                      <td>{it.gapPct ?? '-'}</td>
                      <td className={it.feasible ? 'pass' : 'fail'}>{it.feasible ? '是' : '否'}</td>
                      <td>{it.usedQubits}</td>
                      <td>{it.elapsedSec}</td>
                      <td>{it.note ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>运行示意图</div>
            <div className={styles.infoGrid}>
              {data.artifacts.map((x, idx) => (
                <article key={x.title + idx} className={styles.infoCard}>
                  <div className={styles.subTitle} style={{ marginBottom: 8 }}>{x.title}</div>
                  <div className={styles.thumb} style={{ width: '100%', height: 180 }}>
                    <Image src={x.imageUrl} alt={x.title} width={640} height={360} unoptimized />
                  </div>
                  {x.description ? <div className={`reason ${styles.infoReason}`}>{x.description}</div> : null}
                </article>
              ))}
            </div>
            {data.notes ? <div className={styles.legend}>{data.notes}</div> : null}
          </section>
        </div>
      ) : null}
    </main>
  );
}
