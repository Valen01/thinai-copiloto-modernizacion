"""Genera escenarios_equivalencia.json. Los `esperado` estan escritos A MANO desde el legacy
(lectura del codigo PL/SQL); este script no importa ni llama al codigo nuevo."""
import copy
import json

B = "04_pkg_liquidacion_siniestros_body.sql"

PARAMS = {
    "DIAS_MAX_DENUNCIA": 30, "DIAS_MAX_DENUNCIA_VIDA": 365, "DEDUCIBLE_MINIMO": 100,
    "PCT_DESCUENTO_DED_VIP": 50, "TOLERANCIA_MORA_VIP": 500, "MAX_SINIESTROS_ANUAL": 3,
    "PCT_PENALIZACION_SINIEST": 10, "UMBRAL_RETENCION": 10000, "TASA_RETENCION": 2,
    "TOPE_AUTO_APROBACION": 50000, "DIAS_ALERTA_FRAUDE": 15, "PCT_ALERTA_FRAUDE": 80,
    "FACTOR_INFLACION": 1.035, "TASA_IVA": 19, "VERSION_MOTOR": None,
}


def base_entry():
    return {
        "modo": "liquidar", "siniestro_id": 1, "fecha_proceso": "2026-03-31",
        "parametros": copy.deepcopy(PARAMS),
        "clientes": [{"id": 1, "nombre": "ANA TORRES", "categoria": "ESTANDAR"}],
        "polizas": [{"id": 101, "numero": "AUTO-0001", "cliente_id": 1, "ramo": "AUTO",
                     "inicio": "2025-01-01", "fin": "2026-12-31", "estado": "VIGENTE",
                     "suma_asegurada": "100000", "deducible_tipo": "FIJO",
                     "deducible_valor": "100", "prima_pendiente": "0"}],
        "coberturas": [{"poliza_id": 101, "cod": "COB", "limite": "50000", "porcentaje": "100",
                        "carencia": 0}],
        "siniestros": [{"id": 1, "poliza_id": 101, "cobertura": "COB", "ocurrencia": "2026-02-10",
                        "denuncia": "2026-02-12", "monto": "1000", "estado": "REGISTRADO"}],
        "liquidaciones_previas": [],
    }


ESC = []


def add(id_, regla, titulo, mut, esperado, cita, dif=None):
    e = base_entry()
    mut(e)
    item = {"id": id_, "regla": regla, "descripcion": titulo, "entrada": e, "esperado": esperado,
            "fuente_esperado": "lectura_codigo", "cita": cita}
    if dif:
        item["diferencia_esperada_de"] = dif
    ESC.append(item)


def pol(e, **kw):
    e["polizas"][0].update(kw)


def cob(e, **kw):
    e["coberturas"][0].update(kw)


def sin(e, **kw):
    e["siniestros"][0].update(kw)


def _dos(x):
    """Formato NUMBER(14,2): el importe reclamado se declara con 2 decimales (solo formato)."""
    ent, _, dec = str(x).partition(".")
    return ent + "." + (dec + "00")[:2]


def liq(estado, base, ded, cub, ret, neto, motivo, obs, est_sin=None, fecha="2026-03-31", rec=None):
    r = {"estado": estado, "motivo": motivo, "base": base, "deducible": ded, "cubierto": cub,
         "retencion": ret, "neto": neto, "observaciones": obs, "fecha_liquidacion": fecha,
         "reclamado": "%.2f" % float(rec) if False else _dos(rec)}
    r["estado_siniestro"] = est_sin or {"APROBADA": "LIQUIDADO", "RECHAZADA": "RECHAZADO",
                                        "PENDIENTE_APROBACION": "PENDIENTE_REVISION"}[estado]
    return r


def ok(rec, base, ded, cub, ret, neto, obs=None, motivo="LIQUIDACION_AUTOMATICA"):
    return liq("APROBADA", base, ded, cub, ret, neto, motivo, obs, rec=rec)


def rej(rec, motivo, obs=None):
    return liq("RECHAZADA", "0.00", "0.00", "0.00", "0.00", "0.00", motivo, obs, rec=rec)


def previos(*items):
    """Siniestros historicos de la poliza 101 (estado, ocurrencia)."""
    def m(e):
        for i, (est, occ) in enumerate(items, start=900):
            e["siniestros"].append({"id": i, "poliza_id": 101, "cobertura": "COB", "ocurrencia": occ,
                                    "denuncia": occ, "monto": "100", "estado": est})
    return m


# ---------------- R-001 .. R-004 errores ----------------
def m(e): sin(e, estado="LIQUIDADO")
add("E01", "R-001", "Siniestro no REGISTRADO => ORA-20001 y sin escritura", m,
    {"error": "ORA-20001", "liquidaciones_nuevas": 0, "estado_siniestro": "LIQUIDADO"}, f"{B}:367-370")


def m(e): sin(e, estado="PENDIENTE_REVISION")
add("E02", "R-001", "PENDIENTE_REVISION tampoco se reprocesa (borde)", m,
    {"error": "ORA-20001", "liquidaciones_nuevas": 0, "estado_siniestro": "PENDIENTE_REVISION"}, f"{B}:367-370")


def m(e): e.update(siniestro_id=999)
add("E03", "R-002", "Siniestro inexistente => NO_DATA_FOUND", m,
    {"error": "NO_DATA_FOUND", "liquidaciones_nuevas": 0, "estado_siniestro": None}, f"{B}:361-365")


def m(e): e["clientes"] = [{"id": 2, "nombre": "OTRO", "categoria": "ESTANDAR"}]
add("E04", "R-002", "Cliente de la poliza inexistente => NO_DATA_FOUND, sin escritura", m,
    {"error": "NO_DATA_FOUND", "liquidaciones_nuevas": 0, "estado_siniestro": "REGISTRADO"}, f"{B}:373")


def m(e): e["parametros"].pop("FACTOR_INFLACION")
add("E05", "R-003", "Parametro inexistente (FACTOR_INFLACION, leido al inicio) => ORA-20010 para todo siniestro", m,
    {"error": "ORA-20010", "liquidaciones_nuevas": 0, "estado_siniestro": "REGISTRADO"},
    f"{B}:111,375")


def m(e): e["parametros"].pop("DIAS_MAX_DENUNCIA")
add("E06", "R-003", "Parametro de uso perezoso inexistente (DIAS_MAX_DENUNCIA) => ORA-20010", m,
    {"error": "ORA-20010", "liquidaciones_nuevas": 0, "estado_siniestro": "REGISTRADO"},
    f"{B}:111,412")


# R-004 dominios: categoria PREFERENTE sin beneficio
def m(e): e["clientes"][0]["categoria"] = "PREFERENTE"
add("E07", "R-004", "PREFERENTE no recibe descuento VIP (mismo resultado que ESTANDAR)", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:201-205 (solo VIP)")


def m(e): e["clientes"][0]["categoria"] = "ESTANDAR"; pol(e, estado="VIGENTE")
add("E08", "R-004", "Feliz base: ESTANDAR, FIJO 100, sin ajustes", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:487-612")

# ---------------- R-005 poliza vigente ----------------
def m(e): pol(e, estado="CANCELADA")
add("E09", "R-005", "Poliza CANCELADA => POLIZA_NO_VIGENTE", m, rej("1000", "POLIZA_NO_VIGENTE"), f"{B}:386-389")


def m(e): pol(e, estado="SUSPENDIDA")
add("E10", "R-005", "Poliza SUSPENDIDA (borde): rechazo, el WARN posterior es inalcanzable", m,
    rej("1000", "POLIZA_NO_VIGENTE"), f"{B}:386-389,465-468")

# ---------------- R-006 vigencia ----------------
def m(e): pol(e, inicio="2025-01-01"); sin(e, ocurrencia="2025-01-01", denuncia="2025-01-03")
add("E11", "R-006", "Ocurrencia = fecha_inicio (inclusive) => se liquida", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:395")


def m(e): sin(e, ocurrencia="2024-12-31", denuncia="2025-01-02")
add("E12", "R-006", "Ocurrencia un dia antes del inicio => FUERA_DE_VIGENCIA", m,
    rej("1000", "FUERA_DE_VIGENCIA"), f"{B}:395-399")


def m(e): sin(e, ocurrencia="2026-12-31", denuncia="2026-12-31"); e["fecha_proceso"] = "2026-12-31"
add("E13", "R-006", "Ocurrencia = fecha_fin (inclusive) => se liquida", m,
    liq("APROBADA", "1000.00", "100.00", "900.00", "0.00", "900.00", "LIQUIDACION_AUTOMATICA", None,
        fecha="2026-12-31", rec="1000"), f"{B}:396,277")


def m(e): sin(e, ocurrencia="2027-01-01", denuncia="2027-01-01"); e["fecha_proceso"] = "2027-01-01"
add("E14", "R-006", "Ocurrencia un dia despues del fin => FUERA_DE_VIGENCIA", m,
    dict(rej("1000", "FUERA_DE_VIGENCIA"), fecha_liquidacion="2027-01-01"), f"{B}:396-399,277")

# ---------------- R-007 plazo denuncia ----------------
def m(e): sin(e, ocurrencia="2026-02-01", denuncia="2026-03-03")
add("E15", "R-007", "Denuncia a 30 dias exactos (limite inclusive) => se liquida", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:407,415")


def m(e): sin(e, ocurrencia="2026-02-01", denuncia="2026-03-04")
add("E16", "R-007", "Denuncia a 31 dias => DENUNCIA_EXTEMPORANEA", m,
    rej("1000", "DENUNCIA_EXTEMPORANEA"), f"{B}:415-417")


def m(e): pol(e, ramo="VIDA"); sin(e, ocurrencia="2025-03-01", denuncia="2026-03-01")
add("E17", "R-007", "VIDA: 365 dias exactos => se liquida (sin retencion por VIDA)", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:409-410,415")


def m(e): pol(e, ramo="VIDA"); sin(e, ocurrencia="2025-03-01", denuncia="2026-03-02")
add("E18", "R-007", "VIDA: 366 dias => DENUNCIA_EXTEMPORANEA", m,
    rej("1000", "DENUNCIA_EXTEMPORANEA"), f"{B}:409-417")

# ---------------- R-008 cobertura ----------------
def m(e): sin(e, cobertura="OTRA")
add("E19", "R-008", "Cobertura no contratada => COBERTURA_NO_CONTRATADA", m,
    rej("1000", "COBERTURA_NO_CONTRATADA"), f"{B}:423-433")

# ---------------- R-009 carencia ----------------
def m(e): cob(e, carencia=30); pol(e, inicio="2026-01-11"); sin(e, ocurrencia="2026-02-10", denuncia="2026-02-12")
add("E20", "R-009", "Dias desde inicio = carencia (30) => ya activa, se liquida", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:440-442")


def m(e): cob(e, carencia=30); pol(e, inicio="2026-01-12"); sin(e, ocurrencia="2026-02-10", denuncia="2026-02-12")
add("E21", "R-009", "Dias desde inicio = carencia - 1 (29) => EN_PERIODO_CARENCIA", m,
    rej("1000", "EN_PERIODO_CARENCIA"), f"{B}:440-445")

# ---------------- R-010 mora ----------------
def m(e): pol(e, prima_pendiente="100")
add("E22", "R-010", "ESTANDAR con prima pendiente > 0 => PRIMA_EN_MORA (obs NULL)", m,
    rej("1000", "PRIMA_EN_MORA", None), f"{B}:451-461")


def m(e): pol(e, prima_pendiente="500"); e["clientes"][0]["categoria"] = "VIP"
add("E23", "R-010", "VIP con deuda = 500 (tolerancia inclusive) => se liquida con marca; VIP descuenta deducible", m,
    ok("1000", "1000.00", "50.00", "950.00", "0.00", "950.00", "TOLERANCIA_MORA_VIP;DESCUENTO_VIP"),
    f"{B}:454-457,201-205")


def m(e): pol(e, prima_pendiente="500.01"); e["clientes"][0]["categoria"] = "VIP"
add("E24", "R-010", "VIP con deuda 500.01 => PRIMA_EN_MORA", m,
    rej("1000", "PRIMA_EN_MORA", None), f"{B}:455-460")

# ---------------- R-011 orden de validaciones ----------------
def m(e): pol(e, estado="CANCELADA"); sin(e, ocurrencia="2027-02-01", denuncia="2027-02-02")
add("E25", "R-011", "Poliza cancelada y fuera de vigencia => gana POLIZA_NO_VIGENTE", m,
    rej("1000", "POLIZA_NO_VIGENTE"), f"{B}:386,395")


def m(e): sin(e, ocurrencia="2026-01-01", denuncia="2026-03-01", cobertura="OTRA")
add("E26", "R-011", "Denuncia tardia y sin cobertura => gana DENUNCIA_EXTEMPORANEA", m,
    rej("1000", "DENUNCIA_EXTEMPORANEA"), f"{B}:415,431")


def m(e): sin(e, cobertura="OTRA"); pol(e, prima_pendiente="900")
add("E27", "R-011", "Sin cobertura y prima en mora => gana COBERTURA_NO_CONTRATADA", m,
    rej("1000", "COBERTURA_NO_CONTRATADA"), f"{B}:431,451")


def m(e): cob(e, carencia=500); pol(e, prima_pendiente="900")
add("E28", "R-011", "Carencia y mora => gana EN_PERIODO_CARENCIA", m,
    rej("1000", "EN_PERIODO_CARENCIA"), f"{B}:442,451")

# ---------------- R-012 rechazo en cero ----------------
def m(e): sin(e, monto="777.77"); pol(e, estado="CANCELADA")
add("E29", "R-012", "Rechazo guarda reclamado original e importes en cero", m,
    rej("777.77", "POLIZA_NO_VIGENTE"), f"{B}:303-322,273-279")

# ---------------- R-013 base ----------------
def m(e): sin(e, monto="50000"); pol(e, suma_asegurada="200000")
add("E30", "R-013", "Reclamado = limite => sin tope ni marca LIMITE_COBERTURA", m,
    ok("50000", "50000.00", "100.00", "49900.00", "998.00", "48902.00", "RETENCION_APLICADA"), f"{B}:487-492")


def m(e): sin(e, monto="50000.01"); pol(e, suma_asegurada="200000")
add("E31", "R-013", "Reclamado > limite => base = limite y marca", m,
    ok("50000.01", "50000.00", "100.00", "49900.00", "998.00", "48902.00", "LIMITE_COBERTURA;RETENCION_APLICADA"),
    f"{B}:487-489")

# ---------------- R-014 / R-015 deducible ----------------
def m(e): pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5"); sin(e, monto="4000")
add("E32", "R-014", "Deducible porcentual 5% de 4000 = 200 (sobre base)", m,
    ok("4000", "4000.00", "200.00", "3800.00", "0.00", "3800.00"), f"{B}:193")


def m(e): pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5"); cob(e, limite="2000"); sin(e, monto="9000")
add("E33", "R-014", "Porcentual se calcula sobre el MONTO BASE topado (2000), no el reclamado", m,
    ok("9000", "2000.00", "100.00", "1900.00", "0.00", "1900.00", "LIMITE_COBERTURA"), f"{B}:171,193,487-489")


def m(e): pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5"); sin(e, monto="12345.67")
add("E34", "R-014", "Redondeo 2 dec: ded ROUND(617.2835)=617.28; ret ROUND(234.5678)=234.57", m,
    ok("12345.67", "12345.67", "617.28", "11728.39", "234.57", "11493.82", "RETENCION_APLICADA"),
    f"{B}:193,503,568")


def m(e): pol(e, deducible_valor="1500"); sin(e, monto="3000")
add("E35", "R-014", "Deducible FIJO se usa tal cual, sin minimo (FIJO 1500 > minimo)", m,
    ok("3000", "3000.00", "1500.00", "1500.00", "0.00", "1500.00"), f"{B}:189-190")


def m(e): pol(e, deducible_valor="50")
add("E36", "R-015", "FIJO 50 (< minimo 100) NO aplica minimo (el minimo es solo porcentual)", m,
    ok("1000", "1000.00", "50.00", "950.00", "0.00", "950.00"), f"{B}:189-199")


def m(e): pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5")
add("E37", "R-015", "Porcentual 50 < minimo 100 => deducible 100 y marca DEDUCIBLE_MINIMO", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00", "DEDUCIBLE_MINIMO"), f"{B}:195-198")


def m(e): pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5"); sin(e, monto="2000")
add("E38", "R-015", "Porcentual = minimo exacto (100.00): no es <, sin marca", m,
    ok("2000", "2000.00", "100.00", "1900.00", "0.00", "1900.00"), f"{B}:195")

# ---------------- R-016 descuento VIP ----------------
def m(e): e["clientes"][0]["categoria"] = "VIP"
add("E39", "R-016", "VIP con FIJO 100: deducible 50 y marca DESCUENTO_VIP", m,
    ok("1000", "1000.00", "50.00", "950.00", "0.00", "950.00", "DESCUENTO_VIP"), f"{B}:201-205")


def m(e): e["clientes"][0]["categoria"] = "VIP"; pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5")
add("E40", "R-016", "VIP + minimo: 5% de 1000=50 -> minimo 100 -> descuento 50 (descuento DESPUES del minimo)", m,
    ok("1000", "1000.00", "50.00", "950.00", "0.00", "950.00", "DEDUCIBLE_MINIMO;DESCUENTO_VIP"),
    f"{B}:195-205")


def m(e): e["clientes"][0]["categoria"] = "VIP"; pol(e, deducible_valor="0")
add("E41", "R-016", "VIP con deducible 0: no hay descuento ni marca (borde > 0)", m,
    ok("1000", "1000.00", "0.00", "1000.00", "0.00", "1000.00"), f"{B}:201")

# ---------------- R-017 cubierto / BAJO_DEDUCIBLE ----------------
def m(e): pol(e, deducible_valor="1000")
add("E42", "R-017", "Cubierto = 0 (deducible = base) => BAJO_DEDUCIBLE (el cero rechaza)", m,
    rej("1000", "BAJO_DEDUCIBLE", None), f"{B}:503-508")


def m(e): pol(e, deducible_tipo="PORCENTAJE", deducible_valor="5"); sin(e, monto="50")
add("E43", "R-017", "Cubierto negativo con minimo: rechazo BAJO_DEDUCIBLE conservando marca DEDUCIBLE_MINIMO", m,
    rej("50", "BAJO_DEDUCIBLE", "DEDUCIBLE_MINIMO"), f"{B}:195-198,505-507")


def m(e): cob(e, porcentaje="80")
add("E44", "R-017", "Porcentaje de cobertura 80%: (1000-100)*80/100 = 720", m,
    ok("1000", "1000.00", "100.00", "720.00", "0.00", "720.00"), f"{B}:503")


def m(e): cob(e, porcentaje="33.33"); pol(e, deducible_valor="0"); sin(e, monto="100.05")
add("E45", "R-017", "Redondeo mitad arriba del cubierto: 100.05*33.33/100=33.348... -> 33.35", m,
    ok("100.05", "100.05", "0.00", "33.35", "0.00", "33.35"), f"{B}:503")

# ---------------- R-018 siniestralidad ----------------
def pen(estados_occ, extra=None):
    def mm(e):
        previos(*estados_occ)(e)
        if extra:
            extra(e)
    return mm


add("E46", "R-018", "3 previos LIQUIDADOS en la ventana (>= 3) => penalizacion 10%: 900*90/100=810",
    pen([("LIQUIDADO", "2025-12-01"), ("LIQUIDADO", "2025-11-01"), ("LIQUIDADO", "2025-10-01")]),
    ok("1000", "1000.00", "100.00", "810.00", "0.00", "810.00", "PENALIZACION_SINIESTRALIDAD"),
    f"{B}:521-533")
add("E47", "R-018", "2 previos (< 3) => sin penalizacion",
    pen([("LIQUIDADO", "2025-12-01"), ("LIQUIDADO", "2025-11-01")]),
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:530")
add("E48", "R-018", "Previo con ocurrencia exactamente 365 dias antes SI cuenta (limite inferior inclusive)",
    pen([("LIQUIDADO", "2025-02-10"), ("LIQUIDADO", "2025-11-01"), ("LIQUIDADO", "2025-10-01")]),
    ok("1000", "1000.00", "100.00", "810.00", "0.00", "810.00", "PENALIZACION_SINIESTRALIDAD"), f"{B}:527")
add("E49", "R-018", "Previo a 366 dias NO cuenta => solo 2 en ventana, sin penalizacion",
    pen([("LIQUIDADO", "2025-02-09"), ("LIQUIDADO", "2025-11-01"), ("LIQUIDADO", "2025-10-01")]),
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:527")
add("E50", "R-018", "Previo con la MISMA fecha de ocurrencia no cuenta (limite superior exclusivo)",
    pen([("LIQUIDADO", "2026-02-10"), ("LIQUIDADO", "2025-11-01"), ("LIQUIDADO", "2025-10-01")]),
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:528")
add("E51", "R-018", "Previo en PENDIENTE_REVISION no cuenta (solo LIQUIDADO)",
    pen([("PENDIENTE_REVISION", "2025-12-01"), ("LIQUIDADO", "2025-11-01"), ("LIQUIDADO", "2025-10-01")]),
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:526")

# ---------------- R-019 suma asegurada ----------------
def m(e):
    pol(e, suma_asegurada="1000")
    previos(("LIQUIDADO", "2025-12-01"))(e)
    e["liquidaciones_previas"] = [{"siniestro_id": 900, "estado": "APROBADA", "cubierto": "1000"}]
add("E52", "R-019", "Remanente 0 => SUMA_ASEGURADA_AGOTADA", m,
    rej("1000", "SUMA_ASEGURADA_AGOTADA", None), f"{B}:541-553")


def m(e):
    pol(e, suma_asegurada="1000")
    previos(("LIQUIDADO", "2025-12-01"))(e)
    e["liquidaciones_previas"] = [{"siniestro_id": 900, "estado": "APROBADA", "cubierto": "600"}]
add("E53", "R-019", "Cubierto 900 > remanente 400 => tope a 400 con marca", m,
    ok("1000", "1000.00", "100.00", "400.00", "0.00", "400.00", "TOPE_SUMA_ASEGURADA"), f"{B}:555-558")


def m(e):
    pol(e, suma_asegurada="1000")
    previos(("LIQUIDADO", "2025-12-01"))(e)
    e["liquidaciones_previas"] = [{"siniestro_id": 900, "estado": "APROBADA", "cubierto": "100"}]
add("E54", "R-019", "Cubierto 900 = remanente 900 => sin tope ni marca (borde >)", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:555")


def m(e):
    pol(e, suma_asegurada="1000")
    previos(("LIQUIDADO", "2025-12-01"))(e)
    e["liquidaciones_previas"] = [{"siniestro_id": 900, "estado": "RECHAZADA", "cubierto": "1000"}]
add("E55", "R-019", "Liquidacion previa RECHAZADA no consume suma asegurada", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:546")


def m(e):
    pol(e, suma_asegurada="1000")
    previos(("PENDIENTE_REVISION", "2025-12-01"))(e)
    e["liquidaciones_previas"] = [{"siniestro_id": 900, "estado": "PENDIENTE_APROBACION", "cubierto": "600"}]
add("E56", "R-019", "Liquidacion previa PENDIENTE_APROBACION SI consume suma asegurada", m,
    ok("1000", "1000.00", "100.00", "400.00", "0.00", "400.00", "TOPE_SUMA_ASEGURADA"), f"{B}:546")

# ---------------- R-020 retencion ----------------
def m(e): sin(e, monto="10100")
add("E57", "R-020", "Cubierto = 10000 exacto => sin retencion (estricto >)", m,
    ok("10100", "10100.00", "100.00", "10000.00", "0.00", "10000.00"), f"{B}:565-566")


def m(e): sin(e, monto="10100.01")
add("E58", "R-020", "Cubierto 10000.01 => retencion 2% = 200.00 sobre todo el cubierto", m,
    ok("10100.01", "10100.01", "100.00", "10000.01", "200.00", "9800.01", "RETENCION_APLICADA"),
    f"{B}:565-574")


def m(e): pol(e, ramo="VIDA"); sin(e, monto="20100", ocurrencia="2026-02-10", denuncia="2026-02-12")
add("E59", "R-020", "Ramo VIDA nunca retiene aunque supere el umbral", m,
    ok("20100", "20100.00", "100.00", "20000.00", "0.00", "20000.00"), f"{B}:565")

# ---------------- R-021 orden de calculo ----------------
def m(e):
    pol(e, suma_asegurada="20000")
    sin(e, monto="20100")
    previos(("LIQUIDADO", "2025-12-01"), ("LIQUIDADO", "2025-11-01"), ("LIQUIDADO", "2025-10-01"))(e)
    e["liquidaciones_previas"] = [{"siniestro_id": 900, "estado": "APROBADA", "cubierto": "5000"}]
add("E60", "R-021", "Orden: cubierto 20000 -> penalizacion 18000 -> tope remanente 15000 -> retencion 300 sobre 15000", m,
    ok("20100", "20100.00", "100.00", "15000.00", "300.00", "14700.00",
       "PENALIZACION_SINIESTRALIDAD;TOPE_SUMA_ASEGURADA;RETENCION_APLICADA"), f"{B}:521-574")

# ---------------- R-022 redondeo ----------------
def m(e): cob(e, porcentaje="33.33"); pol(e, deducible_valor="0"); sin(e, monto="100.05")
add("E61", "R-022", "ROUND mitad arriba tras la operacion de porcentaje (33.348 -> 33.35)", m,
    ok("100.05", "100.05", "0.00", "33.35", "0.00", "33.35"), f"{B}:503; cabecera 48-52")


def m(e):
    e["clientes"][0]["categoria"] = "VIP"
    pol(e, deducible_valor="0.01")
add("E62", "R-022", "Descuento VIP redondeado: ROUND(0.01*50/100,2)=ROUND(0.005,2)=0.01 (mitad arriba)", m,
    ok("1000", "1000.00", "0.01", "999.99", "0.00", "999.99", "DESCUENTO_VIP"), f"{B}:203")

# ---------------- R-023 fraude ----------------
def fraude(e, monto, inicio="2026-02-01", occ="2026-02-16", den="2026-02-17"):
    pol(e, inicio=inicio)
    cob(e, limite="10000")
    sin(e, monto=monto, ocurrencia=occ, denuncia=den)


def m(e): fraude(e, "8000")
add("E63", "R-023", "15 dias desde inicio y reclamado = 80% del limite => SOSPECHA_FRAUDE (importes guardados)", m,
    liq("PENDIENTE_APROBACION", "8000.00", "100.00", "7900.00", "0.00", "7900.00", "SOSPECHA_FRAUDE", None, rec="8000"),
    f"{B}:586-592")


def m(e): fraude(e, "7999.99")
add("E64", "R-023", "Reclamado 7999.99 < umbral => no hay fraude, se aprueba", m,
    ok("7999.99", "7999.99", "100.00", "7899.99", "0.00", "7899.99"), f"{B}:589")


def m(e): fraude(e, "8000", occ="2026-02-17", den="2026-02-18")
add("E65", "R-023", "16 dias desde inicio (> 15) => sin alerta de fraude", m,
    ok("8000", "8000.00", "100.00", "7900.00", "0.00", "7900.00"), f"{B}:588")


def m(e): fraude(e, "20000")
add("E66", "R-023", "Fraude se mide sobre el RECLAMADO: reclamado 20000 (> limite 10000) => fraude; base topada 10000", m,
    liq("PENDIENTE_APROBACION", "10000.00", "100.00", "9900.00", "0.00", "9900.00", "SOSPECHA_FRAUDE",
        "LIMITE_COBERTURA", rec="20000"), f"{B}:487-489,589")

# ---------------- R-024 estado final ----------------
def m(e): sin(e, monto="51120.41"); cob(e, limite="100000"); pol(e, suma_asegurada="200000")
add("E67", "R-024", "Neto = tope 50000.00 => se aprueba (estricto >)", m,
    ok("51120.41", "51120.41", "100.00", "51020.41", "1020.41", "50000.00", "RETENCION_APLICADA"), f"{B}:593")


def m(e): sin(e, monto="51120.42"); cob(e, limite="100000"); pol(e, suma_asegurada="200000")
add("E68", "R-024", "Neto 50000.01 => PENDIENTE_APROBACION / SUPERA_TOPE_AUTOMATICO", m,
    liq("PENDIENTE_APROBACION", "51120.42", "100.00", "51020.42", "1020.41", "50000.01",
        "SUPERA_TOPE_AUTOMATICO", "RETENCION_APLICADA", rec="51120.42"), f"{B}:593-595")


def m(e): fraude(e, "90000"); cob(e, limite="100000"); pol(e, suma_asegurada="200000")
add("E69", "R-024", "Fraude y neto > tope: prioridad del fraude (SOSPECHA_FRAUDE)", m,
    liq("PENDIENTE_APROBACION", "90000.00", "100.00", "89900.00", "1798.00", "88102.00", "SOSPECHA_FRAUDE",
        "RETENCION_APLICADA", rec="90000"), f"{B}:584,588-595")

# ---------------- R-025/026/027 efectos ----------------
def m(e): e.update(fecha_proceso="2026-03-31")
add("E70", "R-025", "APROBADA => siniestro LIQUIDADO (mapeo de estados)", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:283-287")


def m(e): e.update(fecha_proceso="2026-04-15")
add("E71", "R-026", "fecha_liquidacion = fecha de proceso recibida (no SYSDATE) y reclamado original", m,
    liq("APROBADA", "1000.00", "100.00", "900.00", "0.00", "900.00", "LIQUIDACION_AUTOMATICA", None,
        fecha="2026-04-15", rec="1000"), f"{B}:277-278")


def m(e): e.update(fecha_proceso="2030-01-01")
add("E72", "R-032", "La fecha de proceso no participa en validaciones (corte muy posterior no rechaza)", m,
    liq("APROBADA", "1000.00", "100.00", "900.00", "0.00", "900.00", "LIQUIDACION_AUTOMATICA", None,
        fecha="2030-01-01", rec="1000"), f"{B}:395-445 (no usan p_fecha_proceso)")


def m(e): e.update(fecha_proceso="2026-02-11")
add("E73", "R-032", "Fecha de proceso anterior a la denuncia en liquidacion directa: igual se liquida", m,
    liq("APROBADA", "1000.00", "100.00", "900.00", "0.00", "900.00", "LIQUIDACION_AUTOMATICA", None,
        fecha="2026-02-11", rec="1000"), f"{B}:327-617")


def m(e): pass
add("E74", "R-027", "La liquidacion solo agrega 1 fila y cambia el estado del siniestro (sin otros efectos visibles)", m,
    ok("1000", "1000.00", "100.00", "900.00", "0.00", "900.00"), f"{B}:272-291")

# ---------------- LOTE ----------------
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


def lote(e):
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

# ---------------- R-036 mejora PO (mapeo de estado; comportamiento heredado) ----------------
def m(e): pol(e, estado="CANCELADA")
add("E84", "R-036", "Mapeo RECHAZADA => RECHAZADO sigue igual (mejora PO solo agrega error ante estado desconocido)", m,
    rej("1000", "POLIZA_NO_VIGENTE"), f"{B}:283-287; reglas_limpias R-036")


def m(e): sin(e, monto="51120.42"); cob(e, limite="100000"); pol(e, suma_asegurada="200000")
add("E85", "R-036", "Mapeo PENDIENTE_APROBACION => PENDIENTE_REVISION", m,
    liq("PENDIENTE_APROBACION", "51120.42", "100.00", "51020.42", "1020.41", "50000.01",
        "SUPERA_TOPE_AUTOMATICO", "RETENCION_APLICADA", rec="51120.42"), f"{B}:283-287; reglas_limpias R-036")

json.dump({"escenarios": ESC}, open("verificador/zip/modern_loan/escenarios_equivalencia.json", "w",
                                     encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(ESC), "escenarios")
