from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Tuple


def canonical_pair(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left <= right else (right, left)


@dataclass
class LinearForm:
    offset: float = 0.0
    terms: Dict[int, float] = field(default_factory=dict)

    def add_term(self, variable: int, coefficient: float) -> None:
        if abs(coefficient) <= 1e-12:
            return
        self.terms[variable] = self.terms.get(variable, 0.0) + coefficient
        if abs(self.terms[variable]) <= 1e-12:
            del self.terms[variable]

    def add_form(self, other: "LinearForm", scale: float = 1.0) -> None:
        self.offset += other.offset * scale
        for variable, coefficient in other.terms.items():
            self.add_term(variable, coefficient * scale)

    def scaled(self, scale: float) -> "LinearForm":
        return LinearForm(
            offset=self.offset * scale,
            terms={variable: coefficient * scale for variable, coefficient in self.terms.items()},
        )

    def shifted(self, value: float) -> "LinearForm":
        return LinearForm(offset=self.offset + value, terms=dict(self.terms))

    def evaluate(self, sample: Mapping[int, int] | Iterable[int]) -> float:
        if isinstance(sample, Mapping):
            return self.offset + sum(coefficient * sample[variable] for variable, coefficient in self.terms.items())
        bits = list(sample)
        return self.offset + sum(coefficient * bits[variable] for variable, coefficient in self.terms.items())


@dataclass
class QuadraticExpression:
    offset: float = 0.0
    linear: Dict[int, float] = field(default_factory=dict)
    quadratic: Dict[Tuple[int, int], float] = field(default_factory=dict)

    def add_offset(self, value: float) -> None:
        self.offset += value

    def add_linear(self, variable: int, coefficient: float) -> None:
        if abs(coefficient) <= 1e-12:
            return
        self.linear[variable] = self.linear.get(variable, 0.0) + coefficient
        if abs(self.linear[variable]) <= 1e-12:
            del self.linear[variable]

    def add_quadratic(self, left: int, right: int, coefficient: float) -> None:
        if abs(coefficient) <= 1e-12:
            return
        if left == right:
            self.add_linear(left, coefficient)
            return
        key = canonical_pair(left, right)
        self.quadratic[key] = self.quadratic.get(key, 0.0) + coefficient
        if abs(self.quadratic[key]) <= 1e-12:
            del self.quadratic[key]

    def add_expression(self, other: "QuadraticExpression", scale: float = 1.0) -> None:
        self.offset += other.offset * scale
        for variable, coefficient in other.linear.items():
            self.add_linear(variable, coefficient * scale)
        for (left, right), coefficient in other.quadratic.items():
            self.add_quadratic(left, right, coefficient * scale)

    def add_linear_form(self, form: LinearForm, scale: float = 1.0) -> None:
        self.add_offset(form.offset * scale)
        for variable, coefficient in form.terms.items():
            self.add_linear(variable, coefficient * scale)

    def add_square_linear_form(self, form: LinearForm, weight: float = 1.0) -> None:
        self.add_offset(weight * form.offset * form.offset)
        for variable, coefficient in form.terms.items():
            self.add_linear(variable, weight * (2.0 * form.offset * coefficient + coefficient * coefficient))
        items = list(form.terms.items())
        for index, (left, left_coeff) in enumerate(items):
            for right, right_coeff in items[index + 1 :]:
                self.add_quadratic(left, right, weight * 2.0 * left_coeff * right_coeff)

    def add_product(self, left: LinearForm, right: LinearForm, scale: float = 1.0) -> None:
        self.add_offset(scale * left.offset * right.offset)
        for variable, coefficient in left.terms.items():
            self.add_linear(variable, scale * coefficient * right.offset)
        for variable, coefficient in right.terms.items():
            self.add_linear(variable, scale * coefficient * left.offset)
        for left_var, left_coeff in left.terms.items():
            for right_var, right_coeff in right.terms.items():
                self.add_quadratic(left_var, right_var, scale * left_coeff * right_coeff)

    def to_qubo(self) -> dict[tuple[int, int], float]:
        qubo: dict[tuple[int, int], float] = {}
        for variable, coefficient in self.linear.items():
            qubo[(variable, variable)] = qubo.get((variable, variable), 0.0) + coefficient
        for pair, coefficient in self.quadratic.items():
            qubo[pair] = qubo.get(pair, 0.0) + coefficient
        return {key: value for key, value in qubo.items() if abs(value) > 1e-12}

    def energy(self, sample: Mapping[int, int] | Iterable[int]) -> float:
        if isinstance(sample, Mapping):
            get_bit = sample.__getitem__
        else:
            bits = list(sample)
            get_bit = bits.__getitem__
        energy = self.offset
        for variable, coefficient in self.linear.items():
            energy += coefficient * get_bit(variable)
        for (left, right), coefficient in self.quadratic.items():
            energy += coefficient * get_bit(left) * get_bit(right)
        return energy

    @classmethod
    def from_qubo(cls, qubo: Mapping[tuple[int, int], float], offset: float = 0.0) -> "QuadraticExpression":
        expression = cls(offset=offset)
        for (left, right), coefficient in qubo.items():
            if left == right:
                expression.add_linear(left, coefficient)
            else:
                expression.add_quadratic(left, right, coefficient)
        return expression
