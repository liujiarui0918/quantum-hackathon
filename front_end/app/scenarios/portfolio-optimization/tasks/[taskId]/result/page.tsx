'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { buildPortfolioResult, createDemoPortfolioTasks, emptyPortfolioPayload } from '@/lib/mock-portfolio';
import type { PortfolioResultPayload } from '@/lib/portfolio-types';
import styles from './result.module.css';

export default function PortfolioResultPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId;
  const [data, setData] = useState<PortfolioResultPayload | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const raw = sessionStorage.getItem(`portfolio-result:${taskId}`);
    if (raw) {
      try {
        setData(JSON.parse(raw) as PortfolioResultPayload);
        return;
      } catch {
        // fallback
      }
    }
    const demo = createDemoPortfolioTasks().find((t) => t.id === taskId);
    const fallbackTask =
      demo ??
      ({
        id: taskId,
        ...emptyPortfolioPayload(),
        name: `演示任务-${taskId.slice(0, 8)}`,
        status: 'completed',
        createdAt: new Date().toISOString(),
      } as const);
    setData(buildPortfolioResult(fallbackTask));
  }, [taskId]);

  const title = useMemo(() => '金融投资组合优化 - 结果页', []);
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
              <div className={styles.infoCard}><span className={styles.infoLabel}>任务名称</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.name}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>预算</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.budget.toLocaleString()}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>候选资产</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.assetUniverseSize}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>最大持仓</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.maxHoldings}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>最低收益</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.minExpectedReturn}%</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>风险上限</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.task.riskLimit}</span></div>
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
            <div className={styles.sectionTitle}>目标函数拆解（MIQP）</div>
            <div className={styles.infoGrid}>
              <div className={styles.infoCard}><span className={styles.infoLabel}>投资金额</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.investedAmount.toLocaleString()}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>剩余现金</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.cashRemain.toLocaleString()}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>预期收益</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.expectedReturnPct}%</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>方差风险</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.varianceRisk}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>波动率</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.volatilityPct}%</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>持仓数量</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.selectedCount}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>收益项</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.returnTerm}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>风险惩罚项</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.riskTerm}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>持仓惩罚项</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.cardinalityTerm}</span></div>
              <div className={styles.infoCard}><span className={styles.infoLabel}>目标值</span><span className={styles.infoSep}>：</span><span className={styles.infoValue}>{data.summary.objectiveScore}</span></div>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>资产权重与选择变量</div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>资产</th>
                    <th>选择变量</th>
                    <th>持仓数量</th>
                    <th>价格</th>
                    <th>权重</th>
                    <th>预期收益</th>
                    <th>边际风险</th>
                  </tr>
                </thead>
                <tbody>
                  {data.assets.map((a) => (
                    <tr key={a.code}>
                      <td>{a.code} / {a.name}</td>
                      <td>{a.selected ? 1 : 0}</td>
                      <td>{a.units}</td>
                      <td>{a.price}</td>
                      <td>{(a.weight * 100).toFixed(2)}%</td>
                      <td>{a.expectedReturn}%</td>
                      <td>{a.marginalRisk}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionTitle}>协方差二次项（Top |Cov|）</div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>资产 i</th>
                    <th>资产 j</th>
                    <th>Cov(i,j)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.covarianceTop.map((c, idx) => (
                    <tr key={`${c.i}-${c.j}-${idx}`}>
                      <td>{c.i}</td>
                      <td>{c.j}</td>
                      <td className={c.value >= 0 ? 'pass' : 'fail'}>{c.value}</td>
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
