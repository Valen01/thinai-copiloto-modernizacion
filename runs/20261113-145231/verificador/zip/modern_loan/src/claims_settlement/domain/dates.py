"""Utilidades de fecha. Las columnas DATE admiten hora (ver R-006)."""
from datetime import date, datetime, timedelta

from claims_settlement.domain.errors import InvalidValueError


def as_datetime(value: object, field: str = "fecha") -> datetime:
    """Normaliza date/datetime a datetime sin zona (date -> medianoche)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    raise InvalidValueError(field, "no es una fecha")


def trunc(value: datetime) -> date:
    """Equivalente a TRUNC(fecha) de Oracle."""
    return value.date()


def day_diff(later: datetime, earlier: datetime) -> int:
    """TRUNC(later) - TRUNC(earlier) en dias calendario."""
    return (trunc(later) - trunc(earlier)).days


def minus_days(value: datetime, days: int) -> datetime:
    return value - timedelta(days=days)
