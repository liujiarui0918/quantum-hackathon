# 后端服务 (Backend Service)

`quantum-hackathon` 优化演示链路的 FastAPI 薄封装层。所有求解均为**本地模拟**，不涉及真实量子硬件。

## 快速开始

```bash
# 安装核心包（提供 quantum_hackathon 导入）
pip install -e .

# 安装后端服务及依赖
pip install -e ./backend_service[dev]

# 启动服务
uvicorn backend_service.main:app --reload --port 8000
```

## API 端点

### `GET /health`

返回服务健康状态。

```json
{ "status": "ok", "service": "backend_service" }
```

### `GET /api/quantum/sample-problem`

返回示例优化问题（来自 `data/sample_problem.json`）。

```json
{ "ok": true, "problem": { "name": "sample_assignment", ... } }
```

### `POST /api/quantum/solve`

同步求解优化问题，返回原始结果和前端可视化数据。

**请求体**:

```json
{
  "problem": {
    "name": "sample_assignment",
    "sense": "maximize",
    "variables": [
      { "name": "model_a", "kind": "binary" }
    ],
    "objective": { "linear": { "model_a": 9.0 } },
    "constraints": [
      { "linear": { "model_a": 1.0 }, "sense": "==", "rhs": 1.0, "constraint_type": "exactly_one" }
    ]
  },
  "run_options": {
    "seed": 7,
    "sa_reads": 60,
    "sa_sweeps": 150,
    "top_k": 20,
    "qaoa_p": 1,
    "qaoa_shots": 200,
    "qaoa_max_qubits": 12,
    "qaoa_grid_size": 5,
    "qaoa_random_trials": 10,
    "skip_qaoa": false
  }
}
```

所有 `run_options` 字段均可选，默认值与上方一致（对齐 demo CLI 默认值）。

**成功响应**:

```json
{
  "ok": true,
  "raw_result": {
    "problem": { ... },
    "run": { "seed": 7, "python": "...", "platform": "...", "total_ms": 0 },
    "diagnostics": { ... },
    "best_solution": {
      "bitstring": "10000",
      "logical_solution": { "model_a": 1, ... },
      "objective_value": 9.0,
      "is_feasible": true,
      ...
    },
    "benchmark": { "rows": [...], "markdown": "..." },
    "solvers": { "exact": {...}, "simulated_annealing": {...} },
    "qaoa": { "status": "ran", "quantum_circuit": {...}, ... },
    "constrained_qaoa": { "status": "ran", ... },
    "report_markdown": "..."
  },
  "visualization": {
    "quantum": {
      "problem": { "name": "...", "num_qubo_bits": 8, ... },
      "best_solution": { ... },
      "benchmark_rows": [...],
      "qaoa": { ... },
      "constrained_qaoa": { ... },
      "diagnostics": { ... }
    },
    "scenario": {
      "scenario_id": "sample_assignment",
      "variables": [{ "name": "model_a", "value": 1, "selected": true }, ...],
      "selected_variables": ["model_a"],
      "constraints": [{ "name": "...", "lhs": 5.0, "sense": "<=", "rhs": 6.0, "violation": 0.0, "is_satisfied": true }, ...],
      "objective_value": 9.0,
      "sample_assignment": { "selected_models": ["model_a"], "enabled_boosts": [] }
    }
  }
}
```

**错误响应**:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_problem",
    "message": "input JSON must contain a non-empty variables list",
    "details": { "source": "problem_from_json" }
  }
}
```

错误码：`invalid_problem` (400/422)、`invalid_run_options` (422)、`solve_failed` (500)、`sample_problem_unavailable` (500)、`internal_error` (500)。

## 前端接入

前端通过 Next.js rewrites 将 `/api/quantum/*` 代理到 FastAPI 后端。详见 `front_end/next.config.ts` 的 rewrite 配置。

## 测试

```bash
# 运行后端测试
python -m pytest backend_service/tests/ -q

# 运行核心回归测试
python -m pytest tests/ -q
```

## 重要说明

- **所有求解均为本地模拟。** 不使用真实量子硬件。QAOA 基于本地 statevector/shot 模拟器运行；constrained QAOA 输出元数据 MVP 诊断信息。
- 本服务为同步 API。大规模问题或过高的 QAOA 参数可能导致响应时间较长。默认参数设置偏保守。
- 本服务是 `src/quantum_hackathon/demo.py` 的薄封装层，不包含求解器逻辑——所有优化计算均在核心包内完成。
