"""Entidades y objetos de valor inmutables (Claim, Policy, Coverage, Settlement...)."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from claims_settlement.domain.dates import as_datetime
from claims_settlement.domain.enums import (
    Branch, ClaimStatus, CustomerCategory, DeductibleType, PolicyStatus)
from claims_settlement.domain.money import ZERO, to_decimal


def _set(obj: object, name: str, value: object) -> None:
    object.__setattr__(obj, name, value)


@dataclass(frozen=True)
class Customer:
    """Cliente (asegurado). Solo se conserva lo que usan las reglas."""

    customer_id: int
    name: str
    category: CustomerCategory

    def __post_init__(self) -> None:
        _set(self, "category", CustomerCategory.parse(self.category, "categoria"))


@dataclass(frozen=True)
class Policy:
    """Poliza (contrato de seguro)."""

    policy_id: int
    policy_number: str
    customer_id: int
    branch: Branch
    start_date: datetime
    end_date: datetime
    status: PolicyStatus
    sum_insured: Decimal
    deductible_type: DeductibleType
    deductible_value: Decimal = ZERO
    pending_premium: Decimal = ZERO

    def __post_init__(self) -> None:
        _set(self, "branch", Branch.parse(self.branch, "ramo"))
        _set(self, "status", PolicyStatus.parse(self.status, "estado_poliza"))
        _set(self, "deductible_type",
             DeductibleType.parse(self.deductible_type, "deducible_tipo"))
        _set(self, "start_date", as_datetime(self.start_date, "fecha_inicio"))
        _set(self, "end_date", as_datetime(self.end_date, "fecha_fin"))
        for name in ("sum_insured", "deductible_value", "pending_premium"):
            _set(self, name, to_decimal(getattr(self, name), name))


@dataclass(frozen=True)
class Coverage:
    """Cobertura contratada (limite, porcentaje y carencia)."""

    policy_id: int
    code: str
    limit: Decimal
    coverage_pct: Decimal
    waiting_days: int = 0

    def __post_init__(self) -> None:
        _set(self, "limit", to_decimal(self.limit, "limite_cobertura"))
        _set(self, "coverage_pct", to_decimal(self.coverage_pct, "porcentaje_cobertura"))


@dataclass(frozen=True)
class Claim:
    """Siniestro reclamado."""

    claim_id: int
    policy_id: int
    coverage_code: str
    occurrence_date: datetime
    report_date: datetime
    claimed_amount: Decimal
    status: ClaimStatus = ClaimStatus.REGISTERED

    def __post_init__(self) -> None:
        _set(self, "status", ClaimStatus.parse(self.status, "estado_siniestro"))
        _set(self, "occurrence_date", as_datetime(self.occurrence_date, "fecha_ocurrencia"))
        _set(self, "report_date", as_datetime(self.report_date, "fecha_denuncia"))
        _set(self, "claimed_amount", to_decimal(self.claimed_amount, "monto_reclamado"))


@dataclass(frozen=True)
class Settlement:
    """Liquidacion registrada. El estado es texto para poder validar R-036."""

    settlement_id: Optional[int]
    claim_id: int
    settlement_date: datetime
    claimed_amount: Decimal
    base_amount: Decimal
    deductible: Decimal
    covered: Decimal
    withholding: Decimal
    net: Decimal
    status: str
    reason: str
    observations: Optional[str]
    process_user: str


@dataclass(frozen=True)
class Amounts:
    """Importes calculados de una liquidacion."""

    base: Decimal = ZERO
    deductible: Decimal = ZERO
    covered: Decimal = ZERO
    withholding: Decimal = ZERO
    net: Decimal = ZERO
