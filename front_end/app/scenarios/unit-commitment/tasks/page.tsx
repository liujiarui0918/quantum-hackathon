'use client';

import { useCallback, useEffect, useState } from 'react';
import type { DragEvent } from 'react';
import { Modal } from '@/components/Modal';
import { TaskFieldsForm } from '@/components/TaskFieldsForm';
import { api } from '@/lib/axios-client';
import { emptyTaskPayload } from '@/lib/mock-miqp';
import type { Task, TaskPayload, TaskStatus } from '@/lib/types';
import styles from './tasks.module.css';

function zhStatus(s: TaskStatus) {
  if (s === 'pending') return '未执行';
  if (s === 'running') return '执行中';
  return '已完成';
}

function pickPayload(t: Task): TaskPayload {
  const { id: _id, status: _s, createdAt: _c, result: _r, ...rest } = t;
  return rest;
}

type UploadItem = { id: string; file: File; previewUrl: string };
type Filters = { datasetName: string; n: string; p: string; m1: string; m2: string };

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [executeOpen, setExecuteOpen] = useState(false);
  const [executeTask, setExecuteTask] = useState<Task | null>(null);
  const [terminateOpen, setTerminateOpen] = useState(false);
  const [terminateTask, setTerminateTask] = useState<Task | null>(null);

  const [recordOpen, setRecordOpen] = useState(false);
  const [recordTask, setRecordTask] = useState<Task | null>(null);
  const [recordText, setRecordText] = useState('');
  const [recordMsg, setRecordMsg] = useState<string | null>(null);
  const [runningImages, setRunningImages] = useState<UploadItem[]>([]);
  const [compareImages, setCompareImages] = useState<UploadItem[]>([]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');

  const [draft, setDraft] = useState<TaskPayload>(() => emptyTaskPayload());
  const [editDraft, setEditDraft] = useState<TaskPayload>(() => emptyTaskPayload());

  const [filters, setFilters] = useState<Filters>({ datasetName: '', n: '', p: '', m1: '', m2: '' });
  const [queryFilters, setQueryFilters] = useState<Filters>({ datasetName: '', n: '', p: '', m1: '', m2: '' });

  const showToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 1800);
  };

  const refresh = useCallback(async (nextFilters?: Filters) => {
    const f = nextFilters ?? queryFilters;
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (f.datasetName) params.datasetName = f.datasetName;
      if (f.n) params.n = f.n;
      if (f.p) params.p = f.p;
      if (f.m1) params.m1 = f.m1;
      if (f.m2) params.m2 = f.m2;
      const res = await api.get<{ data: Task[] }>('/api/tasks', { params });
      setTasks(res.data.data);
    } finally {
      setLoading(false);
    }
  }, [queryFilters]);

  useEffect(() => {
    void refresh(queryFilters);
  }, []);

  useEffect(() => {
    if (!tasks.some((t) => t.status === 'running')) return;
    const id = window.setInterval(() => {
      void refresh(queryFilters);
    }, 2000);
    return () => window.clearInterval(id);
  }, [tasks, refresh, queryFilters]);

  const closeCreate = () => {
    setCreateOpen(false);
    setDraft(emptyTaskPayload());
  };

  const submitCreate = async () => {
    if (!draft.name.trim()) return;
    await api.post('/api/tasks', draft);
    closeCreate();
    await refresh(queryFilters);
  };

  const openEdit = (t: Task) => {
    setEditId(t.id);
    setEditDraft(pickPayload(t));
    setEditOpen(true);
  };

  const submitEdit = async () => {
    if (!editId || !editDraft.name.trim()) return;
    await api.put(`/api/tasks/${editId}`, editDraft);
    setEditOpen(false);
    setEditId(null);
    await refresh(queryFilters);
    showToast('编辑成功');
  };

  const confirmExecute = async () => {
    if (!executeTask) return;
    await api.post(`/api/tasks/${executeTask.id}/execute`);
    setExecuteOpen(false);
    setExecuteTask(null);
    await refresh(queryFilters);
    showToast('任务开始执行');
  };

  const confirmTerminate = async () => {
    if (!terminateTask) return;
    await api.post(`/api/tasks/${terminateTask.id}/terminate`);
    setTerminateOpen(false);
    setTerminateTask(null);
    await refresh(queryFilters);
    showToast('该任务已终止');
  };

  const openRecord = (t: Task) => {
    setRecordTask(t);
    setRecordMsg(null);
    setRecordText('');
    setRunningImages([]);
    setCompareImages([]);
    setRecordOpen(true);
  };

  const reorder = <T,>(arr: T[], from: number, to: number) => {
    const next = arr.slice();
    const [m] = next.splice(from, 1);
    next.splice(to, 0, m);
    return next;
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>, idx: number, type: 'running' | 'compare') => {
    e.preventDefault();
    const from = Number(e.dataTransfer.getData('text/plain'));
    if (Number.isNaN(from)) return;
    if (type === 'running') setRunningImages((prev) => reorder(prev, from, idx));
    else setCompareImages((prev) => reorder(prev, from, idx));
  };

  const appendFiles = (files: FileList | null, type: 'running' | 'compare') => {
    if (!files || files.length === 0) return;
    const mapped = Array.from(files).map((file) => ({ id: crypto.randomUUID(), file, previewUrl: URL.createObjectURL(file) }));
    if (type === 'running') setRunningImages((prev) => [...prev, ...mapped]);
    else setCompareImages((prev) => [...prev, ...mapped]);
  };

  const removeUpload = (id: string, type: 'running' | 'compare') => {
    if (type === 'running') {
      setRunningImages((prev) => {
        const target = prev.find((x) => x.id === id);
        if (target) URL.revokeObjectURL(target.previewUrl);
        return prev.filter((x) => x.id !== id);
      });
      return;
    }
    setCompareImages((prev) => {
      const target = prev.find((x) => x.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((x) => x.id !== id);
    });
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

  const submitRecord = async () => {
    if (!recordTask) return;
    try {
      JSON.parse(recordText);
      const form = new FormData();
      form.set('rawJson', recordText);
      runningImages.forEach((x) => form.append('runningImages', x.file));
      compareImages.forEach((x) => form.append('compareImages', x.file));
      await api.post(`/api/tasks/${recordTask.id}/import-result`, form);
      setRecordOpen(false);
      setRecordTask(null);
      setRecordMsg(null);
      setRecordText('');
      runningImages.forEach((x) => URL.revokeObjectURL(x.previewUrl));
      compareImages.forEach((x) => URL.revokeObjectURL(x.previewUrl));
      setRunningImages([]);
      setCompareImages([]);
      await refresh(queryFilters);
      showToast('结果导入成功');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'JSON 解析失败';
      setRecordMsg(`提交失败：${msg}`);
    }
  };

  const openResult = (t: Task) => {
    window.open(`/scenarios/unit-commitment/tasks/${t.id}/result`, '_blank', 'noopener,noreferrer');
  };

  return (
    <main className={`panel ${styles.pageRoot}`} style={{ padding: 16, position: 'relative' }}>
      {toast ? (
        <div style={{ position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 80, padding: '12px 18px', borderRadius: 12, border: '1px solid rgba(61,255,206,0.4)', background: 'rgba(6,20,30,0.96)', color: 'var(--text)', boxShadow: '0 10px 28px rgba(0,0,0,0.45)', fontWeight: 700 }}>
          {toast}
        </div>
      ) : null}

      <div className={styles.titleRow}>
        <div className={styles.title}>混合整数优化赛题 - 任务管理</div>
      </div>

      <div className={styles.filtersWrap}>
        <div className={styles.filtersGrid}>
          <label className={styles.filterItem}>
            <span className={styles.filterLabel}>数据集</span>
            <select className={styles.filterSelect} value={filters.datasetName} onChange={(e) => setFilters((prev) => ({ ...prev, datasetName: e.target.value }))}>
              <option value="">全部</option>
              <option value="miqp_sample_A.npz">miqp_sample_A.npz</option>
              <option value="miqp_sample_B.npz">miqp_sample_B.npz</option>
              <option value="miqp_test_1.npz">miqp_test_1.npz</option>
              <option value="miqp_test_2.npz">miqp_test_2.npz</option>
              <option value="miqp_test_3.npz">miqp_test_3.npz</option>
              <option value="miqp_test_4.npz">miqp_test_4.npz</option>
              <option value="miqp_test_5.npz">miqp_test_5.npz</option>
            </select>
          </label>
          <label className={styles.filterItem}><span className={styles.filterLabel}>二元变量 n</span><input className={styles.filterInput} value={filters.n} onChange={(e) => setFilters((prev) => ({ ...prev, n: e.target.value }))} /></label>
          <label className={styles.filterItem}><span className={styles.filterLabel}>连续变量 p</span><input className={styles.filterInput} value={filters.p} onChange={(e) => setFilters((prev) => ({ ...prev, p: e.target.value }))} /></label>
          <label className={styles.filterItem}><span className={styles.filterLabel}>混合约束 m1</span><input className={styles.filterInput} value={filters.m1} onChange={(e) => setFilters((prev) => ({ ...prev, m1: e.target.value }))} /></label>
          <label className={styles.filterItem}><span className={styles.filterLabel}>纯二元约束 m2</span><input className={styles.filterInput} value={filters.m2} onChange={(e) => setFilters((prev) => ({ ...prev, m2: e.target.value }))} /></label>
          <div />
        </div>
        <div className={styles.filterActions}>
          <button type="button" className="btn" onClick={() => setCreateOpen(true)}>创建任务</button>
          <button
            type="button"
            className="btn btnGhost"
            onClick={() => {
              const reset = { datasetName: '', n: '', p: '', m1: '', m2: '' };
              setFilters(reset);
              setQueryFilters(reset);
              void refresh(reset);
            }}
          >
            重置
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => {
              setQueryFilters(filters);
              void refresh(filters);
            }}
          >
            搜索
          </button>
        </div>
      </div>

      <div className={styles.hint}>{loading ? <span className="muted">加载中…</span> : <span className="muted">共 {tasks.length} 条</span>}</div>

      <div className={styles.tableWrap}>
        <table className={styles.taskTable}>
          <thead>
            <tr>
              <th>编号</th>
              <th>任务名称</th>
              <th>数据集</th>
              <th>二元变量n</th>
              <th>连续变量p</th>
              <th>混合约束m1</th>
              <th>纯二元约束m2</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t, idx) => (
              <tr key={t.id}>
                <td>{idx + 1}</td>
                <td>{t.name}</td>
                <td>{t.datasetName}</td>
                <td>{t.n}</td>
                <td>{t.p}</td>
                <td>{t.m1}</td>
                <td>{t.m2}</td>
                <td><span className={styles.status} data-status={t.status}>{zhStatus(t.status)}</span></td>
                <td>
                  <div className={styles.actionsInline}>
                    {t.status === 'pending' ? <button type="button" className="btn btnGhost" onClick={() => openEdit(t)}>编辑</button> : null}
                    {t.status === 'pending' ? <button type="button" className="btn" onClick={() => { setExecuteTask(t); setExecuteOpen(true); }}>执行</button> : null}
                    {t.status === 'running' ? <button type="button" className="btn btnDanger" onClick={() => { setTerminateTask(t); setTerminateOpen(true); }}>终止</button> : null}
                    {t.status === 'running' ? <button type="button" className="btn" onClick={() => openRecord(t)}>导入结果</button> : null}
                    {t.status === 'completed' ? <button type="button" className="btn" onClick={() => openResult(t)}>查看结果</button> : null}
                    <button type="button" className="btn btnGhost" onClick={async () => { if (!window.confirm('确认删除该任务么？')) return; await api.delete(`/api/tasks/${t.id}`); await refresh(queryFilters); showToast('删除成功'); }}>删除</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {createOpen ? (
        <Modal title="创建任务" onClose={closeCreate} footer={<><button type="button" className="btn btnGhost" onClick={closeCreate}>取消</button><button type="button" className="btn" onClick={() => void submitCreate()}>确定</button></>}>
          <TaskFieldsForm value={draft} onChange={setDraft} />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal title="编辑任务" onClose={() => setEditOpen(false)} footer={<><button type="button" className="btn btnGhost" onClick={() => setEditOpen(false)}>取消</button><button type="button" className="btn" onClick={() => void submitEdit()}>确定</button></>}>
          <TaskFieldsForm value={editDraft} onChange={setEditDraft} />
        </Modal>
      ) : null}

      {executeOpen && executeTask ? (
        <Modal title="确认执行" onClose={() => setExecuteOpen(false)} footer={<><button type="button" className="btn btnGhost" onClick={() => setExecuteOpen(false)}>取消</button><button type="button" className="btn" onClick={() => void confirmExecute()}>确定</button></>}>
          <div className="muted" style={{ lineHeight: 1.7, marginBottom: 12 }}>确定要执行“{executeTask.name}”任务吗？</div>
          <TaskFieldsForm value={pickPayload(executeTask)} onChange={() => undefined} readOnly />
        </Modal>
      ) : null}

      {terminateOpen && terminateTask ? (
        <Modal title="确认终止" onClose={() => setTerminateOpen(false)} footer={<><button type="button" className="btn btnGhost" onClick={() => setTerminateOpen(false)}>取消</button><button type="button" className="btn btnDanger" onClick={() => void confirmTerminate()}>确认</button></>}>
          <div className="muted" style={{ lineHeight: 1.7 }}>确认是否终止执行该任务</div>
        </Modal>
      ) : null}

      {recordOpen && recordTask ? (
        <Modal title={`导入结果 - ${recordTask.name}`} onClose={() => { setRecordOpen(false); setRecordTask(null); }} width={860} footer={<><button type="button" className="btn btnGhost" onClick={() => { runningImages.forEach((x) => URL.revokeObjectURL(x.previewUrl)); compareImages.forEach((x) => URL.revokeObjectURL(x.previewUrl)); setRecordOpen(false); setRecordTask(null); setRunningImages([]); setCompareImages([]); }}>取消</button><button type="button" className="btn" onClick={() => void submitRecord()}>提交</button></>}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <button type="button" className="btn btnGhost" onClick={validateJson}>JSON 校验</button>
            <button type="button" className="btn btnGhost" onClick={formatJson}>JSON 美化</button>
          </div>
          <textarea value={recordText} onChange={(e) => setRecordText(e.target.value)} placeholder="请粘贴结果 JSON" style={{ width: '100%', minHeight: 200, resize: 'vertical', borderRadius: 10, border: '1px solid rgba(110,203,255,0.22)', background: 'rgba(4,8,18,0.55)', color: 'var(--text)', padding: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 13, lineHeight: 1.55 }} />

          <div style={{ marginTop: 16 }}>
            <div className={styles.groupTitle} style={{ marginBottom: 8 }}>运行信息（多图）</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 8 }}>
              <label style={{ width: 92, height: 92, borderRadius: 10, border: '1px dashed rgba(110,203,255,0.45)', background: 'rgba(6,12,28,0.3)', display: 'grid', placeItems: 'center', cursor: 'pointer', fontSize: 32, color: 'rgba(138,164,191,0.95)' }}>+
                <input type="file" accept="image/*" multiple style={{ display: 'none' }} onChange={(e) => appendFiles(e.target.files, 'running')} />
              </label>
              {runningImages.map((f, idx) => (
                <div key={f.id} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', String(idx))} onDragOver={(e) => e.preventDefault()} onDrop={(e) => handleDrop(e, idx, 'running')} style={{ width: 92, height: 92, border: '1px solid rgba(110,203,255,0.2)', borderRadius: 10, background: 'rgba(6,12,28,0.35)', position: 'relative', overflow: 'hidden', cursor: 'grab' }}>
                  <img src={f.previewUrl} alt={f.file.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} onClick={() => { setPreviewUrl(f.previewUrl); setPreviewOpen(true); }} />
                  <button type="button" onClick={(e) => { e.stopPropagation(); removeUpload(f.id, 'running'); }} style={{ position: 'absolute', top: 4, right: 4, width: 20, height: 20, borderRadius: '50%', border: 'none', background: 'rgba(0,0,0,0.65)', color: '#fff', cursor: 'pointer', lineHeight: '20px', padding: 0 }}>×</button>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <div className={styles.groupTitle} style={{ marginBottom: 8 }}>比对信息（多图）</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 8 }}>
              <label style={{ width: 92, height: 92, borderRadius: 10, border: '1px dashed rgba(110,203,255,0.45)', background: 'rgba(6,12,28,0.3)', display: 'grid', placeItems: 'center', cursor: 'pointer', fontSize: 32, color: 'rgba(138,164,191,0.95)' }}>+
                <input type="file" accept="image/*" multiple style={{ display: 'none' }} onChange={(e) => appendFiles(e.target.files, 'compare')} />
              </label>
              {compareImages.map((f, idx) => (
                <div key={f.id} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', String(idx))} onDragOver={(e) => e.preventDefault()} onDrop={(e) => handleDrop(e, idx, 'compare')} style={{ width: 92, height: 92, border: '1px solid rgba(110,203,255,0.2)', borderRadius: 10, background: 'rgba(6,12,28,0.35)', position: 'relative', overflow: 'hidden', cursor: 'grab' }}>
                  <img src={f.previewUrl} alt={f.file.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} onClick={() => { setPreviewUrl(f.previewUrl); setPreviewOpen(true); }} />
                  <button type="button" onClick={(e) => { e.stopPropagation(); removeUpload(f.id, 'compare'); }} style={{ position: 'absolute', top: 4, right: 4, width: 20, height: 20, borderRadius: '50%', border: 'none', background: 'rgba(0,0,0,0.65)', color: '#fff', cursor: 'pointer', lineHeight: '20px', padding: 0 }}>×</button>
                </div>
              ))}
            </div>
          </div>

          {recordMsg ? <div className="muted" style={{ marginTop: 10 }}>{recordMsg}</div> : null}
        </Modal>
      ) : null}

      {previewOpen ? (
        <Modal title="图片预览" onClose={() => setPreviewOpen(false)} width={980} footer={<button type="button" className="btn" onClick={() => setPreviewOpen(false)}>关闭</button>}>
          <div style={{ width: '100%', minHeight: 420, display: 'grid', placeItems: 'center' }}>
            <img src={previewUrl} alt="preview" style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain' }} />
          </div>
        </Modal>
      ) : null}
    </main>
  );
}
