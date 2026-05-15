'use client';

import { useEffect, useMemo, useState } from 'react';
import Image from 'next/image';
import { useParams } from 'next/navigation';
import axios from 'axios';
import { api } from '@/lib/axios-client';
import type { TaskResultPayload } from '@/lib/types';
import type {
  QuantumApiErrorResponse,
  QuantumSampleProblemResponse,
  QuantumSolveResponse,
  QuantumVisualization,
} from '@/lib/quantum-types';
import { MiniPowerChart } from '@/components/MiniPowerChart';
import styles from './result.module.css';

export default function TaskResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [data, setData] = useState<TaskResultPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [quantum, setQuantum] = useState<QuantumVisualization | null>(null);
  const [quantumErr, setQuantumErr] = useState<string | null>(null);
  const [quantumLoading, setQuantumLoading] = useState(false);

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

  useEffect(() => {
    let cancelled = false;
    setQuantumLoading(true);
    setQuantumErr(null);
    (async () => {
      try {
        const sample = await api.get<QuantumSampleProblemResponse>('/api/quantum/sample-problem');
        const solved = await api.post<QuantumSolveResponse>('/api/quantum/solve', {
          problem: sample.data.problem,
          run_options: {
            seed: 7,
            qaoa_max_qubits: 12,
          },
        });
        if (!cancelled) {
          setQuantum(solved.data.visualization);
          setQuantumErr(null);
        }
      } catch (e) {
        if (!cancelled) {
          setQuantum(null);
          setQuantumErr(readQuantumError(e));
        }
      } finally {
        if (!cancelled) setQuantumLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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

          <QuantumResultSection data={quantum} error={quantumErr} loading={quantumLoading} />

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

function QuantumResultSection({ data, error, loading }: { data: QuantumVisualization | null; error: string | null; loading: boolean }) {
  const quantum = data?.quantum;
  const scenario = data?.scenario;
  const best = quantum?.best_solution;
  const benchmarkRows = quantum?.benchmark_rows ?? [];
  const qaoaCircuit = quantum?.qaoa?.circuit;
  const qaoaGateEstimate = qaoaCircuit?.gate_count_estimate;

  return (
    <section className={styles.section}>
      <div className={styles.sectionTitle}>后端量化优化结果<span className={styles.badge}>FastAPI / 本地模拟</span></div>
      {loading ? <div className="muted">正在通过 /api/quantum/solve 获取后端求解结果…</div> : null}
      {error ? <div className={styles.error}>{error}</div> : null}
      {data ? (
        <div className={styles.quantumStack}>
          <div className={styles.quantumGrid}>
            <div className={styles.metricCard}>
              <span className={styles.infoLabel}>问题名称</span>
              <strong>{quantum?.problem?.name ?? scenario?.scenario_id ?? '-'}</strong>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.infoLabel}>最优业务目标</span>
              <strong>{formatNumber(best?.objective_value)}</strong>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.infoLabel}>可行性</span>
              <strong className={best?.is_feasible ? 'pass' : 'fail'}>{best?.is_feasible ? '可行' : '不可行'}</strong>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.infoLabel}>QUBO bits</span>
              <strong>{quantum?.problem?.num_qubo_bits ?? '-'}</strong>
            </div>
          </div>

          <div className={styles.block}>
            <div className={styles.subTitle}>场景映射</div>
            <div className={styles.chipRow}>
              {(scenario?.selected_models ?? []).map((name) => <span key={name} className={styles.chip}>模型：{name}</span>)}
              {(scenario?.enabled_boosts ?? []).map((name) => <span key={name} className={styles.chip}>增强：{name}</span>)}
              {!(scenario?.selected_models?.length || scenario?.enabled_boosts?.length) ? <span className="muted">暂无选中变量</span> : null}
            </div>
          </div>

          <div className={styles.block}>
            <div className={styles.subTitle}>Solver Benchmark</div>
            <div className={styles.benchmarkGrid}>
              {benchmarkRows.map((row) => (
                <div key={`${row.solver}-${row.status}`} className={styles.infoCard}>
                  <div className={styles.infoMain}>
                    <span className={styles.infoLabel}>{row.solver ?? 'solver'}</span>
                    <span className={row.status === 'ran' ? 'pass' : 'fail'}>{row.status}</span>
                  </div>
                  <div className={styles.infoReason}>目标值：{formatNumber(row.best_feasible_objective)}；可行率：{formatPercent(row.feasible_sample_ratio)}；耗时：{formatMs(row.total_ms)}</div>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.block}>
            <div className={styles.subTitle}>QAOA / Constrained QAOA</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}>
                <div className={styles.infoMain}>
                  <span className={styles.infoLabel}>QAOA 状态</span>
                  <span className={quantum?.qaoa?.status === 'ran' ? 'pass' : 'fail'}>{quantum?.qaoa?.status ?? '-'}</span>
                </div>
                <div className={styles.infoReason}>backend: {quantum?.qaoa?.backend ?? qaoaCircuit?.execution_backend ?? '-'}</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoMain}>
                  <span className={styles.infoLabel}>量子线路</span>
                  <span className={styles.infoValue}>{qaoaCircuit?.num_qubits ?? '-'} qubits / {qaoaCircuit?.layers ?? '-'} layers</span>
                </div>
                <div className={styles.infoReason}>H: {qaoaGateEstimate?.h ?? '-'}；RZ/layer: {qaoaGateEstimate?.rz_per_layer ?? '-'}；RZZ/layer: {qaoaGateEstimate?.rzz_per_layer ?? '-'}</div>
              </div>
              <div className={styles.infoCard}>
                <div className={styles.infoMain}>
                  <span className={styles.infoLabel}>Constrained QAOA</span>
                  <span className={quantum?.constrained_qaoa?.status === 'ran' ? 'pass' : 'fail'}>{quantum?.constrained_qaoa?.status ?? '-'}</span>
                </div>
                <div className={styles.infoReason}>route: {quantum?.constrained_qaoa?.diagnostics?.route ?? '-'}</div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function readQuantumError(e: unknown) {
  if (axios.isAxiosError(e)) {
    const payload = e.response?.data as QuantumApiErrorResponse | undefined;
    return payload?.error?.message ?? '后端量化求解失败，请确认 backend_service 已启动。';
  }
  return '后端量化求解失败，请稍后重试。';
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return `${(value * 100).toFixed(1)}%`;
}

function formatMs(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return `${value.toFixed(1)} ms`;
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
