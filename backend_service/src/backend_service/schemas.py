from __future__ import annotations

from pydantic import BaseModel, Field


class RunOptions(BaseModel):
    seed: int = Field(default=7, ge=0)
    sa_reads: int = Field(default=60, ge=1)
    sa_sweeps: int = Field(default=150, ge=1)
    top_k: int = Field(default=20, ge=1)
    qaoa_p: int = Field(default=1, ge=1)
    qaoa_shots: int = Field(default=200, ge=1)
    qaoa_max_qubits: int = Field(default=12, ge=1)
    qaoa_grid_size: int = Field(default=5, ge=1)
    qaoa_random_trials: int = Field(default=10, ge=1)
    skip_qaoa: bool = False


class SolveRequest(BaseModel):
    problem: dict
    run_options: RunOptions = RunOptions()
