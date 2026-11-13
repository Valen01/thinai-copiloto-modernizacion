"""Construccion de escenarios de prueba (valores calculados a mano en cada test)."""
from datetime import datetime
from decimal import Decimal

from claims_settlement.adapters.outbound.memory_store import TenantData, TenantDataStore
from claims_settlement.bootstrap import Application, build_application
from claims_settlement.domain.model import Claim, Coverage, Customer, Policy
from claims_settlement.domain.parameters import BusinessParameters

TENANT = "T1"
D = Decimal

BASE_PARAMS = {
    "DIAS_MAX_DENUNCIA": D(30), "DIAS_MAX_DENUNCIA_VIDA": D(365),
    "DEDUCIBLE_MINIMO": D(100), "PCT_DESCUENTO_DED_VIP": D(50),
    "TOLERANCIA_MORA_VIP": D(500), "MAX_SINIESTROS_ANUAL": D(3),
    "PCT_PENALIZACION_SINIEST": D(10), "UMBRAL_RETENCION": D(10000),
    "TASA_RETENCION": D(2), "TOPE_AUTO_APROBACION": D(50000),
    "DIAS_ALERTA_FRAUDE": D(15), "PCT_ALERTA_FRAUDE": D(80),
    "FACTOR_INFLACION": D("1.035"), "VERSION_MOTOR": None,
}


def dt(text: str) -> datetime:
    fmt = "%Y-%m-%d %H:%M:%S" if " " in text else "%Y-%m-%d"
    return datetime.strptime(text, fmt)


def params(**overrides) -> BusinessParameters:
    values = dict(BASE_PARAMS)
    for key, value in overrides.items():
        if value == "DROP":
            values.pop(key)
        else:
            values[key] = value
    return BusinessParameters(values)


def customer(category="ESTANDAR", name="ANA TORRES") -> Customer:
    return Customer(1, name, category)


def policy(**kw) -> Policy:
    base = dict(policy_id=101, policy_number="AUTO-0001", customer_id=1, branch="AUTO",
                start_date=dt("2025-01-01"), end_date=dt("2026-12-31"), status="VIGENTE",
                sum_insured=D(100000), deductible_type="FIJO", deductible_value=D(100),
                pending_premium=D(0))
    base.update(kw)
    return Policy(**base)


def coverage(**kw) -> Coverage:
    base = dict(policy_id=101, code="COB", limit=D(50000), coverage_pct=D(100), waiting_days=0)
    base.update(kw)
    return Coverage(**base)


def claim(**kw) -> Claim:
    base = dict(claim_id=1, policy_id=101, coverage_code="COB",
                occurrence_date=dt("2026-02-10"), report_date=dt("2026-02-12"),
                claimed_amount=D(1000))
    base.update(kw)
    return Claim(**base)


def world(pol=None, cov=None, cust=None, claims=(), prm=None, tenant=TENANT,
          store=None) -> Application:
    """Crea una aplicacion con un tenant cargado."""
    store = store or TenantDataStore()
    data = TenantData(prm or params())
    pol = pol or policy()
    data.customers[1] = cust or customer()
    data.policies[pol.policy_id] = pol
    cov = cov if cov is not None else coverage()
    if cov != "NONE":
        data.coverages[(cov.policy_id, cov.code)] = cov
    for c in claims or (claim(),):
        data.claims[c.claim_id] = c
    store.register(tenant, data)
    return build_application(store)


def settle(app: Application, claim_id=1, date_="2026-03-31", tenant=TENANT):
    return app.settle_one.execute(tenant, claim_id, dt(date_))
