"""Pruebas del calculo de indemnizacion (R-013 a R-022, R-034). Valores hechos a mano."""
from decimal import Decimal

import pytest
from factories import D, customer, params, policy

from claims_settlement.domain import calculation as calc
from claims_settlement.domain.enums import Branch, Mark
from claims_settlement.domain.errors import InvalidValueError, ObservationsOverflowError
from claims_settlement.domain.money import format_amount, percent_of, round2, to_decimal
from claims_settlement.domain.observations import Observations

EMPTY = Observations()


def test_r013_base_amount_capped_only_when_strictly_greater():
    """REGLA: R-013 - tope solo si reclamado > limite; igual no topa ni marca."""
    assert calc.compute_base_amount(D(1000), D(1000), EMPTY) == (D(1000), EMPTY)
    base, obs = calc.compute_base_amount(D("1000.01"), D(1000), EMPTY)
    assert base == D(1000) and obs.marks == ("LIMITE_COBERTURA",)


def test_r014_fixed_deductible_used_as_is_without_minimum():
    """REGLA: R-014 - FIJO se usa tal cual aun por debajo del minimo (50 < 100)."""
    pol = policy(deductible_type="FIJO", deductible_value=D(50))
    assert calc.compute_deductible(pol, customer(), D(5000), params(), EMPTY) == (D(50), EMPTY)


def test_r014_percentage_deductible_is_over_capped_base():
    """REGLA: R-014 - porcentual sobre el monto base ya topado: 10% de 50000 = 5000.00."""
    pol = policy(deductible_type="PORCENTAJE", deductible_value=D(10))
    deductible, obs = calc.compute_deductible(pol, customer(), D(50000), params(), EMPTY)
    assert deductible == D("5000.00") and obs.marks == ()


def test_r014_percentage_rounds_half_up():
    """REGLA: R-014 - 5% de 12345.67 = 617.2835 -> 617.28 (2 decimales)."""
    pol = policy(deductible_type="PORCENTAJE", deductible_value=D(5))
    assert calc.compute_deductible(pol, customer(), D("12345.67"), params(), EMPTY)[0] == D("617.28")


@pytest.mark.parametrize("base,pct,expected,marked", [
    ("5000", "1", "100.00", True),     # 1% de 5000 = 50 < 100 -> minimo
    ("10000", "1", "100.00", False),   # 100.00 no es < 100: sin minimo ni marca
    ("80", "1", "100.00", True),       # el minimo puede superar el monto base
])
def test_r015_minimum_deductible_strict(base, pct, expected, marked):
    """REGLA: R-015 - minimo 100 solo en rama porcentual, comparacion estricta <."""
    pol = policy(deductible_type="PORCENTAJE", deductible_value=Decimal(pct))
    deductible, obs = calc.compute_deductible(pol, customer(), Decimal(base), params(), EMPTY)
    assert deductible == Decimal(expected)
    assert (obs.marks == ("DEDUCIBLE_MINIMO",)) is marked


def test_r015_minimum_parameter_read_only_in_percentage_branch():
    """REGLA: R-015 - en deducible FIJO no se lee DEDUCIBLE_MINIMO (no falla si falta)."""
    pol = policy(deductible_type="FIJO", deductible_value=D(30))
    prm = params(DEDUCIBLE_MINIMO="DROP")
    assert calc.compute_deductible(pol, customer(), D(900), prm, EMPTY)[0] == D(30)


@pytest.mark.parametrize("typ,val,base,expected,marks", [
    ("FIJO", "500", "9000", "250.00", ("DESCUENTO_VIP",)),
    ("FIJO", "333.33", "9000", "166.67", ("DESCUENTO_VIP",)),      # 166.665 -> 166.67
    ("FIJO", "0", "9000", "0", ()),                                  # deducible 0: sin descuento
    ("PORCENTAJE", "5", "5000", "125.00", ("DESCUENTO_VIP",)),      # 250 -> 125
    ("PORCENTAJE", "1", "1000", "50.00", ("DEDUCIBLE_MINIMO", "DESCUENTO_VIP")),  # tras minimo
])
def test_r016_vip_discount_after_minimum(typ, val, base, expected, marks):
    """REGLA: R-016 - VIP con deducible > 0: ROUND(ded*(100-50)/100, 2) despues del minimo."""
    pol = policy(deductible_type=typ, deductible_value=Decimal(val))
    deductible, obs = calc.compute_deductible(pol, customer("VIP"), Decimal(base), params(), EMPTY)
    assert deductible == Decimal(expected) and obs.marks == marks


def test_r016_non_vip_has_no_discount():
    """REGLA: R-016 - ESTANDAR y PREFERENTE no reciben descuento (R-004)."""
    pol = policy(deductible_type="FIJO", deductible_value=D(500))
    for category in ("ESTANDAR", "PREFERENTE"):
        assert calc.compute_deductible(pol, customer(category), D(9000), params(), EMPTY)[0] == D(500)


@pytest.mark.parametrize("base,ded,pct,expected", [
    ("1000", "100", "80", "720.00"),
    ("8123.45", "200", "90", "7131.11"),   # 7923.45 * 0.9 = 7131.105 -> 7131.11
    ("1000", "1000", "100", "0.00"),        # cero: se rechazara
    ("1000", "1200", "100", "-200.00"),     # negativo: se rechazara
])
def test_r017_covered_amount(base, ded, pct, expected):
    """REGLA: R-017 - cubierto = ROUND((base - deducible) * % / 100, 2); <= 0 rechaza."""
    assert calc.compute_covered(Decimal(base), Decimal(ded), Decimal(pct)) == Decimal(expected)


@pytest.mark.parametrize("prior,covered,expected,marked", [
    (2, "1000", "1000", False),
    (3, "1000", "900.00", True),         # >= 3 inclusive
    (5, "333.33", "300.00", True),       # 299.997 -> 300.00
])
def test_r018_claims_penalty_threshold_inclusive(prior, covered, expected, marked):
    """REGLA: R-018 - cuenta >= MAX_SINIESTROS_ANUAL reduce el cubierto 10% redondeado."""
    result, obs = calc.apply_claims_penalty(Decimal(covered), prior, params(), EMPTY)
    assert result == Decimal(expected)
    assert (obs.marks == ("PENALIZACION_SINIESTRALIDAD",)) is marked


def test_r019_remaining_and_cap():
    """REGLA: R-019 - remanente = suma asegurada - pagado; tope solo si cubierto > remanente."""
    remaining = calc.remaining_sum_insured(D(100000), D(99000))
    assert remaining == D(1000)
    assert calc.apply_sum_insured_cap(D(1000), remaining, EMPTY) == (D(1000), EMPTY)
    capped, obs = calc.apply_sum_insured_cap(D("1000.01"), remaining, EMPTY)
    assert capped == D(1000) and obs.marks == ("TOPE_SUMA_ASEGURADA",)


@pytest.mark.parametrize("branch,covered,withholding,marked", [
    (Branch.AUTO, "10000", "0.00", False),         # umbral estricto
    (Branch.AUTO, "10000.01", "200.00", True),     # 2% sobre TODO el cubierto = 200.0002
    (Branch.HOME, "20000", "400.00", True),
    (Branch.LIFE, "50000", "0.00", False),         # VIDA exento
])
def test_r020_withholding(branch, covered, withholding, marked):
    """REGLA: R-020 - retencion 2% del total si ramo <> VIDA y cubierto > 10000 (estricto)."""
    amount, obs = calc.compute_withholding(branch, Decimal(covered), params(), EMPTY)
    assert amount == Decimal(withholding)
    assert (obs.marks == ("RETENCION_APLICADA",)) is marked


def test_r020_net_is_covered_minus_withholding():
    """REGLA: R-020 - neto = cubierto - retencion (20000 - 400 = 19600)."""
    assert calc.compute_net(D(20000), D("400.00")) == D("19600.00")


@pytest.mark.parametrize("amount,pct,expected", [
    ("10.10", "5", "0.51"),        # 0.505 -> mitad hacia arriba
    ("0.10", "5", "0.01"),         # 0.005 -> 0.01
    ("100", "33.333", "33.33"),
    ("1000", "0.0149", "0.15"),    # 0.149 -> 0.15
])
def test_r022_round_half_up_after_each_percentage(amount, pct, expected):
    """REGLA: R-022 - ROUND mitad hacia arriba a 2 decimales tras cada porcentaje."""
    assert percent_of(Decimal(amount), Decimal(pct)) == Decimal(expected)
    assert round2(Decimal("2.675")) == Decimal("2.68")


def test_money_rejects_binary_floats_and_negative_output():
    """REGLA: R-022 - el dinero es Decimal; no se admiten binarios ni importes negativos."""
    with pytest.raises(InvalidValueError):
        to_decimal(1.5)
    with pytest.raises(InvalidValueError):
        to_decimal("abc")
    with pytest.raises(InvalidValueError):
        to_decimal("NaN")
    with pytest.raises(InvalidValueError):
        format_amount(Decimal("-0.01"))
    assert format_amount(Decimal("5")) == "5.00"


def test_r034_observations_joined_with_semicolon_in_order():
    """REGLA: R-034 - marcas con ';' en orden de generacion; sin marcas el texto es NULL."""
    assert EMPTY.text is None
    obs = EMPTY.add(Mark.COVERAGE_LIMIT).add(Mark.VIP_DISCOUNT)
    assert obs.text == "LIMITE_COBERTURA;DESCUENTO_VIP"
    assert EMPTY.add(Mark.VIP_DISCOUNT).text == "DESCUENTO_VIP"


def test_r034_overflow_is_explicit_error():
    """REGLA: R-034 - mas de 400 caracteres es error explicito, nunca truncado silencioso."""
    obs = EMPTY.extend([Mark.CLAIMS_PENALTY] * 20)
    with pytest.raises(ObservationsOverflowError):
        obs.text
