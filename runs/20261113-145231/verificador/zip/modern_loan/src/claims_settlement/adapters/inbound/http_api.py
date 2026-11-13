"""Adaptador HTTP (stdlib). La logica de ruteo es una funcion pura testeable sin sockets."""
import json
import logging
import os
import re
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Mapping, NamedTuple, Optional

from claims_settlement.adapters.inbound.batch_format import load_tenant_data
from claims_settlement.application.process_batch import BatchSummary
from claims_settlement.application.tenant import validate_tenant_id
from claims_settlement.bootstrap import Application
from claims_settlement.domain.errors import (
    ClaimNotRegisteredError, DomainError, EntityNotFoundError, InvalidValueError,
    TenantNotFoundError)
from claims_settlement.domain.model import Settlement
from claims_settlement.domain.money import format_amount
from claims_settlement.shared.masking import mask_id

TENANT_HEADER = "X-Tenant-ID"
MAX_BODY = 65536
_LOCK = threading.Lock()  # el almacen en memoria es de un solo escritor
_log = logging.getLogger("claims_settlement.http")

_SETTLE_RE = re.compile(r"^/v1/claims/(\d{1,12})/settlements$")
_LATEST_RE = re.compile(r"^/v1/claims/(\d{1,12})/settlement$")
_BATCH_RE = re.compile(r"^/v1/settlement-batches$")

# Tabla de decision: error de dominio -> (estado HTTP, codigo)
_ERROR_STATUS: tuple[tuple[type, int, str], ...] = (
    (ClaimNotRegisteredError, 409, "claim_not_registered"),
    (EntityNotFoundError, 404, "not_found"),
    (TenantNotFoundError, 404, "tenant_not_found"),
    (InvalidValueError, 422, "invalid_value"),
    (DomainError, 500, "domain_error"),
)


class ApiResponse(NamedTuple):
    status: int
    body: dict


def settlement_json(s: Settlement) -> dict:
    return {
        "settlement_id": s.settlement_id, "claim_id": s.claim_id,
        "settlement_date": s.settlement_date.strftime("%Y-%m-%d"),
        "claimed_amount": format_amount(s.claimed_amount),
        "base_amount": format_amount(s.base_amount),
        "deductible": format_amount(s.deductible), "covered": format_amount(s.covered),
        "withholding": format_amount(s.withholding), "net": format_amount(s.net),
        "status": s.status, "reason": s.reason, "observations": s.observations,
        "process_user": s.process_user,
    }


def summary_json(s: BatchSummary) -> dict:
    return {"processed": s.processed, "settled": s.settled, "rejected": s.rejected,
            "pending": s.pending, "errors": s.errors,
            "total_net_approved": format_amount(s.total_net_approved)}


def error_response(exc: DomainError) -> ApiResponse:
    for kind, status, code in _ERROR_STATUS:
        if isinstance(exc, kind):
            return ApiResponse(status, {"error": code, "detail": str(exc)})
    return ApiResponse(500, {"error": "domain_error", "detail": str(exc)})


def _process_date(body: bytes) -> datetime:
    try:
        payload = json.loads(body or b"{}")
        return datetime.strptime(payload["process_date"], "%Y-%m-%d")
    except (ValueError, KeyError, TypeError):
        raise InvalidValueError("process_date", "se espera YYYY-MM-DD") from None


def tenant_from_headers(headers: Mapping[str, str]) -> str:
    """Lee X-Tenant-ID sin distinguir mayusculas y lo valida."""
    wanted = TENANT_HEADER.lower()
    raw = next((v for k, v in headers.items() if k.lower() == wanted), None)
    return validate_tenant_id(raw)


class Router:
    """Resuelve rutas y delega en los casos de uso. Siempre exige X-Tenant-ID."""

    def __init__(self, app: Application, data_dir: Optional[Path] = None) -> None:
        self._app = app
        self._data_dir = data_dir

    def handle(self, method: str, path: str, headers: Mapping[str, str],
               body: bytes) -> ApiResponse:
        try:
            tenant_id = tenant_from_headers(headers)
            self._ensure_tenant(tenant_id)
            return self._dispatch(tenant_id, method, path, body)
        except DomainError as exc:
            return error_response(exc)

    def _ensure_tenant(self, tenant_id: str) -> None:
        if self._app.store.has(tenant_id):
            return
        directory = None if self._data_dir is None else self._data_dir / tenant_id
        if directory is None or not directory.is_dir():
            raise TenantNotFoundError(tenant_id)
        self._app.store.register(tenant_id, load_tenant_data(directory))

    def _dispatch(self, tenant_id: str, method: str, path: str, body: bytes) -> ApiResponse:
        for pattern, verb, handler in self._routes():
            found = pattern.match(path)
            if found and verb == method:
                return handler(tenant_id, found, body)
        return ApiResponse(404, {"error": "route_not_found", "detail": "ruta no definida"})

    def _routes(self) -> tuple:
        return (
            (_SETTLE_RE, "POST", self._settle),
            (_LATEST_RE, "GET", self._latest),
            (_BATCH_RE, "POST", self._batch),
        )

    def _settle(self, tenant_id: str, found, body: bytes) -> ApiResponse:
        date_ = _process_date(body)
        with _LOCK:
            result = self._app.settle_one.execute(tenant_id, int(found.group(1)), date_)
        return ApiResponse(201, settlement_json(result))

    def _latest(self, tenant_id: str, found, body: bytes) -> ApiResponse:
        claim_id = int(found.group(1))
        result = self._app.settlements.latest_for_claim(tenant_id, claim_id)
        if result is None:
            raise EntityNotFoundError("Liquidacion", claim_id)
        return ApiResponse(200, settlement_json(result))

    def _batch(self, tenant_id: str, found, body: bytes) -> ApiResponse:
        date_ = _process_date(body)
        with _LOCK:
            summary = self._app.batch.execute(tenant_id, date_)
        return ApiResponse(200, summary_json(summary))


def make_handler(router: Router) -> Callable[..., BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _serve(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self._send(ApiResponse(413, {"error": "body_too_large", "detail": "limite 64KB"}))
                return
            body = self.rfile.read(length) if length else b""
            self._send(router.handle(self.command, self.path, dict(self.headers), body))

        def _send(self, response: ApiResponse) -> None:
            data = json.dumps(response.body).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = _serve
        do_POST = _serve

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            _log.info("http %s ref=%s", self.command, mask_id(self.path))

    return Handler


def make_server(router: Router, host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(router))


def serve() -> None:  # pragma: no cover - arranque manual
    from claims_settlement.adapters.outbound.memory_store import TenantDataStore
    from claims_settlement.bootstrap import build_application
    data_dir = Path(os.environ.get("CLAIMS_DATA_DIR", "examples"))
    router = Router(build_application(TenantDataStore()), data_dir)
    host = os.environ.get("CLAIMS_HTTP_HOST", "127.0.0.1")
    port = int(os.environ.get("CLAIMS_HTTP_PORT", "8080"))
    make_server(router, host, port).serve_forever()


if __name__ == "__main__":  # pragma: no cover
    serve()
