"""Estado final de la liquidacion, correspondencia de estados y mensajes."""
from decimal import Decimal

from claims_settlement.domain import parameters as P
from claims_settlement.domain.enums import ClaimStatus, Reason, SettlementStatus
from claims_settlement.domain.errors import UnknownSettlementStatusError
from claims_settlement.domain.model import Claim, Customer, Policy, Settlement
from claims_settlement.domain.money import format_amount, percent_of
from claims_settlement.domain.parameters import BusinessParameters
from claims_settlement.shared.masking import mask_id, mask_name

# REGLA: R-025 (APROBADA->LIQUIDADO, RECHAZADA->RECHAZADO, PENDIENTE_APROBACION->PENDIENTE_REVISION)
STATUS_MAP: dict[str, ClaimStatus] = {
    SettlementStatus.APPROVED.value: ClaimStatus.SETTLED,
    SettlementStatus.REJECTED.value: ClaimStatus.REJECTED,
    SettlementStatus.PENDING_APPROVAL.value: ClaimStatus.PENDING_REVIEW,
}


def claim_status_for(settlement_status: str) -> ClaimStatus:
    """Estado del siniestro segun el de la liquidacion; desconocido => error."""
    # REGLA: R-036 (mejora PO: estado desconocido es error explicito, nunca estado nulo)
    # REGLA: R-025 (correspondencia de estados)
    try:
        return STATUS_MAP[settlement_status]
    except KeyError:
        raise UnknownSettlementStatusError(settlement_status) from None


def fraud_threshold(limit: Decimal, params: BusinessParameters) -> Decimal:
    """Umbral = ROUND(limite * PCT_ALERTA_FRAUDE / 100, 2)."""
    # REGLA: R-023 (umbral sobre el limite de la cobertura)
    return percent_of(limit, params.require(P.FRAUD_ALERT_PCT))


def is_fraud_alert(days_since_start: int, claimed: Decimal, limit: Decimal,
                   params: BusinessParameters) -> bool:
    """Alerta si dias <= DIAS_ALERTA_FRAUDE y el RECLAMADO >= umbral (ambos inclusive)."""
    # REGLA: R-023 (se compara el monto reclamado, no el base ni el cubierto)
    threshold = fraud_threshold(limit, params)
    within_days = days_since_start <= params.require(P.FRAUD_ALERT_DAYS)
    return within_days and claimed >= threshold


def decide_final_status(is_fraud: bool, net: Decimal,
                        params: BusinessParameters) -> tuple[SettlementStatus, Reason]:
    """Prioridad: fraude, luego neto > tope automatico, si no aprobada."""
    # REGLA: R-024 (fraude primero; neto > TOPE_AUTO_APROBACION estricto; neto igual aprueba)
    if is_fraud:
        return SettlementStatus.PENDING_APPROVAL, Reason.FRAUD_SUSPICION
    if net > params.require(P.AUTO_APPROVAL_LIMIT):
        return SettlementStatus.PENDING_APPROVAL, Reason.EXCEEDS_AUTO_LIMIT
    return SettlementStatus.APPROVED, Reason.AUTOMATIC_SETTLEMENT


def format_result_message(settlement: Settlement) -> str:
    """Mensaje INFO de resultado: estado / motivo / neto."""
    # REGLA: R-033 (cada registro de resultado escribe un log INFO con estado, motivo y neto)
    return (f"Resultado: {settlement.status} / {settlement.reason}"
            f" / neto={format_amount(settlement.net)}")


def build_debug_trace(claim: Claim, policy: Policy, customer: Customer) -> str:
    """Traza de depuracion sin datos personales: ids enmascarados, nombre en iniciales."""
    # REGLA: R-041 (mejora PO: la traza enmascara identificadores y reduce el nombre a iniciales)
    return (f"DEBUG siniestro={mask_id(claim.claim_id)} poliza={mask_id(policy.policy_id)}"
            f" asegurado={mask_name(customer.name)}")
