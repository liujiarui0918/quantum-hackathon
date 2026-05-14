'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/axios-client';
import type { Task, TaskPayload, TaskStatus } from '@/lib/types';
import { Modal } from '@/components/Modal';
import { emptyTaskPayload, TaskFieldsForm } from '@/components/TaskFieldsForm';
import styles from './tasks.module.css';

function zhStatus(s: TaskStatus) {
  if (s === 'pending') return '未执行';
  if (s === 'running') return '执行中';
  return '已完成';
}

function pickPayload(t: Task): TaskPayload {
  const { id: _id, status: _s, createdAt: _c, ...rest } = t;
  return rest;
}

async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<{ data: Task[] }>('/api/tasks');
      setTasks(res.data.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!tasks.some((t) => t.status === 'running')) return;
    const id = window.setInterval(() => {
      void refresh();
    }, 2000);
    return () => window.clearInterval(id);
  }, [tasks, refresh]);

  const [createOpen, setCreateOpen] = useState(false);
  const [draft, setDraft] = useState<TaskPayload>(() => emptyTaskPayload());

  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<TaskPayload>(() => emptyTaskPayload());

  const [terminateOpen, setTerminateOpen] = useState(false);
  const [terminateTask, setTerminateTask] = useState<Task | null>(null);

  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTask, setExecuteTask] = useState<Task | null>(null);

  const closeCreate = () => {
    setCreateOpen(false);
    setDraft(emptyTaskPayload());
  };

  const submitCreate = async () => {
    if (!draft.name.trim()) return;
    await api.post('/api/tasks', draft);
    closeCreate();
    await refresh();
  };

  const openEdit = (t: Task) => {
    setEditId(t.id);
    setEditDraft(pickPayload(t));
    setEditOpen(true);
  };

  const closeEdit = () => {
    setEditOpen(false);
    setEditId(null);
    setEditDraft(emptyTaskPayload());
  };

  const submitEdit = async () => {
    if (!editId) return;
    if (!editDraft.name.trim()) return;
    await api.put(`/api/tasks/${editId}`, editDraft);
    closeEdit();
    await refresh();
  };

  const openTerminate = (t: Task) => {
    setTerminateTask(t);
    setTerminateOpen(true);
  };

  const closeTerminate = () => {
    setTerminateOpen(false);
    setTerminateTask(null);
  };

  const confirmTerminate = async () => {
    if (!terminateTask) return;
    await api.post(`/api/tasks/${terminateTask.id}/terminate`);
    closeTerminate();
    await sleep(2000);
    await refresh();
  };

  const openExecute = (t: Task) => {
    setExecuteTask(t);
    setExecuteOpen(true);
  };

  const closeExecute = () => {
    setExecuteOpen(false);
    setExecuteTask(null);
  };

  const confirmExecute = async () => {
    if (!executeTask) return;
    await api.post(`/api/tasks/${executeTask.id}/execute`);
    closeExecute();
    await sleep(2000);
    await refresh();
  };

  const openResult = (t: Task) => {
    window.open(`/scenarios/unit-commitment/tasks/${t.id}/result`, '_blank', 'noopener,noreferrer');
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
        <div className={styles.title}>发电机组调度 - 任务管理</div>
        {headerRight}
      </div>

      <div className={styles.hint}>
        {loading ? <span className="muted">加载中…</span> : <span className="muted">共 {tasks.length} 条</span>}
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
                <div className={styles.groupTitle}>基础设置</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>机组数量</span>
                    <span className={styles.kvValue}>{t.counts}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>调度时段</span>
                    <span className={styles.kvValue}>{t.period}</span>
                  </div>
                </div>
              </div>
              <div className={styles.group}>
                <div className={styles.groupTitle}>系统约束</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>目标负荷</span>
                    <span className={styles.kvValue}>{t.targetNeed} MW</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>备用上限</span>
                    <span className={styles.kvValue}>{t.backNeed} MW</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>碳排限额</span>
                    <span className={styles.kvValue}>{t.co2Limit} 吨/天</span>
                  </div>
                </div>
              </div>
              <div className={styles.group}>
                <div className={styles.groupTitle}>单机组约束</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>最小输出</span>
                    <span className={styles.kvValue}>{t.minOutput} MW</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>最大输出</span>
                    <span className={styles.kvValue}>{t.maxOutput} MW</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>爬坡</span>
                    <span className={styles.kvValue}>{t.changeOimit} MW/min</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>启停</span>
                    <span className={styles.kvValue}>{t.startAndEndTime}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>碳排放系数</span>
                    <span className={styles.kvValue}>{t.co2Counts}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>启动成本</span>
                    <span className={styles.kvValue}>{t.startCosts}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>关停成本</span>
                    <span className={styles.kvValue}>{t.endCosts}</span>
                  </div>
                  <div className={styles.kvItem}>
                    <span className={styles.kvLabel}>燃料成本</span>
                    <span className={styles.kvValue}>{t.fuelCosts}</span>
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
              {t.status === 'running' ? (
                <button type="button" className="btn btnDanger" onClick={() => openTerminate(t)}>
                  终止
                </button>
              ) : null}
              {t.status === 'pending' ? (
                <button type="button" className="btn" onClick={() => openExecute(t)}>
                  执行
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
              <button type="button" className="btn" onClick={() => void submitCreate()}>
                确定
              </button>
            </>
          }
        >
          <TaskFieldsForm value={draft} onChange={setDraft} />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal
          title="编辑任务"
          onClose={closeEdit}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={closeEdit}>
                取消
              </button>
              <button type="button" className="btn" onClick={() => void submitEdit()}>
                确定
              </button>
            </>
          }
        >
          <TaskFieldsForm value={editDraft} onChange={setEditDraft} />
        </Modal>
      ) : null}

      {terminateOpen && terminateTask ? (
        <Modal
          title="确认终止"
          onClose={closeTerminate}
          width={560}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={closeTerminate}>
                取消
              </button>
              <button type="button" className="btn btnDanger" onClick={() => void confirmTerminate()}>
                确定
              </button>
            </>
          }
        >
          <div className="muted" style={{ lineHeight: 1.7 }}>
            确定要终止“{terminateTask.name}”的任务么？
          </div>
        </Modal>
      ) : null}

      {executeOpen && executeTask ? (
        <Modal
          title="确认执行"
          onClose={closeExecute}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={closeExecute}>
                取消
              </button>
              <button type="button" className="btn" onClick={() => void confirmExecute()}>
                确定
              </button>
            </>
          }
        >
          <div className="muted" style={{ lineHeight: 1.7, marginBottom: 12 }}>
            确定要执行“{executeTask.name}”的任务么？
          </div>
          <TaskFieldsForm value={pickPayload(executeTask)} onChange={() => undefined} readOnly />
        </Modal>
      ) : null}
    </main>
  );
}
