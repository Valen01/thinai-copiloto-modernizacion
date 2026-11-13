"""Vocabulario controlado del dominio (glosario del Extractor)."""
from enum import StrEnum

from claims_settlement.domain.errors import InvalidValueError


class CodeEnum(StrEnum):
    """Enumeracion de codigos persistidos con parseo estricto."""

    @classmethod
    def parse(cls, raw: object, field: str = "codigo"):
        """Convierte un texto en miembro; rechaza valores fuera del dominio."""
        if isinstance(raw, cls):
            return raw
        try:
            return cls(raw)
        except ValueError:
            raise InvalidValueError(field) from None


# REGLA: R-004 (dominios de valores impuestos por los CHECK de la base)
class CustomerCategory(CodeEnum):
    VIP = "VIP"
    PREFERRED = "PREFERENTE"  # categoria valida sin beneficio (R-004)
    STANDARD = "ESTANDAR"


class Branch(CodeEnum):
    AUTO = "AUTO"
    HOME = "HOGAR"
    HEALTH = "SALUD"
    LIFE = "VIDA"


class PolicyStatus(CodeEnum):
    ACTIVE = "VIGENTE"
    CANCELLED = "CANCELADA"
    SUSPENDED = "SUSPENDIDA"


class DeductibleType(CodeEnum):
    FIXED = "FIJO"
    PERCENTAGE = "PORCENTAJE"


class ClaimStatus(CodeEnum):
    REGISTERED = "REGISTRADO"
    SETTLED = "LIQUIDADO"
    REJECTED = "RECHAZADO"
    PENDING_REVIEW = "PENDIENTE_REVISION"


class SettlementStatus(CodeEnum):
    APPROVED = "APROBADA"
    REJECTED = "RECHAZADA"
    PENDING_APPROVAL = "PENDIENTE_APROBACION"


class Reason(CodeEnum):
    """Codigos de motivo de LS_LIQUIDACIONES.MOTIVO."""

    AUTOMATIC_SETTLEMENT = "LIQUIDACION_AUTOMATICA"
    EXCEEDS_AUTO_LIMIT = "SUPERA_TOPE_AUTOMATICO"
    FRAUD_SUSPICION = "SOSPECHA_FRAUDE"
    POLICY_NOT_ACTIVE = "POLIZA_NO_VIGENTE"
    OUT_OF_FORCE = "FUERA_DE_VIGENCIA"
    LATE_REPORT = "DENUNCIA_EXTEMPORANEA"
    COVERAGE_NOT_CONTRACTED = "COBERTURA_NO_CONTRATADA"
    IN_WAITING_PERIOD = "EN_PERIODO_CARENCIA"
    PREMIUM_IN_ARREARS = "PRIMA_EN_MORA"
    BELOW_DEDUCTIBLE = "BAJO_DEDUCIBLE"
    SUM_INSURED_EXHAUSTED = "SUMA_ASEGURADA_AGOTADA"


class Mark(CodeEnum):
    """Marcas de observacion (R-034)."""

    VIP_ARREARS_TOLERANCE = "TOLERANCIA_MORA_VIP"
    COVERAGE_LIMIT = "LIMITE_COBERTURA"
    MINIMUM_DEDUCTIBLE = "DEDUCIBLE_MINIMO"
    VIP_DISCOUNT = "DESCUENTO_VIP"
    CLAIMS_PENALTY = "PENALIZACION_SINIESTRALIDAD"
    SUM_INSURED_CAP = "TOPE_SUMA_ASEGURADA"
    WITHHOLDING_APPLIED = "RETENCION_APLICADA"
