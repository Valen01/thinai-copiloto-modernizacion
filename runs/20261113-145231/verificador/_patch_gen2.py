p = "verificador/_gen_escenarios.py"
t = open(p, encoding="utf-8").read()

# --- E13/E14: fecha_liquidacion = fecha de proceso (body:277) ---
t = t.replace('''add("E13", "R-006", "Ocurrencia = fecha_fin (inclusive) => se liquida", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:396")''',
'''add("E13", "R-006", "Ocurrencia = fecha_fin (inclusive) => se liquida", m,
    liq("APROBADA", "1000.00", "100.00", "900.00", "0.00", "900.00", "LIQUIDACION_AUTOMATICA", None,
        fecha="2026-12-31", rec="1000"), f"{B}:396,277")''')
t = t.replace('''add("E14", "R-006", "Ocurrencia un dia despues del fin => FUERA_DE_VIGENCIA", m,
    rej("1000", "FUERA_DE_VIGENCIA"), f"{B}:396-399")''',
'''add("E14", "R-006", "Ocurrencia un dia despues del fin => FUERA_DE_VIGENCIA", m,
    dict(rej("1000", "FUERA_DE_VIGENCIA"), fecha_liquidacion="2027-01-01"), f"{B}:396-399,277")''')

# --- Ayudantes para esperados de lote (todo derivado del legacy) ---
t = t.replace('''# ---------------- LOTE ----------------''', '''# ---------------- LOTE ----------------
def L_ok(rec, neto="900.00", cub="900.00", ded="100.00", base="1000.00", obs=None, ret="0.00"):
    return {"estado": "APROBADA", "motivo": "LIQUIDACION_AUTOMATICA", "base": base, "deducible": ded,
            "cubierto": cub, "retencion": ret, "neto": neto, "observaciones": obs,
            "fecha_liquidacion": "2026-03-31", "reclamado": _dos(rec)}


def L_rej(rec, motivo):
    return {"estado": "RECHAZADA", "motivo": motivo, "base": "0.00", "deducible": "0.00",
            "cubierto": "0.00", "retencion": "0.00", "neto": "0.00", "observaciones": None,
            "fecha_liquidacion": "2026-03-31", "reclamado": _dos(rec)}


def L_pen(rec):
    return {"estado": "PENDIENTE_APROBACION", "motivo": "SUPERA_TOPE_AUTOMATICO", "base": "51120.42",
            "deducible": "100.00", "cubierto": "51020.42", "retencion": "1020.41", "neto": "50000.01",
            "observaciones": "RETENCION_APLICADA", "fecha_liquidacion": "2026-03-31", "reclamado": _dos(rec)}


def RES(p, l, r, pe, er, tot):
    return {"procesados": p, "liquidados": l, "rechazados": r, "pendientes": pe, "errores": er,
            "total_neto_aprobado": tot}

''')

import re
start = t.index("def lote(e):")
end = t.index("# ---------------- R-036 mejora PO")
nuevo_lote = '''def lote(e):
    e["modo"] = "lote"
    e["siniestros"] = []
    e["fecha_proceso"] = "2026-03-31"


def s_(id_, occ="2026-02-10", den="2026-02-12", monto="1000", est="REGISTRADO", cob_="COB"):
    return {"id": id_, "poliza_id": 101, "cobertura": cob_, "ocurrencia": occ, "denuncia": den,
            "monto": monto, "estado": est}


def m(e):
    lote(e)
    e["siniestros"] = [s_(3), s_(1), s_(2)]
add("E75", "R-028", "Lote procesa en orden ascendente de siniestro_id", m,
    {"resumen": RES(3, 3, 0, 0, 0, "2700.00"), "orden_liquidaciones": [1, 2, 3],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "LIQUIDADO", "3": "LIQUIDADO"},
     "liquidaciones": {"1": L_ok("1000"), "2": L_ok("1000"), "3": L_ok("1000")},
     "commits": 1, "log_niveles": ["INFO"] * 5}, f"{B}:625-630,679")


def m(e):
    lote(e)
    e["siniestros"] = [s_(1, occ="2026-03-20", den="2026-03-31"), s_(2, occ="2026-03-20", den="2026-04-01"),
                       s_(3, occ="2026-03-20", den="2026-03-30")]
add("E76", "R-028", "Corte inclusivo (denuncia = corte entra); denuncia posterior al corte no se toca", m,
    {"resumen": RES(2, 2, 0, 0, 0, "1800.00"), "orden_liquidaciones": [1, 3],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "REGISTRADO", "3": "LIQUIDADO"},
     "liquidaciones": {"1": L_ok("1000"), "3": L_ok("1000")},
     "commits": 1, "log_niveles": ["INFO"] * 4}, f"{B}:628-629")


def m(e):
    lote(e)
    e["siniestros"] = [s_(1, est="LIQUIDADO"), s_(2, est="RECHAZADO")]
add("E77", "R-028", "Lote ignora siniestros que no estan REGISTRADO", m,
    {"resumen": RES(0, 0, 0, 0, 0, "0.00"), "orden_liquidaciones": [],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "RECHAZADO"}, "liquidaciones": {},
     "commits": 1, "log_niveles": ["INFO", "INFO"]}, f"{B}:628,642,679-685")


def m3(e):
    lote(e)
    e["siniestros"] = [s_(1), s_(2, cob_="OTRA"), s_(3, monto="51120.42")]
    cob(e, limite="100000")
    pol(e, suma_asegurada="500000")


ESP3 = {"resumen": RES(3, 1, 1, 1, 0, "900.00"), "orden_liquidaciones": [1, 2, 3],
        "estados_siniestros": {"1": "LIQUIDADO", "2": "RECHAZADO", "3": "PENDIENTE_REVISION"},
        "liquidaciones": {"1": L_ok("1000"), "2": L_rej("1000", "COBERTURA_NO_CONTRATADA"),
                          "3": L_pen("51120.42")},
        "commits": 1, "log_niveles": ["INFO"] * 5}
add("E78", "R-030", "Contadores: liquidado suma neto; rechazado cuenta; pendiente NO suma neto", m3,
    copy.deepcopy(ESP3), f"{B}:645-670")


def m(e):
    lote(e)
    e["siniestros"] = [s_(1), s_(2, occ="2026-02-11")]
    pol(e, suma_asegurada="1500")
add("E79", "R-019", "Lote: el liquidado antes afecta al siguiente (suma asegurada: 1500-900=600 -> 2do topado a 600)", m,
    {"resumen": RES(2, 2, 0, 0, 0, "1500.00"), "orden_liquidaciones": [1, 2],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "LIQUIDADO"},
     "liquidaciones": {"1": L_ok("1000"),
                       "2": L_ok("1000", neto="600.00", cub="600.00", obs="TOPE_SUMA_ASEGURADA")},
     "commits": 1, "log_niveles": ["INFO"] * 4}, f"{B}:541-558,645-651")


def m(e):
    lote(e)
    e["siniestros"] = [s_(1), s_(2, occ="2026-02-11"), s_(3, occ="2026-02-12"), s_(4, occ="2026-02-13")]
add("E80", "R-018", "Lote: tras 3 liquidados previos en ventana, el 4to recibe penalizacion (810)", m,
    {"resumen": RES(4, 4, 0, 0, 0, "3510.00"), "orden_liquidaciones": [1, 2, 3, 4],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "LIQUIDADO", "3": "LIQUIDADO", "4": "LIQUIDADO"},
     "liquidaciones": {"1": L_ok("1000"), "2": L_ok("1000"), "3": L_ok("1000"),
                       "4": L_ok("1000", neto="810.00", cub="810.00", obs="PENALIZACION_SINIESTRALIDAD")},
     "commits": 1, "log_niveles": ["INFO"] * 6}, f"{B}:521-533,645-651")


def m(e):
    lote(e)
    e["siniestros"] = [s_(1), s_(2), s_(3)]
    e["siniestros"][1]["poliza_id"] = 999  # poliza inexistente => NO_DATA_FOUND (error aislado)
add("E81", "R-029", "Aislamiento: un siniestro con error cuenta como error y el lote continua; sigue REGISTRADO", m,
    {"resumen": RES(3, 2, 0, 0, 1, "1800.00"), "orden_liquidaciones": [1, 3],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "REGISTRADO", "3": "LIQUIDADO"},
     "liquidaciones": {"1": L_ok("1000"), "3": L_ok("1000")},
     "commits": 1, "log_niveles": ["INFO", "INFO", "ERROR", "INFO", "INFO"]}, f"{B}:649-676")


def m(e):
    lote(e)
    e["siniestros"] = [s_(1), s_(2)]
add("E82", "R-031", "Lote: un unico COMMIT al final y bitacora INFO inicio/fin (+1 INFO por resultado)", m,
    {"resumen": RES(2, 2, 0, 0, 0, "1800.00"), "orden_liquidaciones": [1, 2],
     "estados_siniestros": {"1": "LIQUIDADO", "2": "LIQUIDADO"},
     "liquidaciones": {"1": L_ok("1000"), "2": L_ok("1000")},
     "commits": 1, "log_niveles": ["INFO", "INFO", "INFO", "INFO"]}, f"{B}:642-643,679-685,293-295")


add("E83", "R-030", "Procesados cuenta todos, incluidos rechazados y pendientes (3 de 3)", m3,
    copy.deepcopy(ESP3), f"{B}:646")

'''
t = t[:start] + nuevo_lote + t[end:]
open(p, "w", encoding="utf-8").write(t)
print("ok")
