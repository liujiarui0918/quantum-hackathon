'use client';

import { useMemo, useState } from 'react';
import { Modal } from '@/components/Modal';
import formStyles from '@/components/task-form.module.css';
import {
  buildLogisticsResult,
  createDemoLogisticsTasks,
  emptyLogisticsPayload,
  persistLogisticsResult,
  type LogisticsTask,
  type LogisticsTaskPayload,
  type LogisticsTaskStatus,
} from '@/lib/mock-logistics-routing';
import styles from './tasks.module.css';

function zhStatus(s: LogisticsTaskStatus) {
  if (s === 'pending') return '未执行';
  if (s === 'running') return '执行中';
  return '已完成';
}

function pickPayload(t: LogisticsTask): LogisticsTaskPayload {
  const { id: _id, status: _s, createdAt: _c, ...rest } = t;
  return rest;
}

function LogisticsForm({
  value,
  onChange,
  readOnly,
}: {
  value: LogisticsTaskPayload;
  onChange: (next: LogisticsTaskPayload) => void;
  readOnly?: boolean;
}) {
  const ro = readOnly ?? false;
  const patch = (p: Partial<LogisticsTaskPayload>) => onChange({ ...value, ...p });
  return (
    <div className={formStyles.grid}>
      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>任务名称</h3>
        <label className={formStyles.field}>
          <span className={formStyles.label}>任务名称</span>
          <input
            className={formStyles.input}
            value={value.name}
            disabled={ro}
            placeholder="请输入任务名称"
            onChange={(e) => patch({ name: e.target.value })}
          />
        </label>
      </section>

      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>规模</h3>
        <div className={formStyles.row3}>
          <label className={formStyles.field}>
            <span className={formStyles.label}>车辆数</span>
            <input
              className={formStyles.input}
              type="number"
              min={1}
              max={8}
              value={value.vehicleCount}
              disabled={ro}
              onChange={(e) => patch({ vehicleCount: Number(e.target.value) })}
            />
          </label>
          <label className={formStyles.field}>
            <span className={formStyles.label}>客户点数</span>
            <input
              className={formStyles.input}
              type="number"
              min={4}
              max={40}
              value={value.customerCount}
              disabled={ro}
              onChange={(e) => patch({ customerCount: Number(e.target.value) })}
            />
          </label>
          <label className={formStyles.field}>
            <span className={formStyles.label}>单车容量</span>
            <input
              className={formStyles.input}
              type="number"
              min={20}
              max={500}
              value={value.vehicleCapacity}
              disabled={ro}
              onChange={(e) => patch({ vehicleCapacity: Number(e.target.value) })}
            />
          </label>
        </div>
      </section>

      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>区域</h3>
        <label className={formStyles.field}>
          <span className={formStyles.label}>区域标签</span>
          <input
            className={formStyles.input}
            value={value.regionLabel}
            disabled={ro}
            onChange={(e) => patch({ regionLabel: e.target.value })}
          />
        </label>
      </section>

      <section className={formStyles.section}>
        <h3 className={formStyles.h3}>约束</h3>
        <label className={styles.checkLabel}>
          <input
            type="checkbox"
            className={styles.checkInput}
            checked={value.useTimeWindow}
            disabled={ro}
            onChange={(e) => patch({ useTimeWindow: e.target.checked })}
          />
          <span className={formStyles.label}>启用时间窗约束（演示）</span>
        </label>
      </section>
    </div>
  );
}

export default function LogisticsRoutingTasksPage() {
  const [tasks, setTasks] = useState<LogisticsTask[]>(() => createDemoLogisticsTasks());
  const [draft, setDraft] = useState<LogisticsTaskPayload>(() => emptyLogisticsPayload());
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<LogisticsTaskPayload>(() => emptyLogisticsPayload());

  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTask, setExecuteTask] = useState<LogisticsTask | null>(null);
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [terminateTask, setTerminateTask] = useState<LogisticsTask | null>(null);

  const closeCreate = () => {
    setCreateOpen(false);
    setDraft(emptyLogisticsPayload());
  };

  const submitCreate = () => {
    if (!draft.name.trim()) return;
    const t: LogisticsTask = {
      id: crypto.randomUUID(),
      ...draft,
      status: 'pending',
      createdAt: new Date().toISOString(),
    };
    setTasks((prev) => [t, ...prev]);
    closeCreate();
  };

  const openEdit = (t: LogisticsTask) => {
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

  const openResult = (t: LogisticsTask) => {
    const merged: LogisticsTask = { ...t, status: 'completed' };
    const result = buildLogisticsResult(merged);
    persistLogisticsResult(t.id, result);
    window.open(`/scenarios/logistics-routing/tasks/${t.id}/result`, '_blank', 'noopener,noreferrer');
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
        <div>
          <div className={styles.title}>物流路径规划 - 任务管理</div>
          <div className={styles.scenarioHint}>
            场景 3：多车从仓库服务一批客户，优化总距离/成本。整数变量刻画「是否从地点 i 前往 j」；约束含单客户一次服务、车辆容量与时间窗等。
            路径组合规模极大，约束略复杂即难以精确求解。本页为纯前端假数据演示。
          </div>
        </div>
        {headerRight}
      </div>

      <div className={styles.hint}>
        <span className="muted">共 {tasks.length} 条</span>
      </div>

      <div className={styles.list}>
        {tasks.map((t) => (
          <article key={t.id} className={styles.card}>
            <div className={styles.cardTop}>
              <div className={styles.name}>{t.name}</div>
              <div className={styles.status} data-status={t.status}>
                {zhStatus(t.status)}
              </div>
            </div>

            <div className={styles.groups}>
              <div className={styles.group}>
                <div className={styles.groupTitle}>规模与区域</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>车辆数</span>
                    <span className={styles.kvValue}>{t.vehicleCount}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>客户点数</span>
                    <span className={styles.kvValue}>{t.customerCount}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>单车容量</span>
                    <span className={styles.kvValue}>{t.vehicleCapacity}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>区域</span>
                    <span className={styles.kvValue}>{t.regionLabel}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>时间窗</span>
                    <span className={styles.kvValue}>{t.useTimeWindow ? '是' : '否'}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className={styles.actions}>
              {t.status === 'pending' ? (
                <button type="button" className="btn btnGhost" onClick={() => openEdit(t)}>
                  编辑
                </button>
              ) : null}
              {t.status === 'pending' ? (
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    setExecuteTask(t);
                    setExecuteOpen(true);
                  }}
                >
                  执行
                </button>
              ) : null}
              {t.status === 'running' ? (
                <button
                  type="button"
                  className="btn btnDanger"
                  onClick={() => {
                    setTerminateTask(t);
                    setTerminateOpen(true);
                  }}
                >
                  终止
                </button>
              ) : null}
              {t.status === 'completed' ? (
                <button type="button" className="btn" onClick={() => openResult(t)}>
                  查看结果
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>

      {createOpen ? (
        <Modal
          title="创建任务"
          onClose={closeCreate}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={closeCreate}>
                取消
              </button>
              <button type="button" className="btn" onClick={submitCreate}>
                确定
              </button>
            </>
          }
        >
          <LogisticsForm value={draft} onChange={setDraft} />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal
          title="编辑任务"
          onClose={() => setEditOpen(false)}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={() => setEditOpen(false)}>
                取消
              </button>
              <button type="button" className="btn" onClick={submitEdit}>
                确定
              </button>
            </>
          }
        >
          <LogisticsForm value={editDraft} onChange={setEditDraft} />
        </Modal>
      ) : null}

      {executeOpen && executeTask ? (
        <Modal
          title="确认执行"
          onClose={() => setExecuteOpen(false)}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={() => setExecuteOpen(false)}>
                取消
              </button>
              <button type="button" className="btn" onClick={confirmExecute}>
                确定
              </button>
            </>
          }
        >
          <div className="muted" style={{ marginBottom: 12, lineHeight: 1.65 }}>
            确定要执行「{executeTask.name}」吗？演示环境将直接标记为已完成并生成假数据结果。
          </div>
          <LogisticsForm value={pickPayload(executeTask)} onChange={() => undefined} readOnly />
        </Modal>
      ) : null}

      {terminateOpen && terminateTask ? (
        <Modal
          title="确认终止"
          onClose={() => setTerminateOpen(false)}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={() => setTerminateOpen(false)}>
                取消
              </button>
              <button type="button" className="btn btnDanger" onClick={confirmTerminate}>
                确定
              </button>
            </>
          }
        >
          <div className="muted">确定要终止「{terminateTask.name}」吗？</div>
        </Modal>
      ) : null}
    </main>
  );
}
