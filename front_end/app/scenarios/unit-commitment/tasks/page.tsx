'use client';

import { useMemo, useState } from 'react';
import { Modal } from '@/components/Modal';
import { TaskFieldsForm } from '@/components/TaskFieldsForm';
import { buildMockResult, createDemoTasks, emptyTaskPayload } from '@/lib/mock-miqp';
import type { Task, TaskPayload, TaskStatus } from '@/lib/types';
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

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>(() => createDemoTasks());
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTask, setExecuteTask] = useState<Task | null>(null);
  const [recordOpen, setRecordOpen] = useState(false);
  const [recordTask, setRecordTask] = useState<Task | null>(null);
  const [recordText, setRecordText] = useState('');
  const [recordMsg, setRecordMsg] = useState<string | null>(null);

  const [draft, setDraft] = useState<TaskPayload>(() => emptyTaskPayload());
  const [editDraft, setEditDraft] = useState<TaskPayload>(() => emptyTaskPayload());

  const closeCreate = () => {
    setCreateOpen(false);
    setDraft(emptyTaskPayload());
  };

  const submitCreate = () => {
    if (!draft.name.trim()) return;
    const t: Task = {
      id: crypto.randomUUID(),
      ...draft,
      status: 'pending',
      createdAt: new Date().toISOString(),
    };
    setTasks((prev) => [t, ...prev]);
    closeCreate();
  };

  const openEdit = (t: Task) => {
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

  const openRecord = (t: Task) => {
    setRecordTask(t);
    setRecordMsg(null);
    setRecordText('');
    setRecordOpen(true);
  };

  const validateJson = () => {
    try {
      JSON.parse(recordText);
      setRecordMsg('JSON 校验通过');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'JSON 解析失败';
      setRecordMsg(`JSON 校验失败：${msg}`);
    }
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(recordText);
      setRecordText(JSON.stringify(parsed, null, 2));
      setRecordMsg('JSON 已美化');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'JSON 解析失败';
      setRecordMsg(`JSON 美化失败：${msg}`);
    }
  };

  const submitRecord = () => {
    if (!recordTask) return;
    try {
      JSON.parse(recordText);
      sessionStorage.setItem(`miqp-manual-result:${recordTask.id}`, recordText);
      setRecordMsg('结果已本地保存（sessionStorage）');
      setRecordOpen(false);
      setRecordTask(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'JSON 解析失败';
      setRecordMsg(`提交失败：${msg}`);
    }
  };

  const openResult = (t: Task) => {
    const result = buildMockResult(t);
    sessionStorage.setItem(`miqp-result:${t.id}`, JSON.stringify(result));
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
        <div className={styles.title}>混合整数优化赛题 - 任务管理</div>
        {headerRight}
      </div>

      <div className={styles.hint}>
        <span className="muted">共 {tasks.length} 条（当前为前端假数据演示）</span>
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
                <div className={styles.groupTitle}>问题规模</div>
                <div className={styles.kvGrid}>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>数据集</span><span className={styles.kvValue}>{t.datasetName}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>二元变量 n</span><span className={styles.kvValue}>{t.n}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>连续变量 p</span><span className={styles.kvValue}>{t.p}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>混合约束 m1</span><span className={styles.kvValue}>{t.m1}</span></div>
                  <div className={styles.kvItem}><span className={styles.kvLabel}>纯二元约束 m2</span><span className={styles.kvValue}>{t.m2}</span></div>
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
                <button type="button" className="btn" onClick={() => { setExecuteTask(t); setExecuteOpen(true); }}>
                  执行
                </button>
              ) : null}
              {t.status === 'running' ? (
                <button type="button" className="btn" onClick={() => openRecord(t)}>
                  结果录入
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
              <button type="button" className="btn btnGhost" onClick={closeCreate}>取消</button>
              <button type="button" className="btn" onClick={submitCreate}>确定</button>
            </>
          }
        >
          <TaskFieldsForm value={draft} onChange={setDraft} />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal
          title="编辑任务"
          onClose={() => setEditOpen(false)}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={() => setEditOpen(false)}>取消</button>
              <button type="button" className="btn" onClick={submitEdit}>确定</button>
            </>
          }
        >
          <TaskFieldsForm value={editDraft} onChange={setEditDraft} />
        </Modal>
      ) : null}

      {executeOpen && executeTask ? (
        <Modal
          title="确认执行"
          onClose={() => setExecuteOpen(false)}
          footer={
            <>
              <button type="button" className="btn btnGhost" onClick={() => setExecuteOpen(false)}>取消</button>
              <button type="button" className="btn" onClick={confirmExecute}>确定</button>
            </>
          }
        >
          <div className="muted" style={{ lineHeight: 1.7, marginBottom: 12 }}>
            确定要执行“{executeTask.name}”任务吗？
          </div>
          <TaskFieldsForm value={pickPayload(executeTask)} onChange={() => undefined} readOnly />
        </Modal>
      ) : null}

      {recordOpen && recordTask ? (
        <Modal
          title={`结果录入 - ${recordTask.name}`}
          onClose={() => {
            setRecordOpen(false);
            setRecordTask(null);
          }}
          width={860}
          footer={
            <>
              <button
                type="button"
                className="btn btnGhost"
                onClick={() => {
                  setRecordOpen(false);
                  setRecordTask(null);
                }}
              >
                取消
              </button>
              <button type="button" className="btn" onClick={submitRecord}>
                提交
              </button>
            </>
          }
        >
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <button type="button" className="btn btnGhost" onClick={validateJson}>JSON 校验</button>
            <button type="button" className="btn btnGhost" onClick={formatJson}>JSON 美化</button>
          </div>
          <textarea
            value={recordText}
            onChange={(e) => setRecordText(e.target.value)}
            placeholder="请粘贴结果 JSON"
            style={{
              width: '100%',
              minHeight: 340,
              resize: 'vertical',
              borderRadius: 10,
              border: '1px solid rgba(110,203,255,0.22)',
              background: 'rgba(4,8,18,0.55)',
              color: 'var(--text)',
              padding: 12,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              fontSize: 13,
              lineHeight: 1.55,
            }}
          />
          {recordMsg ? <div className="muted" style={{ marginTop: 10 }}>{recordMsg}</div> : null}
        </Modal>
      ) : null}
    </main>
  );
}
