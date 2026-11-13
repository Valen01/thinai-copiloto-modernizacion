"""Errores de dominio. Los mensajes enmascaran identificadores (mask_*)."""
from claims_settlement.shared.masking import mask_id


class DomainError(Exception):
    """Error base; el codigo simbolico conserva el del legacy cuando existe."""

    code = "DOMAIN"

    def __init__(self, detail: str) -> None:
        super().__init__(f"{self.code}: {detail}")


class ClaimNotRegisteredError(DomainError):
    """ORA-20001: el siniestro no esta en estado REGISTRADO."""

    code = "ORA-20001"

    def __init__(self, claim_id: object, status: object) -> None:
        super().__init__(
            f"El siniestro {mask_id(claim_id)} no esta en estado REGISTRADO ({status})")


class ParameterNotDefinedError(DomainError):
    """ORA-20010: parametro de negocio inexistente."""

    code = "ORA-20010"

    def __init__(self, parameter: str) -> None:
        super().__init__(f"Parametro no definido: {parameter}")


class ParameterNullError(DomainError):
    """Parametro definido con valor NULL usado en un calculo (decision por defecto)."""

    code = "PARAM-NULL"

    def __init__(self, parameter: str) -> None:
        super().__init__(f"Parametro sin valor numerico: {parameter}")


class EntityNotFoundError(DomainError):
    """NO_DATA_FOUND: siniestro, poliza o cliente inexistente."""

    code = "NO_DATA_FOUND"

    def __init__(self, entity: str, key: object) -> None:
        super().__init__(f"{entity} {mask_id(key)} no existe")


class UnknownSettlementStatusError(DomainError):
    """Estado de liquidacion fuera de los tres conocidos (mejora R-036)."""

    code = "LIQ-STATUS"

    def __init__(self, status: object) -> None:
        super().__init__(f"Estado de liquidacion desconocido: {status}")


class InvalidValueError(DomainError):
    """Valor fuera del dominio permitido (CHECK de la base, tipos)."""

    code = "INVALID_VALUE"

    def __init__(self, field: str, detail: str = "valor no permitido") -> None:
        super().__init__(f"{field}: {detail}")


class ObservationsOverflowError(DomainError):
    """Las observaciones exceden la columna VARCHAR2(400)."""

    code = "OBS-OVERFLOW"

    def __init__(self, length: int) -> None:
        super().__init__(f"Observaciones de {length} caracteres exceden 400")


class StorageConflictError(DomainError):
    """Conflicto de clave unica al persistir."""

    code = "STORAGE-CONFLICT"

    def __init__(self, entity: str, key: object) -> None:
        super().__init__(f"Clave duplicada en {entity}: {mask_id(key)}")


class TenantNotFoundError(DomainError):
    """El tenant no tiene datos ni configuracion."""

    code = "TENANT-NOT-FOUND"

    def __init__(self, tenant_id: str) -> None:
        super().__init__(f"Tenant desconocido: {tenant_id}")
