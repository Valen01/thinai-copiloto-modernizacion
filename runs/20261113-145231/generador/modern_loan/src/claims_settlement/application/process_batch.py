"""Casos de uso por lote (pr_procesar_lote) y liquidacion individual con commit."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from claims_settlement.application.ports import (
    AuditLog, ClaimRepository, SettlementRepository, TransactionManager)
from claims_settlement.application.settle_claim import SettleClaim
from claims_settlement.domain.dates import as_datetime
from claims_settlement.domain.enums import ClaimStatus
from claims_settlement.domain.errors import DomainError
from claims_settlement.domain.model import Settlement
from claims_settlement.domain.money import ZERO


@dataclass(frozen=True)
class BatchSummary:
    """Contadores del lote."""

    processed: int
    settled: int
    rejected: int
    pending: int
    errors: int
    total_net_approved: Decimal


@dataclass
class _Counters:
    processed: int = 0
    settled: int = 0
    rejected: int = 0
    pending: int = 0
    errors: int = 0
    total_net: Decimal = ZERO

    def to_summary(self) -> BatchSummary:
        return BatchSummary(self.processed, self.settled, self.rejected,
                            self.pending, self.errors, self.total_net)


def describe_error(exc: Exception) -> str:
    """Mensaje seguro para bitacora: los de dominio ya vienen enmascarados."""
    if isinstance(exc, DomainError):
        return str(exc)
    return f"{type(exc).__name__}: error interno"


def format_process_date(process_date: datetime) -> str:
    return process_date.strftime("%Y-%m-%d")


class ProcessBatch:
    """Liquida los siniestros REGISTRADO con denuncia <= fecha de proceso."""

    def __init__(self, settle_claim: SettleClaim, claims: ClaimRepository,
                 settlements: SettlementRepository, audit: AuditLog,
                 transactions: TransactionManager) -> None:
        self._settle = settle_claim
        self._claims = claims
        self._settlements = settlements
        self._audit = audit
        self._tx = transactions

    def execute(self, tenant_id: str, process_date: datetime) -> BatchSummary:
        process_date = as_datetime(process_date, "fecha_proceso")
        # REGLA: R-031 (INFO de inicio con la fecha de proceso)
        self._audit.record(tenant_id, "INFO", None,
                           "Inicio lote de liquidacion. Fecha proceso: "
                           + format_process_date(process_date))
        counters = _Counters()
        # REGLA: R-028 (REGISTRADO con denuncia <= fecha de proceso, por id ascendente)
        for claim_id in self._claims.list_registered_claim_ids(tenant_id, process_date):
            counters.processed += 1
            self._process_one(tenant_id, claim_id, process_date, counters)
        # REGLA: R-031 (un unico COMMIT al terminar el bucle, no por siniestro)
        self._tx.commit(tenant_id)
        summary = counters.to_summary()
        self._audit.record(tenant_id, "INFO", None, self._end_message(summary))
        return summary

    @staticmethod
    def _end_message(s: BatchSummary) -> str:
        return (f"Fin lote. Procesados={s.processed} Liquidados={s.settled}"
                f" Rechazados={s.rejected} Pendientes={s.pending} Errores={s.errors}")

    def _process_one(self, tenant_id: str, claim_id: int, process_date: datetime,
                     counters: _Counters) -> None:
        # REGLA: R-029 (SAVEPOINT por siniestro; ante error, rollback, contar y continuar)
        self._tx.savepoint(tenant_id)
        try:
            self._settle.execute(tenant_id, claim_id, process_date)
            final = self._claims.get_claim(tenant_id, claim_id).status
            self._count(tenant_id, claim_id, final, counters)
        except Exception as exc:  # noqa: BLE001 - equivale a WHEN OTHERS
            self._tx.rollback_to_savepoint(tenant_id)
            counters.errors += 1
            self._audit.record(tenant_id, "ERROR", claim_id, describe_error(exc))

    def _count(self, tenant_id: str, claim_id: int, final: ClaimStatus,
               counters: _Counters) -> None:
        # REGLA: R-030 (contadores por estado final; solo el neto APROBADO suma al total)
        if final == ClaimStatus.SETTLED:
            counters.settled += 1
            counters.total_net += self._settlements.approved_net_for_claim(
                tenant_id, claim_id)
        elif final == ClaimStatus.REJECTED:
            counters.rejected += 1
        elif final == ClaimStatus.PENDING_REVIEW:
            counters.pending += 1


class SettleOneClaim:
    """Liquida un siniestro y controla la transaccion (el dominio no hace commit)."""

    def __init__(self, settle_claim: SettleClaim, transactions: TransactionManager) -> None:
        self._settle = settle_claim
        self._tx = transactions

    def execute(self, tenant_id: str, claim_id: int, process_date: datetime) -> Settlement:
        self._tx.savepoint(tenant_id)
        try:
            result = self._settle.execute(tenant_id, claim_id, process_date)
        except Exception:
            self._tx.rollback_to_savepoint(tenant_id)
            raise
        self._tx.commit(tenant_id)
        return result
