from decimal import Decimal


def cutoff(hhmm: int) -> bool:
    """REGLA: R-013 pago posterior al corte."""
    return hhmm > 2000


def fee(x: Decimal) -> Decimal:
    return x
