from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class RoundingStrategy:
    method: str = "threshold"
    threshold: float = 0.5
    top_k: int | None = None
    seed: int | None = None

    def round(self, values: dict[str, float]) -> dict[str, int]:
        if self.method == "threshold":
            return {name: int(value >= self.threshold) for name, value in values.items()}
        if self.method == "top_k":
            if self.top_k is None:
                raise ValueError("top_k rounding requires top_k")
            ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))
            selected = {name for name, _value in ordered[: self.top_k]}
            return {name: int(name in selected) for name in values}
        if self.method == "randomized":
            generator = random.Random(self.seed)
            return {name: int(generator.random() < min(1.0, max(0.0, value))) for name, value in values.items()}
        raise ValueError(f"unsupported rounding method {self.method!r}")
