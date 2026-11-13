"""Auxiliar: ejecuta el harness y lista diferencias entre esperado (a mano) y obtenido."""
import json
import os
import subprocess
import sys

proy = "verificador/zip/modern_loan"
esc = json.load(open(f"{proy}/escenarios_equivalencia.json", encoding="utf-8"))["escenarios"]
subprocess.run([sys.executable, f"{proy}/harness_equivalencia.py", f"{proy}/escenarios_equivalencia.json",
                "verificador/salida_tmp.json"], env=dict(os.environ, PYTHONPATH=f"{proy}/src"), check=True)
obt = json.load(open("verificador/salida_tmp.json", encoding="utf-8"))
n = 0
for e in esc:
    o = obt[e["id"]]
    if o != e["esperado"]:
        n += 1
        print("DIF", e["id"], e["regla"], e["descripcion"])
        if isinstance(o, dict) and isinstance(e["esperado"], dict):
            for k in sorted(set(o) | set(e["esperado"])):
                if o.get(k) != e["esperado"].get(k):
                    print("    ", k, "esperado=", e["esperado"].get(k), "obtenido=", o.get(k))
        else:
            print("    ", o)
print("diferencias:", n, "de", len(esc))
