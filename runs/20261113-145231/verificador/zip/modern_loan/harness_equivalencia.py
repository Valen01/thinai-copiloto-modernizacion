"""Harness de equivalencia: ejecuta el codigo NUEVO con la `entrada` de cada escenario.

Uso (con PYTHONPATH=src):
    python harness_equivalencia.py escenarios_equivalencia.json salida.json

Escribe {id_escenario: obtenido}. No lee ni recalcula el `esperado`.

Formato de `entrada`:
  modo: "liquidar" (un siniestro, pr_liquidar_siniestro) | "lote" (pr_procesar_lote)
  parametros: {COD: numero|null}   (omitir un codigo = parametro inexistente)
  clientes:   [{id, nombre, categoria}]
  polizas:    [{id, numero, cliente_id, ramo, inicio, fin, estado, suma_asegurada,
                deducible_tipo, deducible_valor, prima_pendiente}]
  coberturas: [{poliza_id, cod, limite, porcentaje, carencia}]
  siniestros: [{id, poliza_id, cobertura, ocurrencia, denuncia, monto, estado}]
  liquidaciones_previas: [{siniestro_id, estado, cubierto, neto, motivo}]
  siniestro_id (modo liquidar) y fecha_proceso.
Fechas: "YYYY-MM-DD" o "YYYY-MM-DD HH:MM:SS". Importes: texto decimal.
"""
import json
import sys
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from claims_settlement.adapters.outbound.memory_store import TenantData, TenantDataStore
from claims_settlement.bootstrap import build_application
from claims_settlement.domain.model import (
    Claim, Coverage, Customer, Policy, Settlement)
from claims_settlement.domain.parameters import BusinessParameters

TENANT = "VERIF"


def _dt(text):
    fmt = "%Y-%m-%d %H:%M:%S" if " " in text else "%Y-%m-%d"
    return datetime.strptime(text, fmt)


def _dec(value):
    return Decimal(str(value))


def _build(entrada):
    params = {k: (None if v is None else _dec(v)) for k, v in entrada.get("parametros", {}).items()}
    data = TenantData(BusinessParameters(params))
    for c in entrada.get("clientes", []):
        data.customers[c["id"]] = Customer(c["id"], c.get("nombre", "NN"), c["categoria"])
    for p in entrada.get("polizas", []):
        data.policies[p["id"]] = Policy(
            p["id"], p.get("numero", f"P-{p['id']}"), p["cliente_id"], p["ramo"],
            _dt(p["inicio"]), _dt(p["fin"]), p["estado"], _dec(p["suma_asegurada"]),
            p["deducible_tipo"], _dec(p.get("deducible_valor", 0)),
            _dec(p.get("prima_pendiente", 0)))
    for c in entrada.get("coberturas", []):
        data.coverages[(c["poliza_id"], c["cod"])] = Coverage(
            c["poliza_id"], c["cod"], _dec(c["limite"]), _dec(c["porcentaje"]),
            int(c.get("carencia", 0)))
    for s in entrada.get("siniestros", []):
        data.claims[s["id"]] = Claim(
            s["id"], s["poliza_id"], s["cobertura"], _dt(s["ocurrencia"]), _dt(s["denuncia"]),
            _dec(s["monto"]), s.get("estado", "REGISTRADO"))
    for i, l in enumerate(entrada.get("liquidaciones_previas", []), start=9000):
        data.settlements.append(Settlement(
            i, l["siniestro_id"], _dt("2025-12-31"), _dec(l.get("cubierto", 0)),
            _dec(l.get("cubierto", 0)), _dec(0), _dec(l.get("cubierto", 0)), _dec(0),
            _dec(l.get("neto", l.get("cubierto", 0))), l["estado"],
            l.get("motivo", "LIQUIDACION_AUTOMATICA"), None, "HIST"))
    data.next_settlement_id = 1
    store = TenantDataStore()
    store.register(TENANT, data)
    return build_application(store), data


def _num(x):
    """Importe como NUMBER(x,2) de Oracle: texto con exactamente 2 decimales (mitad arriba)."""
    return format(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def _liq(s):
    return {
        "estado": s.status, "motivo": s.reason, "base": _num(s.base_amount),
        "deducible": _num(s.deductible), "cubierto": _num(s.covered),
        "retencion": _num(s.withholding), "neto": _num(s.net),
        "observaciones": s.observations, "fecha_liquidacion": s.settlement_date.strftime("%Y-%m-%d"),
        "reclamado": _num(s.claimed_amount),
    }


def _run(entrada):
    app, data = _build(entrada)
    modo = entrada.get("modo", "liquidar")
    fecha = _dt(entrada["fecha_proceso"])
    if modo == "liquidar":
        sid = entrada["siniestro_id"]
        try:
            res = app.settle_one.execute(TENANT, sid, fecha)
        except Exception as exc:  # noqa: BLE001
            return {"error": getattr(exc, "code", type(exc).__name__),
                    "liquidaciones_nuevas": len(data.settlements) - len(entrada.get("liquidaciones_previas", [])),
                    "estado_siniestro": data.claims[sid].status.value if sid in data.claims else None}
        out = _liq(res)
        out["estado_siniestro"] = data.claims[sid].status.value
        return out
    summary = app.batch.execute(TENANT, fecha)
    previas = len(entrada.get("liquidaciones_previas", []))
    nuevas = data.settlements[previas:]
    orden = [s.claim_id for s in nuevas]
    return {
        "resumen": {"procesados": summary.processed, "liquidados": summary.settled,
                    "rechazados": summary.rejected, "pendientes": summary.pending,
                    "errores": summary.errors, "total_neto_aprobado": _num(summary.total_net_approved)},
        "orden_liquidaciones": orden,
        "estados_siniestros": {str(k): v.status.value for k, v in sorted(data.claims.items())},
        "liquidaciones": {str(s.claim_id): _liq(s) for s in nuevas},
        "commits": data.commits,
        "log_niveles": [e.level for e in app.audit.entries(TENANT)],
    }


def main(argv):
    esc_path, out_path = argv[1], argv[2]
    escenarios = json.load(open(esc_path, encoding="utf-8"))["escenarios"]
    salida = {}
    for e in escenarios:
        try:
            salida[e["id"]] = _run(e["entrada"])
        except Exception as exc:  # noqa: BLE001
            salida[e["id"]] = {"error_harness": f"{type(exc).__name__}: {exc}"}
    json.dump(salida, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
