"""Resumen del lote con el formato del DBMS_OUTPUT del legacy."""
from datetime import datetime

from claims_settlement.application.process_batch import BatchSummary, format_process_date
from claims_settlement.domain.money import format_amount

_LINE = "=" * 41


def render_batch_summary(tenant_id: str, summary: BatchSummary,
                         process_date: datetime) -> str:
    """Resumen informativo de un tenant (solo salida, sin logica de negocio).

    El tenant_id identifica el lote al que pertenece el resumen; el texto no lo
    incluye para conservar el formato original (el adaptador lo antepone).
    """
    # REGLA: R-035 (procesados, liquidados, rechazados, pendientes, errores y neto 0.00)
    lines = [
        _LINE,
        " RESUMEN LOTE DE LIQUIDACION",
        " Fecha de proceso   : " + format_process_date(process_date),
        f" Procesados         : {summary.processed}",
        f" Liquidados         : {summary.settled}",
        f" Rechazados         : {summary.rejected}",
        f" Pendientes revision: {summary.pending}",
        f" Errores            : {summary.errors}",
        " Total neto aprobado: " + format_amount(summary.total_net_approved),
        _LINE,
    ]
    return "\n".join(lines) + "\n"
