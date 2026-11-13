"""Pruebas del caso de uso de liquidacion (R-001, R-002, R-012, R-018, R-019, R-021, R-023..R-027,
R-032, R-033, R-036, R-041, R-044). Valores esperados calculados a mano."""
import pytest
from factories import D, TENANT, claim, coverage, customer, dt, policy, params, settle, world

from claims_settlement.adapters.outbound.audit import EnvProcessUserProvider, InMemoryAuditLog
from claims_settlement.adapters.outbound.memory_repositories import (
    InMemoryClaimRepository, InMemoryParameterRepository, InMemoryPolicyRepository,
    InMemorySettlementRepository)
from claims_settlement.application.settle_claim import SettleClaim
from claims_settlement.domain.errors import (
    ClaimNotRegisteredError, EntityNotFoundError, ParameterNotDefinedError,
    UnknownSettlementStatusError)
from claims_settlement.domain.model import Amounts, Settlement


@pytest.fixture(autouse=True)
def process_user(monkeypatch):
    monkeypatch.setenv("CLAIMS_PROCESS_USER", "TESTER")


def add_prior(app, claim_id, occurrence, status="LIQUIDADO", covered="1000",
              liq_status="APROBADA"):
    """Agrega un siniestro previo de la poliza 101 con su liquidacion."""
    data = app.store.data(TENANT)
    data.claims[claim_id] = claim(claim_id=claim_id, occurrence_date=dt(occurrence),
                                  report_date=dt(occurrence), status=status)
    amount = D(covered)
    app.settlements.add(TENANT, Settlement(
        None, claim_id, dt(occurrence), amount, amount, D(0), amount, D(0), amount,
        liq_status, "LIQUIDACION_AUTOMATICA", None, "HIST"))


def final_claim(app, claim_id=1):
    return app.claims.get_claim(TENANT, claim_id)


def test_r001_only_registered_claims_are_settled():
    """REGLA: R-001 - estado distinto de REGISTRADO => ORA-20001 con id enmascarado, sin escribir."""
    app = world(claims=[claim(claim_id=1001, status="PENDIENTE_REVISION")])
    with pytest.raises(ClaimNotRegisteredError) as err:
        settle(app, 1001)
    assert "ORA-20001" in str(err.value) and "PENDIENTE_REVISION" in str(err.value)
    assert "**01" in str(err.value) and "1001" not in str(err.value)
    assert app.store.data(TENANT).settlements == []


@pytest.mark.parametrize("claim_id,pol_id,customer_id", [(99, 101, 1), (1, 999, 1), (1, 101, 9)])
def test_r002_missing_claim_policy_or_customer_propagates_no_data_found(
        claim_id, pol_id, customer_id):
    """REGLA: R-002 - siniestro, poliza o cliente inexistente => NO_DATA_FOUND, sin liquidacion."""
    app = world(pol=policy(customer_id=customer_id), claims=[claim(policy_id=pol_id)])
    with pytest.raises(EntityNotFoundError) as err:
        settle(app, claim_id)
    assert "NO_DATA_FOUND" in str(err.value)
    assert app.store.data(TENANT).settlements == []


def test_normal_settlement_amounts_and_record():
    """REGLA: R-026 - fila con fecha de proceso recibida, importes, estado, motivo y usuario.
    Calculo: base 1000, deducible 100, cubierto 900, retencion 0, neto 900."""
    app = world()
    s = settle(app, 1, "2026-03-31")
    assert (s.base_amount, s.deductible, s.covered, s.withholding, s.net) == (
        D(1000), D(100), D("900.00"), D("0.00"), D("900.00"))
    assert (s.status, s.reason, s.observations) == (
        "APROBADA", "LIQUIDACION_AUTOMATICA", None)
    assert s.settlement_date == dt("2026-03-31") and s.claimed_amount == D(1000)
    assert s.process_user == "TESTER" and s.settlement_id == 1
    assert final_claim(app).status.value == "LIQUIDADO"  # REGLA: R-025


def test_r033_result_is_logged_with_state_reason_and_net():
    """REGLA: R-033 - cada resultado escribe un INFO con estado, motivo y neto."""
    app = world()
    settle(app)
    messages = [e.message for e in app.audit.entries(TENANT)]
    assert messages == ["Resultado: APROBADA / LIQUIDACION_AUTOMATICA / neto=900.00"]


def test_r033_message_truncated_to_1000_chars():
    """REGLA: R-033 - el mensaje de bitacora se trunca a 1000 caracteres."""
    audit = InMemoryAuditLog()
    audit.record(TENANT, "INFO", None, "x" * 1500)
    assert len(audit.entries(TENANT)[0].message) == 1000


def test_r012_rejection_stores_zero_amounts():
    """REGLA: R-012 - poliza cancelada: RECHAZADA, importes en cero, motivo, siniestro RECHAZADO."""
    app = world(pol=policy(status="CANCELADA"))
    s = settle(app)
    assert (s.status, s.reason, s.observations) == ("RECHAZADA", "POLIZA_NO_VIGENTE", None)
    assert (s.base_amount, s.deductible, s.covered, s.withholding, s.net) == (D(0),) * 5
    assert final_claim(app).status.value == "RECHAZADO"


def test_r012_below_deductible_keeps_marks_but_zero_amounts():
    """REGLA: R-012 - BAJO_DEDUCIBLE conserva marcas y guarda importes en cero.
    Reclamado 60000, limite 50000 (marca), deducible fijo 50000 => cubierto 0."""
    app = world(pol=policy(deductible_value=D(50000)),
                claims=[claim(claimed_amount=D(60000))])
    s = settle(app)
    assert (s.reason, s.observations) == ("BAJO_DEDUCIBLE", "LIMITE_COBERTURA")
    assert (s.base_amount, s.covered, s.net) == (D(0), D(0), D(0))  # REGLA: R-017


def test_r012_arrears_rejection_has_empty_observations():
    """REGLA: R-012 - PRIMA_EN_MORA: las observaciones aun estan vacias (R-010)."""
    s = settle(world(pol=policy(pending_premium=D(900))))
    assert (s.reason, s.observations, s.net) == ("PRIMA_EN_MORA", None, D(0))


def test_r010_vip_tolerance_mark_is_first_observation():
    """REGLA: R-010 - VIP con deuda 300 <= 500: continua con marca TOLERANCIA_MORA_VIP.
    Deducible fijo 100 con descuento VIP 50% = 50.00 => cubierto 950.00."""
    app = world(pol=policy(pending_premium=D(300)), cust=customer("VIP"))
    s = settle(app)
    assert s.observations == "TOLERANCIA_MORA_VIP;DESCUENTO_VIP"
    assert (s.deductible, s.covered) == (D("50.00"), D("950.00"))


def test_r019_sum_insured_exhausted_rejects_with_marks():
    """REGLA: R-019 - remanente <= 0 => SUMA_ASEGURADA_AGOTADA (aprobadas y pendientes suman)."""
    app = world(pol=policy(sum_insured=D(1000)))
    add_prior(app, 2, "2025-03-01", covered="600", liq_status="APROBADA")
    add_prior(app, 3, "2025-03-02", status="PENDIENTE_REVISION", covered="400",
              liq_status="PENDIENTE_APROBACION")
    s = settle(app)
    assert (s.status, s.reason, s.covered) == ("RECHAZADA", "SUMA_ASEGURADA_AGOTADA", D(0))


def test_r019_rejected_settlements_do_not_consume_sum_insured():
    """REGLA: R-019 - una liquidacion RECHAZADA no suma al total indemnizado."""
    app = world(pol=policy(sum_insured=D(1000)))
    add_prior(app, 2, "2025-03-01", status="RECHAZADO", covered="1000", liq_status="RECHAZADA")
    assert settle(app).covered == D("900.00")


def test_r021_order_penalty_then_cap_then_withholding():
    """REGLA: R-021 - penalizacion antes del tope y retencion despues.
    Reclamado 20000, ded 100 => cubierto 19900; 3 previos => *0.9 = 17910.00;
    remanente 20000-3000 = 17000 => tope 17000; retencion 2% = 340.00; neto 16660.00."""
    app = world(pol=policy(sum_insured=D(20000), deductible_value=D(100)),
                claims=[claim(claimed_amount=D(20000))])
    for cid, occ in ((2, "2025-06-01"), (3, "2025-08-01"), (4, "2025-12-01")):
        add_prior(app, cid, occ)
    s = settle(app)
    assert (s.base_amount, s.deductible, s.covered) == (D(20000), D(100), D("17000.00"))
    assert (s.withholding, s.net) == (D("340.00"), D("16660.00"))
    assert s.observations == (
        "PENALIZACION_SINIESTRALIDAD;TOPE_SUMA_ASEGURADA;RETENCION_APLICADA")


@pytest.mark.parametrize("third_occurrence,status,penalized", [
    ("2025-02-10", "LIQUIDADO", True),          # ocurrencia - 365 dias: limite inferior inclusive
    ("2025-02-09", "LIQUIDADO", False),         # 366 dias antes: fuera
    ("2026-02-10", "LIQUIDADO", False),         # misma fecha: limite superior exclusivo
    ("2025-06-01", "PENDIENTE_REVISION", False),  # solo cuenta LIQUIDADO
    ("2025-06-01", "LIQUIDADO", True),
])
def test_r018_window_boundaries_and_state(third_occurrence, status, penalized):
    """REGLA: R-018 - ventana [ocurrencia-365, ocurrencia); 3 previos LIQUIDADO penalizan.
    Cubierto 900 -> 810.00 si hay penalizacion."""
    app = world()
    add_prior(app, 2, "2025-06-01", covered="0")
    add_prior(app, 3, "2025-08-01", covered="0")
    add_prior(app, 4, third_occurrence, status=status, covered="0")
    s = settle(app)
    assert (s.covered == D("810.00")) is penalized
    assert (s.observations == "PENALIZACION_SINIESTRALIDAD") is penalized


def test_r018_other_policy_claims_do_not_count():
    """REGLA: R-018 - solo cuentan siniestros de la misma poliza."""
    app = world()
    for cid in (2, 3, 4):
        data = app.store.data(TENANT)
        data.claims[cid] = claim(claim_id=cid, policy_id=555, status="LIQUIDADO",
                                 occurrence_date=dt("2025-06-01"))
    assert settle(app).covered == D("900.00")


def test_r023_fraud_alert_keeps_amounts_and_is_pending():
    """REGLA: R-023 - 9 dias desde inicio y reclamado 800 >= 80% de 1000: PENDIENTE_APROBACION.
    Los importes SI se guardan: base 800, deducible 100, cubierto 700, neto 700."""
    app = world(pol=policy(start_date=dt("2026-02-01")), cov=coverage(limit=D(1000)),
                claims=[claim(claimed_amount=D(800))])
    s = settle(app)
    assert (s.status, s.reason) == ("PENDIENTE_APROBACION", "SOSPECHA_FRAUDE")
    assert (s.base_amount, s.deductible, s.covered, s.net) == (D(800), D(100), D(700), D(700))
    assert final_claim(app).status.value == "PENDIENTE_REVISION"


def test_r023_fraud_compares_claimed_not_covered():
    """REGLA: R-023 - se compara el RECLAMADO: 799.99 < 800.00 no alerta aunque sea temprano."""
    app = world(pol=policy(start_date=dt("2026-02-01")), cov=coverage(limit=D(1000)),
                claims=[claim(claimed_amount=D("799.99"))])
    assert settle(app).status == "APROBADA"


def test_r024_net_above_auto_limit_is_pending():
    """REGLA: R-024 - reclamado 70000 sin deducible: retencion 2% = 1400.00, neto 68600.00 > 50000."""
    app = world(pol=policy(deductible_value=D(0)), cov=coverage(limit=D(100000)),
                claims=[claim(claimed_amount=D(70000))])
    s = settle(app)
    assert (s.status, s.reason, s.net) == (
        "PENDIENTE_APROBACION", "SUPERA_TOPE_AUTOMATICO", D("68600.00"))


def test_r044_missing_inflation_factor_fails_every_claim_first():
    """REGLA: R-044 - sin FACTOR_INFLACION todo siniestro falla con ORA-20010 antes de validar."""
    app = world(pol=policy(status="CANCELADA"), prm=params(FACTOR_INFLACION="DROP"))
    with pytest.raises(ParameterNotDefinedError):
        settle(app)
    assert app.store.data(TENANT).settlements == []


def test_r032_process_date_only_sets_settlement_date():
    """REGLA: R-032 - la fecha de proceso no participa en validaciones: mismo resultado."""
    first = settle(world(), 1, "2020-01-01")
    second = settle(world(), 1, "2031-12-31")
    assert first.settlement_date == dt("2020-01-01") and second.settlement_date == dt("2031-12-31")
    assert (first.status, first.net, first.reason) == (second.status, second.net, second.reason)


def build_raw(app, debug=False):
    store = app.store
    return SettleClaim(InMemoryClaimRepository(store), InMemoryPolicyRepository(store),
                       InMemorySettlementRepository(store), InMemoryParameterRepository(store),
                       app.audit, EnvProcessUserProvider(), debug)


def test_r027_settle_claim_never_commits():
    """REGLA: R-027 - la liquidacion no hace COMMIT; el llamador controla la transaccion."""
    app = world()
    build_raw(app).execute(TENANT, 1, dt("2026-03-31"))
    assert app.store.data(TENANT).commits == 0
    settle(app, 1) if False else None
    app2 = world()
    settle(app2)
    assert app2.store.data(TENANT).commits == 1  # la envoltura (SettleOneClaim) confirma


def test_r036_unknown_status_writes_nothing():
    """REGLA: R-036 - estado de liquidacion desconocido: error y no se escribe nada."""
    app = world()
    raw = build_raw(app)
    with pytest.raises(UnknownSettlementStatusError):
        raw._register(TENANT, claim(), dt("2026-03-31"), Amounts(), "ANULADA", "X", None)
    assert app.store.data(TENANT).settlements == []
    assert final_claim(app).status.value == "REGISTRADO"


def test_r041_debug_trace_off_by_default_and_masked_when_enabled():
    """REGLA: R-041 - trazas DEBUG apagadas por defecto; si se activan, enmascaradas."""
    app = world()
    build_raw(app).execute(TENANT, 1, dt("2026-03-31"))
    assert [e.level for e in app.audit.entries(TENANT)] == ["INFO"]
    app2 = world()
    build_raw(app2, debug=True).execute(TENANT, 1, dt("2026-03-31"))
    debug = [e.message for e in app2.audit.entries(TENANT) if e.level == "DEBUG"]
    assert debug == ["DEBUG siniestro=* poliza=*01 asegurado=A. T."]
