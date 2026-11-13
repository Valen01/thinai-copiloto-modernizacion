"""Enmascaramiento de datos sensibles para logs y mensajes de error."""

_VISIBLE = 2


def mask_id(value: object) -> str:
    """Enmascara un identificador dejando visibles solo los ultimos 2 caracteres."""
    text = str(value)
    if len(text) <= _VISIBLE:
        return "*" * len(text)
    return "*" * (len(text) - _VISIBLE) + text[-_VISIBLE:]


def mask_name(name: str) -> str:
    """Reduce un nombre a sus iniciales (p. ej. 'ANA TORRES' -> 'A. T.')."""
    parts = [p for p in str(name).split() if p]
    return " ".join(p[0].upper() + "." for p in parts)
