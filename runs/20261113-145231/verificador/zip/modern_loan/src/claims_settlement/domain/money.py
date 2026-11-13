"""Dinero con Decimal y redondeo mitad hacia arriba."""
from decimal import ROUND_HALF_UP, Context, Decimal

from claims_settlement.domain.errors import InvalidValueError

# Contexto de alta precision (NUMBER de Oracle admite 38 digitos).
_CTX = Context(prec=38, rounding=ROUND_HALF_UP)
CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal(100)


def to_decimal(value: object, field: str = "importe") -> Decimal:
    """Convierte int/str/Decimal a Decimal; rechaza binarios de coma flotante."""
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise InvalidValueError(field, "tipo no permitido para dinero")
    try:
        result = Decimal(value)
    except ArithmeticError:
        raise InvalidValueError(field, "no es un numero") from None
    if not result.is_finite():
        raise InvalidValueError(field, "no es un numero finito")
    return result


def round2(value: Decimal) -> Decimal:
    """ROUND(valor, 2) con mitad hacia arriba (R-022)."""
    # REGLA: R-022 (cada operacion de porcentaje se redondea de inmediato a 2 decimales)
    return value.quantize(CENT, rounding=ROUND_HALF_UP, context=_CTX)


def percent_of(amount: Decimal, pct: Decimal) -> Decimal:
    """ROUND(amount * pct / 100, 2) sin redondeos intermedios."""
    # REGLA: R-022 (redondeo inmediato tras cada operacion de porcentaje)
    return round2(_CTX.divide(_CTX.multiply(amount, pct), HUNDRED))


def subtract(left: Decimal, right: Decimal) -> Decimal:
    return _CTX.subtract(left, right)


def format_amount(value: Decimal) -> str:
    """Importe sin signo con dos decimales (formato de salida)."""
    rounded = round2(value)
    if rounded < 0:
        raise InvalidValueError("importe", "negativo no representable sin signo")
    return f"{rounded:f}"
