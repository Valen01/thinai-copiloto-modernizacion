"""Calculo de la indemnizacion (servicio de dominio). Orden fijo, ver R-021."""
from decimal import Decimal

from claims_settlement.domain import parameters as P
from claims_settlement.domain.enums import (
    Branch, CustomerCategory, DeductibleType, Mark)
from claims_settlement.domain.model import Customer, Policy
from claims_settlement.domain.money import HUNDRED, percent_of, round2, subtract
from claims_settlement.domain.observations import Observations
from claims_settlement.domain.parameters import BusinessParameters

Staged = tuple[Decimal, Observations]


def compute_base_amount(claimed: Decimal, limit: Decimal, obs: Observations) -> Staged:
    """Monto base = menor entre lo reclamado y el limite de la cobertura."""
    # REGLA: R-013 (solo si reclamado > limite, estricto, se topa y se marca LIMITE_COBERTURA)
    if claimed > limit:
        return limit, obs.add(Mark.COVERAGE_LIMIT)
    return claimed, obs


def _percentage_deductible(policy: Policy, base: Decimal,
                           params: BusinessParameters, obs: Observations) -> Staged:
    # REGLA: R-014 (porcentual: ROUND(base * valor / 100, 2) sobre el monto base ya topado)
    minimum = round2(params.require(P.MINIMUM_DEDUCTIBLE))
    deductible = percent_of(base, policy.deductible_value)
    # REGLA: R-015 (minimo solo en la rama porcentual; estricto <; marca DEDUCIBLE_MINIMO)
    if deductible < minimum:
        return minimum, obs.add(Mark.MINIMUM_DEDUCTIBLE)
    return deductible, obs


def _vip_discount(customer: Customer, deductible: Decimal,
                  params: BusinessParameters, obs: Observations) -> Staged:
    # REGLA: R-016 (VIP y deducible > 0: descuento tras el minimo, marca DESCUENTO_VIP)
    if customer.category == CustomerCategory.VIP and deductible > 0:
        pct = params.require(P.VIP_DEDUCTIBLE_DISCOUNT_PCT)
        return percent_of(deductible, HUNDRED - pct), obs.add(Mark.VIP_DISCOUNT)
    return deductible, obs


def compute_deductible(policy: Policy, customer: Customer, base: Decimal,
                       params: BusinessParameters, obs: Observations) -> Staged:
    """Deducible FIJO tal cual o porcentual con minimo; luego descuento VIP."""
    # REGLA: R-014 (FIJO se usa tal cual, sin minimo; cualquier otro tipo es porcentual)
    if policy.deductible_type == DeductibleType.FIXED:
        deductible, obs = policy.deductible_value, obs
    else:
        deductible, obs = _percentage_deductible(policy, base, params, obs)
    return _vip_discount(customer, deductible, params, obs)


def compute_covered(base: Decimal, deductible: Decimal, coverage_pct: Decimal) -> Decimal:
    """Monto cubierto = ROUND((base - deducible) * % cobertura / 100, 2)."""
    # REGLA: R-017 (el rechazo BAJO_DEDUCIBLE cuando <= 0 lo aplica el caso de uso)
    return percent_of(subtract(base, deductible), coverage_pct)


def apply_claims_penalty(covered: Decimal, prior_claims: int,
                         params: BusinessParameters, obs: Observations) -> Staged:
    """Penalizacion por siniestralidad si hay MAX_SINIESTROS_ANUAL o mas previos."""
    # REGLA: R-018 (cuenta >= maximo, inclusive; cubierto * (100 - pct) / 100 redondeado)
    if prior_claims >= params.require(P.MAX_CLAIMS_PER_YEAR):
        pct = params.require(P.CLAIMS_PENALTY_PCT)
        return percent_of(covered, HUNDRED - pct), obs.add(Mark.CLAIMS_PENALTY)
    return covered, obs


def remaining_sum_insured(sum_insured: Decimal, total_paid: Decimal) -> Decimal:
    """Suma asegurada remanente = suma asegurada - cubierto APROBADO o PENDIENTE."""
    # REGLA: R-019 (acumulado total de la poliza sin filtro de fechas)
    return subtract(sum_insured, total_paid)


def apply_sum_insured_cap(covered: Decimal, remaining: Decimal, obs: Observations) -> Staged:
    """Topa el cubierto al remanente (estricto >) con marca TOPE_SUMA_ASEGURADA."""
    # REGLA: R-019 (cubierto > remanente => cubierto = remanente)
    if covered > remaining:
        return remaining, obs.add(Mark.SUM_INSURED_CAP)
    return covered, obs


def compute_withholding(branch: Branch, covered: Decimal,
                        params: BusinessParameters, obs: Observations) -> Staged:
    """Retencion sobre todo el cubierto si ramo no es VIDA y cubierto > umbral."""
    # REGLA: R-020 (ramo <> VIDA y cubierto > UMBRAL_RETENCION, estricto; tasa sobre el total)
    if branch != Branch.LIFE and covered > params.require(P.WITHHOLDING_THRESHOLD):
        rate = params.require(P.WITHHOLDING_RATE)
        return percent_of(covered, rate), obs.add(Mark.WITHHOLDING_APPLIED)
    return Decimal("0.00"), obs


def compute_net(covered: Decimal, withholding: Decimal) -> Decimal:
    """Neto = cubierto - retencion."""
    # REGLA: R-020 (neto = cubierto - retencion)
    return subtract(covered, withholding)
