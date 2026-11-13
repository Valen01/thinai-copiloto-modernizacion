#!/usr/bin/env python3
"""
Politica de aprobacion automatica (reemplaza la aprobacion humana por entrada).

Uso: python3 -I autoaprobar.py <rules_trazadas.json> <carpeta_codigo> <carpeta_salida> [--segunda otra_extraccion.json]

Se ejecuta DESPUES de trace_rules.py (que ya verifico citas, orden y ausencias).
Una regla de negocio queda 'aprobada_automatica' solo si cumple TODOS los criterios:
  C1 todas sus citas estan resueltas a lineas del codigo (verificadas)
  C2 confianza 'alta'
  C3 si la regla no dice 'Solo COBOL/PL/SQL', tiene citas en AMBOS programas
  C4 consenso: si se pasa --segunda (extraccion independiente), alguna regla de esa
     segunda extraccion cubre >=30% de las mismas lineas citadas
  C5 no declara 'no probado por ejecucion' en su descripcion
Si falla alguno -> 'requiere_revision_humana' (cola por excepcion, no detiene el flujo).
Hallazgos tecnicos (tipo 'tecnico') -> 'hallazgo_tecnico' (no se portan como regla; van a ADR).
Las reglas ya 'aprobada' por una persona no se tocan.
"""
import json, os, re, sys
from datetime import date

POLITICA = "1.0"


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def lineas_de(regla, carpeta, cache):
    """Conjunto {(archivo, linea)} de una regla; resuelve si no vienen 'lineas'."""
    out = set()
    for ev in regla.get("evidencia", []):
        if ev.get("lineas"):
            out.add((ev["archivo"], ev["lineas"][0]))
            continue
        ruta = os.path.join(carpeta, ev["archivo"])
        if ev["archivo"] not in cache:
            cache[ev["archivo"]] = open(ruta, encoding="utf-8").read().splitlines()
        f = norm(ev["fragmento"])
        hits = [i for i, l in enumerate(cache[ev["archivo"]], 1) if f in norm(l)]
        if ev.get("ocurrencia") and len(hits) >= ev["ocurrencia"]:
            hits = [hits[ev["ocurrencia"] - 1]]
        if len(hits) == 1:
            out.add((ev["archivo"], hits[0]))
    return out


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    rj, carpeta, salida = sys.argv[1:4]
    datos = json.load(open(rj, encoding="utf-8"))
    cache = {}
    segunda = None
    if "--segunda" in sys.argv:
        s = json.load(open(sys.argv[sys.argv.index("--segunda") + 1], encoding="utf-8"))
        segunda = [lineas_de(r, carpeta, cache) for r in s["reglas"]]
    hoy = date.today().isoformat()
    cuentas, cola = {}, []
    for r in datos["reglas"]:
        if r.get("estado_revision") == "aprobada":
            cuentas["aprobada (persona)"] = cuentas.get("aprobada (persona)", 0) + 1
            continue
        if r.get("tipo") == "tecnico":
            r["estado_revision"] = "hallazgo_tecnico"
            cuentas["hallazgo_tecnico"] = cuentas.get("hallazgo_tecnico", 0) + 1
            continue
        mia = lineas_de(r, carpeta, cache)
        crit = {
            "C1_citas_verificadas": bool(r.get("evidencia")) and len(mia) == len(
                {(e["archivo"], e.get("fragmento"), e.get("ocurrencia")) for e in r["evidencia"]}),
            "C2_confianza_alta": r.get("confianza") == "alta",
            "C3_ambos_programas": _ambos(r),
            "C4_consenso": None if segunda is None else any(
                mia and len(mia & o) / len(mia | o) >= 0.30 or (mia and len(mia & o) / len(mia) >= 0.5)
                for o in segunda),
            "C5_sin_pendiente_de_ejecucion": "no probado por ejecuci" not in r.get("descripcion", "").lower(),
        }
        falla = [k for k, v in crit.items() if v is False]
        r["aprobacion"] = {"modo": "automatica", "politica": POLITICA, "fecha": hoy, "criterios": crit}
        if falla:
            r["estado_revision"] = "requiere_revision_humana"
            r["aprobacion"]["motivo"] = falla
            cola.append((r["rule_id"], falla))
        else:
            r["estado_revision"] = "aprobada_automatica"
        k = r["estado_revision"]
        cuentas[k] = cuentas.get(k, 0) + 1
    datos["politica_aprobacion"] = {"version": POLITICA, "nota": (
        "Aprobacion automatica = evidencia verificada + criterios objetivos. No equivale a validacion "
        "humana ni a equivalencia funcional; esa la demuestra el Verificador con el golden master.")}
    os.makedirs(salida, exist_ok=True)
    json.dump(datos, open(os.path.join(salida, "rules_autoaprobadas.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open(os.path.join(salida, "aprobacion_automatica.md"), "w", encoding="utf-8") as f:
        f.write(f"# Aprobación automática (política {POLITICA}, {hoy})\n\n")
        for k, v in sorted(cuentas.items()):
            f.write(f"- {k}: **{v}**\n")
        f.write("\n## Cola de revisión humana por excepción\n\n")
        f.write("\n".join(f"- {i}: no cumple {', '.join(m)}" for i, m in cola) or "Ninguna.")
        f.write("\n")
    print("estados:", cuentas)
    print("cola humana (por excepcion):", [i for i, _ in cola])


def _ambos(r):
    desc = r.get("descripcion", "")
    archivos = {e["archivo"] for e in r.get("evidencia", [])}
    if desc.startswith("Solo en PL/SQL") or desc.startswith("Solo PL/SQL") or desc.startswith("Solo COBOL"):
        return True
    return len(archivos) >= 2


if __name__ == "__main__":
    main()
