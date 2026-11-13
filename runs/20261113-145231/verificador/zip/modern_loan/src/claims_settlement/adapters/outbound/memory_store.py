"""Almacen en memoria aislado por tenant (los datos de tenants nunca se mezclan)."""
from dataclasses import dataclass, field
from typing import Optional

from claims_settlement.domain.errors import TenantNotFoundError
from claims_settlement.domain.model import Claim, Coverage, Customer, Policy, Settlement
from claims_settlement.domain.parameters import BusinessParameters


@dataclass
class TenantData:
    """Datos y configuracion de un tenant."""

    parameters: BusinessParameters
    customers: dict[int, Customer] = field(default_factory=dict)
    policies: dict[int, Policy] = field(default_factory=dict)
    coverages: dict[tuple[int, str], Coverage] = field(default_factory=dict)
    claims: dict[int, Claim] = field(default_factory=dict)
    settlements: list[Settlement] = field(default_factory=list)
    next_settlement_id: int = 1  # secuencia: no se revierte con el rollback
    savepoint: Optional[tuple[dict[int, Claim], list[Settlement]]] = None
    commits: int = 0


class TenantDataStore:
    """Registro de TenantData por tenant_id."""

    def __init__(self) -> None:
        self._tenants: dict[str, TenantData] = {}

    def register(self, tenant_id: str, data: TenantData) -> None:
        self._tenants[tenant_id] = data

    def has(self, tenant_id: str) -> bool:
        return tenant_id in self._tenants

    def data(self, tenant_id: str) -> TenantData:
        try:
            return self._tenants[tenant_id]
        except KeyError:
            raise TenantNotFoundError(tenant_id) from None
