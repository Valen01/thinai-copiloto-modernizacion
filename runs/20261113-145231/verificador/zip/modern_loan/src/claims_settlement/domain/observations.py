"""Marcas de observacion concatenadas con ';' (objeto de valor inmutable)."""
from dataclasses import dataclass
from typing import Iterable, Optional

from claims_settlement.domain.enums import Mark
from claims_settlement.domain.errors import ObservationsOverflowError

SEPARATOR = ";"
MAX_LENGTH = 400


@dataclass(frozen=True)
class Observations:
    """Lista ordenada de marcas generadas durante el calculo."""

    marks: tuple[str, ...] = ()

    def add(self, mark: Mark) -> "Observations":
        """Agrega una marca al final conservando el orden de generacion."""
        # REGLA: R-034 (marcas concatenadas con ';' en el orden en que se generan)
        return Observations(self.marks + (mark.value,))

    def extend(self, marks: Iterable[Mark]) -> "Observations":
        result = self
        for mark in marks:
            result = result.add(mark)
        return result

    @property
    def text(self) -> Optional[str]:
        """Texto final; None si no hay marcas (NULL). Error si excede 400."""
        # REGLA: R-034 (si no hay marcas el texto es NULL; limite VARCHAR2(400) explicito)
        if not self.marks:
            return None
        joined = SEPARATOR.join(self.marks)
        if len(joined) > MAX_LENGTH:
            raise ObservationsOverflowError(len(joined))
        return joined
