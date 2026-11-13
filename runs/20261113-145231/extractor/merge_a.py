import json, os
base = os.path.dirname(os.path.abspath(__file__))
reglas = []
for i in range(1, 6):
    with open(os.path.join(base, "parts_a", f"p{i}.json"), encoding="utf-8") as f:
        reglas += json.load(f)

B = "04_pkg_liquidacion_siniestros_body.sql"
for r in reglas:
    # R-016: la constante c_cat_vip se declara antes (linea 62): va primero para respetar el orden
    if r["rule_id"] == "R-016":
        ev = r["evidencia"]
        k = [i for i, e in enumerate(ev) if e["fragmento"].startswith("c_cat_vip CONSTANT")][0]
        ev.insert(0, ev.pop(k))
    # R-032: la linea con ese fragmento aparece en pr_rechazar y en pr_liquidar; se cita la segunda
    if r["rule_id"] == "R-032":
        r["evidencia"][0]["ocurrencia"] = 2

tecnicos = {
    B + ":pr_enviar_notificacion": "utilidad de salida/notificacion: solo arma un texto y lo imprime; solo se invoca con modo debug desactivado (ver R-041)",
    B + ":pr_agregar_obs": "utilidad de formato del texto de observaciones (ver R-034)",
    B + ":fn_es_dia_habil": "funcion utilitaria sin llamadas (ver R-037)",
}
glosario = {
    "v_sin": "registro del siniestro que se liquida",
    "v_pol": "registro de la poliza del siniestro",
    "v_cli": "registro del cliente (asegurado) de la poliza",
    "v_cob": "cobertura contratada reclamada (limite, porcentaje, dias de carencia)",
    "v_dias_denuncia": "dias calendario entre ocurrencia y denuncia",
    "v_dias_desde_inicio": "dias entre inicio de la poliza y la ocurrencia (usado en carencia y fraude)",
    "v_monto_base": "monto reclamado topado por el limite de la cobertura",
    "v_deducible": "monto que el asegurado asume antes de la indemnizacion",
    "v_cubierto": "monto que paga la aseguradora antes de retencion",
    "v_retencion": "retencion impositiva sobre el monto cubierto",
    "v_neto": "monto cubierto menos retencion; lo que se paga",
    "v_suma_remanente": "suma asegurada menos lo cubierto en liquidaciones aprobadas o pendientes",
    "v_umbral_fraude": "porcentaje del limite de cobertura que dispara la alerta de fraude",
    "v_observaciones": "marcas de ajustes aplicados separadas por ';'",
    "c_modo_debug": "constante que apaga trazas y notificaciones",
    "DIAS_CARENCIA": "dias desde el inicio de la poliza en que la cobertura aun no esta activa",
    "PRIMA_PENDIENTE": "prima vencida y no pagada (mora) de la poliza",
}
out = {"reglas": reglas, "glosario": glosario, "tecnicos": tecnicos}
with open(os.path.join(base, "rules_a.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(len(reglas), "reglas")
