'use client';

import Image from 'next/image';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { createPortal } from 'react-dom';
import { api } from '@/lib/axios-client';
import type { Task } from '@/lib/types';
import styles from './result.module.css';

type StoredResult = {
  rawJson: string;
  runImgList?: string[];
  compareImgList?: string[];
};

type ApiPayload = {
  task: Task;
  result: StoredResult;
};

type ViewData = {
  task: {
    name: string;
    datasetName: string;
    n: string;
    p: string;
    m1: string;
    m2: string;
    solver: string;
    maxQubits: string;
    subQuboSize: string;
  };
  summary: {
    bestObjective: string;
    bestSolution: string;
    gapPct: string;
    feasible: boolean;
    violationCount: string;
    selectedBinaryCount: string;
    activeContinuousCount: string;
    totalRuntimeSec: string;
  };
  validations: Array<{ key: string; label: string; pass: boolean }>;
  iterations: Array<{
    iter: string;
    objective: string;
    bestBound: string;
    gapPct: string;
    feasible: boolean;
    usedQubits: string;
    elapsedSec: string;
    note: string;
  }>;
};

function asObj(v: unknown): Record<string, unknown> {
  return typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {};
}

function asNum(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) return Number(v);
  return null;
}

function fmt(v: number | null, digits = 6): string {
  if (v === null) return '-';
  return Number(v.toFixed(digits)).toString();
}

function parseViewData(task: Task, stored: StoredResult): ViewData {
  const parsed = asObj(JSON.parse(stored.rawJson));
  const instance = asObj(parsed.instance);
  const referenceSolution = asObj(parsed.reference_solution);
  const route = asObj(parsed.miqp_aware_route7);
  const routeSolution = asObj(route.solution);
  const diagnostics = asObj(routeSolution.diagnostics);
  const constraintReport = asObj(diagnostics.constraint_report);
  const runtimeMs = asNum(parsed.runtime_ms);

  const portfolio = Array.isArray(parsed.portfolio) ? parsed.portfolio : [];

  const bestObjective = asNum(routeSolution.objective) ?? asNum(referenceSolution.objective);
  const bestSolution = asNum(referenceSolution.optimal_value) ?? asNum(routeSolution.objective);
  const feasible = Boolean(routeSolution.feasible ?? referenceSolution.feasible);
  const violation = asNum(constraintReport.total_violation);

  const gapPct =
    bestObjective !== null && bestSolution !== null && Math.abs(bestSolution) > 1e-12
      ? (Math.abs(bestObjective - bestSolution) / Math.abs(bestSolution)) * 100
      : null;

  const x = Array.isArray(routeSolution.x) ? routeSolution.x : [];
  const y = Array.isArray(routeSolution.y) ? routeSolution.y : [];
  const selectedBinaryCount = x.filter((v) => Number(v) > 0.5).length;
  const activeContinuousCount = y.filter((v) => Math.abs(Number(v) || 0) > 1e-10).length;

  const validations: ViewData['validations'] = [
    { key: 'feasible', label: '可行性校验', pass: feasible },
    { key: 'violation', label: '约束违反量', pass: (violation ?? 1) <= 1e-8 },
  ];

  const iterations: ViewData['iterations'] = [];
  if (portfolio.length > 0) {
    for (let i = 0; i < portfolio.length; i += 1) {
      const p = asObj(portfolio[i]);
      iterations.push({
        iter: String(i + 1),
        objective: fmt(asNum(p.objective)),
        bestBound: fmt(bestSolution),
        gapPct: gapPct === null ? '-' : fmt(gapPct, 4),
        feasible: Boolean(p.feasible),
        usedQubits: String(task.maxQubits),
        elapsedSec: runtimeMs === null ? '-' : fmt(runtimeMs / 1000, 3),
        note: typeof p.mode === 'string' ? p.mode : '-',
      });
    }
  } else {
    iterations.push({
      iter: '1',
      objective: fmt(bestObjective),
      bestBound: fmt(bestSolution),
      gapPct: gapPct === null ? '-' : fmt(gapPct, 4),
      feasible,
      usedQubits: String(task.maxQubits),
      elapsedSec: runtimeMs === null ? '-' : fmt(runtimeMs / 1000, 3),
      note: 'miqp_aware_route7',
    });
  }

  return {
    task: {
      name: task.name,
      datasetName: task.datasetName || String(instance.name ?? '-'),
      n: String(task.n || asNum(instance.n) || '-'),
      p: String(task.p || asNum(instance.p) || '-'),
      m1: String(task.m1 || asNum(instance.m1) || '-'),
      m2: String(task.m2 || asNum(instance.m2) || '-'),
      solver: task.solver,
      maxQubits: String(task.maxQubits),
      subQuboSize: String(task.subQuboSize),
    },
    summary: {
      bestObjective: fmt(bestObjective),
      bestSolution: fmt(bestSolution),
      gapPct: gapPct === null ? '-' : fmt(gapPct, 4),
      feasible,
      violationCount: violation === null ? '-' : fmt(violation, 10),
      selectedBinaryCount: String(selectedBinaryCount),
      activeContinuousCount: String(activeContinuousCount),
      totalRuntimeSec: runtimeMs === null ? '-' : fmt(runtimeMs / 1000, 3),
    },
    validations,
    iterations,
  };
}

export default function TaskResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<ApiPayload | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewIndex, setPreviewIndex] = useState(0);
  const [previewType, setPreviewType] = useState<'run' | 'compare'>('run');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  useEffect(() => {
    if (!taskId) return;
    setLoading(true);
    setError(null);
    api
      .get<{ data: ApiPayload }>(`/api/tasks/${taskId}/result`)
      .then((res) => {
        setPayload(res.data.data ?? null);
      })
      .catch(() => {
        setError('结果不存在或尚未导入');
        setPayload(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [taskId]);

  const view = useMemo(() => {
    if (!payload?.task || !payload?.result?.rawJson) return null;
    try {
      return parseViewData(payload.task, payload.result);
    } catch {
      return null;
    }
  }, [payload]);

  const previewImages = useMemo(() => {
    if (!payload?.result) return [] as string[];
    return previewType === 'run' ? (payload.result.runImgList ?? []) : (payload.result.compareImgList ?? []);
  }, [payload, previewType]);

  useEffect(() => {
    if (!previewOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setPreviewOpen(false);
        return;
      }
      if (previewImages.length <= 1) return;
      if (e.key === 'ArrowRight') {
        setPreviewIndex((prev) => (prev + 1) % previewImages.length);
      }
      if (e.key === 'ArrowLeft') {
        setPreviewIndex((prev) => (prev - 1 + previewImages.length) % previewImages.length);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [previewOpen, previewImages.length]);

  useEffect(() => {
    if (!previewOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [previewOpen]);

  const openPreview = (type: 'run' | 'compare', index: number) => {
    setPreviewType(type);
    setPreviewIndex(index);
    setPreviewOpen(true);
  };

  const gotoPrev = () => {
    if (previewImages.length <= 1) return;
    setPreviewIndex((prev) => (prev - 1 + previewImages.length) % previewImages.length);
  };

  const gotoNext = () => {
    if (previewImages.length <= 1) return;
    setPreviewIndex((prev) => (prev + 1) % previewImages.length);
  };

  const title = useMemo(() => '比赛题结果展示', []);
  if (!taskId) return null;

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.pageTitle}>{title}</div>
      {loading ? <div className="muted">加载中…</div> : null}
      {error ? <div className={styles.error}>{error}</div> : null}
      {!loading && !error && !view ? <div className={styles.error}>结果数据格式不正确</div> : null}

      {!loading && !error && payload && view ? (
        <div className={styles.stack}>
          <section className={styles.section}>
            <div className={styles.sectionTitle}>任务信息 / 约束校验</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>任务名</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.task.name}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>数据集</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.task.datasetName}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>变量规模</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>n={view.task.n}, p={view.task.p}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>约束规模</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>m1={view.task.m1}, m2={view.task.m2}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>求解模式</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.task.solver}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>比特/分块</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.task.maxQubits}/{view.task.subQuboSize}</span></div>
            </div>
            <div className={styles.legend}>
              {view.validations.map((v) => (
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
              <div className={styles.infoCard}><span className={styles.infoLabel}>最优目标</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.bestObjective}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>最优解</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.bestSolution}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>Gap</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.gapPct}%</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>可行性</span><span className={styles.infoSep}>：</span><span className={view.summary.feasible ? 'pass' : 'fail'}>{view.summary.feasible ? '可行' : '不可行'}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>违反约束数</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.violationCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>激活二元变量</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.selectedBinaryCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>激活连续变量</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.activeContinuousCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>总耗时</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{view.summary.totalRuntimeSec}s</span></div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>迭代过程</div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>迭代</th>
                    <th>目标值</th>
                    <th>最优解</th>
                    <th>Gap%</th>
                    <th>可行</th>
                    <th>比特</th>
                    <th>耗时(s)</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  {view.iterations.map((it, idx) => (
                    <tr key={`${it.iter}-${idx}`}>
                      <td>{it.iter}</td>
                      <td>{it.objective}</td>
                      <td>{it.bestBound}</td>
                      <td>{it.gapPct}</td>
                      <td className={it.feasible ? 'pass' : 'fail'}>{it.feasible ? '是' : '否'}</td>
                      <td>{it.usedQubits}</td>
                      <td>{it.elapsedSec}</td>
                      <td>{it.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>运行信息</div>
            <div className={styles.imageGrid}>
              {(payload.result.runImgList ?? []).map((url, idx) => (
                <button key={`${url}-${idx}`} type="button" className={styles.imageCard} onClick={() => openPreview('run', idx)}>
                  <div className={styles.thumb} style={{ width: '100%', height: 180 }}>
                    <Image src={url} alt={`运行信息-${idx + 1}`} width={640} height={360} unoptimized />
                  </div>
                </button>
              ))}
              {(payload.result.runImgList ?? []).length === 0 ? <div className="muted">暂无图片</div> : null}
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>比对信息</div>
            <div className={styles.imageGrid}>
              {(payload.result.compareImgList ?? []).map((url, idx) => (
                <button key={`${url}-${idx}`} type="button" className={styles.imageCard} onClick={() => openPreview('compare', idx)}>
                  <div className={styles.thumb} style={{ width: '100%', height: 180 }}>
                    <Image src={url} alt={`比对信息-${idx + 1}`} width={640} height={360} unoptimized />
                  </div>
                </button>
              ))}
              {(payload.result.compareImgList ?? []).length === 0 ? <div className="muted">暂无图片</div> : null}
            </div>
          </section>

          {mounted && previewOpen && previewImages.length > 0
            ? createPortal(
            <div className={styles.previewMask} onClick={() => setPreviewOpen(false)}>
              <div className={styles.previewPanel} onClick={(e) => e.stopPropagation()}>
                <button type="button" className={styles.previewClose} onClick={() => setPreviewOpen(false)}>×</button>
                <div className={styles.previewBody}>
                  <img src={previewImages[previewIndex]} alt="preview" className={styles.previewImg} />
                </div>
                <div className={styles.previewFoot}>
                  <span className="muted">{previewIndex + 1} / {previewImages.length}</span>
                </div>
                {previewImages.length > 1 ? (
                  <>
                    <button type="button" className={styles.previewNavLeft} onClick={gotoPrev}>‹</button>
                    <button type="button" className={styles.previewNavRight} onClick={gotoNext}>›</button>
                  </>
                ) : null}
              </div>
            </div>,
            document.body,
          ) : null}
        </div>
      ) : null}
    </main>
  );
}
