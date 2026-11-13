"""Puertos (interfaces) de salida. Todo metodo recibe tenant_id como primer parametro."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Protocol, Sequence

from claims_settlement.domain.enums import ClaimStatus
from claims_settlement.domain.model import Claim, Coverage, Customer, Policy, Settlement
from claims_settlement.domain.parameters import BusinessParameters


class ClaimRepository(Protocol):
    def get_claim_for_update(self, tenant_id: str, claim_id: int) -> Claim:
        """Lee con bloqueo de fila; EntityNotFoundError si no existe."""

    def get_claim(self, tenant_id: str, claim_id: int) -> Claim:
        """Lee un siniestro; EntityNotFoundError si no existe."""

    def list_registered_claim_ids(self, tenant_id: str, cutoff: datetime) -> Sequence[int]:
        """Ids REGISTRADO con fecha_denuncia <= cutoff, ascendentes."""

    def update_status(self, tenant_id: str, claim_id: int, status: ClaimStatus) -> None:
        """Actualiza el estado del siniestro."""

    def count_settled_in_window(self, tenant_id: str, policy_id: int, excluding_claim_id: int,
                                window_start: datetime, window_end: datetime) -> int:
        """Siniestros LIQUIDADO de la poliza con ocurrencia en [inicio, fin)."""


class PolicyRepository(Protocol):
    def get_policy(self, tenant_id: str, policy_id: int) -> Policy:
        """EntityNotFoundError si no existe."""

    def get_customer(self, tenant_id: str, customer_id: int) -> Customer:
        """EntityNotFoundError si no existe."""

    def find_coverage(self, tenant_id: str, policy_id: int, code: str) -> Optional[Coverage]:
        """None si la cobertura no esta contratada."""


class SettlementRepository(Protocol):
    def add(self, tenant_id: str, settlement: Settlement) -> Settlement:
        """Inserta y devuelve la liquidacion con su identificador asignado."""

    def total_covered_for_policy(self, tenant_id: str, policy_id: int) -> Decimal:
        """Suma de cubierto de liquidaciones APROBADA o PENDIENTE_APROBACION."""

    def approved_net_for_claim(self, tenant_id: str, claim_id: int) -> Decimal:
        """Neto de la liquidacion APROBADA del siniestro."""

    def latest_for_claim(self, tenant_id: str, claim_id: int) -> Optional[Settlement]:
        """Ultima liquidacion del siniestro, si existe."""


class ParameterRepository(Protocol):
    def load(self, tenant_id: str) -> BusinessParameters:
        """Parametros de negocio del tenant."""


class AuditLog(Protocol):
    def record(self, tenant_id: str, level: str, claim_id: Optional[int], message: str) -> None:
        """Bitacora autonoma: no se revierte con el rollback del siniestro."""


class TransactionManager(Protocol):
    def savepoint(self, tenant_id: str) -> None:
        """Marca un punto de retorno."""

    def rollback_to_savepoint(self, tenant_id: str) -> None:
        """Deshace lo escrito desde el ultimo savepoint."""

    def commit(self, tenant_id: str) -> None:
        """Confirma la transaccion del tenant."""


class ProcessUserProvider(Protocol):
    def current_user(self, tenant_id: str) -> str:
        """Usuario ejecutor registrado en la liquidacion."""
