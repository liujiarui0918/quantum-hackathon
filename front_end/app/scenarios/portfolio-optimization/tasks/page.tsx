'use client';

import { useMemo, useState } from 'react';
import { Modal } from '@/components/Modal';
import { buildPortfolioResult, createDemoPortfolioTasks, emptyPortfolioPayload } from '@/lib/mock-portfolio';
import type { PortfolioTask, PortfolioTaskPayload, PortfolioTaskStatus } from '@/lib/portfolio-types';
import styles from './tasks.module.css';
import formStyles from './task-form.module.css';

function zhStatus(s: PortfolioTaskStatus) {
  if (s === 'pending') return '未执行';
  if (s === 'running') return '执行中';
  return '已完成';
}

function pickPayload(t: PortfolioTask): PortfolioTaskPayload {
  const { id: _id, status: _s, createdAt: _c, ...rest } = t;
  return rest;
}

function PortfolioForm({
  value,
  onChange,
  readOnly,
}: {
  value: PortfolioTaskPayload;
  onChange: (next: PortfolioTaskPayload) => void;
  readOnly?: boolean;
}) {
  const ro = readOnly ?? false;
  const patch = (p: Partial<PortfolioTaskPayload>) => onChange({ ...value, ...p });
  return (
    <div className={formStyles.grid}>
      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>任务名称</h3>
        <label className={formStyles.field}>
          <span className={formStyles.label}>任务名称（name）</span>
          <input className={formStyles.input} value={value.name} disabled={ro} onChange={(e) => patch({ name: e.target.value })} placeholder="请输入任务名称" />
        </label>
      </section>

      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>组合规模</h3>
        <div className={formStyles.row3}>
          <label className={formStyles.field}><span className={formStyles.label}>预算（budget）</span><input className={formStyles.input} type="number" min={100000} step={10000} value={value.budget} disabled={ro} onChange={(e) => patch({ budget: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>候选资产数（assetUniverseSize）</span><input className={formStyles.input} type="number" min={12} max={100} value={value.assetUniverseSize} disabled={ro} onChange={(e) => patch({ assetUniverseSize: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>最大持仓数（maxHoldings）</span><input className={formStyles.input} type="number" min={2} max={30} value={value.maxHoldings} disabled={ro} onChange={(e) => patch({ maxHoldings: Number(e.target.value) })} /></label>
        </div>
      </section>

      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>目标与约束（MIQP）</h3>
        <div className={formStyles.row2}>
          <label className={formStyles.field}><span className={formStyles.label}>最低收益（minExpectedReturn, %）</span><input className={formStyles.input} type="number" step={0.1} min={1} max={30} value={value.minExpectedReturn} disabled={ro} onChange={(e) => patch({ minExpectedReturn: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>风险上限（riskLimit）</span><input className={formStyles.input} type="number" step={0.001} min={0.005} max={0.2} value={value.riskLimit} disabled={ro} onChange={(e) => patch({ riskLimit: Number(e.target.value) })} /></label>
        </div>
        <div className={formStyles.row2} style={{ marginTop: 12 }}>
          <label className={formStyles.field}><span className={formStyles.label}>单资产权重上限（maxWeightPerAsset）</span><input className={formStyles.input} type="number" step={0.01} min={0.05} max={0.8} value={value.maxWeightPerAsset} disabled={ro} onChange={(e) => patch({ maxWeightPerAsset: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>持仓数量惩罚（cardinalityPenalty）</span><input className={formStyles.input} type="number" step={0.001} min={0} max={0.1} value={value.cardinalityPenalty} disabled={ro} onChange={(e) => patch({ cardinalityPenalty: Number(e.target.value) })} /></label>
        </div>
      </section>
    </div>
  );
}

export default function PortfolioTasksPage() {
  const [tasks, setTasks] = useState<PortfolioTask[]>(() => createDemoPortfolioTasks());
  const [draft, setDraft] = useState<PortfolioTaskPayload>(() => emptyPortfolioPayload());
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<PortfolioTaskPayload>(() => emptyPortfolioPayload());
  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTask, setExecuteTask] = useState<PortfolioTask | null>(null);

  const closeCreate = () => {
    setCreateOpen(false);
    setDraft(emptyPortfolioPayload());
  };
  const submitCreate = () => {
    if (!draft.name.trim()) return;
    const t: PortfolioTask = { id: crypto.randomUUID(), ...draft, status: 'pending', createdAt: new Date().toISOString() };
    setTasks((prev) => [t, ...prev]);
    closeCreate();
  };
  const openEdit = (t: PortfolioTask) => {
    setEditId(t.id);
    setEditDraft(pickPayload(t));
    setEditOpen(true);
  };
  const submitEdit = () => {
    if (!editId || !editDraft.name.trim()) return;
    setTasks((prev) => prev.map((t) => (t.id === editId ? { ...t, ...editDraft } : t)));
    setEditOpen(false);
    setEditId(null);
  };
  const confirmExecute = () => {
    if (!executeTask) return;
    setTasks((prev) => prev.map((t) => (t.id === executeTask.id ? { ...t, status: 'completed' } : t)));
    setExecuteOpen(false);
    setExecuteTask(null);
  };
  const openResult = (t: PortfolioTask) => {
    const result = buildPortfolioResult(t);
    sessionStorage.setItem(`portfolio-result:${t.id}`, JSON.stringify(result));
    window.open(`/scenarios/portfolio-optimization/tasks/${t.id}/result`, '_blank', 'noopener,noreferrer');
  };

  const headerRight = useMemo(() => <button type="button" className="btn" onClick={() => setCreateOpen(true)}>创建任务</button>, []);

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.titleRow}>
        <div className={styles.title}>金融投资组合优化 - 任务管理</div>
        {headerRight}
      </div>
      <div className={styles.hint}><span className="muted">共 {tasks.length} 条</span></div>

      <div className={styles.list}>
        {tasks.map((t) => (
          <article key={t.id} className={styles.card}>
            <div className={styles.cardTop}>
              <div className={styles.name}>{t.name}</div>
              <div className={styles.status} data-status={t.status}>{zhStatus(t.status)}</div>
            </div>
            <div className={styles.groups}>
              <div className={styles.group}>
                <div className={styles.groupTitle}>组合规模</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>预算</span><span className={styles.kvValue}>{t.budget.toLocaleString()}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>候选资产</span><span className={styles.kvValue}>{t.assetUniverseSize}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>最大持仓</span><span className={styles.kvValue}>{t.maxHoldings}</span></div>
                </div>
              </div>
              <div className={styles.group}>
                <div className={styles.groupTitle}>目标与约束</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>最低收益</span><span className={styles.kvValue}>{t.minExpectedReturn}%</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>风险上限</span><span className={styles.kvValue}>{t.riskLimit}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>单资产上限</span><span className={styles.kvValue}>{t.maxWeightPerAsset}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>持仓惩罚</span><span className={styles.kvValue}>{t.cardinalityPenalty}</span></div>
                </div>
              </div>
            </div>
            <div className={styles.actions}>
              {t.status === 'pending' ? <button type="button" className="btn btnGhost" onClick={() => openEdit(t)}>编辑</button> : null}
              {t.status === 'pending' ? <button type="button" className="btn" onClick={() => { setExecuteTask(t); setExecuteOpen(true); }}>执行</button> : null}
              {t.status === 'completed' ? <button type="button" className="btn" onClick={() => openResult(t)}>查看结果</button> : null}
            </div>
          </article>
        ))}
      </div>

      {createOpen ? (
        <Modal title="创建任务" onClose={closeCreate} footer={<><button className="btn btnGhost" onClick={closeCreate}>取消</button><button className="btn" onClick={submitCreate}>确定</button></>}>
          <PortfolioForm value={draft} onChange={setDraft} />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal title="编辑任务" onClose={() => setEditOpen(false)} footer={<><button className="btn btnGhost" onClick={() => setEditOpen(false)}>取消</button><button className="btn" onClick={submitEdit}>确定</button></>}>
          <PortfolioForm value={editDraft} onChange={setEditDraft} />
        </Modal>
      ) : null}

      {executeOpen && executeTask ? (
        <Modal title="确认执行" onClose={() => setExecuteOpen(false)} footer={<><button className="btn btnGhost" onClick={() => setExecuteOpen(false)}>取消</button><button className="btn" onClick={confirmExecute}>确定</button></>}>
          <div className="muted" style={{ marginBottom: 12 }}>确定要执行“{executeTask.name}”吗？</div>
          <PortfolioForm value={pickPayload(executeTask)} onChange={() => undefined} readOnly />
        </Modal>
      ) : null}
    </main>
  );
}
