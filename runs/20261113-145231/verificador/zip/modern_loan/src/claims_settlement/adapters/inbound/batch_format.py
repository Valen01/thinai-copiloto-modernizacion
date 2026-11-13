"""Formato de archivos del lote: campos separados por '|', importes sin signo con punto.

Entrada (carpeta por tenant, un registro por linea, '#' inicia comentario):
  clientes.dat      cliente_id|nombre|tipo_documento|num_documento|categoria|fecha_alta
  polizas.dat       poliza_id|numero_poliza|cliente_id|ramo|fecha_inicio|fecha_fin|estado|
                    suma_asegurada|deducible_tipo|deducible_valor|prima_pendiente
  coberturas.dat    poliza_id|cod_cobertura|limite_cobertura|porcentaje_cobertura|dias_carencia
  siniestros.dat    siniestro_id|poliza_id|cod_cobertura|fecha_ocurrencia|fecha_denuncia|
                    monto_reclamado|estado|descripcion
  liquidaciones.dat historico: liquidacion_id|siniestro_id|fecha_liquidacion|monto_reclamado|
                    monto_base|monto_deducible|monto_cubierto|monto_retencion|monto_neto|
                    estado|motivo|observaciones
  parametros.dat    cod_parametro|valor_numerico|valor_texto|descripcion
Fechas: YYYY-MM-DD o YYYY-MM-DD HH:MM:SS.
"""
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from claims_settlement.adapters.outbound.memory_store import TenantData
from claims_settlement.domain.errors import DomainError
from claims_settlement.domain.model import Claim, Coverage, Customer, Policy, Settlement
from claims_settlement.domain.money import format_amount
from claims_settlement.domain.parameters import BusinessParameters

HISTORY_USER = "HIST"
_AMOUNT_RE = re.compile(r"^\d{1,12}(\.\d{1,2})?$")  # NUMBER(14,2) sin signo
_PCT_RE = re.compile(r"^\d{1,3}(\.\d{1,2})?$")  # NUMBER(5,2)
_PARAM_RE = re.compile(r"^\d{1,10}(\.\d{1,4})?$")  # NUMBER(14,4)
_INT_RE = re.compile(r"^\d{1,12}$")
_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S")


class BatchFormatError(DomainError):
    """Archivo de entrada mal formado (se rechaza completo, sin truncar)."""

    code = "BATCH-FORMAT"

    def __init__(self, file: str, line: int, detail: str) -> None:
        super().__init__(f"{file} linea {line}: {detail}")


def parse_int(text: str) -> int:
    if not _INT_RE.match(text):
        raise ValueError("entero invalido")
    return int(text)


def _parse_decimal(text: str, pattern: re.Pattern) -> Decimal:
    if not pattern.match(text):
        raise ValueError("importe invalido (sin signo, punto decimal, maximo 2 decimales)")
    return Decimal(text)


def parse_amount(text: str) -> Decimal:
    return _parse_decimal(text, _AMOUNT_RE)


def parse_pct(text: str) -> Decimal:
    return _parse_decimal(text, _PCT_RE)


def parse_date(text: str) -> datetime:
    """Fecha estricta: una fecha inexistente (p. ej. 2026-02-30) se rechaza."""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError("fecha invalida o inexistente")


def read_records(path: Path, width: int) -> list[tuple[int, list[str]]]:
    """Lee lineas no vacias; valida el numero de campos."""
    if not path.exists():
        raise BatchFormatError(path.name, 0, "archivo requerido no encontrado")
    records = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        fields = raw.split("|")
        if len(fields) != width:
            raise BatchFormatError(path.name, number, f"se esperan {width} campos")
        records.append((number, fields))
    return records


def load_file(path: Path, width: int, builder: Callable[[list[str]], None]) -> None:
    """Aplica builder a cada registro convirtiendo errores en BatchFormatError."""
    for number, fields in read_records(path, width):
        try:
            builder(fields)
        except DomainError as exc:
            raise BatchFormatError(path.name, number, str(exc)) from None
        except ValueError as exc:
            raise BatchFormatError(path.name, number, str(exc)) from None


def _customer(data: TenantData, f: list[str]) -> None:
    cid = parse_int(f[0])
    data.customers[cid] = Customer(cid, f[1], f[4])


def _policy(data: TenantData, f: list[str]) -> None:
    pid = parse_int(f[0])
    data.policies[pid] = Policy(
        pid, f[1], parse_int(f[2]), f[3], parse_date(f[4]), parse_date(f[5]), f[6],
        parse_amount(f[7]), f[8], parse_amount(f[9]), parse_amount(f[10]))


def _coverage(data: TenantData, f: list[str]) -> None:
    pid = parse_int(f[0])
    data.coverages[(pid, f[1])] = Coverage(
        pid, f[1], parse_amount(f[2]), parse_pct(f[3]), parse_int(f[4]))


def _claim(data: TenantData, f: list[str]) -> None:
    sid = parse_int(f[0])
    data.claims[sid] = Claim(sid, parse_int(f[1]), f[2], parse_date(f[3]), parse_date(f[4]),
                             parse_amount(f[5]), f[6])


def _history(data: TenantData, f: list[str]) -> None:
    amounts = [parse_amount(x) for x in f[3:9]]
    data.settlements.append(Settlement(
        parse_int(f[0]), parse_int(f[1]), parse_date(f[2]), *amounts,
        f[9], f[10], f[11] or None, HISTORY_USER))


def _parameter(values: dict[str, Optional[Decimal]], f: list[str]) -> None:
    values[f[0]] = _parse_decimal(f[1], _PARAM_RE) if f[1] else None


def load_tenant_data(directory: Path) -> TenantData:
    """Carga los archivos de un tenant en un TenantData (configuracion y datos)."""
    values: dict[str, Optional[Decimal]] = {}
    load_file(directory / "parametros.dat", 4, lambda f: _parameter(values, f))
    data = TenantData(BusinessParameters(values))
    load_file(directory / "clientes.dat", 6, lambda f: _customer(data, f))
    load_file(directory / "polizas.dat", 11, lambda f: _policy(data, f))
    load_file(directory / "coberturas.dat", 5, lambda f: _coverage(data, f))
    load_file(directory / "siniestros.dat", 8, lambda f: _claim(data, f))
    load_file(directory / "liquidaciones.dat", 12, lambda f: _history(data, f))
    return data


def format_settlement_line(s: Settlement) -> str:
    """Salida: liquidacion_id|siniestro_id|fecha|reclamado|base|deducible|cubierto|retencion|
    neto|estado|motivo|observaciones|usuario (importes sin signo, 2 decimales)."""
    fields = [str(s.settlement_id), str(s.claim_id), s.settlement_date.strftime("%Y-%m-%d"),
              format_amount(s.claimed_amount), format_amount(s.base_amount),
              format_amount(s.deductible), format_amount(s.covered),
              format_amount(s.withholding), format_amount(s.net),
              s.status, s.reason, s.observations or "", s.process_user]
    return "|".join(fields)
