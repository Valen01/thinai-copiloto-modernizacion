#!/usr/bin/env python3
"""
Consolida las decisiones del Validador (PO bancario) en UN solo archivo para el Generador.

Uso: python3 -I consolidar_reglas.py <reglas_entrada.json> <decisiones.json> <reglas_limpias.json>

Reglas de gobierno (si alguna falla, sale con codigo 1):
 - exactamente una decision por regla; ninguna pregunta queda abierta
 - cada pregunta abierta del Extractor se cierra en 'preguntas_cerradas' con respuesta y base
 - no se cambian valores fijados por el negocio; solo se AGREGAN valores por defecto cuando no existen
 - cambios de comportamiento legacy solo por seguridad, integridad_datos o regulatorio, con diferencia esperada
"""
import json, os, sys
from datetime import date

DECISIONES = {"aprobada", "mejorada", "rechazada"}
CRITERIOS = {"codigo", "negocio_fijado", "practica_bancaria", "buena_practica_seguridad",
             "valor_por_defecto", "normativa_investigada"}
HALLAZGOS = {"seguridad", "integridad_datos", "regulatorio", "ambiguedad", "consistencia", "ninguno"}
IMPACTOS = {"ninguno", "cambia_comportamiento_legacy"}
BASES = {"codigo", "tal_como_se_recibio", "buena_practica_seguridad", "valor_por_defecto",
         "practica_bancaria", "normativa_investigada", "no_se_inventa"}
PERMITEN_CAMBIAR = {"seguridad", "integridad_datos", "regulatorio"}
CAMPOS = ("descripcion", "condicion", "accion", "parametros")
fallos = []


def f(rid, msg):
    fallos.append(f"{rid}: {msg}")


def preguntas(d, r):
    rid = r["rule_id"]
    abiertas = r.get("preguntas_abiertas") or []
    cerradas = d.get("preguntas_cerradas") or []
    if len(cerradas) < len(abiertas):
        f(rid, f"{len(abiertas)} pregunta(s) abierta(s) del Extractor y solo {len(cerradas)} cerrada(s)")
    for q in cerradas:
        if not q.get("pregunta") or not q.get("respuesta"):
            f(rid, "pregunta_cerrada sin 'pregunta' o 'respuesta'")
        if q.get("base") not in BASES:
            f(rid, f"pregunta_cerrada con base invalida {q.get('base')!r}")
        if q.get("base") == "normativa_investigada" and not d.get("fuentes"):
            f(rid, "pregunta cerrada por normativa_investigada sin fuentes")
    for k in ("requiere_confirmacion_humana", "preguntas_abiertas"):
        if d.get(k):
            f(rid, f"'{k}' no se permite: el Validador cierra sus propias preguntas")


def validar(d, r):
    rid = r["rule_id"]
    dec = d.get("decision")
    if dec not in DECISIONES:
        return f(rid, f"decision invalida {dec!r}")
    preguntas(d, r)
    hall = d.get("categoria_hallazgo", "ninguno")
    if hall not in HALLAZGOS:
        f(rid, f"categoria_hallazgo invalida {hall!r}")
    crit = d.get("criterio")
    if crit not in CRITERIOS:
        f(rid, f"criterio invalido {crit!r}")
    if d.get("impacto", "ninguno") not in IMPACTOS:
        f(rid, "impacto invalido")
    if dec == "aprobada":
        return
    if len(d.get("justificacion", "")) < 40:
        f(rid, "mejorada/rechazada exige justificacion (>= 40 caracteres)")
    if crit == "normativa_investigada":
        fu = d.get("fuentes") or []
        if not fu or not all(str(x.get("url", "")).startswith("https://") for x in fu):
            f(rid, "criterio normativa_investigada exige fuentes con URL https")
    if crit in ("codigo", "negocio_fijado") and dec == "mejorada" and hall not in ("ambiguedad", "consistencia"):
        f(rid, "una mejora por 'codigo/negocio_fijado' solo puede aclarar (ambiguedad/consistencia)")
    cambia = d.get("impacto") == "cambia_comportamiento_legacy"
    if cambia:
        de = d.get("diferencia_esperada") or {}
        for k in ("descripcion", "caso_legacy", "resultado_legacy", "resultado_nuevo"):
            if not de.get(k):
                f(rid, f"impacto que cambia comportamiento exige diferencia_esperada.{k}")
        if hall not in PERMITEN_CAMBIAR:
            f(rid, f"no se puede cambiar el comportamiento legacy por '{hall}' (solo {sorted(PERMITEN_CAMBIAR)})")
    if dec == "rechazada":
        if hall not in PERMITEN_CAMBIAR:
            f(rid, "solo se rechaza una regla por seguridad, integridad_datos o regulatorio")
        return
    fin = d.get("regla_final")
    if not fin:
        return f(rid, "mejorada exige regla_final")
    if all(fin.get(k) == r.get(k) for k in CAMPOS):
        f(rid, "marcada 'mejorada' pero regla_final es identica a la original")
    po, pf = r.get("parametros") or {}, fin.get("parametros") or {}
    cambiados = [k for k in po if pf.get(k) != po[k]]
    agregados = [k for k in pf if k not in po]
    if cambiados and not (cambia and hall in PERMITEN_CAMBIAR):
        f(rid, f"cambia valores fijados por el negocio {cambiados} sin ser seguridad/integridad/regulatorio con impacto declarado")
    if agregados and crit not in ("valor_por_defecto", "buena_practica_seguridad", "practica_bancaria",
                                  "normativa_investigada"):
        f(rid, f"agrega parametros {agregados} con criterio '{crit}' (usar valor_por_defecto o buena_practica_seguridad)")


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    ent, dj, out = sys.argv[1:4]
    reglas = json.load(open(ent, encoding="utf-8"))
    decs = json.load(open(dj, encoding="utf-8"))["decisiones"]
    por_id = {}
    for d in decs:
        if d.get("rule_id") in por_id:
            f(d["rule_id"], "decision duplicada")
        por_id[d.get("rule_id")] = d
    ids = {r["rule_id"] for r in reglas["reglas"]}
    for i in sorted(ids - por_id.keys()):
        f(i, "sin decision del PO")
    for i in sorted(por_id.keys() - ids):
        f(str(i), "decision para una regla que no existe")
    limpias, rech, difs, mejoras, cuenta = [], [], [], [], {}
    for r in reglas["reglas"]:
        d = por_id.get(r["rule_id"])
        if not d:
            continue
        validar(d, r)
        dec = d.get("decision")
        cuenta[dec] = cuenta.get(dec, 0) + 1
        if d.get("diferencia_esperada") and dec != "aprobada":
            difs.append({"rule_id": r["rule_id"], **d["diferencia_esperada"]})
        if dec == "rechazada":
            rech.append({"rule_id": r["rule_id"], "descripcion_original": r["descripcion"],
                         "justificacion": d.get("justificacion"), "fuentes": d.get("fuentes", [])})
            continue
        n = {k: v for k, v in r.items() if k not in ("preguntas_abiertas",)}
        if dec == "mejorada" and d.get("regla_final"):
            n["original"] = {k: r.get(k) for k in CAMPOS}
            n.update({k: d["regla_final"][k] for k in CAMPOS if k in d["regla_final"]})
            n["origen"] = "po_mejorada"
            mejoras.append({"rule_id": r["rule_id"], "hallazgo": d.get("categoria_hallazgo"),
                            "criterio": d.get("criterio"), "justificacion": d.get("justificacion"),
                            "fuentes": d.get("fuentes", [])})
        else:
            n["origen"] = "legacy"
        n["estado_revision"] = "aprobada_po"
        n["validacion_po"] = {k: d.get(k) for k in ("decision", "categoria_hallazgo", "criterio", "impacto",
                                                    "justificacion", "fuentes", "preguntas_cerradas")}
        limpias.append(n)
    paquete = {"generado_por": "validador-reglas-po", "fecha": date.today().isoformat(),
               "resumen": {**cuenta, "diferencias_esperadas": len(difs)},
               "reglas": limpias, "glosario": reglas.get("glosario", {}),
               "diferencias_esperadas": difs, "reglas_rechazadas": rech, "mejoras": mejoras}
    if not fallos:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(paquete, fh, ensure_ascii=False, indent=2)
    print("decisiones:", cuenta, "| diferencias esperadas:", len(difs))
    for x in fallos:
        print("  FALLA:", x)
    print("RESULTADO:", f"APROBADO -> {out}" if not fallos else f"RECHAZADO ({len(fallos)} fallas, no se escribio archivo)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
