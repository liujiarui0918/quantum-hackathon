from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Literal

from .expressions import LinearForm


VariableKind = Literal["binary", "integer_encoded", "slack", "auxiliary"]


@dataclass(frozen=True)
class EncodedBit:
    name: str
    index: int
    kind: VariableKind
    source: str
    logical_name: str | None = None
    weight: int = 1


@dataclass
class VariableRegistry:
    bits: list[EncodedBit] = field(default_factory=list)
    logical_forms: Dict[str, LinearForm] = field(default_factory=dict)
    logical_bounds: Dict[str, tuple[int, int]] = field(default_factory=dict)

    def add_binary(self, name: str) -> LinearForm:
        bit = self._add_bit(name=name, kind="binary", source="logical", logical_name=name, weight=1)
        form = LinearForm(terms={bit.index: 1.0})
        self.logical_forms[name] = form
        self.logical_bounds[name] = (0, 1)
        return form

    def add_integer(self, name: str, lower: int, upper: int) -> LinearForm:
        span = upper - lower
        form = LinearForm(offset=float(lower))
        if span == 0:
            self.logical_forms[name] = form
            self.logical_bounds[name] = (lower, upper)
            return form

        weights = self._bounded_weights(span)
        for bit_index, weight in enumerate(weights):
            bit = self._add_bit(
                name=f"{name}__b{bit_index}",
                kind="integer_encoded",
                source=f"logical:{name}",
                logical_name=name,
                weight=weight,
            )
            form.add_term(bit.index, float(weight))
        self.logical_forms[name] = form
        self.logical_bounds[name] = (lower, upper)
        return form

    def add_slack(self, constraint_name: str, upper: int) -> LinearForm:
        if upper < 0:
            raise ValueError(f"slack upper bound for {constraint_name!r} is negative")
        form = LinearForm()
        if upper == 0:
            return form
        for bit_index, weight in enumerate(self._bounded_weights(upper)):
            bit = self._add_bit(
                name=f"slack_{constraint_name}_{bit_index}",
                kind="slack",
                source=f"constraint:{constraint_name}",
                logical_name=None,
                weight=weight,
            )
            form.add_term(bit.index, float(weight))
        return form

    def add_auxiliary(self, name: str, source: str) -> int:
        return self._add_bit(name=name, kind="auxiliary", source=source, logical_name=None).index

    def form_for(self, logical_name: str) -> LinearForm:
        return self.logical_forms[logical_name]

    def decode_logical(self, bitstring: Iterable[int]) -> dict[str, int]:
        bits = list(bitstring)
        decoded: dict[str, int] = {}
        for name, form in self.logical_forms.items():
            value = form.evaluate(bits)
            lower, upper = self.logical_bounds[name]
            decoded[name] = int(round(min(max(value, lower), upper)))
        return decoded

    def index_by_name(self) -> dict[str, int]:
        return {bit.name: bit.index for bit in self.bits}

    def diagnostics(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "logical_variables": len(self.logical_forms),
            "slack_variables": 0,
            "auxiliary_variables": 0,
            "total_binary_variables": len(self.bits),
        }
        for bit in self.bits:
            if bit.kind == "slack":
                counts["slack_variables"] += 1
            elif bit.kind == "auxiliary":
                counts["auxiliary_variables"] += 1
        return counts

    def _add_bit(
        self,
        *,
        name: str,
        kind: VariableKind,
        source: str,
        logical_name: str | None,
        weight: int = 1,
    ) -> EncodedBit:
        if any(bit.name == name for bit in self.bits):
            raise ValueError(f"encoded bit {name!r} already exists")
        bit = EncodedBit(
            name=name,
            index=len(self.bits),
            kind=kind,
            source=source,
            logical_name=logical_name,
            weight=weight,
        )
        self.bits.append(bit)
        return bit

    @staticmethod
    def _bounded_weights(upper: int) -> list[int]:
        weights: list[int] = []
        remaining = upper
        power = 1
        while remaining > 0:
            weight = min(power, remaining)
            weights.append(weight)
            remaining -= weight
            power *= 2
        return weights
