"""Pruebas de validaciones de procedencia (R-005 a R-011). Valores calculados a mano."""
from decimal import Decimal

import pytest
from factories import D, claim, coverage, customer, dt, params, policy

from claims_settlement.domain.eligibility import (
    EligibilityContext, check_coverage_contracted, check_in_force, check_policy_active,
    check_premium_arrears, check_report_deadline, check_waiting_period, evaluate_eligibility)
from claims_settlement.domain.enums import Mark, Reason


def ctx(**kw) -> EligibilityContext:
    base = dict(claim=claim(), policy=policy(), customer=customer(),
                coverage=coverage(), params=params())
    base.update(kw)
    return EligibilityContext(**base)


@pytest.mark.parametrize("status,expected", [
    ("VIGENTE", None), ("CANCELADA", Reason.POLICY_NOT_ACTIVE),
    ("SUSPENDIDA", Reason.POLICY_NOT_ACTIVE)])
def test_r005_only_active_policies(status, expected):
    """REGLA: R-005 - solo VIGENTE se liquida; CANCELADA y SUSPENDIDA se rechazan."""
    assert check_policy_active(ctx(policy=policy(status=status))).reason == expected


@pytest.mark.parametrize("occurrence,rejected", [
    ("2025-01-01", False),            # igual al inicio: inclusive
    ("2026-12-31", False),            # igual al fin: inclusive
    ("2024-12-31 23:59:59", True),    # un segundo antes del inicio
    ("2026-12-31 00:00:01", True),    # sin TRUNC: un segundo despues del fin (medianoche)
])
def test_r006_force_boundaries_inclusive_without_trunc(occurrence, rejected):
    """REGLA: R-006 - vigencia [inicio, fin] inclusive, comparacion directa sin truncar."""
    verdict = check_in_force(ctx(claim=claim(occurrence_date=dt(occurrence))))
    assert (verdict.reason == Reason.OUT_OF_FORCE) is rejected


@pytest.mark.parametrize("report,rejected", [
    ("2026-03-12", False),            # 30 dias: dia limite aceptado
    ("2026-03-12 23:00:00", False),   # la hora se trunca: sigue siendo 30 dias
    ("2026-03-13", True),             # 31 dias > 30
])
def test_r007_general_deadline_strict(report, rejected):
    """REGLA: R-007 - dias > maximo (estricto); 30 dias calendario para ramos generales."""
    c = claim(occurrence_date=dt("2026-02-10 08:00:00"), report_date=dt(report))
    assert (check_report_deadline(ctx(claim=c)).reason == Reason.LATE_REPORT) is rejected


@pytest.mark.parametrize("report,rejected", [("2027-02-10", False), ("2027-02-11", True)])
def test_r007_life_deadline_365(report, rejected):
    """REGLA: R-007 - ramo VIDA usa DIAS_MAX_DENUNCIA_VIDA = 365 (365 ok, 366 rechaza)."""
    c = claim(occurrence_date=dt("2026-02-10"), report_date=dt(report))
    verdict = check_report_deadline(ctx(claim=c, policy=policy(branch="VIDA")))
    assert (verdict.reason == Reason.LATE_REPORT) is rejected


def test_r008_coverage_not_contracted():
    """REGLA: R-008 - sin cobertura para poliza y codigo => COBERTURA_NO_CONTRATADA."""
    assert check_coverage_contracted(ctx(coverage=None)).reason == Reason.COVERAGE_NOT_CONTRACTED
    assert check_coverage_contracted(ctx()).reason is None


@pytest.mark.parametrize("occurrence,rejected", [
    ("2025-01-31", False),   # 30 dias desde inicio == carencia: activa
    ("2025-01-30", True),    # 29 dias < 30
])
def test_r009_waiting_period_strict(occurrence, rejected):
    """REGLA: R-009 - rechaza si dias_desde_inicio < dias_carencia (estricto)."""
    c = ctx(claim=claim(occurrence_date=dt(occurrence)), coverage=coverage(waiting_days=30))
    assert (check_waiting_period(c).reason == Reason.IN_WAITING_PERIOD) is rejected


@pytest.mark.parametrize("debt,category,reason,marks", [
    ("0", "ESTANDAR", None, ()),
    ("300", "VIP", None, (Mark.VIP_ARREARS_TOLERANCE,)),
    ("500", "VIP", None, (Mark.VIP_ARREARS_TOLERANCE,)),     # deuda == tolerancia: tolera
    ("500.01", "VIP", Reason.PREMIUM_IN_ARREARS, ()),
    ("1", "ESTANDAR", Reason.PREMIUM_IN_ARREARS, ()),
    ("300", "PREFERENTE", Reason.PREMIUM_IN_ARREARS, ()),    # PREFERENTE sin beneficio (R-004)
])
def test_r010_arrears_with_vip_tolerance(debt, category, reason, marks):
    """REGLA: R-010 - mora rechaza salvo VIP con deuda <= TOLERANCIA_MORA_VIP (por poliza)."""
    c = ctx(policy=policy(pending_premium=Decimal(debt)), customer=customer(category))
    verdict = check_premium_arrears(c)
    assert (verdict.reason, verdict.marks) == (reason, marks)


def test_r010_parameter_read_only_when_debt_exists():
    """REGLA: R-010 - el parametro solo se lee si hay deuda (sin deuda no falla si falta)."""
    c = ctx(params=params(TOLERANCIA_MORA_VIP="DROP"))
    assert check_premium_arrears(c).reason is None


@pytest.mark.parametrize("pol,clm,cov,expected", [
    # poliza cancelada y ademas fuera de vigencia: gana la poliza
    (dict(status="CANCELADA"), dict(occurrence_date=dt("2020-01-01")), {},
     Reason.POLICY_NOT_ACTIVE),
    # fuera de vigencia y ademas denuncia tardia: gana la vigencia
    ({}, dict(occurrence_date=dt("2020-01-01"), report_date=dt("2021-01-01")), {},
     Reason.OUT_OF_FORCE),
    # denuncia tardia con carencia pendiente: gana la denuncia
    ({}, dict(occurrence_date=dt("2025-01-02"), report_date=dt("2025-06-01")),
     dict(waiting_days=90), Reason.LATE_REPORT),
    # carencia y mora: gana la carencia
    (dict(pending_premium=D(900)), dict(occurrence_date=dt("2025-01-02"),
                                        report_date=dt("2025-01-03")),
     dict(waiting_days=90), Reason.IN_WAITING_PERIOD),
    # solo mora
    (dict(pending_premium=D(900)), {}, {}, Reason.PREMIUM_IN_ARREARS),
])
def test_r011_first_failure_wins(pol, clm, cov, expected):
    """REGLA: R-011 - orden poliza, vigencia, denuncia, cobertura, carencia, mora."""
    verdict = evaluate_eligibility(ctx(policy=policy(**pol), claim=claim(**clm),
                                       coverage=coverage(**cov)))
    assert verdict.reason == expected


def test_r011_missing_coverage_beats_waiting_and_arrears():
    """REGLA: R-011 - cobertura no contratada se evalua antes que carencia y mora."""
    verdict = evaluate_eligibility(ctx(coverage=None, policy=policy(pending_premium=D(900))))
    assert verdict.reason == Reason.COVERAGE_NOT_CONTRACTED


def test_r011_all_pass_collects_tolerance_mark():
    """REGLA: R-011 - si todo pasa se devuelven las marcas acumuladas (tolerancia VIP)."""
    c = ctx(policy=policy(pending_premium=D(200)), customer=customer("VIP"))
    verdict = evaluate_eligibility(c)
    assert verdict.reason is None and verdict.marks == (Mark.VIP_ARREARS_TOLERANCE,)
