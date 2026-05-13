export type PortfolioTaskStatus = 'pending' | 'running' | 'completed';

export interface PortfolioTaskPayload {
  name: string;
  budget: number;
  assetUniverseSize: number;
  maxHoldings: number;
  minExpectedReturn: number; // 年化 %
  riskLimit: number; // 方差上限
  maxWeightPerAsset: number; // 0~1
  cardinalityPenalty: number;
}

export interface PortfolioTask extends PortfolioTaskPayload {
  id: string;
  status: PortfolioTaskStatus;
  createdAt: string;
}

export interface PortfolioValidationItem {
  key: string;
  label: string;
  pass: boolean;
  reason?: string;
}

export interface PortfolioAssetRow {
  code: string;
  name: string;
  selected: boolean; // 整数变量
  units: number; // 整数变量
  price: number;
  expectedReturn: number; // 年化 %
  weight: number; // 连续变量
  marginalRisk: number;
}

export interface PortfolioSummary {
  investedAmount: number;
  cashRemain: number;
  expectedReturnPct: number;
  varianceRisk: number;
  volatilityPct: number;
  selectedCount: number;
  objectiveScore: number;
  returnTerm: number;
  riskTerm: number;
  cardinalityTerm: number;
}

export interface CovarianceCell {
  i: string;
  j: string;
  value: number;
}

export interface PortfolioResultPayload {
  task: PortfolioTask;
  validations: PortfolioValidationItem[];
  summary: PortfolioSummary;
  assets: PortfolioAssetRow[];
  covarianceTop: CovarianceCell[];
}
