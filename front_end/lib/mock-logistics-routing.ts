/**
 * 物流路径规划场景 — 纯演示假数据，不请求后端。
 */

export type LogisticsTaskStatus = 'pending' | 'running' | 'completed';

export interface LogisticsTask {
  id: string;
  name: string;
  status: LogisticsTaskStatus;
  createdAt: string;
  vehicleCount: number;
  customerCount: number;
  vehicleCapacity: number;
  useTimeWindow: boolean;
  regionLabel: string;
}

export type LogisticsTaskPayload = Omit<LogisticsTask, 'id' | 'status' | 'createdAt'>;

export interface RouteNode {
  id: string;
  label: string;
  x: number;
  y: number;
  kind: 'depot' | 'customer';
  demand?: number;
}

export interface VehicleRoute {
  vehicleId: string;
  label: string;
  color: string;
  nodeIds: string[];
}

export interface CostPoint {
  iter: number;
  cost: number;
}

export interface LogisticsResult {
  task: LogisticsTask;
  totalDistanceKm: number;
  totalCost: number;
  violationRatePct: number;
  nodes: RouteNode[];
  routes: VehicleRoute[];
  costSeries: CostPoint[];
}

const ROUTE_COLORS = ['#3dffce', '#6ecbff', '#ffb86b', '#c792ea', '#82aaff'];

function hashId(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i += 1) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return h;
}

function mulberry32(seed: number) {
  return function rand() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function emptyLogisticsPayload(): LogisticsTaskPayload {
  return {
    name: '新建物流路径任务',
    vehicleCount: 3,
    customerCount: 12,
    vehicleCapacity: 100,
    useTimeWindow: true,
    regionLabel: '长三角',
  };
}

export function createDemoLogisticsTasks(): LogisticsTask[] {
  const now = new Date().toISOString();
  return [
    {
      id: 'demo-logistics-001',
      name: '演示任务-城配早高峰',
      status: 'completed',
      createdAt: now,
      vehicleCount: 3,
      customerCount: 10,
      vehicleCapacity: 120,
      useTimeWindow: true,
      regionLabel: '杭州主城区',
    },
    {
      id: 'demo-logistics-002',
      name: '演示任务-仓配一体化',
      status: 'pending',
      createdAt: now,
      vehicleCount: 4,
      customerCount: 18,
      vehicleCapacity: 160,
      useTimeWindow: false,
      regionLabel: '上海外环',
    },
    {
      id: 'demo-logistics-003',
      name: '演示任务-冷链时间窗',
      status: 'completed',
      createdAt: now,
      vehicleCount: 2,
      customerCount: 8,
      vehicleCapacity: 80,
      useTimeWindow: true,
      regionLabel: '苏锡常',
    },
  ];
}

export function findLogisticsTaskById(id: string): LogisticsTask | undefined {
  return createDemoLogisticsTasks().find((t) => t.id === id);
}

/** 由任务字段生成稳定的演示结果（路线图、成本曲线、违反率）。 */
export function buildLogisticsResult(task: LogisticsTask): LogisticsResult {
  const rand = mulberry32(hashId(task.id));
  const n = Math.max(4, Math.min(24, task.customerCount));
  const vCount = Math.max(1, Math.min(5, task.vehicleCount));

  const depot: RouteNode = {
    id: 'depot',
    label: '仓',
    x: 50,
    y: 50,
    kind: 'depot',
  };

  const customers: RouteNode[] = [];
  for (let i = 0; i < n; i += 1) {
    const angle = (i / n) * Math.PI * 2 + rand() * 0.35;
    const r = 28 + rand() * 18;
    const demand = Math.round(8 + rand() * (task.vehicleCapacity * 0.06));
    customers.push({
      id: `c${i + 1}`,
      label: `客${i + 1}`,
      x: 50 + Math.cos(angle) * r,
      y: 50 + Math.sin(angle) * r,
      kind: 'customer',
      demand,
    });
  }

  const nodes = [depot, ...customers];

  const chunks: RouteNode[][] = [];
  let idx = 0;
  const per = Math.ceil(n / vCount);
  for (let vi = 0; vi < vCount; vi += 1) {
    const slice = customers.slice(idx, idx + per);
    idx += slice.length;
    if (slice.length) chunks.push(slice);
  }

  const routes: VehicleRoute[] = chunks.map((slice, vi) => ({
    vehicleId: `V${vi + 1}`,
    label: `车辆 ${vi + 1}`,
    color: ROUTE_COLORS[vi % ROUTE_COLORS.length],
    nodeIds: ['depot', ...slice.map((c) => c.id), 'depot'],
  }));

  const baseCost = 8000 + n * 420 + vCount * 900;
  const steps = 36;
  const costSeries: CostPoint[] = [];
  let last = baseCost * (1.15 + rand() * 0.12);
  for (let iter = 0; iter < steps; iter += 1) {
    const t = iter / (steps - 1);
    const target = baseCost * (0.88 + rand() * 0.04);
    last = last * (1 - t * 0.038) + target * t * 0.02 + (rand() - 0.5) * baseCost * 0.012;
    costSeries.push({ iter: iter + 1, cost: Math.round(last) });
  }

  const totalDistanceKm = Math.round(12 + n * 2.1 + rand() * 8 + (task.useTimeWindow ? 4 : 0));
  const totalCost = costSeries[costSeries.length - 1]?.cost ?? baseCost;
  const violationBase = task.useTimeWindow ? 2.8 : 0.9;
  const violationRatePct = Math.round((violationBase + rand() * 1.4) * 10) / 10;

  return {
    task,
    totalDistanceKm,
    totalCost,
    violationRatePct,
    nodes,
    routes,
    costSeries,
  };
}

const STORAGE_KEY = 'logistics-routing-result';

export function persistLogisticsResult(taskId: string, result: LogisticsResult) {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(`${STORAGE_KEY}:${taskId}`, JSON.stringify(result));
}

export function loadLogisticsResult(taskId: string): LogisticsResult | null {
  if (typeof window === 'undefined') return null;
  const raw = sessionStorage.getItem(`${STORAGE_KEY}:${taskId}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LogisticsResult;
  } catch {
    return null;
  }
}

/** 无 session 时：仅对已完成的内置演示任务可还原结果。 */
export function tryLoadLogisticsResult(taskId: string): LogisticsResult | null {
  const fromSession = loadLogisticsResult(taskId);
  if (fromSession) return fromSession;
  const t = findLogisticsTaskById(taskId);
  if (t?.status === 'completed') return buildLogisticsResult(t);
  return null;
}
