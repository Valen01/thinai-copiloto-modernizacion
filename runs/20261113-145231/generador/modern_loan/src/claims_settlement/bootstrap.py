"""Raiz de composicion: conecta casos de uso con adaptadores concretos."""
from dataclasses import dataclass

from claims_settlement.adapters.outbound.audit import EnvProcessUserProvider, InMemoryAuditLog
from claims_settlement.adapters.outbound.memory_repositories import (
    InMemoryClaimRepository, InMemoryParameterRepository, InMemoryPolicyRepository,
    InMemorySettlementRepository, InMemoryTransactionManager)
from claims_settlement.adapters.outbound.memory_store import TenantDataStore
from claims_settlement.application.process_batch import ProcessBatch, SettleOneClaim
from claims_settlement.application.settle_claim import SettleClaim


@dataclass
class Application:
    """Casos de uso y puertos ya cableados."""

    store: TenantDataStore
    audit: InMemoryAuditLog
    claims: InMemoryClaimRepository
    settlements: InMemorySettlementRepository
    settle_one: SettleOneClaim
    batch: ProcessBatch


def build_application(store: TenantDataStore, debug_trace: bool = False) -> Application:
    """Crea la aplicacion sobre un almacen (multitenant por tenant_id)."""
    claims = InMemoryClaimRepository(store)
    policies = InMemoryPolicyRepository(store)
    settlements = InMemorySettlementRepository(store)
    parameters = InMemoryParameterRepository(store)
    transactions = InMemoryTransactionManager(store)
    audit = InMemoryAuditLog()
    settle = SettleClaim(claims, policies, settlements, parameters, audit,
                         EnvProcessUserProvider(), debug_trace)
    return Application(
        store, audit, claims, settlements, SettleOneClaim(settle, transactions),
        ProcessBatch(settle, claims, settlements, audit, transactions))
