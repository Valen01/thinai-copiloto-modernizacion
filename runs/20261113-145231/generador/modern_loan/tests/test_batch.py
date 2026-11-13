"""Pruebas del lote (R-028 a R-031, R-033, R-035) con valores calculados a mano."""
from decimal import Decimal

import pytest
from factories import D, TENANT, claim, coverage, dt, policy, world

from claims_settlement.adapters.outbound.audit import EnvProcessUserProvider
from claims_settlement.adapters.outbound.memory_repositories import (
    InMemoryClaimRepository, InMemoryParameterRepository, InMemoryPolicyRepository,
    InMemorySettlementRepository, InMemoryTransactionManager)
from claims_settlement.application.batch_summary import render_batch_summary
from claims_settlement.application.process_batch import (
    BatchSummary, ProcessBatch, describe_error)
from claims_settlement.application.settle_claim import SettleClaim
from claims_settlement.domain.errors import InvalidValueError

CUTOFF = dt("2026-03-31")


def batch_app():
    """Reclamos: 1,3 aprobados; 2 poliza cancelada; 6 poliza inexistente; 7 sospecha de fraude;
    4 denuncia posterior al corte y 5 ya LIQUIDADO (no se seleccionan)."""
    app = world(claims=[
        claim(claim_id=3, claimed_amount=D(2000), occurrence_date=dt("2026-03-25"),
              report_date=dt("2026-03-31")),            # denuncia == corte: inclusive
        claim(claim_id=1),
        claim(claim_id=2, policy_id=102),
        claim(claim_id=6, policy_id=999),
        claim(claim_id=7, policy_id=103, claimed_amount=D(800)),
        claim(claim_id=4, report_date=dt("2026-04-01")),
        claim(claim_id=5, status="LIQUIDADO"),
    ])
    data = app.store.data(TENANT)
    for pid, kw in ((102, dict(status="CANCELADA")), (103, dict(start_date=dt("2026-02-01")))):
        data.policies[pid] = policy(policy_id=pid, **kw)
        data.coverages[(pid, "COB")] = coverage(policy_id=pid, limit=D(1000 if pid == 103 else 50000))
    return app


def test_r028_selection_and_order_and_r030_counters():
    """REGLA: R-028 - REGISTRADO con denuncia <= corte, ids ascendentes (1,2,3,6,7).
    REGLA: R-030 - liquidados 2 (neto 900 + 1900 = 2800.00), rechazados 1, pendientes 1, errores 1."""
    app = batch_app()
    summary = app.batch.execute(TENANT, CUTOFF)
    assert summary == BatchSummary(5, 2, 1, 1, 1, D("2800.00"))
    assert [s.claim_id for s in app.store.data(TENANT).settlements] == [1, 2, 3, 7]
    statuses = {c.claim_id: c.status.value for c in app.store.data(TENANT).claims.values()}
    assert statuses == {1: "LIQUIDADO", 2: "RECHAZADO", 3: "LIQUIDADO", 4: "REGISTRADO",
                        5: "LIQUIDADO", 6: "REGISTRADO", 7: "PENDIENTE_REVISION"}


def test_r030_pending_net_is_not_added_to_total():
    """REGLA: R-030 - el neto PENDIENTE (claim 7: 700) no entra en el total neto aprobado."""
    app = batch_app()
    assert app.batch.execute(TENANT, CUTOFF).total_net_approved == D("2800.00")


def test_r029_error_is_isolated_logged_and_reselected_next_batch():
    """REGLA: R-029 - el error de un siniestro no detiene el lote y queda REGISTRADO;
    el siguiente lote lo vuelve a seleccionar (procesados 1, errores 1)."""
    app = batch_app()
    app.batch.execute(TENANT, CUTOFF)
    errors = [e for e in app.audit.entries(TENANT) if e.level == "ERROR"]
    assert len(errors) == 1 and errors[0].claim_id == 6 and "NO_DATA_FOUND" in errors[0].message
    second = app.batch.execute(TENANT, CUTOFF)
    assert (second.processed, second.settled, second.errors) == (1, 0, 1)


class FlakyClaims(InMemoryClaimRepository):
    """Falla al actualizar el estado del siniestro 2, despues de insertar la liquidacion."""

    def update_status(self, tenant_id, claim_id, status):
        if claim_id == 2:
            raise RuntimeError("fallo simulado")
        super().update_status(tenant_id, claim_id, status)


def flaky_batch(app):
    store = app.store
    claims = FlakyClaims(store)
    settlements = InMemorySettlementRepository(store)
    tx = InMemoryTransactionManager(store)
    settle = SettleClaim(claims, InMemoryPolicyRepository(store), settlements,
                         InMemoryParameterRepository(store), app.audit,
                         EnvProcessUserProvider())
    return ProcessBatch(settle, claims, settlements, app.audit, tx)


def test_r029_rollback_to_savepoint_undoes_insert_but_not_sequence_or_log():
    """REGLA: R-029 - ROLLBACK al savepoint deshace liquidacion y estado; la secuencia no vuelve.
    REGLA: R-033 - la bitacora de errores persiste tras el rollback."""
    app = world(claims=[claim(claim_id=1), claim(claim_id=2), claim(claim_id=3)])
    summary = flaky_batch(app).execute(TENANT, CUTOFF)
    data = app.store.data(TENANT)
    assert (summary.processed, summary.settled, summary.errors) == (3, 2, 1)
    assert [(s.claim_id, s.settlement_id) for s in data.settlements] == [(1, 1), (3, 3)]
    assert data.claims[2].status.value == "REGISTRADO"
    error = [e for e in app.audit.entries(TENANT) if e.level == "ERROR"][0]
    assert error.message == "RuntimeError: error interno"  # sin datos del error original


def test_r031_single_commit_and_start_end_logs():
    """REGLA: R-031 - un unico COMMIT al final y logs INFO de inicio y fin con contadores."""
    app = batch_app()
    app.batch.execute(TENANT, CUTOFF)
    assert app.store.data(TENANT).commits == 1
    messages = [e.message for e in app.audit.entries(TENANT) if e.claim_id is None]
    assert messages == [
        "Inicio lote de liquidacion. Fecha proceso: 2026-03-31",
        "Fin lote. Procesados=5 Liquidados=2 Rechazados=1 Pendientes=1 Errores=1"]


def test_r031_empty_batch_still_commits_and_logs():
    """REGLA: R-031 - sin siniestros seleccionables igual hay COMMIT y logs de inicio y fin."""
    app = world(claims=[claim(status="LIQUIDADO")])
    summary = app.batch.execute(TENANT, CUTOFF)
    assert summary == BatchSummary(0, 0, 0, 0, 0, D("0.00"))
    assert app.store.data(TENANT).commits == 1 and len(app.audit.entries(TENANT)) == 2


def test_r035_summary_format():
    """REGLA: R-035 - resumen con procesados, liquidados, rechazados, pendientes, errores y neto."""
    text = render_batch_summary(TENANT, BatchSummary(5, 2, 1, 1, 1, Decimal("2800")), CUTOFF)
    assert text == (
        "=========================================\n"
        " RESUMEN LOTE DE LIQUIDACION\n"
        " Fecha de proceso   : 2026-03-31\n"
        " Procesados         : 5\n"
        " Liquidados         : 2\n"
        " Rechazados         : 1\n"
        " Pendientes revision: 1\n"
        " Errores            : 1\n"
        " Total neto aprobado: 2800.00\n"
        "=========================================\n")


def test_describe_error_uses_domain_message_or_generic_text():
    """REGLA: R-029 - el log ERROR lleva el mensaje de dominio (enmascarado) o texto generico."""
    assert describe_error(InvalidValueError("x")) == "INVALID_VALUE: x: valor no permitido"
    assert describe_error(ValueError("dato sensible")) == "ValueError: error interno"


def test_batch_rejects_invalid_process_date_type():
    """REGLA: R-032 - la fecha de proceso debe ser una fecha valida (no texto)."""
    with pytest.raises(InvalidValueError):
        batch_app().batch.execute(TENANT, "2026-03-31")
