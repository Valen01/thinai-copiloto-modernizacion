"""Adaptador batch: lee los archivos de un tenant, ejecuta el lote y escribe la salida."""
import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Sequence

from claims_settlement.adapters.inbound.batch_format import (
    format_settlement_line, load_tenant_data)
from claims_settlement.adapters.outbound.memory_store import TenantDataStore
from claims_settlement.application.batch_summary import render_batch_summary
from claims_settlement.application.process_batch import BatchSummary
from claims_settlement.application.tenant import validate_tenant_id
from claims_settlement.bootstrap import Application, build_application
from claims_settlement.domain.errors import DomainError
from claims_settlement.shared.masking import mask_id

DATA_DIR_ENV = "CLAIMS_DATA_DIR"
OUT_DIR_ENV = "CLAIMS_OUT_DIR"


def default_process_date() -> datetime:
    """Fecha por defecto del lote: la fecha del sistema sin hora (TRUNC(SYSDATE))."""
    # REGLA: R-028 (p_fecha_proceso por defecto = TRUNC(SYSDATE))
    return datetime.combine(date.today(), datetime.min.time())


def parse_process_date(text: Optional[str]) -> datetime:
    if text is None:
        return default_process_date()
    return datetime.strptime(text, "%Y-%m-%d")


def run_tenant(app: Application, tenant_id: str, process_date: datetime,
               out_dir: Path) -> BatchSummary:
    """Ejecuta el lote de un tenant y escribe liquidaciones, siniestros, bitacora y resumen."""
    history_ids = {s.settlement_id for s in app.store.data(tenant_id).settlements}
    summary = app.batch.execute(tenant_id, process_date)
    write_outputs(app, tenant_id, process_date, summary, out_dir, history_ids)
    return summary


def write_outputs(app: Application, tenant_id: str, process_date: datetime,
                  summary: BatchSummary, out_dir: Path, history_ids: set) -> None:
    data = app.store.data(tenant_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    new = [s for s in data.settlements if s.settlement_id not in history_ids]
    (out_dir / "liquidaciones.out").write_text(
        "".join(format_settlement_line(s) + "\n" for s in new), encoding="utf-8")
    (out_dir / "siniestros.out").write_text(
        "".join(f"{c.claim_id}|{c.status.value}\n" for _, c in sorted(data.claims.items())),
        encoding="utf-8")
    (out_dir / "bitacora.out").write_text(
        "".join(_log_line(e) for e in app.audit.entries(tenant_id)), encoding="utf-8")
    (out_dir / "resumen.txt").write_text(
        render_batch_summary(tenant_id, summary, process_date), encoding="utf-8")


def _log_line(entry) -> str:
    ref = "" if entry.claim_id is None else mask_id(entry.claim_id)
    return f"{entry.log_id}|{entry.level}|{ref}|{entry.message}\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lote de liquidacion de siniestros")
    parser.add_argument("--tenant", required=True, help="identificador del tenant")
    parser.add_argument("--data-dir", default=os.environ.get(DATA_DIR_ENV, "examples"))
    parser.add_argument("--out-dir", default=os.environ.get(OUT_DIR_ENV, "out"))
    parser.add_argument("--process-date", default=None, help="YYYY-MM-DD (por defecto hoy)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tenant_id = validate_tenant_id(args.tenant)
        process_date = parse_process_date(args.process_date)
        store = TenantDataStore()
        store.register(tenant_id, load_tenant_data(Path(args.data_dir) / tenant_id))
        app = build_application(store)
        summary = run_tenant(app, tenant_id, process_date, Path(args.out_dir) / tenant_id)
    except (DomainError, ValueError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2
    sys.stdout.write(f"Tenant {tenant_id}\n"
                     + render_batch_summary(tenant_id, summary, process_date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
