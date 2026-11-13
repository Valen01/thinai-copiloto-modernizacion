"""Validaciones de procedencia (servicio de dominio de elegibilidad)."""
from dataclasses import dataclass
from typing import Callable, Optional

from claims_settlement.domain import parameters as P
from claims_settlement.domain.dates import day_diff
from claims_settlement.domain.enums import Branch, CustomerCategory, Mark, PolicyStatus, Reason
from claims_settlement.domain.model import Claim, Coverage, Customer, Policy
from claims_settlement.domain.parameters import BusinessParameters


@dataclass(frozen=True)
class EligibilityContext:
    """Datos que necesitan las validaciones."""

    claim: Claim
    policy: Policy
    customer: Customer
    coverage: Optional[Coverage]
    params: BusinessParameters


@dataclass(frozen=True)
class Verdict:
    """Resultado de una validacion: motivo de rechazo (si aplica) y marcas."""

    reason: Optional[Reason] = None
    marks: tuple[Mark, ...] = ()


PASS = Verdict()


def days_since_start(claim: Claim, policy: Policy) -> int:
    """TRUNC(ocurrencia) - TRUNC(inicio de poliza); usado en carencia y fraude."""
    return day_diff(claim.occurrence_date, policy.start_date)


def check_policy_active(ctx: EligibilityContext) -> Verdict:
    """Solo se liquidan polizas VIGENTES."""
    # REGLA: R-005 (estado de poliza distinto de VIGENTE => POLIZA_NO_VIGENTE)
    if ctx.policy.status != PolicyStatus.ACTIVE:
        return Verdict(Reason.POLICY_NOT_ACTIVE)
    return PASS


def check_in_force(ctx: EligibilityContext) -> Verdict:
    """Ocurrencia en [inicio, fin] inclusive, sin truncar la hora."""
    # REGLA: R-006 (comparacion directa < inicio o > fin; extremos inclusive)
    occurrence = ctx.claim.occurrence_date
    if occurrence < ctx.policy.start_date or occurrence > ctx.policy.end_date:
        return Verdict(Reason.OUT_OF_FORCE)
    return PASS


def check_report_deadline(ctx: EligibilityContext) -> Verdict:
    """Plazo de denuncia en dias calendario; el dia limite se acepta."""
    # REGLA: R-007 (dias > maximo, estricto; 30 general, 365 VIDA, por parametro)
    days = day_diff(ctx.claim.report_date, ctx.claim.occurrence_date)
    is_life = ctx.policy.branch == Branch.LIFE
    code = P.MAX_REPORT_DAYS_LIFE if is_life else P.MAX_REPORT_DAYS
    if days > ctx.params.require(code):
        return Verdict(Reason.LATE_REPORT)
    return PASS


def check_coverage_contracted(ctx: EligibilityContext) -> Verdict:
    """La cobertura reclamada debe existir en la poliza."""
    # REGLA: R-008 (sin fila de cobertura => COBERTURA_NO_CONTRATADA)
    if ctx.coverage is None:
        return Verdict(Reason.COVERAGE_NOT_CONTRACTED)
    return PASS


def check_waiting_period(ctx: EligibilityContext) -> Verdict:
    """Carencia: dias desde inicio < dias de carencia (estricto)."""
    # REGLA: R-009 (con exactamente dias_carencia dias la cobertura ya esta activa)
    if days_since_start(ctx.claim, ctx.policy) < ctx.coverage.waiting_days:
        return Verdict(Reason.IN_WAITING_PERIOD)
    return PASS


def check_premium_arrears(ctx: EligibilityContext) -> Verdict:
    """Mora de prima con tolerancia VIP por poliza."""
    # REGLA: R-010 (prima_pendiente > 0 rechaza salvo VIP con deuda <= tolerancia)
    debt = ctx.policy.pending_premium
    if debt <= 0:
        return PASS
    tolerance = ctx.params.require(P.VIP_ARREARS_TOLERANCE)
    if ctx.customer.category == CustomerCategory.VIP and debt <= tolerance:
        return Verdict(marks=(Mark.VIP_ARREARS_TOLERANCE,))
    return Verdict(Reason.PREMIUM_IN_ARREARS)


# REGLA: R-011 (orden fijo: el primer fallo gana y corta las siguientes validaciones)
ELIGIBILITY_CHECKS: tuple[Callable[[EligibilityContext], Verdict], ...] = (
    check_policy_active,
    check_in_force,
    check_report_deadline,
    check_coverage_contracted,
    check_waiting_period,
    check_premium_arrears,
)


def evaluate_eligibility(ctx: EligibilityContext) -> Verdict:
    """Ejecuta las validaciones en orden; devuelve el primer rechazo o las marcas."""
    # REGLA: R-011 (secuencia poliza, vigencia, denuncia, cobertura, carencia, mora)
    marks: tuple[Mark, ...] = ()
    for check in ELIGIBILITY_CHECKS:
        verdict = check(ctx)
        if verdict.reason is not None:
            return Verdict(verdict.reason, marks + verdict.marks)
        marks += verdict.marks
    return Verdict(None, marks)
