from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from quantum_hackathon.miqp.route7 import BLOCK_SCORE_FEATURE_NAMES


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    rows = _load_rows(args.inputs)
    x, y = _matrix(rows, label_key=args.label_key)
    if len(y) == 0:
        raise SystemExit("no labeled trace rows found")
    model = _fit_ridge(x, y, l2=args.l2)
    model.update(
        {
            "model_type": "linear_block_scorer",
            "feature_names": list(BLOCK_SCORE_FEATURE_NAMES),
            "label_key": args.label_key,
            "training_rows": int(len(y)),
            "label_mean": float(np.mean(y)),
            "label_std": float(np.std(y)),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    torch_status = _maybe_train_torch(x, y, args.torch_output, args.epochs, args.learning_rate)
    summary = {
        "output": str(args.output),
        "rows": int(len(y)),
        "features": list(BLOCK_SCORE_FEATURE_NAMES),
        "label_key": args.label_key,
        "torch_status": torch_status,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote block model: {args.output}")
    print(f"training rows: {len(y)}")
    print(f"torch_status: {torch_status}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train fallback route7++ block scorer from trace JSONL.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("models/block_selector_model.json"))
    parser.add_argument("--summary", type=Path, default=Path("models/block_selector_model_summary.json"))
    parser.add_argument("--torch-output", type=Path, default=Path("models/block_selector_model.pt"))
    parser.add_argument("--label-key", default="improvement_per_lp_call")
    parser.add_argument("--l2", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    return parser


def _load_rows(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _matrix(rows: Sequence[dict[str, Any]], *, label_key: str) -> tuple[np.ndarray, np.ndarray]:
    features = []
    labels = []
    for row in rows:
        for block_record in _iter_block_records(row):
            label = block_record.get(label_key)
            if label is None:
                continue
            score_features = block_record.get("score_features", {})
            features.append([float(score_features.get(name, 0.0)) for name in BLOCK_SCORE_FEATURE_NAMES])
            labels.append(float(label))
    if not features:
        return np.zeros((0, len(BLOCK_SCORE_FEATURE_NAMES))), np.zeros(0)
    return np.asarray(features, dtype=float), np.asarray(labels, dtype=float)


def _iter_block_records(row: dict[str, Any]):
    if "score_features" in row:
        yield row
    for block in row.get("block_pool", []):
        yield block


def _fit_ridge(x: np.ndarray, y: np.ndarray, *, l2: float) -> dict[str, Any]:
    means = np.mean(x, axis=0)
    scales = np.std(x, axis=0)
    scales = np.where(scales <= 1e-12, 1.0, scales)
    x_norm = (x - means) / scales
    design = np.column_stack([np.ones(len(x_norm)), x_norm])
    reg = np.eye(design.shape[1]) * l2
    reg[0, 0] = 0.0
    params = np.linalg.pinv(design.T @ design + reg) @ design.T @ y
    return {
        "bias": float(params[0]),
        "weights": [float(value) for value in params[1:]],
        "feature_means": [float(value) for value in means],
        "feature_scales": [float(value) for value in scales],
    }


def _maybe_train_torch(
    x: np.ndarray,
    y: np.ndarray,
    torch_output: Path,
    epochs: int,
    learning_rate: float,
) -> str:
    try:
        import torch
    except Exception as exc:
        return f"skipped: torch unavailable ({type(exc).__name__})"
    device = "cpu"
    try:
        if hasattr(torch, "musa") and torch.musa.is_available():
            device = "musa"
        elif torch.cuda.is_available():
            device = "cuda"
    except Exception:
        device = "cpu"
    means = x.mean(axis=0)
    scales = x.std(axis=0)
    scales[scales <= 1e-12] = 1.0
    xt = torch.tensor((x - means) / scales, dtype=torch.float32, device=device)
    yt = torch.tensor(y.reshape(-1, 1), dtype=torch.float32, device=device)
    model = torch.nn.Sequential(
        torch.nn.Linear(x.shape[1], 16),
        torch.nn.ReLU(),
        torch.nn.Linear(16, 1),
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = torch.nn.MSELoss()
    for _epoch in range(max(1, epochs)):
        optimizer.zero_grad()
        loss = loss_fn(model(xt), yt)
        loss.backward()
        optimizer.step()
    torch_output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "feature_names": list(BLOCK_SCORE_FEATURE_NAMES),
            "feature_means": means.tolist(),
            "feature_scales": scales.tolist(),
            "device_trained": device,
        },
        torch_output,
    )
    return f"trained: {torch_output} on {device}"


if __name__ == "__main__":
    raise SystemExit(main())
