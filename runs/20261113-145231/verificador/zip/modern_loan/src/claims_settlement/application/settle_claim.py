"""Caso de uso: liquidar un siniestro (equivale a pr_liquidar_siniestro)."""
from datetime import datetime
from typing import Optional

from claims_settlement.application.ports import (
    AuditLog, ClaimRepository, ParameterRepository, PolicyRepository,
    ProcessUserProvider, SettlementRepository)
from claims_settlement.domain import calculation as calc
from claims_settlement.domain import outcome
from claims_settlement.domain import parameters as P
from claims_settlement.domain.dates import as_datetime, minus_days
from claims_settlement.domain.eligibility import (
    EligibilityContext, days_since_start, evaluate_eligibility)
from claims_settlement.domain.enums import ClaimStatus, Reason, SettlementStatus
from claims_settlement.domain.errors import ClaimNotRegisteredError
from claims_settlement.domain.model import Amounts, Claim, Settlement
from claims_settlement.domain.money import ZERO
from claims_settlement.domain.observations import Observations

SINISTER_WINDOW_DAYS = 365  # REGLA: R-018 (ventana de 365 dias previos a la ocurrencia)


def ensure_registered(claim: Claim) -> None:
    """Solo se liquida un siniestro REGISTRADO."""
    # REGLA: R-001 (estado distinto de REGISTRADO => ORA-20001 y no se escribe nada)
    if claim.status != ClaimStatus.REGISTERED:
        raise ClaimNotRegisteredError(claim.claim_id, claim.status.value)


class SettleClaim:
    """Orquesta validaciones, calculo y registro del resultado de un siniestro."""

    def __init__(self, claims: ClaimRepository, policies: PolicyRepository,
                 settlements: SettlementRepository, parameters: ParameterRepository,
                 audit: AuditLog, users: ProcessUserProvider,
                 debug_trace: bool = False) -> None:
        self._claims = claims
        self._policies = policies
        self._settlements = settlements
        self._parameters = parameters
        self._audit = audit
        self._users = users
        self._debug_trace = debug_trace  # REGLA: R-041 (apagado por defecto)

    def execute(self, tenant_id: str, claim_id: int, process_date: datetime) -> Settlement:
        """Liquida un siniestro; NO hace commit (lo controla el llamador)."""
        # REGLA: R-027 (solo INSERT de liquidacion y UPDATE de estado; sin COMMIT propio)
        # REGLA: R-032 (process_date solo fija fecha_liquidacion; no entra en validaciones)
        process_date = as_datetime(process_date, "fecha_proceso")
        ctx = self._load_context(tenant_id, claim_id)
        verdict = evaluate_eligibility(ctx)
        if verdict.reason is not None:
            return self._reject(tenant_id, ctx.claim, process_date, verdict.reason, None)
        obs = Observations().extend(verdict.marks)
        return self._calculate(tenant_id, ctx, process_date, obs)

    def _load_context(self, tenant_id: str, claim_id: int) -> EligibilityContext:
        # REGLA: R-002 (siniestro, poliza o cliente inexistentes propagan NO_DATA_FOUND)
        claim = self._claims.get_claim_for_update(tenant_id, claim_id)
        ensure_registered(claim)
        policy = self._policies.get_policy(tenant_id, claim.policy_id)
        customer = self._policies.get_customer(tenant_id, policy.customer_id)
        params = self._parameters.load(tenant_id)
        # REGLA: R-044 (lee FACTOR_INFLACION sin usarlo: si falta, todo siniestro falla)
        params.num(P.INFLATION_FACTOR)
        if self._debug_trace:
            self._audit.record(tenant_id, "DEBUG", claim.claim_id,
                               outcome.build_debug_trace(claim, policy, customer))
        coverage = self._policies.find_coverage(
            tenant_id, policy.policy_id, claim.coverage_code)
        return EligibilityContext(claim, policy, customer, coverage, params)

    def _calculate(self, tenant_id: str, ctx: EligibilityContext,
                   process_date: datetime, obs: Observations) -> Settlement:
        # REGLA: R-021 (orden: base, deducible, cubierto, penalizacion, tope, retencion, estado)
        claim, policy, cov, params = ctx.claim, ctx.policy, ctx.coverage, ctx.params
        base, obs = calc.compute_base_amount(claim.claimed_amount, cov.limit, obs)
        deductible, obs = calc.compute_deductible(policy, ctx.customer, base, params, obs)
        covered = calc.compute_covered(base, deductible, cov.coverage_pct)
        if covered <= 0:
            return self._reject(tenant_id, claim, process_date, Reason.BELOW_DEDUCTIBLE, obs)
        covered, obs = self._penalize(tenant_id, ctx, covered, obs)
        remaining = self._remaining(tenant_id, ctx)
        if remaining <= 0:
            return self._reject(
                tenant_id, claim, process_date, Reason.SUM_INSURED_EXHAUSTED, obs)
        covered, obs = calc.apply_sum_insured_cap(covered, remaining, obs)
        withholding, obs = calc.compute_withholding(policy.branch, covered, params, obs)
        amounts = Amounts(base, deductible, covered, withholding,
                          calc.compute_net(covered, withholding))
        status, reason = self._final_status(ctx, amounts)
        return self._register(tenant_id, claim, process_date, amounts, status.value,
                              reason.value, obs)

    def _penalize(self, tenant_id: str, ctx: EligibilityContext, covered, obs):
        claim = ctx.claim
        prior = self._claims.count_settled_in_window(
            tenant_id, claim.policy_id, claim.claim_id,
            minus_days(claim.occurrence_date, SINISTER_WINDOW_DAYS), claim.occurrence_date)
        return calc.apply_claims_penalty(covered, prior, ctx.params, obs)

    def _remaining(self, tenant_id: str, ctx: EligibilityContext):
        paid = self._settlements.total_covered_for_policy(tenant_id, ctx.policy.policy_id)
        return calc.remaining_sum_insured(ctx.policy.sum_insured, paid)

    @staticmethod
    def _final_status(ctx: EligibilityContext, amounts: Amounts):
        fraud = outcome.is_fraud_alert(
            days_since_start(ctx.claim, ctx.policy), ctx.claim.claimed_amount,
            ctx.coverage.limit, ctx.params)
        return outcome.decide_final_status(fraud, amounts.net, ctx.params)

    def _reject(self, tenant_id: str, claim: Claim, process_date: datetime,
                reason: Reason, obs: Optional[Observations]) -> Settlement:
        # REGLA: R-012 (todo rechazo guarda importes en cero, RECHAZADA y el motivo)
        return self._register(tenant_id, claim, process_date, Amounts(),
                              SettlementStatus.REJECTED.value, reason.value, obs)

    def _register(self, tenant_id: str, claim: Claim, process_date: datetime,
                  amounts: Amounts, status: str, reason: str,
                  obs: Optional[Observations]) -> Settlement:
        # REGLA: R-036 (el estado se traduce ANTES de escribir; desconocido => error)
        claim_status = outcome.claim_status_for(status)
        # REGLA: R-026 (INSERT con fecha de proceso recibida, importes, marcas y usuario)
        settlement = Settlement(
            None, claim.claim_id, process_date, claim.claimed_amount, amounts.base,
            amounts.deductible, amounts.covered, amounts.withholding, amounts.net,
            status, reason, (obs or Observations()).text, self._users.current_user(tenant_id))
        saved = self._settlements.add(tenant_id, settlement)
        # REGLA: R-025 (UPDATE del estado del siniestro segun la correspondencia)
        self._claims.update_status(tenant_id, claim.claim_id, claim_status)
        self._audit.record(tenant_id, "INFO", claim.claim_id, outcome.format_result_message(saved))
        return saved


__all__ = ["SettleClaim", "ensure_registered", "ZERO"]
