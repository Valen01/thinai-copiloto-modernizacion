"""Bitacora de auditoria autonoma (no participa del rollback) y usuario de proceso."""
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from claims_settlement.shared.masking import mask_id

MAX_MESSAGE = 1000  # R-033: VARCHAR2(1000)
MAX_USER = 30  # VARCHAR2(30)
USER_ENV = "CLAIMS_PROCESS_USER"
DEFAULT_USER = "BATCH"

_logger = logging.getLogger("claims_settlement.audit")


@dataclass(frozen=True)
class AuditEntry:
    log_id: int
    timestamp: datetime
    level: str
    claim_id: Optional[int]
    message: str


class InMemoryAuditLog:
    """Bitacora por tenant; el rollback del almacen no la modifica."""

    def __init__(self) -> None:
        self._entries: dict[str, list[AuditEntry]] = {}
        self._sequence = 0

    def record(self, tenant_id: str, level: str, claim_id: Optional[int], message: str) -> None:
        # REGLA: R-033 (bitacora autonoma que persiste tras rollback; mensaje a 1000 caracteres)
        self._sequence += 1
        entry = AuditEntry(self._sequence, datetime.now(), level, claim_id,
                           message[:MAX_MESSAGE])
        self._entries.setdefault(tenant_id, []).append(entry)
        shown = "-" if claim_id is None else mask_id(claim_id)
        _logger.info("audit tenant=%s level=%s ref=%s", tenant_id, level, shown)

    def entries(self, tenant_id: str) -> list[AuditEntry]:
        return list(self._entries.get(tenant_id, []))


class EnvProcessUserProvider:
    """Usuario ejecutor tomado de la variable de entorno CLAIMS_PROCESS_USER."""

    def current_user(self, tenant_id: str) -> str:
        user = os.environ.get(USER_ENV, DEFAULT_USER)
        if not user or len(user) > MAX_USER:
            raise ValueError(f"{USER_ENV} vacio o mayor de {MAX_USER} caracteres")
        return user
