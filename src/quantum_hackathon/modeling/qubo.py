from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Mapping

from .expressions import LinearForm, QuadraticExpression
from .problem import ConstraintSpec, OptimizationProblem
from .variables import VariableRegistry


TOLERANCE = 1e-9


@dataclass(frozen=True)
class QuboBuilderConfig:
    default_penalty: float | str = "auto"
    penalty_scale: float = 2.0
    quadratization_penalty: float | None = None


@dataclass(frozen=True)
class ConstraintCheckResult:
    name: str
    lhs: float
    sense: str
    rhs: float
    violation: float
    is_satisfied: bool
    penalty_energy: float = 0.0


@dataclass(frozen=True)
class FeasibilityReport:
    results: list[ConstraintCheckResult]

    @property
    def is_feasible(self) -> bool:
        return all(result.is_satisfied for result in self.results)

    @property
    def total_violation(self) -> float:
        return sum(result.violation for result in self.results)

    @property
    def num_violated(self) -> int:
        return sum(1 for result in self.results if not result.is_satisfied)


@dataclass(frozen=True)
class DecodedSample:
    bitstring: tuple[int, ...]
    logical_solution: dict[str, int]
    qubo_energy: float
    objective_value: float
    penalty_energy: float
    is_feasible: bool
    constraint_violations: list[ConstraintCheckResult]
    num_occurrences: int = 1
    source_backend: str = "decoded"
    repair_info: dict | None = None

    @property
    def total_violation(self) -> float:
        return sum(result.violation for result in self.constraint_violations)


@dataclass
class IsingModel:
    h: dict[int, float]
    j: dict[tuple[int, int], float]
    offset: float

    def energy_from_bits(self, bitstring: Iterable[int]) -> float:
        bits = tuple(bitstring)
        spins = {index: 1 - 2 * bit for index, bit in enumerate(bits)}
        energy = self.offset
        for index, coefficient in self.h.items():
            energy += coefficient * spins[index]
        for (left, right), coefficient in self.j.items():
            energy += coefficient * spins[left] * spins[right]
        return energy


@dataclass
class QuboModel:
    problem: OptimizationProblem
    registry: VariableRegistry
    objective_expression: QuadraticExpression
    penalty_expression: QuadraticExpression
    qubo: dict[tuple[int, int], float]
    offset: float
    warnings: list[str] = field(default_factory=list)

    @property
    def num_variables(self) -> int:
        return len(self.registry.bits)

    def energy(self, bitstring: Iterable[int]) -> float:
        bits = tuple(bitstring)
        value = self.offset
        for (left, right), coefficient in self.qubo.items():
            value += coefficient * bits[left] * bits[right]
        return round(value, 12)

    def objective_value(self, bitstring: Iterable[int]) -> float:
        logical = self.registry.decode_logical(tuple(bitstring))
        return self.problem.evaluate_objective(logical)

    def internal_objective_energy(self, bitstring: Iterable[int]) -> float:
        return self.objective_expression.energy(tuple(bitstring))

    def decode(
        self,
        bitstring: Iterable[int],
        *,
        num_occurrences: int = 1,
        source_backend: str = "decoded",
    ) -> DecodedSample:
        bits = tuple(int(bit) for bit in bitstring)
        logical = self.registry.decode_logical(bits)
        feasibility = self.check_constraints(logical)
        objective = self.problem.evaluate_objective(logical)
        qubo_energy = self.energy(bits)
        penalty_energy = round(qubo_energy - self.internal_objective_energy(bits), 12)
        return DecodedSample(
            bitstring=bits,
            logical_solution=logical,
            qubo_energy=qubo_energy,
            objective_value=objective,
            penalty_energy=penalty_energy,
            is_feasible=feasibility.is_feasible,
            constraint_violations=feasibility.results,
            num_occurrences=num_occurrences,
            source_backend=source_backend,
        )

    def check_constraints(self, logical_assignment: dict[str, int]) -> FeasibilityReport:
        results: list[ConstraintCheckResult] = []
        for constraint in self.problem.constraints:
            lhs = sum(coefficient * logical_assignment[name] for name, coefficient in constraint.linear.items())
            violation = _constraint_violation(lhs, constraint.sense, constraint.rhs)
            results.append(
                ConstraintCheckResult(
                    name=constraint.name,
                    lhs=round(lhs, 12),
                    sense=constraint.sense,
                    rhs=constraint.rhs,
                    violation=round(violation, 12),
                    is_satisfied=violation <= TOLERANCE,
                    penalty_energy=0.0 if violation <= TOLERANCE else violation,
                )
            )
        return FeasibilityReport(results)

    def bitstring_from_logical(self, logical_assignment: Mapping[str, int]) -> tuple[int, ...]:
        bits = [0] * self.num_variables
        for bit in self.registry.bits:
            if bit.kind == "binary" and bit.logical_name in logical_assignment:
                bits[bit.index] = int(logical_assignment[bit.logical_name])
        for name, value in logical_assignment.items():
            if name not in self.registry.logical_forms:
                continue
            lower, _upper = self.registry.logical_bounds[name]
            remaining = int(value - lower)
            encoded_bits = [
                bit for bit in self.registry.bits if bit.logical_name == name and bit.kind == "integer_encoded"
            ]
            for bit in sorted(encoded_bits, key=lambda item: item.weight, reverse=True):
                if remaining >= bit.weight:
                    bits[bit.index] = 1
                    remaining -= bit.weight
        self._fill_constraint_slacks(bits)
        self._fill_auxiliaries(bits)
        return tuple(bits)

    def iter_bitstrings(self) -> Iterable[tuple[int, ...]]:
        return product((0, 1), repeat=self.num_variables)

    def diagnostics(self) -> dict[str, float | int | list[str]]:
        diagnostics = self.registry.diagnostics()
        couplers = sum(1 for left, right in self.qubo if left != right)
        coefficients = [abs(value) for value in self.qubo.values() if abs(value) > TOLERANCE]
        density_denominator = max(1, self.num_variables * (self.num_variables - 1) / 2)
        diagnostics.update(
            {
                "linear_terms": sum(1 for left, right in self.qubo if left == right),
                "quadratic_couplers": couplers,
                "density": couplers / density_denominator,
                "coefficient_min": min(coefficients) if coefficients else 0.0,
                "coefficient_max": max(coefficients) if coefficients else 0.0,
                "coefficient_ratio": (max(coefficients) / min(coefficients)) if len(coefficients) > 1 else 1.0,
                "warnings": list(self.warnings),
            }
        )
        return diagnostics

    def to_ising(self) -> IsingModel:
        h: dict[int, float] = {}
        j: dict[tuple[int, int], float] = {}
        offset = self.offset
        for (left, right), coefficient in self.qubo.items():
            if left == right:
                offset += coefficient / 2.0
                h[left] = h.get(left, 0.0) - coefficient / 2.0
            else:
                offset += coefficient / 4.0
                h[left] = h.get(left, 0.0) - coefficient / 4.0
                h[right] = h.get(right, 0.0) - coefficient / 4.0
                j[(left, right)] = j.get((left, right), 0.0) + coefficient / 4.0
        return IsingModel(h=h, j=j, offset=offset)

    def _fill_constraint_slacks(self, bits: list[int]) -> None:
        for constraint in self.problem.constraints:
            if constraint.sense not in ("<=", ">="):
                continue
            logical = self.registry.decode_logical(bits)
            lhs = sum(coefficient * logical[name] for name, coefficient in constraint.linear.items())
            slack_value = int(round(constraint.rhs - lhs if constraint.sense == "<=" else lhs - constraint.rhs))
            slack_bits = [
                bit for bit in self.registry.bits if bit.kind == "slack" and bit.source == f"constraint:{constraint.name}"
            ]
            for bit in sorted(slack_bits, key=lambda item: item.weight, reverse=True):
                if slack_value >= bit.weight:
                    bits[bit.index] = 1
                    slack_value -= bit.weight

    def _fill_auxiliaries(self, bits: list[int]) -> None:
        for bit in self.registry.bits:
            if bit.kind != "auxiliary" or not bit.source.startswith("and:"):
                continue
            _prefix, left_name, right_name = bit.source.split(":", 2)
            index_by_name = self.registry.index_by_name()
            bits[bit.index] = bits[index_by_name[left_name]] * bits[index_by_name[right_name]]


class QuboBuilder:
    def __init__(self, config: QuboBuilderConfig | None = None):
        self.config = config or QuboBuilderConfig()
        self._and_auxiliaries: dict[tuple[int, int], int] = {}

    def build(self, problem: OptimizationProblem) -> QuboModel:
        self._and_auxiliaries = {}
        registry = VariableRegistry()
        for spec in problem.variables.values():
            if spec.kind == "binary":
                registry.add_binary(spec.name)
            elif spec.kind == "integer":
                registry.add_integer(spec.name, spec.lower, spec.upper)
            else:
                raise ValueError(f"unsupported variable kind {spec.kind!r}")

        objective = QuadraticExpression(offset=problem.objective_offset)
        penalty = QuadraticExpression()
        warnings: list[str] = []

        objective_scale = -1.0 if problem.sense == "maximize" else 1.0
        for name, coefficient in problem.objective_linear.items():
            objective.add_linear_form(registry.form_for(name), coefficient * objective_scale)
        for (left, right), coefficient in problem.objective_quadratic.items():
            objective.add_product(
                registry.form_for(left),
                registry.form_for(right),
                coefficient * objective_scale,
            )
        for names, coefficient in problem.high_order_terms:
            term_expression = self._quadratize_monomial(
                [registry.form_for(name) for name in names],
                registry,
                coefficient * objective_scale,
            )
            objective.add_expression(term_expression)

        objective_bound = _objective_bound(problem)
        for constraint in problem.constraints:
            weight = self._penalty_weight(constraint, objective_bound)
            if constraint.sense == "==":
                form = _constraint_form(registry, constraint).shifted(-constraint.rhs)
                penalty.add_square_linear_form(form, weight)
            elif constraint.sense in ("<=", ">="):
                normalized = _constraint_form(registry, constraint)
                slack_upper = _slack_upper(problem, constraint)
                slack_form = registry.add_slack(constraint.name, int(round(slack_upper)))
                if constraint.sense == "<=":
                    normalized.add_form(slack_form)
                    normalized.offset -= constraint.rhs
                else:
                    normalized.add_form(slack_form, scale=-1.0)
                    normalized.offset = constraint.rhs - normalized.offset
                    normalized.terms = {variable: -coefficient for variable, coefficient in normalized.terms.items()}
                penalty.add_square_linear_form(normalized, weight)
                if slack_upper > 16:
                    warnings.append(f"slack_blowup_warning:{constraint.name}")
            else:
                raise ValueError(f"unsupported constraint sense {constraint.sense!r}")

        combined = QuadraticExpression()
        combined.add_expression(objective)
        combined.add_expression(penalty)
        return QuboModel(
            problem=problem,
            registry=registry,
            objective_expression=objective,
            penalty_expression=penalty,
            qubo=combined.to_qubo(),
            offset=combined.offset,
            warnings=warnings,
        )

    def _penalty_weight(self, constraint: ConstraintSpec, objective_bound: float) -> float:
        if constraint.penalty_weight is not None:
            return constraint.penalty_weight
        if isinstance(self.config.default_penalty, (int, float)):
            return float(self.config.default_penalty)
        return self.config.penalty_scale * (objective_bound + 1.0)

    def _quadratize_monomial(
        self,
        factors: list[LinearForm],
        registry: VariableRegistry,
        coefficient: float,
    ) -> QuadraticExpression:
        bit_indices = [_single_bit_index(form) for form in factors]
        expression = QuadraticExpression()
        current = bit_indices[0]
        for next_index in bit_indices[1:-1]:
            current = self._and_auxiliary(current, next_index, registry, expression)
        expression.add_quadratic(current, bit_indices[-1], coefficient)
        return expression

    def _and_auxiliary(
        self,
        left: int,
        right: int,
        registry: VariableRegistry,
        expression: QuadraticExpression,
    ) -> int:
        key = (left, right) if left <= right else (right, left)
        if key in self._and_auxiliaries:
            return self._and_auxiliaries[key]
        left_name = registry.bits[key[0]].name
        right_name = registry.bits[key[1]].name
        aux_name = f"aux_and_{left_name}_{right_name}"
        aux = registry.add_auxiliary(aux_name, source=f"and:{left_name}:{right_name}")
        weight = self.config.quadratization_penalty or (
            float(self.config.default_penalty)
            if isinstance(self.config.default_penalty, (int, float))
            else 20.0
        )
        expression.add_quadratic(key[0], key[1], weight)
        expression.add_quadratic(key[0], aux, -2.0 * weight)
        expression.add_quadratic(key[1], aux, -2.0 * weight)
        expression.add_linear(aux, 3.0 * weight)
        self._and_auxiliaries[key] = aux
        return aux


def _single_bit_index(form: LinearForm) -> int:
    if form.offset != 0 or len(form.terms) != 1:
        raise ValueError("high-order monomial quadratization currently supports binary variables only")
    [(index, coefficient)] = form.terms.items()
    if abs(coefficient - 1.0) > TOLERANCE:
        raise ValueError("high-order monomial quadratization currently supports direct binary variables only")
    return index


def _constraint_form(registry: VariableRegistry, constraint: ConstraintSpec) -> LinearForm:
    form = LinearForm()
    for name, coefficient in constraint.linear.items():
        form.add_form(registry.form_for(name), coefficient)
    return form


def _constraint_violation(lhs: float, sense: str, rhs: float) -> float:
    if sense == "==":
        return abs(lhs - rhs)
    if sense == "<=":
        return max(0.0, lhs - rhs)
    if sense == ">=":
        return max(0.0, rhs - lhs)
    raise ValueError(f"unsupported constraint sense {sense!r}")


def _objective_bound(problem: OptimizationProblem) -> float:
    bound = abs(problem.objective_offset)
    bound += sum(abs(value) for value in problem.objective_linear.values())
    bound += sum(abs(value) for value in problem.objective_quadratic.values())
    bound += sum(abs(value) for _names, value in problem.high_order_terms)
    return bound


def _slack_upper(problem: OptimizationProblem, constraint: ConstraintSpec) -> float:
    min_lhs = 0.0
    max_lhs = 0.0
    for name, coefficient in constraint.linear.items():
        lower, upper = problem.variable_bounds(name)
        values = (coefficient * lower, coefficient * upper)
        min_lhs += min(values)
        max_lhs += max(values)
    if constraint.sense == "<=":
        upper = constraint.rhs - min_lhs
    else:
        upper = max_lhs - constraint.rhs
    if upper < -TOLERANCE:
        raise ValueError(f"constraint {constraint.name!r} is infeasible within variable bounds")
    return max(0.0, upper)
