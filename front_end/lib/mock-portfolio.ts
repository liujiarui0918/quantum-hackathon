import type { PortfolioResultPayload, PortfolioTask, PortfolioTaskPayload } from './portfolio-types';

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

export function emptyPortfolioPayload(): PortfolioTaskPayload {
  return {
    name: '',
    budget: 5_000_000,
    assetUniverseSize: 40,
    maxHoldings: 10,
    minExpectedReturn: 9.5,
    riskLimit: 0.03,
    maxWeightPerAsset: 0.2,
    cardinalityPenalty: 0.015,
  };
}

export function createDemoPortfolioTasks(): PortfolioTask[] {
  const now = new Date().toISOString();
  const base = emptyPortfolioPayload();
  return [
    { id: 'portfolio-demo-completed', ...base, name: '演示任务-稳健成长组合', status: 'completed', createdAt: now },
    { id: 'portfolio-demo-pending', ...base, name: '演示任务-未执行', status: 'pending', createdAt: now },
  ];
}

export function buildPortfolioResult(task: PortfolioTask): PortfolioResultPayload {
  const rnd = mulberry32(hashSeed(task.id, 23));
  const n = Math.max(12, Math.min(100, Math.floor(task.assetUniverseSize)));
  const maxK = Math.max(2, Math.min(n, Math.floor(task.maxHoldings)));
  const chosenCount = Math.max(2, Math.min(maxK, Math.floor(maxK * (0.8 + rnd() * 0.2))));
  const chosenIdx = new Set<number>();
  while (chosenIdx.size < chosenCount) chosenIdx.add(Math.floor(rnd() * n));

  const baseWeights: number[] = [];
  for (let i = 0; i < chosenCount; i++) baseWeights.push(0.2 + rnd());
  const weightSum = baseWeights.reduce((s, x) => s + x, 0);
  let ws = baseWeights.map((w) => w / weightSum);
  ws = ws.map((w) => Math.min(task.maxWeightPerAsset, w));
  const ws2 = ws.reduce((s, x) => s + x, 0);
  ws = ws.map((w) => w / ws2);

  const assets = Array.from({ length: n }).map((_, i) => {
    const selected = chosenIdx.has(i);
    const price = Math.round((25 + rnd() * 180) * 100) / 100;
    const expectedReturn = Math.round((5 + rnd() * 14) * 100) / 100;
    const marginalRisk = Math.round((0.01 + rnd() * 0.05) * 10000) / 10000;
    const pos = Array.from(chosenIdx).indexOf(i);
    const weight = selected && pos >= 0 ? ws[pos] : 0;
    const amount = task.budget * weight;
    const units = selected ? Math.max(1, Math.floor(amount / price / 100) * 100) : 0;
    return {
      code: `A${String(i + 1).padStart(3, '0')}`,
      name: `资产-${i + 1}`,
      selected,
      units,
      price,
      expectedReturn,
      weight: Math.round(weight * 10000) / 10000,
      marginalRisk,
    };
  });

  const selectedAssets = assets.filter((a) => a.selected);
  const investedAmount = selectedAssets.reduce((s, a) => s + a.units * a.price, 0);
  const cashRemain = Math.max(0, task.budget - investedAmount);
  const expectedReturnPct =
    selectedAssets.reduce((s, a) => s + a.weight * a.expectedReturn, 0);

  // w'Σw
  const cov: number[][] = Array.from({ length: selectedAssets.length }).map((_, i) =>
    Array.from({ length: selectedAssets.length }).map((__, j) => {
      if (i === j) return selectedAssets[i].marginalRisk;
      return (Math.round((0.002 + rnd() * 0.012) * 10000) / 10000) * (rnd() > 0.25 ? 1 : -1);
    }),
  );
  let varianceRisk = 0;
  for (let i = 0; i < selectedAssets.length; i++) {
    for (let j = 0; j < selectedAssets.length; j++) {
      varianceRisk += selectedAssets[i].weight * cov[i][j] * selectedAssets[j].weight;
    }
  }
  varianceRisk = Math.max(0, Math.round(varianceRisk * 100000) / 100000);
  const volatilityPct = Math.round(Math.sqrt(varianceRisk) * 10000) / 100;

  const returnTerm = Math.round(expectedReturnPct * 1000);
  const riskTerm = Math.round(varianceRisk * 100000);
  const cardinalityTerm = Math.round(selectedAssets.length * task.cardinalityPenalty * 1000);
  const objectiveScore = returnTerm - riskTerm - cardinalityTerm;

  const covCells: { i: string; j: string; value: number }[] = [];
  for (let i = 0; i < selectedAssets.length; i++) {
    for (let j = i + 1; j < selectedAssets.length; j++) {
      covCells.push({ i: selectedAssets[i].code, j: selectedAssets[j].code, value: cov[i][j] });
    }
  }
  covCells.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  return {
    task,
    validations: [
      { key: 'budget', label: '预算约束满足', pass: investedAmount <= task.budget + 1e-6 },
      { key: 'risk', label: '风险上限满足', pass: varianceRisk <= task.riskLimit },
      { key: 'cardinality', label: '持仓数量约束满足', pass: selectedAssets.length <= task.maxHoldings },
      { key: 'return', label: '最低收益约束满足', pass: expectedReturnPct >= task.minExpectedReturn },
    ],
    summary: {
      investedAmount: Math.round(investedAmount),
      cashRemain: Math.round(cashRemain),
      expectedReturnPct: Math.round(expectedReturnPct * 100) / 100,
      varianceRisk,
      volatilityPct,
      selectedCount: selectedAssets.length,
      objectiveScore,
      returnTerm,
      riskTerm,
      cardinalityTerm,
    },
    assets: assets.sort((a, b) => Number(b.selected) - Number(a.selected) || b.weight - a.weight),
    covarianceTop: covCells.slice(0, 8),
  };
}
