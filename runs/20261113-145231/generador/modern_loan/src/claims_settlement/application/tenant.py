"""Validacion del identificador de tenant (seguro para rutas y logs)."""
import re

from claims_settlement.domain.errors import InvalidValueError

_TENANT_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def validate_tenant_id(tenant_id: object) -> str:
    """Devuelve el tenant_id si es valido; si no, InvalidValueError."""
    if not isinstance(tenant_id, str) or not _TENANT_RE.match(tenant_id):
        raise InvalidValueError("tenant_id", "formato no permitido")
    return tenant_id
