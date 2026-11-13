#!/usr/bin/env python3
"""
Validador del Extractor: trazabilidad, cobertura y reporte de revision.

Uso:  python3 trace_rules.py [rules.json] [carpeta_con_el_codigo] [salida]

1. TRAZABILIDAD  Cada evidencia trae un fragmento literal. Se busca en el
                 archivo y se asigna su numero de linea ("ocurrencia" elige
                 entre varias coincidencias). Si no existe o es ambiguo la
                 regla FALLA: asi se atrapan las alucinaciones.
2. ORDEN         Si una regla marca "evidencia_ordenada": true, las lineas
                 citadas de cada archivo deben ir en orden ascendente (sirve
                 para demostrar secuencias, como el orden de validaciones).
3. AUSENCIAS     Una regla puede declarar "ausencias": busquedas de un patron
                 en un rango del codigo con un conteo esperado (por ejemplo,
                 "no hay UPDATE en el paquete"). Asi se respaldan afirmaciones
                 negativas.
4. COBERTURA     Cada parrafo (COBOL) / funcion (PL-SQL) debe tener al menos
                 una regla, o una justificacion tecnica explicita.
5. DECISIONES    Cada IF/ELSIF/WHILE del codigo debe estar citado por alguna
                 regla; si no, se lista para revision humana.
6. REPORTE       Genera reporte_reglas.md para revision humana.

Sale con codigo 1 si algo de lo anterior falla.
"""
import json
import os
import re
import sys
from collections import Counter

TECNICOS = {
    "LNCALC01.cbl:1000-EXIT": "etiqueta de salida del parrafo, sin logica",
    "PKG_LOAN_CALC.sql:setf": "utilidad para armar el texto de flags de salida",
    "PKG_LOAN_CALC.sql:FMT": "formato del texto de salida, sin regla de negocio",
}


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def cargar(carpeta, nombre, cache):
    if nombre not in cache:
        with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
            cache[nombre] = f.read().splitlines()
    return cache[nombre]


LEG_EXT = (".cbl", ".cob", ".cobol", ".sql", ".pls", ".pks", ".pkb")


def es_cobol(nombre):
    return nombre.lower().endswith((".cbl", ".cob", ".cobol"))


def inicio_cuerpo(nombre, lineas):
    """Primera linea de logica: PROCEDURE DIVISION (COBOL) o PACKAGE BODY (PL/SQL)."""
    clave = "PROCEDURE DIVISION" if es_cobol(nombre) else "PACKAGE BODY"
    return next((i for i, ln in enumerate(lineas, 1) if clave in ln.upper()), 1)


def bloques(nombre, lineas):
    """Devuelve [(etiqueta, inicio, fin)] con numeros de linea 1-based."""
    marcas = []
    ini = inicio_cuerpo(nombre, lineas)
    if es_cobol(nombre):
        for i, ln in enumerate(lineas, 1):
            m = re.match(r"^       ([A-Z0-9][A-Z0-9-]*)\.\s*$", ln)
            if i > ini and m:
                marcas.append((m.group(1), i))
    else:
        paquete = any("PACKAGE BODY" in ln.upper() for ln in lineas)
        patron = (r"^\s{0,4}(?:FUNCTION|PROCEDURE)\s+(\w+)" if paquete else
                  r"^\s*(?:CREATE\s+(?:OR\s+REPLACE\s+)?)?(?:FUNCTION|PROCEDURE)\s+(\w+)")
        for i, ln in enumerate(lineas, 1):
            m = re.match(patron, ln, re.I)
            if i >= ini and m:
                marcas.append((m.group(1), i))
    out = []
    for k, (et, i) in enumerate(marcas):
        fin = marcas[k + 1][1] - 1 if k + 1 < len(marcas) else len(lineas)
        out.append((et, i, fin))
    return out


def archivos_legacy(carpeta, datos):
    nombres = {e["archivo"] for r in datos["reglas"] for e in r.get("evidencia", [])}
    for f in os.listdir(carpeta):
        if f.lower().endswith(LEG_EXT) and "numerad" not in f.lower():
            nombres.add(f)
    return sorted(n for n in nombres if n.lower().endswith(LEG_EXT))


def decisiones(nombre, lineas):
    """Lineas de decision (IF/ELSIF/WHILE/EVALUATE) dentro de la logica."""
    res = []
    ini = inicio_cuerpo(nombre, lineas)
    for i, ln in enumerate(lineas, 1):
        if i < ini:
            continue
        if es_cobol(nombre) and ln[6:7] == "*":
            continue
        t = ln.strip()
        if re.match(r"^(IF|ELSIF|WHILE|EVALUATE)\b", t, re.I) and not t.upper().startswith("END"):
            res.append(i)
    return res


def ubicar(lineas, frag, occ=None):
    frag = norm(frag)
    hits = [i for i, ln in enumerate(lineas, 1) if frag in norm(ln)]
    if occ and len(hits) >= occ:
        hits = [hits[occ - 1]]
    return hits


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    reglas_json = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        base, "rules.json")
    carpeta = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(base)
    salida = sys.argv[3] if len(sys.argv) > 3 else base
    datos = json.load(open(reglas_json, encoding="utf-8"))
    cache, fallos = {}, []
    citadas = {}   # archivo -> set de lineas citadas

    # ---- 1 y 2. trazabilidad y orden
    total_ev = ok_ev = 0
    for r in datos["reglas"]:
        previas = {}
        for ev in r["evidencia"]:
            total_ev += 1
            lineas = cargar(carpeta, ev["archivo"], cache)
            hits = ubicar(lineas, ev["fragmento"], ev.get("ocurrencia"))
            if len(hits) == 1:
                ev["lineas"] = [hits[0], hits[0]]
                citadas.setdefault(ev["archivo"], set()).add(hits[0])
                ok_ev += 1
                if r.get("evidencia_ordenada"):
                    ant = previas.get(ev["archivo"], 0)
                    if hits[0] <= ant:
                        fallos.append(f"{r['rule_id']} {ev['archivo']}: "
                                      f"'{ev['fragmento']}' (linea {hits[0]})"
                                      f" rompe el orden (anterior {ant})")
                    previas[ev["archivo"]] = hits[0]
            else:
                motivo = "no existe" if not hits else f"ambiguo {hits}"
                fallos.append(f"{r['rule_id']} {ev['archivo']}: "
                              f"'{ev['fragmento']}' -> {motivo}")
        r["estado_revision"] = r.get("estado_revision", "pendiente")

    # ---- 3. ausencias
    total_aus = ok_aus = 0
    for r in datos["reglas"]:
        for a in r.get("ausencias", []):
            total_aus += 1
            lineas = cargar(carpeta, a["archivo"], cache)
            ini, fin = 1, len(lineas)
            if a.get("desde_fragmento"):
                h = ubicar(lineas, a["desde_fragmento"], a.get("desde_ocurrencia"))
                ini = h[0] if len(h) == 1 else ini
            if a.get("hasta_fragmento"):
                h = ubicar(lineas, a["hasta_fragmento"], a.get("hasta_ocurrencia"))
                fin = h[0] if len(h) == 1 else fin
            pat = re.compile(a["patron"], re.I)
            encontradas = [i for i in range(ini, fin + 1)
                           if pat.search(lineas[i - 1])]
            a["rango"] = [ini, fin]
            a["encontradas"] = len(encontradas)
            if len(encontradas) == a["esperado"]:
                ok_aus += 1
            else:
                fallos.append(f"{r['rule_id']} ausencia {a['archivo']} "
                              f"/{a['patron']}/ lineas {ini}-{fin}: "
                              f"esperado {a['esperado']}, hay "
                              f"{len(encontradas)} {encontradas}")

    # ---- 4. cobertura por bloque
    sin_cubrir, cob_ok, cob_tot = [], 0, 0
    for arch in archivos_legacy(carpeta, datos):
        lineas = cargar(carpeta, arch, cache)
        for et, a, b in bloques(arch, lineas):
            cob_tot += 1
            if any(a <= n <= b for n in citadas.get(arch, ())):
                cob_ok += 1
            elif f"{arch}:{et}" in TECNICOS or f"{arch}:{et}" in datos.get("tecnicos", {}):
                cob_ok += 1
            else:
                sin_cubrir.append(f"{arch}:{et} (lineas {a}-{b})")

    # ---- 5. decisiones sin regla
    dec_sin, dec_tot = [], 0
    for arch in archivos_legacy(carpeta, datos):
        lineas = cargar(carpeta, arch, cache)
        for n in decisiones(arch, lineas):
            dec_tot += 1
            if n not in citadas.get(arch, ()):
                dec_sin.append(f"{arch}:{n}: {norm(lineas[n - 1])}")

    # ---- salidas
    os.makedirs(salida, exist_ok=True)
    with open(os.path.join(salida, "rules_trazadas.json"), "w",
              encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    escribir_reporte(datos, salida)

    estados = Counter(r["estado_revision"] for r in datos["reglas"])
    print(f"Reglas extraidas ........ {len(datos['reglas'])}")
    print(f"Estados de revision ..... {dict(estados)}")
    print(f"Evidencias verificadas .. {ok_ev}/{total_ev}")
    print(f"Ausencias comprobadas ... {ok_aus}/{total_aus}")
    print(f"Bloques con regla ....... {cob_ok}/{cob_tot}")
    print(f"Decisiones citadas ...... {dec_tot - len(dec_sin)}/{dec_tot}")
    for titulo, lista in (("FALLOS DE TRAZABILIDAD", fallos),
                          ("BLOQUES SIN REGLA", sin_cubrir),
                          ("DECISIONES SIN REGLA", dec_sin)):
        if lista:
            print(f"\n{titulo}:")
            for x in lista:
                print("  -", x)
    sys.exit(1 if (fallos or sin_cubrir or dec_sin) else 0)


ETIQUETA = {"aprobada": "APROBADA", "pendiente": "pendiente",
            "corregida_pendiente_reaprobacion": "CORREGIDA - requiere reaprobacion"}


def escribir_reporte(datos, salida):
    rs = datos["reglas"]
    estados = Counter(r["estado_revision"] for r in rs)
    o = ["# Reporte de reglas — estado tras el dictamen", ""]
    if datos.get("dictamen"):
        d = datos["dictamen"]
        o += [f"**Dictamen:** {d['documento']} — {d['responsable']} "
              f"({d['fecha']}).", ""]
    o += [f"- Aprobadas: **{estados.get('aprobada', 0)}**",
          f"- Corregidas, requieren reaprobación: "
          f"**{estados.get('corregida_pendiente_reaprobacion', 0)}**",
          f"- Pendientes: **{estados.get('pendiente', 0)}**", "",
          "Cada línea citada fue verificada automáticamente contra el "
          "código. «Aprobada» valida la extracción del comportamiento "
          "existente, no que sea un requisito de negocio deseable.", ""]
    corr = [r for r in rs if r["estado_revision"] ==
            "corregida_pendiente_reaprobacion"]
    if corr:
        o += ["## Reglas que requieren tu reaprobación", "",
              "| ID | Tipo | Qué pidió el dictamen | Qué se cambió |",
              "|---|---|---|---|"]
        for r in corr:
            o.append(f"| {r['rule_id']} | {r.get('tipo', '')} | "
                     f"{r['dictamen']['justificacion']} | "
                     f"{r['correccion']['resumen']} |")
        o.append("")
    for titulo, tipo in (("Reglas de negocio", "negocio"),
                         ("Hallazgos técnicos", "tecnico")):
        sel = [r for r in rs if r.get("tipo", "negocio") == tipo]
        o += [f"## {titulo} ({len(sel)})", "",
              "| ID | Categoría | Confianza | Estado |", "|---|---|---|---|"]
        for r in sel:
            o.append(f"| {r['rule_id']} | {r['categoria']} | "
                     f"{r['confianza']} | {ETIQUETA[r['estado_revision']]} |")
        o.append("")
    for tipo in ("negocio", "tecnico"):
        for r in [x for x in rs if x.get("tipo", "negocio") == tipo]:
            o += [f"### {r['rule_id']} — {r['categoria']} ({r['confianza']}) "
                  f"· {ETIQUETA[r['estado_revision']]}", "",
                  r["descripcion"], "",
                  f"- **Condición:** {r['condicion']}",
                  f"- **Acción:** {r['accion']}"]
            if r.get("parametros"):
                o.append("- **Parámetros:** `" + json.dumps(
                    r["parametros"], ensure_ascii=False) + "`")
            o.append("- **Evidencia:**" + (" (en orden de ejecución)"
                                           if r.get("evidencia_ordenada")
                                           else ""))
            for ev in r["evidencia"]:
                o.append(f"  - `{ev['archivo']}` línea {ev['lineas'][0]}: "
                         f"`{norm(ev['fragmento'])}`")
            for a in r.get("ausencias", []):
                o.append(f"- **Comprobación de ausencia:** {a['descripcion']} "
                         f"(`{a['archivo']}`, líneas {a['rango'][0]}-"
                         f"{a['rango'][1]}, patrón `{a['patron']}`: "
                         f"{a['encontradas']} coincidencias, esperado "
                         f"{a['esperado']})")
            for c in r.get("comprobaciones", []):
                o.append(f"- **Comprobación:** {c}")
            if r.get("dictamen"):
                o.append(f"- **Dictamen:** {r['dictamen']['decision']} — "
                         f"{r['dictamen']['justificacion']}")
            if r.get("correccion"):
                o.append(f"- **Corrección aplicada:** "
                         f"{r['correccion']['resumen']}")
            if r.get("preguntas_abiertas"):
                o.append("- **Preguntas para el dueño del negocio:**")
                for q in r["preguntas_abiertas"]:
                    o.append(f"  - {q}")
            o.append("")
    if datos.get("preguntas_negocio"):
        o += ["## Preguntas pendientes para negocio y QA (del dictamen)", ""]
        for i, q in enumerate(datos["preguntas_negocio"], 1):
            o.append(f"{i}. {q}")
        o.append("")
    o += ["## Glosario de variables", "", "| Variable | Significado |",
          "|---|---|"]
    for k, v in datos["glosario"].items():
        o.append(f"| `{k}` | {v} |")
    with open(os.path.join(salida, "reporte_reglas.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
