export type DatasetExecParams = {
  input: string;
  'solution-npz': string;
  'exact-binary-limit': number;
  'max-block-size': number;
  'candidate-limit': number;
  'max-iterations'?: number;
  seed?: number;
  seeds?: string;
  'block-pool'?: boolean;
  'blocks-per-iteration'?: number;
  'candidate-budget-per-block'?: number;
  'max-lp-evals'?: number;
  'qaoa-max-qubits'?: number;
  'weight-objective'?: number;
  'weight-coupling'?: number;
  'weight-mixed'?: number;
  'weight-binary'?: number;
  'post-polish-rounds'?: number;
  'polish-candidate-limit'?: number;
  route7Alias?: string;
  baselineStudy?: {
    enabled: boolean;
    inputs?: string[];
    'output-dir': string;
    'route7-json-dir': string;
    'random-reads': number;
    'sa-reads': number;
    'sa-sweeps': number;
    'qaoa-block-size': number;
    'qaoa-shots': number;
    'meta-population': number;
    'meta-iterations': number;
  };
};

const BASELINE_STUDY_CONFIG: NonNullable<DatasetExecParams['baselineStudy']> = {
  enabled: true,
  inputs: ['{input}'],
  'output-dir': 'results/{taskId}_baseline_study',
  'route7-json-dir': 'results/{taskId}_route7_json',
  'random-reads': 96,
  'sa-reads': 48,
  'sa-sweeps': 80,
  'qaoa-block-size': 10,
  'qaoa-shots': 160,
  'meta-population': 24,
  'meta-iterations': 8,
};

const DATASET_EXEC_CONFIG: Record<string, DatasetExecParams> = {
  'miqp_sample_A.npz': {
    'input': '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz',
    'solution-npz': 'results/miqp_sample_A_solution.npz',
    'exact-binary-limit': 15,
    'max-block-size': 12,
    'candidate-limit': 64,
    route7Alias: 'results/{instanceName}_route7.json',
    baselineStudy: BASELINE_STUDY_CONFIG,
  },
  'miqp_sample_B.npz': {
    input: '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_B.npz',
    'solution-npz': 'results/miqp_sample_B_solution.npz',
    'exact-binary-limit': 16,
    'max-block-size': 20,
    'candidate-limit': 192,
    'max-iterations': 8,
    'seed': 11,
    'block-pool': true,
    'blocks-per-iteration': 3,
    'candidate-budget-per-block': 64,
    'max-lp-evals': 800,
    'qaoa-max-qubits': 0,
    'weight-objective': 0.25,
    'weight-coupling': 0.25,
    'weight-mixed': 0.25,
    'weight-binary': 0.25,
    'post-polish-rounds': 2,
    'polish-candidate-limit': 128,
    route7Alias: 'results/{instanceName}_route7.json',
    baselineStudy: BASELINE_STUDY_CONFIG,
  },
  'miqp_test_1.npz': {
    input: '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz',
    'solution-npz': 'results/miqp_sample_A_solution.npz',
    'exact-binary-limit': 15,
    'max-block-size': 12,
    'candidate-limit': 64,
  },
  'miqp_test_2.npz': {
    'input': '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz',
    'solution-npz': 'results/miqp_sample_A_solution.npz',
    'exact-binary-limit': 15,
    'max-block-size': 12,
    'candidate-limit': 64,
  },
  'miqp_test_3.npz': {
    'input': '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz',
    'solution-npz': 'results/miqp_sample_A_solution.npz',
    'exact-binary-limit': 15,
    'max-block-size': 12,
    'candidate-limit': 64,
  },
  'miqp_test_4.npz': {
    'input': '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz',
    'solution-npz': 'results/miqp_sample_A_solution.npz',
    'exact-binary-limit': 15,
    'max-block-size': 12,
    'candidate-limit': 64,
  },
  'miqp_test_5.npz': {
    'input': '量化优化/量化优化/2026量子计算大赛·混合整数优化问题赛道小规模测试数据/miqp_sample_A.npz',
    'solution-npz': 'results/miqp_sample_A_solution.npz',
    'exact-binary-limit': 15,
    'max-block-size': 12,
    'candidate-limit': 64,
  },
};

export function getDatasetExecParams(datasetName: string): DatasetExecParams | null {
  return DATASET_EXEC_CONFIG[datasetName] ?? null;
}
