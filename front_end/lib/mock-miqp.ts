import type { Task, TaskPayload, TaskResultPayload, ValidationItem } from './types';

function hashSeed(id: string, salt: number) {
  let h = 0;
  const s = id + String(salt);
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

function mulberry32(seed: number) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

export function emptyTaskPayload(): TaskPayload {
  return {
    name: '',
    datasetName: 'miqp_sample_A.npz',
    n: 15,
    p: 5,
    m1: 5,
    m2: 1,
    solver: 'hybrid',
    maxQubits: 20,
    subQuboSize: 12,
    maxIterations: 12,
    timeLimitSec: 120,
    penaltyLambda: 8,
  };
}

export function createDemoTasks(): Task[] {
  const now = new Date().toISOString();
  const base = emptyTaskPayload();
  return [
    { id: 'miqp-demo-completed', ...base, name: '演示任务-miqp_sample_A', status: 'completed', createdAt: now },
    {
      id: 'miqp-demo-running',
      ...base,
      name: '演示任务-执行中-100变量',
      datasetName: 'miqp_sample_B.npz',
      n: 80,
      p: 20,
      m1: 20,
      m2: 4,
      subQuboSize: 18,
      maxIterations: 30,
      timeLimitSec: 1200,
      status: 'running',
      createdAt: now,
    },
    {
      id: 'miqp-demo-pending',
      ...base,
      name: '演示任务-miqp_sample_B',
      datasetName: 'miqp_sample_B.npz',
      n: 80,
      p: 20,
      m1: 20,
      m2: 4,
      subQuboSize: 18,
      maxIterations: 22,
      timeLimitSec: 900,
      status: 'pending',
      createdAt: now,
    },
  ];
}

function buildValidations(task: Task): ValidationItem[] {
  const v = (key: string, label: string, pass: boolean, reason: string): ValidationItem => ({
    key,
    label,
    pass,
    reason: pass ? undefined : reason,
  });
  return [
    v('qubit_limit', '量子比特上限（<=30）', task.maxQubits <= 30, '超过 30 比特会触发一票否决。'),
    v('subqubo_size', 'subQUBO 规模（建议<=20）', task.subQuboSize <= 20, '建议控制在 20 以内。'),
    v('size_n', '二元变量规模 n', task.n >= 10 && task.n <= 200, 'n 建议在 10~200。'),
    v('size_p', '连续变量规模 p', task.p >= 5 && task.p <= 50, 'p 建议在 5~50。'),
    v('constraints', '约束规模（m1,m2）', task.m1 > 0 && task.m2 >= 0, 'm1 需>0，m2 需>=0。'),
  ];
}

export function buildMockResult(task: Task): TaskResultPayload {
  const rnd = mulberry32(hashSeed(task.id, 9));
  const iters = Math.max(6, Math.min(40, task.maxIterations));
  const iterations = [] as TaskResultPayload['iterations'];

  let objective = 3000 + task.n * 8 + task.p * 12;
  let bestBound = objective * 1.16;
  let elapsed = 0;
  for (let i = 1; i <= iters; i++) {
    objective *= 0.9 + rnd() * 0.05;
    bestBound *= 0.91 + rnd() * 0.04;
    elapsed += 3 + rnd() * 4;
    const gapPct = Math.abs((objective - bestBound) / Math.max(1, Math.abs(objective))) * 100;
    iterations.push({
      iter: i,
      objective: Math.round(objective * 1000) / 1000,
      bestBound: Math.round(bestBound * 1000) / 1000,
      gapPct: Math.round(gapPct * 100) / 100,
      feasible: i > 1 || rnd() > 0.2,
      usedQubits: Math.min(task.maxQubits, Math.max(8, task.subQuboSize + Math.floor(rnd() * 3))),
      elapsedSec: Math.round(elapsed * 100) / 100,
      note: i % 4 === 0 ? '生成割平面并更新主问题' : undefined,
    });
  }

  const last = iterations[iterations.length - 1];
  const validations = buildValidations(task);
  const violations = validations.filter((x) => !x.pass).length;

  return {
    task,
    validations,
    summary: {
      bestObjective: last.objective,
      bestBound: last.bestBound,
      gapPct: last.gapPct,
      feasible: iterations.some((x) => x.feasible),
      constraintViolationCount: violations,
      usedQubits: Math.max(...iterations.map((x) => x.usedQubits)),
      selectedBinaryCount: Math.max(1, Math.round(task.n * (0.22 + rnd() * 0.12))),
      activeContinuousCount: Math.max(1, Math.round(task.p * (0.5 + rnd() * 0.3))),
      totalRuntimeSec: last.elapsedSec,
    },
    iterations,
    artifacts: [
      { title: '迭代收敛曲线', imageUrl: '/imgs/power_egine.gif', description: '示意图：目标值随迭代下降趋势。' },
      { title: 'subQUBO 划分示意', imageUrl: '/imgs/power_egine.gif', description: '示意图：变量分块与强耦合连接。' },
      { title: '可行解结构', imageUrl: '/imgs/power_egine.gif', description: '示意图：二元变量激活与连续变量分布。' },
    ],
    notes: '当前为前端假数据演示页。后续接入真实 MongoDB 结果后，页面结构可直接复用。',
  };
}
