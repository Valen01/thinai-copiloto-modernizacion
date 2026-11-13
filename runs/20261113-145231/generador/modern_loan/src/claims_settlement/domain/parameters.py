"""Parametros de negocio por tenant (equivalente a LS_PARAMETROS)."""
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping, Optional

from claims_settlement.domain.errors import ParameterNotDefinedError, ParameterNullError

MAX_REPORT_DAYS = "DIAS_MAX_DENUNCIA"
MAX_REPORT_DAYS_LIFE = "DIAS_MAX_DENUNCIA_VIDA"
MINIMUM_DEDUCTIBLE = "DEDUCIBLE_MINIMO"
VIP_DEDUCTIBLE_DISCOUNT_PCT = "PCT_DESCUENTO_DED_VIP"
VIP_ARREARS_TOLERANCE = "TOLERANCIA_MORA_VIP"
MAX_CLAIMS_PER_YEAR = "MAX_SINIESTROS_ANUAL"
CLAIMS_PENALTY_PCT = "PCT_PENALIZACION_SINIEST"
WITHHOLDING_THRESHOLD = "UMBRAL_RETENCION"
WITHHOLDING_RATE = "TASA_RETENCION"
AUTO_APPROVAL_LIMIT = "TOPE_AUTO_APROBACION"
FRAUD_ALERT_DAYS = "DIAS_ALERTA_FRAUDE"
FRAUD_ALERT_PCT = "PCT_ALERTA_FRAUDE"
INFLATION_FACTOR = "FACTOR_INFLACION"


@dataclass(frozen=True, eq=False)
class BusinessParameters:
    """Parametros inmutables de un tenant; se consultan al usarse (lectura perezosa)."""

    values: Mapping[str, Optional[Decimal]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def num(self, code: str) -> Optional[Decimal]:
        """Devuelve el valor numerico; NULL se devuelve como None sin error."""
        # REGLA: R-003 (ORA-20010 si el parametro no existe; NULL se devuelve tal cual)
        if code not in self.values:
            raise ParameterNotDefinedError(code)
        return self.values[code]

    def require(self, code: str) -> Decimal:
        """Como num(), pero un NULL usado en un calculo es un error explicito."""
        # REGLA: R-003 (decision por defecto: NULL usado en calculo no se propaga en silencio)
        value = self.num(code)
        if value is None:
            raise ParameterNullError(code)
        return value
