p = "verificador/_gen_escenarios.py"
t = open(p, encoding="utf-8").read()
t = t.replace('''    r = {"estado": estado, "motivo": motivo, "base": base, "deducible": ded, "cubierto": cub,
         "retencion": ret, "neto": neto, "observaciones": obs, "fecha_liquidacion": fecha,
         "reclamado": rec}''', '''    r = {"estado": estado, "motivo": motivo, "base": base, "deducible": ded, "cubierto": cub,
         "retencion": ret, "neto": neto, "observaciones": obs, "fecha_liquidacion": fecha,
         "reclamado": "%.2f" % float(rec) if False else _dos(rec)}''')
t = t.replace('''def liq(estado,''', '''def _dos(x):
    """Formato NUMBER(14,2): el importe reclamado se declara con 2 decimales (solo formato)."""
    ent, _, dec = str(x).partition(".")
    return ent + "." + (dec + "00")[:2]


def liq(estado,''', 1)
open(p, "w", encoding="utf-8").write(t)
print("ok")
