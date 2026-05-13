'use client';

import { useMemo, useState } from 'react';
import { Modal } from '@/components/Modal';
import { buildSchedulingResult, createDemoSchedulingTasks, emptySchedulingPayload } from '@/lib/mock-production';
import type { SchedulingTask, SchedulingTaskPayload, SchedulingTaskStatus } from '@/lib/production-types';
import styles from './tasks.module.css';
import formStyles from './task-form.module.css';

function zhStatus(s: SchedulingTaskStatus) {
  if (s === 'pending') return '未执行';
  if (s === 'running') return '执行中';
  return '已完成';
}

function pickPayload(t: SchedulingTask): SchedulingTaskPayload {
  const { id: _id, status: _s, createdAt: _c, ...rest } = t;
  return rest;
}

function MiniForm({
  value,
  onChange,
  readOnly,
}: {
  value: SchedulingTaskPayload;
  onChange: (next: SchedulingTaskPayload) => void;
  readOnly?: boolean;
}) {
  const ro = readOnly ?? false;
  const patch = (p: Partial<SchedulingTaskPayload>) => onChange({ ...value, ...p });
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
        <h3 className={formStyles.h3}>任务规模</h3>
        <div className={formStyles.row3}>
          <label className={formStyles.field}><span className={formStyles.label}>订单数（orderCount）</span><input className={formStyles.input} type="number" min={8} max={500} value={value.orderCount} disabled={ro} onChange={(e) => patch({ orderCount: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>机器数（machineCount）</span><input className={formStyles.input} type="number" min={2} max={30} value={value.machineCount} disabled={ro} onChange={(e) => patch({ machineCount: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>排程时域（horizonHours, h）</span><input className={formStyles.input} type="number" min={24} max={336} value={value.horizonHours} disabled={ro} onChange={(e) => patch({ horizonHours: Number(e.target.value) })} /></label>
        </div>
      </section>

      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>目标与成本参数</h3>
        <div className={formStyles.row3}>
          <label className={formStyles.field}><span className={formStyles.label}>交期紧度（dueTightness）</span><input className={formStyles.input} type="number" step="0.05" min={0.6} max={1.4} value={value.dueTightness} disabled={ro} onChange={(e) => patch({ dueTightness: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>换线成本（switchCostPerChange）</span><input className={formStyles.input} type="number" min={20} max={5000} value={value.switchCostPerChange} disabled={ro} onChange={(e) => patch({ switchCostPerChange: Number(e.target.value) })} /></label>
          <label className={formStyles.field}><span className={formStyles.label}>空闲惩罚（idlePenaltyPerHour）</span><input className={formStyles.input} type="number" min={10} max={1000} value={value.idlePenaltyPerHour} disabled={ro} onChange={(e) => patch({ idlePenaltyPerHour: Number(e.target.value) })} /></label>
        </div>
        <div className={formStyles.row2} style={{ marginTop: 12 }}>
          <label className={formStyles.field}><span className={formStyles.label}>优先订单占比（priorityOrderRatio，0~1）</span><input className={formStyles.input} type="number" step="0.05" min={0} max={1} value={value.priorityOrderRatio} disabled={ro} onChange={(e) => patch({ priorityOrderRatio: Number(e.target.value) })} /></label>
        </div>
      </section>
    </div>
  );
}

export default function ProductionTasksPage() {
  const [tasks, setTasks] = useState<SchedulingTask[]>(() => createDemoSchedulingTasks());
  const [draft, setDraft] = useState<SchedulingTaskPayload>(() => emptySchedulingPayload());
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<SchedulingTaskPayload>(() => emptySchedulingPayload());

  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTask, setExecuteTask] = useState<SchedulingTask | null>(null);
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [terminateTask, setTerminateTask] = useState<SchedulingTask | null>(null);

  const closeCreate = () => {
    setCreateOpen(false);
    setDraft(emptySchedulingPayload());
  };
  const submitCreate = () => {
    if (!draft.name.trim()) return;
    const t: SchedulingTask = { id: crypto.randomUUID(), ...draft, status: 'pending', createdAt: new Date().toISOString() };
    setTasks((prev) => [t, ...prev]);
    closeCreate();
  };

  const openEdit = (t: SchedulingTask) => {
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
  const confirmTerminate = () => {
    if (!terminateTask) return;
    setTasks((prev) => prev.map((t) => (t.id === terminateTask.id ? { ...t, status: 'pending' } : t)));
    setTerminateOpen(false);
    setTerminateTask(null);
  };

  const openResult = (t: SchedulingTask) => {
    const result = buildSchedulingResult(t);
    sessionStorage.setItem(`production-result:${t.id}`, JSON.stringify(result));
    window.open(`/scenarios/production-scheduling/tasks/${t.id}/result`, '_blank', 'noopener,noreferrer');
  };

  const headerRight = useMemo(
    () => (
      <button type="button" className="btn" onClick={() => setCreateOpen(true)}>
        创建任务
      </button>
    ),
    [],
  );

  return (
    <main className="panel" style={{ padding: 16 }}>
      <div className={styles.titleRow}>
        <div className={styles.title}>工业排产调度 - 任务管理</div>
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
                <div className={styles.groupTitle}>任务规模</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>订单数</span><span className={styles.kvValue}>{t.orderCount}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>机器数</span><span className={styles.kvValue}>{t.machineCount}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>时域</span><span className={styles.kvValue}>{t.horizonHours} h</span></div>
                </div>
              </div>
              <div className={styles.group}>
                <div className={styles.groupTitle}>目标与约束</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>交期紧度</span><span className={styles.kvValue}>{t.dueTightness}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>换线成本</span><span className={styles.kvValue}>{t.switchCostPerChange}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>空闲惩罚</span><span className={styles.kvValue}>{t.idlePenaltyPerHour}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>优先订单占比</span><span className={styles.kvValue}>{Math.round(t.priorityOrderRatio * 100)}%</span></div>
                </div>
              </div>
            </div>
            <div className={styles.actions}>
              {t.status === 'pending' ? <button type="button" className="btn btnGhost" onClick={() => openEdit(t)}>编辑</button> : null}
              {t.status === 'pending' ? <button type="button" className="btn" onClick={() => { setExecuteTask(t); setExecuteOpen(true); }}>执行</button> : null}
              {t.status === 'running' ? <button type="button" className="btn btnDanger" onClick={() => { setTerminateTask(t); setTerminateOpen(true); }}>终止</button> : null}
              {t.status === 'completed' ? <button type="button" className="btn" onClick={() => openResult(t)}>查看结果</button> : null}
            </div>
          </article>
        ))}
      </div>

      {createOpen ? (
        <Modal title="创建任务" onClose={closeCreate} footer={<><button className="btn btnGhost" onClick={closeCreate}>取消</button><button className="btn" onClick={submitCreate}>确定</button></>}>
          <MiniForm value={draft} onChange={setDraft} />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal title="编辑任务" onClose={() => setEditOpen(false)} footer={<><button className="btn btnGhost" onClick={() => setEditOpen(false)}>取消</button><button className="btn" onClick={submitEdit}>确定</button></>}>
          <MiniForm value={editDraft} onChange={setEditDraft} />
        </Modal>
      ) : null}

      {executeOpen && executeTask ? (
        <Modal title="确认执行" onClose={() => setExecuteOpen(false)} footer={<><button className="btn btnGhost" onClick={() => setExecuteOpen(false)}>取消</button><button className="btn" onClick={confirmExecute}>确定</button></>}>
          <div className="muted" style={{ marginBottom: 12 }}>确定要执行“{executeTask.name}”吗？</div>
          <MiniForm value={pickPayload(executeTask)} onChange={() => undefined} readOnly />
        </Modal>
      ) : null}

      {terminateOpen && terminateTask ? (
        <Modal title="确认终止" onClose={() => setTerminateOpen(false)} footer={<><button className="btn btnGhost" onClick={() => setTerminateOpen(false)}>取消</button><button className="btn btnDanger" onClick={confirmTerminate}>确定</button></>}>
          <div className="muted">确定要终止“{terminateTask.name}”吗？</div>
        </Modal>
      ) : null}
    </main>
  );
}
