'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import type { LogisticsResult, RouteNode, VehicleRoute } from '@/lib/mock-logistics-routing';
import { tryLoadLogisticsResult } from '@/lib/mock-logistics-routing';
import styles from './result.module.css';

export default function LogisticsRoutingResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [data, setData] = useState<LogisticsResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const r = tryLoadLogisticsResult(taskId);
    if (r) {
      setData(r);
      setErr(null);
    } else {
      setData(null);
      setErr('未找到结果数据：请先在该任务为「已完成」时从任务列表点击「查看结果」，或使用已完成的演示任务链接。');
    }
  }, [taskId]);

  const title = useMemo(() => '物流路径规划 - 结果页', []);

  if (!taskId) return null;

  const violationBarPct = data ? Math.min(100, data.violationRatePct * 18 + 6) : 0;

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.pageTitle}>{title}</div>
      <div className={styles.intro}>
        多车从仓库出发服务客户，最小化总距离与运营成本。决策可建模为「车辆是否从地点 i 前往地点 j」的整数/组合结构；容量与时间窗等约束使精确求解困难。下图分别为示意路线图、求解过程中目标值（成本）变化曲线，以及软约束违反率（演示假数据）。
      </div>

      {err ? <div className={styles.error}>{err}</div> : null}
      {!data && !err ? <div className="muted">加载中…</div> : null}

      {data ? (
        <div className={styles.stack}>
          <section className={styles.section}>
            <div className={styles.sectionTitle}>任务信息</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>任务名称</span>
                <span className={styles.infoSep}>：</span>
                <span className={styles.infoValue}>{data.task.name}</span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>区域</span>
                <span className={styles.infoSep}>：</span>
                <span className={styles.infoValue}>{data.task.regionLabel}</span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>时间窗</span>
                <span className={styles.infoSep}>：</span>
                <span className={styles.infoValue}>{data.task.useTimeWindow ? '启用' : '未启用'}</span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>车辆 / 客户点</span>
                <span className={styles.infoSep}>：</span>
                <span className={styles.infoValue}>
                  {data.task.vehicleCount} / {data.task.customerCount}
                </span>
              </div>
              <div className={styles.infoCard}>
                <span className={styles.infoLabel}>单车容量</span>
                <span className={styles.infoSep}>：</span>
                <span className={styles.infoValue}>{data.task.vehicleCapacity}</span>
              </div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>汇总指标</div>
            <div className={styles.metrics}>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>总行驶距离（示意）</div>
                <div className={styles.metricValue}>{data.totalDistanceKm} km</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>总成本（目标值终值）</div>
                <div className={styles.metricValue}>{data.totalCost.toLocaleString()} 元</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>约束违反率（软约束）</div>
                <div className={styles.metricValue}>{data.violationRatePct}%</div>
              </div>
            </div>

            <div className={styles.violationBlock}>
              <div className={styles.violationHead}>
                <span className="muted">违反率可视化（条越长表示违反越多，演示刻度）</span>
              </div>
              <div className={styles.violationTrack}>
                <div className={styles.violationFill} style={{ width: `${violationBarPct}%` }} />
              </div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>路线图（示意）</div>
            <div className={styles.mapWrap}>
              <RouteMapSvg nodes={data.nodes} routes={data.routes} />
            </div>
            <div className={styles.legendRow}>
              {data.routes.map((r) => (
                <span key={r.vehicleId}>
                  <span className={styles.legendSwatch} style={{ background: r.color }} />
                  <span className="muted">{r.label}</span>
                </span>
              ))}
              <span className="muted">中央节点为仓库，外圈为客户；折线为单车回路。</span>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>成本下降曲线（迭代 vs 目标值）</div>
            <div className={styles.chartWrap}>
              <div className={styles.chartTitle}>演示用随机下降曲线，非真实求解器输出</div>
              <CostCurveSvg series={data.costSeries} />
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}

function nodeById(nodes: RouteNode[], id: string) {
  return nodes.find((n) => n.id === id);
}

function RouteMapSvg({ nodes, routes }: { nodes: RouteNode[]; routes: VehicleRoute[] }) {
  const vb = '0 0 100 100';
  return (
    <svg className={styles.mapSvg} viewBox={vb} preserveAspectRatio="xMidYMid meet">
      <defs>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.6" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="100" height="100" fill="rgba(4,10,24,0.4)" />
      {routes.map((route) => {
        const pts = route.nodeIds
          .map((id) => nodeById(nodes, id))
          .filter(Boolean) as RouteNode[];
        if (pts.length < 2) return null;
        const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
        return (
          <path
            key={route.vehicleId}
            d={d}
            fill="none"
            stroke={route.color}
            strokeWidth={0.9}
            strokeLinejoin="round"
            strokeLinecap="round"
            opacity={0.92}
            filter="url(#glow)"
          />
        );
      })}
      {nodes.map((n) => {
        const isDepot = n.kind === 'depot';
        const r = isDepot ? 3.2 : 2.1;
        return (
          <g key={n.id}>
            <circle cx={n.x} cy={n.y} r={r + 0.6} fill="rgba(0,0,0,0.35)" />
            <circle
              cx={n.x}
              cy={n.y}
              r={r}
              fill={isDepot ? 'rgba(61,255,206,0.95)' : 'rgba(110,203,255,0.9)'}
              stroke="rgba(232,247,255,0.35)"
              strokeWidth={0.25}
            />
            <text
              x={n.x + (isDepot ? 4 : 3)}
              y={n.y - (isDepot ? 3.5 : 2.8)}
              fill="rgba(232,247,255,0.88)"
              fontSize={3.2}
              style={{ fontFamily: 'system-ui, sans-serif' }}
            >
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CostCurveSvg({ series }: { series: { iter: number; cost: number }[] }) {
  if (!series.length) return null;
  const w = 360;
  const h = 140;
  const padL = 36;
  const padR = 12;
  const padT = 14;
  const padB = 28;
  const innerW = w - padL - padR;
  const innerH = h - padT - padB;
  const minC = Math.min(...series.map((p) => p.cost));
  const maxC = Math.max(...series.map((p) => p.cost));
  const span = Math.max(1, maxC - minC);
  const maxIter = series[series.length - 1]?.iter ?? 1;

  const pts = series.map((p) => {
    const x = padL + (p.iter / maxIter) * innerW;
    const y = padT + innerH - ((p.cost - minC) / span) * innerH;
    return `${x},${y}`;
  });

  const pathD = `M ${pts.join(' L ')}`;

  return (
    <svg className={styles.chartSvg} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <rect x={0} y={0} width={w} height={h} fill="transparent" />
      <line
        x1={padL}
        y1={padT + innerH}
        x2={padL + innerW}
        y2={padT + innerH}
        stroke="rgba(110,203,255,0.25)"
        strokeWidth={1}
      />
      <line
        x1={padL}
        y1={padT}
        x2={padL}
        y2={padT + innerH}
        stroke="rgba(110,203,255,0.25)"
        strokeWidth={1}
      />
      <path
        d={pathD}
        fill="none"
        stroke="rgba(61,255,206,0.9)"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <text x={padL} y={h - 8} className={styles.axisLabel}>
        迭代步
      </text>
      <text x={padL - 26} y={padT + 4} className={styles.axisLabel} transform={`rotate(-90 ${padL - 26} ${padT + 4})`}>
        成本
      </text>
      <text x={padL + innerW - 40} y={padT + 12} className={styles.axisLabel} fill="rgba(61,255,206,0.75)">
        终值 {series[series.length - 1]?.cost.toLocaleString()}
      </text>
    </svg>
  );
}
