"""Repositorios en memoria que implementan los puertos de la aplicacion."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from claims_settlement.adapters.outbound.memory_store import TenantDataStore
from claims_settlement.domain.enums import ClaimStatus, SettlementStatus
from claims_settlement.domain.errors import EntityNotFoundError, StorageConflictError
from claims_settlement.domain.model import Claim, Coverage, Customer, Policy, Settlement
from claims_settlement.domain.money import ZERO
from claims_settlement.domain.parameters import BusinessParameters

_PAID_STATES = (SettlementStatus.APPROVED.value, SettlementStatus.PENDING_APPROVAL.value)


class InMemoryClaimRepository:
    def __init__(self, store: TenantDataStore) -> None:
        self._store = store

    def get_claim_for_update(self, tenant_id: str, claim_id: int) -> Claim:
        # FOR UPDATE: el almacen en memoria es de un solo escritor (ver HTTP: lock global)
        return self.get_claim(tenant_id, claim_id)

    def get_claim(self, tenant_id: str, claim_id: int) -> Claim:
        claim = self._store.data(tenant_id).claims.get(claim_id)
        if claim is None:
            raise EntityNotFoundError("Siniestro", claim_id)
        return claim

    def list_registered_claim_ids(self, tenant_id: str, cutoff: datetime) -> Sequence[int]:
        claims = self._store.data(tenant_id).claims.values()
        return sorted(c.claim_id for c in claims
                      if c.status == ClaimStatus.REGISTERED and c.report_date <= cutoff)

    def update_status(self, tenant_id: str, claim_id: int, status: ClaimStatus) -> None:
        data = self._store.data(tenant_id)
        data.claims[claim_id] = replace(self.get_claim(tenant_id, claim_id), status=status)

    def count_settled_in_window(self, tenant_id: str, policy_id: int, excluding_claim_id: int,
                                window_start: datetime, window_end: datetime) -> int:
        claims = self._store.data(tenant_id).claims.values()
        return sum(1 for c in claims
                   if c.policy_id == policy_id and c.claim_id != excluding_claim_id
                   and c.status == ClaimStatus.SETTLED
                   and window_start <= c.occurrence_date < window_end)


class InMemoryPolicyRepository:
    def __init__(self, store: TenantDataStore) -> None:
        self._store = store

    def get_policy(self, tenant_id: str, policy_id: int) -> Policy:
        policy = self._store.data(tenant_id).policies.get(policy_id)
        if policy is None:
            raise EntityNotFoundError("Poliza", policy_id)
        return policy

    def get_customer(self, tenant_id: str, customer_id: int) -> Customer:
        customer = self._store.data(tenant_id).customers.get(customer_id)
        if customer is None:
            raise EntityNotFoundError("Cliente", customer_id)
        return customer

    def find_coverage(self, tenant_id: str, policy_id: int, code: str) -> Optional[Coverage]:
        return self._store.data(tenant_id).coverages.get((policy_id, code))


class InMemorySettlementRepository:
    def __init__(self, store: TenantDataStore) -> None:
        self._store = store

    def add(self, tenant_id: str, settlement: Settlement) -> Settlement:
        data = self._store.data(tenant_id)
        SettlementStatus.parse(settlement.status, "estado_liquidacion")  # CHECK (R-004)
        new_id = data.next_settlement_id
        data.next_settlement_id += 1  # la secuencia avanza aunque luego haya rollback
        if any(s.settlement_id == new_id for s in data.settlements):
            raise StorageConflictError("Liquidacion", new_id)
        saved = replace(settlement, settlement_id=new_id)
        data.settlements.append(saved)
        return saved

    def total_covered_for_policy(self, tenant_id: str, policy_id: int) -> Decimal:
        data = self._store.data(tenant_id)
        owned = {c.claim_id for c in data.claims.values() if c.policy_id == policy_id}
        total = ZERO
        for s in data.settlements:
            if s.claim_id in owned and s.status in _PAID_STATES:
                total += s.covered
        return total

    def approved_net_for_claim(self, tenant_id: str, claim_id: int) -> Decimal:
        rows = [s for s in self._store.data(tenant_id).settlements
                if s.claim_id == claim_id and s.status == SettlementStatus.APPROVED.value]
        if not rows:
            raise EntityNotFoundError("Liquidacion", claim_id)
        return rows[0].net

    def latest_for_claim(self, tenant_id: str, claim_id: int) -> Optional[Settlement]:
        rows = [s for s in self._store.data(tenant_id).settlements if s.claim_id == claim_id]
        return rows[-1] if rows else None


class InMemoryParameterRepository:
    def __init__(self, store: TenantDataStore) -> None:
        self._store = store

    def load(self, tenant_id: str) -> BusinessParameters:
        return self._store.data(tenant_id).parameters


class InMemoryTransactionManager:
    """Savepoint y rollback sobre siniestros y liquidaciones (no sobre la secuencia)."""

    def __init__(self, store: TenantDataStore) -> None:
        self._store = store

    def savepoint(self, tenant_id: str) -> None:
        data = self._store.data(tenant_id)
        data.savepoint = (dict(data.claims), list(data.settlements))

    def rollback_to_savepoint(self, tenant_id: str) -> None:
        data = self._store.data(tenant_id)
        if data.savepoint is not None:
            data.claims, data.settlements = dict(data.savepoint[0]), list(data.savepoint[1])

    def commit(self, tenant_id: str) -> None:
        data = self._store.data(tenant_id)
        data.savepoint = None
        data.commits += 1
