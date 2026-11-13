"""Pruebas de estado final, correspondencia de estados, parametros y dominios (R-003/4/23/24/25/36/41)."""
import pytest
from factories import D, claim, customer, params, policy

from claims_settlement.domain.enums import (
    Branch, ClaimStatus, CustomerCategory, DeductibleType, PolicyStatus, Reason,
    SettlementStatus)
from claims_settlement.domain.errors import (
    InvalidValueError, ParameterNotDefinedError, ParameterNullError,
    UnknownSettlementStatusError)
from claims_settlement.domain.model import Customer, Policy
from claims_settlement.domain import outcome


def test_r003_missing_parameter_raises_ora_20010():
    """REGLA: R-003 - parametro inexistente => ORA-20010 'Parametro no definido'."""
    with pytest.raises(ParameterNotDefinedError) as err:
        params(TASA_RETENCION="DROP").num("TASA_RETENCION")
    assert "ORA-20010" in str(err.value) and "TASA_RETENCION" in str(err.value)


def test_r003_null_value_is_returned_without_error():
    """REGLA: R-003 - valor NULL (VERSION_MOTOR) se devuelve tal cual, sin error."""
    assert params().num("VERSION_MOTOR") is None


def test_r003_null_used_in_calculation_is_explicit_error():
    """REGLA: R-003 - decision por defecto: un NULL usado en un calculo es error explicito."""
    with pytest.raises(ParameterNullError):
        params().require("VERSION_MOTOR")


def test_r004_value_domains_accept_valid_and_reject_others():
    """REGLA: R-004 - dominios de categoria, ramo, estados y tipo de deducible."""
    assert CustomerCategory.parse("PREFERENTE") == CustomerCategory.PREFERRED
    assert Branch.parse("SALUD") == Branch.HEALTH
    assert PolicyStatus.parse("SUSPENDIDA") == PolicyStatus.SUSPENDED
    assert DeductibleType.parse("FIJO") == DeductibleType.FIXED
    assert ClaimStatus.parse("PENDIENTE_REVISION") == ClaimStatus.PENDING_REVIEW
    assert SettlementStatus.parse("PENDIENTE_APROBACION") == SettlementStatus.PENDING_APPROVAL
    for enum, bad in ((CustomerCategory, "GOLD"), (Branch, "MOTO"), (PolicyStatus, "ANULADA"),
                      (DeductibleType, "MIXTO"), (ClaimStatus, "ABIERTO"),
                      (SettlementStatus, "OTRO")):
        with pytest.raises(InvalidValueError):
            enum.parse(bad)


def test_r004_entities_validate_on_construction():
    """REGLA: R-004 - las entidades rechazan valores fuera de los CHECK de la base."""
    with pytest.raises(InvalidValueError):
        Customer(1, "ANA TORRES", "GOLD")
    with pytest.raises(InvalidValueError):
        policy(branch="MOTO")
    assert isinstance(policy(), Policy)


@pytest.mark.parametrize("days,claimed,expected", [
    (15, "32000", True),       # ambos limites inclusive: 15 dias y umbral exacto
    (16, "32000", False),      # un dia fuera de la ventana
    (15, "31999.99", False),   # un centavo bajo el umbral 80% de 40000
    (0, "40000", True),
])
def test_r023_fraud_alert_boundaries(days, claimed, expected):
    """REGLA: R-023 - dias <= 15 y RECLAMADO >= ROUND(40000 * 80 / 100, 2) = 32000.00."""
    assert outcome.is_fraud_alert(days, D(claimed), D(40000), params()) is expected


def test_r023_threshold_uses_coverage_limit():
    """REGLA: R-023 - umbral = ROUND(limite * 80 / 100, 2); 33.33 * 0.8 = 26.664 -> 26.66."""
    assert outcome.fraud_threshold(D("33.33"), params()) == D("26.66")


@pytest.mark.parametrize("fraud,net,status,reason", [
    (True, "10", SettlementStatus.PENDING_APPROVAL, Reason.FRAUD_SUSPICION),
    (True, "99999", SettlementStatus.PENDING_APPROVAL, Reason.FRAUD_SUSPICION),  # fraude prioritario
    (False, "50000", SettlementStatus.APPROVED, Reason.AUTOMATIC_SETTLEMENT),   # igual al tope aprueba
    (False, "50000.01", SettlementStatus.PENDING_APPROVAL, Reason.EXCEEDS_AUTO_LIMIT),
])
def test_r024_final_status_priority_and_strict_cap(fraud, net, status, reason):
    """REGLA: R-024 - fraude primero; neto > 50000 (estricto) pendiente; si no, aprobada."""
    assert outcome.decide_final_status(fraud, D(net), params()) == (status, reason)


def test_r025_status_correspondence():
    """REGLA: R-025 - APROBADA->LIQUIDADO, RECHAZADA->RECHAZADO, PENDIENTE->PENDIENTE_REVISION."""
    assert outcome.claim_status_for("APROBADA") == ClaimStatus.SETTLED
    assert outcome.claim_status_for("RECHAZADA") == ClaimStatus.REJECTED
    assert outcome.claim_status_for("PENDIENTE_APROBACION") == ClaimStatus.PENDING_REVIEW


def test_r036_unknown_settlement_status_is_explicit_error():
    """REGLA: R-036 - estado desconocido: error explicito, nunca estado de siniestro nulo."""
    with pytest.raises(UnknownSettlementStatusError):
        outcome.claim_status_for("ANULADA")


def test_r041_debug_trace_masks_personal_data():
    """REGLA: R-041 - la traza usa ids enmascarados e iniciales, sin nombre completo."""
    text = outcome.build_debug_trace(claim(claim_id=1001), policy(policy_id=101),
                                     customer(name="ANA TORRES"))
    assert text == "DEBUG siniestro=**01 poliza=*01 asegurado=A. T."
    assert "TORRES" not in text and "1001" not in text
