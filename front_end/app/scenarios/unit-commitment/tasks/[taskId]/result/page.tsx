'use client';

import { useEffect, useMemo, useState } from 'react';
import Image from 'next/image';
import { useParams } from 'next/navigation';
import axios from 'axios';
import { api } from '@/lib/axios-client';
import type { TaskResultPayload } from '@/lib/types';
import { MiniPowerChart } from '@/components/MiniPowerChart';
import styles from './result.module.css';

export default function TaskResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [data, setData] = useState<TaskResultPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<{ data: TaskResultPayload }>(`/api/tasks/${taskId}/result`);
        if (!cancelled) {
          setErr(null);
          setData(res.data.data);
        }
      } catch (e) {
        if (!cancelled) {
          setData(null);
          const code = axios.isAxiosError(e) ? (e.response?.data as { error?: string } | undefined)?.error : undefined;
          if (code === 'not_completed') {
            setErr('该任务尚未执行完成，请先在任务管理页执行并等待状态变为「已完成」后再查看结果。');
          } else if (code === 'not_found') {
            setErr(
              '找不到该任务。开发环境使用内存数据，服务重启后历史链接会失效；请返回「任务管理」从列表重新打开「查看结果」，或使用演示任务「演示任务-华东电网」的查看结果入口。',
            );
          } else {
            setErr('暂无法获取结果，请稍后重试或返回任务列表重新进入。');
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  const title = useMemo(() => '任务结果', []);

  if (!taskId) return null;

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.pageTitle}>{title}</div>

      {err ? <div className={styles.error}>{err}</div> : null}
      {!data && !err ? <div className="muted">加载中…</div> : null}

      {data ? (
        <div className={styles.stack}>
          <section className={styles.section}>
            <div className={styles.sectionTitle}>任务信息 / 约束校验<span className="pass" style={{ marginLeft: 10 }}>通过</span></div>

            <div className={styles.block}>
              <div className={styles.taskNameLine}>
                <span className={styles.infoLabel}>任务名称（name）</span>
                <span className={styles.infoSep}>：</span>
                <span className={styles.strong}>{data.task.name}</span>
              </div>
            </div>

            <div className={styles.block}>
              <div className={styles.subTitle}>基础设置</div>
              <div className={styles.infoGrid}>
                <div className={styles.infoCard}>
                  <span className={styles.infoLabel}>机组数量（counts）</span>
                  <span className={styles.infoSep}>：</span>
                  <span className={styles.infoValue}>{data.task.counts}</span>
                </div>
                <div className={styles.infoCard}>
                  <span className={styles.infoLabel}>调度时段（period）</span>
                  <span className={styles.infoSep}>：</span>
                  <span className={styles.infoValue}>{data.task.period}</span>
                </div>
              </div>
            </div>

            <div className={styles.block}>
              <div className={styles.subTitle}>系统约束</div>
              <div className={styles.infoGrid}>
                {(['targetNeed', 'backNeed', 'co2Limit'] as const).map((k) => {
                  const item = data.validations.find((x) => x.key === k);
                  if (!item) return null;
                  return (
                    <div key={k} className={styles.infoCard}>
                      <div className={styles.infoMain}>
                        <span className={styles.infoLabel}>{item.label}</span>
                        <span className={styles.infoSep}>：</span>
                        <span className={styles.infoValue}>{renderTaskFieldValue(data.task, k)}</span>
                        <span className={item.pass ? 'pass' : 'fail'}>{item.pass ? '通过' : '不通过'}</span>
                      </div>
                      {!item.pass && item.reason ? (
                        <div className={`reason ${styles.infoReason}`}>{item.reason}</div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className={styles.block}>
              <div className={styles.subTitle}>单机组约束</div>
              <div className={styles.infoGrid}>
                {data.validations
                  .filter((x) =>
                    [
                      'minOutput',
                      'maxOutput',
                      'changeOimit',
                      'startAndEndTime',
                      'co2Counts',
                      'startCosts',
                      'endCosts',
                      'fuelCosts',
                    ].includes(x.key),
                  )
                  .map((item) => (
                    <div key={item.key} className={styles.infoCard}>
                      <div className={styles.infoMain}>
                        <span className={styles.infoLabel}>{item.label}</span>
                        <span className={styles.infoSep}>：</span>
                        <span className={styles.infoValue}>{renderTaskFieldValue(data.task, item.key)}</span>
                        <span className={item.pass ? 'pass' : 'fail'}>{item.pass ? '通过' : '不通过'}</span>
                      </div>
                      {!item.pass && item.reason ? (
                        <div className={`reason ${styles.infoReason}`}>{item.reason}</div>
                      ) : null}
                    </div>
                  ))}
              </div>
            </div>

            <div className={styles.legend}>
              <span className="pass">通过</span>
              <span className="muted">使用绿色字体展示；</span>
              <span className="fail">不通过</span>
              <span className="muted">使用红色字体展示，原因见黑色描述语义（本页为深色底，使用浅色可读文本）。</span>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>结果明细</div>

            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <colgroup>
                  <col className={styles.colIdx} />
                  <col className={styles.colThumb} />
                  <col className={styles.colEnergy} />
                  <col className={styles.colCost} />
                  <col className={styles.colChart} />
                </colgroup>
                <thead>
                  <tr>
                    <th>编号</th>
                    <th>发电机组图片</th>
                    <th>能耗</th>
                    <th>成本明细</th>
                    <th>功率时序图</th>
                  </tr>
                </thead>
                <tbody>
                  {data.units.map((u) => (
                    <tr key={u.index}>
                      <td className={styles.tdIdx}>{u.index}</td>
                      <td className={styles.tdThumb}>
                        <div className={styles.thumb}>
                          <Image
                            src="/imgs/power_egine.gif"
                            alt="发电机组"
                            width={120}
                            height={88}
                            unoptimized
                          />
                        </div>
                      </td>
                      <td className={styles.tdStack}>
                        <div className={styles.stackLines}>
                          发电量：{u.totalPowerMw} MW
                          <br />
                          碳排放：{u.totalCo2Ton} 吨
                          <br />
                          总成本：{u.totalCostYuan} 元
                        </div>
                      </td>
                      <td className={styles.tdStack}>
                        <div className={styles.stackLines}>
                          启动：{u.startCostYuan} 元
                          <br />
                          关停：{u.shutdownCostYuan} 元
                          <br />
                          燃料：{u.fuelCostYuan} 元
                        </div>
                      </td>
                      <td className={styles.tdChart}>
                        <div className={styles.chartCell} style={{ paddingTop: '10px'}}>
                          <MiniPowerChart
                            data={u.series}
                            minRef={data.task.minOutput}
                            maxRef={data.task.maxOutput}
                            height={110}
                          />
                        </div>
                      </td>
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

function renderTaskFieldValue(task: TaskResultPayload['task'], key: string) {
  if (key === 'targetNeed') return `${task.targetNeed} MW`;
  if (key === 'backNeed') return `${task.backNeed} MW`;
  if (key === 'co2Limit') return `${task.co2Limit} 吨/天`;
  if (key === 'minOutput') return `${task.minOutput} MW`;
  if (key === 'maxOutput') return `${task.maxOutput} MW`;
  if (key === 'changeOimit') return `${task.changeOimit} MW/min`;
  if (key === 'startAndEndTime') return `${task.startAndEndTime}`;
  if (key === 'co2Counts') return `${task.co2Counts} 吨CO2/MWh`;
  if (key === 'startCosts') return `${task.startCosts} 元`;
  if (key === 'endCosts') return `${task.endCosts} 元`;
  if (key === 'fuelCosts') return `${task.fuelCosts} 元/MWh`;
  return '';
}
