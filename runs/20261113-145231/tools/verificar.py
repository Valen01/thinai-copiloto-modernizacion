#!/usr/bin/env python3
"""
Verificador: compara el codigo nuevo contra las reglas y contra el comportamiento del legacy.
Solo libreria estandar.

Uso: python3 -I verificar.py <carpeta_del_zip_del_generador> --legacy <archivo_o_carpeta_legacy> [--legacy ...]
                             [--narrativa narrativa.json] [--salida informe_verificacion.md]

Entradas del flujo: (1) los archivos legacy que entraron al Extractor (--legacy) y (2) el ZIP del Generador
descomprimido, que debe traer docs/reglas_limpias.json y el proyecto (src/<paquete>/domain, tests, docs/adr).
escenarios_equivalencia.json y harness_equivalencia.py los escribe el agente en la carpeta del proyecto.
Genera UN informe Markdown. Sale con 1 si el veredicto no es favorable.
"""
import ast, json, os, re, subprocess, sys, xml.etree.ElementTree as ET
from datetime import date

LEGACY_EXT = (".cbl", ".cob", ".cobol", ".sql", ".pls", ".pks", ".pkb", ".rpg", ".rpgle")
SKIP = ("__pycache__", ".git", ".venv", "node_modules", "build", ".pytest_cache")


def walk(base):
    for r, ds, fs in os.walk(base):
        ds[:] = [d for d in ds if d not in SKIP]
        for f in fs:
            yield os.path.join(r, f)


def leer(p):
    return open(p, encoding="utf-8", errors="replace").read()


def buscar(base):
    out = {"reglas": None, "proyecto": None, "pkg": None, "legacy": [], "escenarios": None,
           "harness": None, "golden": [], "gate": None}
    for p in walk(base):
        n = os.path.basename(p)
        if n == "reglas_limpias.json":
            out["reglas"] = p
        elif n == "escenarios_equivalencia.json":
            out["escenarios"] = p
        elif n == "harness_equivalencia.py":
            out["harness"] = p
        elif n == "gate_codigo.py":
            out["gate"] = p
        elif n.lower().startswith("golden_master"):
            out["golden"].append(p)
        elif n.lower().endswith(LEGACY_EXT) and "numerado" not in n.lower() and "/src/" not in p.replace("\\", "/") \
                and "/tests/" not in p.replace("\\", "/"):
            out["legacy"].append(p)
    for p in walk(base):
        q = p.replace("\\", "/")
        if q.endswith("/domain/__init__.py") and "/src/" in q:
            out["pkg"] = os.path.dirname(os.path.dirname(p))
            out["proyecto"] = os.path.dirname(os.path.dirname(out["pkg"]))
            break
    return out


def marcadores(texto):
    return set(re.findall(r"R-\d{3}", " ".join(re.findall(r"REGLA:[^\n]*", texto))))


def tests_por_regla(tests_dir):
    """funcion de prueba -> reglas que cita en su docstring/comentarios."""
    res = {}
    for f in walk(tests_dir):
        if not f.endswith(".py"):
            continue
        txt = leer(f)
        lineas = txt.splitlines()
        for n in ast.walk(ast.parse(txt)):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                seg = "\n".join(lineas[n.lineno - 1:n.end_lineno])
                m = marcadores(seg)
                if m:
                    res[n.name] = m
    return res


def correr_pytest(proy):
    env = dict(os.environ, PYTHONPATH=os.path.join(proy, "src") + os.pathsep + os.environ.get("PYTHONPATH", ""))
    x = os.path.join(proy, ".verif_junit.xml")
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml", x,
                        os.path.join(proy, "tests")], cwd=proy, env=env, capture_output=True, text=True)
    resultados = {}
    if os.path.exists(x):
        for tc in ET.parse(x).getroot().iter("testcase"):
            nombre = re.sub(r"\[.*\]$", "", tc.get("name"))
            malo = tc.find("failure") is not None or tc.find("error") is not None
            resultados[nombre] = resultados.get(nombre, True) and not malo
        os.remove(x)
    return p.returncode, resultados, (p.stdout + p.stderr)[-600:]


def sin_regla(pkg):
    """Funciones/clases publicas de domain y application sin marcador REGLA en su cuerpo."""
    cand = []
    for capa in ("domain", "application"):
        for f in walk(os.path.join(pkg, capa)):
            if not f.endswith(".py") or os.path.basename(f) in ("__init__.py", "ports.py"):
                continue
            txt = leer(f)
            ls = txt.splitlines()
            for n in ast.iter_child_nodes(ast.parse(txt)):
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"):
                    seg = "\n".join(ls[n.lineno - 1:n.end_lineno])
                    if not marcadores(seg):
                        cand.append({"id": f"{capa}/{os.path.basename(f)}::{n.name}", "archivo": os.path.relpath(f, pkg),
                                     "linea": n.lineno, "tipo": "clase" if isinstance(n, ast.ClassDef) else "funcion"})
    return cand


def equivalencia(h, esc_path, difs, proy):
    esc = json.load(open(esc_path, encoding="utf-8"))["escenarios"]
    salida = os.path.join(proy, ".verif_out.json")
    p = subprocess.run([sys.executable, h, esc_path, salida], cwd=proy, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=os.path.join(proy, "src")))
    if p.returncode != 0 or not os.path.exists(salida):
        return None, esc, (p.stdout + p.stderr)[-600:]
    obt = json.load(open(salida, encoding="utf-8"))
    os.remove(salida)
    reglas_dif = {d["rule_id"] for d in difs}
    filas = []
    for e in esc:
        o = obt.get(e["id"], "<<sin resultado>>")
        if o == e["esperado"]:
            est = "IGUAL"
        elif e.get("diferencia_esperada_de") in reglas_dif:
            est = "DIFERENCIA_ESPERADA"
        else:
            est = "DIFERENCIA_NO_ESPERADA"
        filas.append({**e, "obtenido": o, "estado": est})
    return filas, esc, ""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    base = os.path.abspath(sys.argv[1])
    arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    narr = json.load(open(arg("--narrativa"), encoding="utf-8")) if arg("--narrativa") else {}
    salida = arg("--salida", "informe_verificacion.md")
    a = buscar(base)
    if "--legacy" in sys.argv:
        a["legacy"] = []
        for i, v in enumerate(sys.argv):
            if v == "--legacy":
                ruta = os.path.abspath(sys.argv[i + 1])
                a["legacy"] += [ruta] if os.path.isfile(ruta) else \
                    [q for q in walk(ruta) if q.lower().endswith(LEGACY_EXT)]
    problemas = []
    if not a["legacy"]:
        problemas.append("No se recibieron archivos legacy (--legacy)")
    if not a["reglas"]:
        problemas.append("No se encontro reglas_limpias.json")
    if not a["pkg"]:
        problemas.append("No se encontro el proyecto (src/<paquete>/domain)")
    if problemas:
        print("FALLA:", problemas)
        return 1
    pk = json.load(open(a["reglas"], encoding="utf-8"))
    reglas = [r for r in pk["reglas"] if r.get("tipo") != "tecnico" or r.get("origen") == "po_mejorada"]
    difs = pk.get("diferencias_esperadas", [])
    src_txt = "\n".join(leer(f) for f in walk(a["pkg"]) if f.endswith(".py"))
    tdir = os.path.join(a["proyecto"], "tests")
    tpr = tests_por_regla(tdir)
    rc, res_tests, cola = correr_pytest(a["proyecto"])
    en_src = marcadores(src_txt)
    adr = "\n".join(leer(f) for f in walk(os.path.join(a["proyecto"], "docs", "adr")) if f.endswith(".md")) \
        if os.path.isdir(os.path.join(a["proyecto"], "docs", "adr")) else ""

    # 1. reglas -> codigo -> prueba
    filas_r, incumplidas = [], 0
    for r in reglas:
        rid = r["rule_id"]
        tests = [t for t, m in tpr.items() if rid in m]
        if rid in en_src and tests:
            est = "CUMPLIDA" if all(res_tests.get(t, False) for t in tests) else "FALLA_EN_PRUEBA"
        elif rid in en_src:
            est = "IMPLEMENTADA_SIN_PRUEBA"
        elif re.search(rf"{rid}[^\n]*(no portada|no aplica)", adr, re.I):
            est = "NO_PORTADA_DOCUMENTADA"
        else:
            est = "NO_IMPLEMENTADA"
        if est not in ("CUMPLIDA", "NO_PORTADA_DOCUMENTADA"):
            incumplidas += 1
        filas_r.append((rid, r.get("categoria", ""), r.get("origen", ""), est, len(tests)))
    rech = [x["rule_id"] for x in pk.get("reglas_rechazadas", [])]
    rech_impl = [x for x in rech if x in en_src]
    desconocidas = sorted(en_src - {r["rule_id"] for r in pk["reglas"]} - set(rech))

    # 2. implementado sin regla
    cand = sin_regla(a["pkg"])
    clasif = narr.get("implementado_sin_regla", {})
    sin_clasificar = [c["id"] for c in cand if c["id"] not in clasif]

    # 3. equivalencia
    filas_e, estado_e, err_e = None, None, ""
    if a["harness"] and a["escenarios"]:
        filas_e, _, err_e = equivalencia(a["harness"], a["escenarios"], difs, a["proyecto"])
    n_ig = n_de = n_dn = 0
    if filas_e:
        n_ig = sum(1 for x in filas_e if x["estado"] == "IGUAL")
        n_de = sum(1 for x in filas_e if x["estado"] == "DIFERENCIA_ESPERADA")
        n_dn = sum(1 for x in filas_e if x["estado"] == "DIFERENCIA_NO_ESPERADA")
        todo_ejec = all(x.get("fuente_esperado") in ("ejecucion_legacy", "golden_master_entregado") for x in filas_e)
    cubiertas = {x.get("regla") for x in (filas_e or [])}
    sin_esc = [r["rule_id"] for r in reglas if r.get("origen") == "legacy" and r["rule_id"] not in cubiertas]

    # veredicto
    if rc != 0 or n_dn or incumplidas or rech_impl or desconocidas or sin_clasificar:
        veredicto = "NO APROBADO: hay incumplimientos que corregir"
    elif filas_e is None:
        veredicto = "SIN EVIDENCIA DE EQUIVALENCIA: faltan escenarios o el harness no corrio"
    elif sin_esc:
        veredicto = "PARCIAL: hay reglas legacy sin escenario de equivalencia"
    elif todo_ejec:
        veredicto = "EQUIVALENTE (DEMOSTRADO POR EJECUCION en los escenarios probados)"
    else:
        veredicto = "EQUIVALENTE POR LECTURA (no demostrado por ejecucion del legacy)"

    L = [f"# Informe de verificación — {date.today().isoformat()}", "", f"## Veredicto\n\n**{veredicto}**", ""]
    L += ["| Control | Resultado |", "|---|---|",
          f"| Reglas cumplidas (código + prueba que pasa) | {sum(1 for f in filas_r if f[3]=='CUMPLIDA')} de {len(filas_r)} |",
          f"| Reglas no portadas y documentadas | {sum(1 for f in filas_r if f[3]=='NO_PORTADA_DOCUMENTADA')} |",
          f"| Reglas con incumplimiento | {incumplidas} |",
          f"| Pruebas del proyecto | {'todas pasan' if rc == 0 else 'FALLAN'} ({len(res_tests)} casos) |",
          f"| Código implementado sin regla | {len(cand)} elementos ({len(sin_clasificar)} sin clasificar) |",
          f"| Reglas rechazadas pero implementadas | {len(rech_impl)} |",
          f"| Escenarios de equivalencia | {len(filas_e or [])}: {n_ig} iguales, {n_de} diferencias esperadas, {n_dn} no esperadas |", ""]
    L += ["## 1. Qué interpreto del legacy", ""]
    L += [f"- {x}" for x in narr.get("interpretacion_legacy", ["(el agente no entregó interpretación)"])]
    L += ["", "Archivos legacy encontrados: " + (", ".join(os.path.basename(p) for p in a["legacy"]) or "ninguno"), ""]
    L += ["## 2. Reglas de negocio contra el código nuevo", "", "| Regla | Categoría | Origen | Estado | Pruebas |", "|---|---|---|---|---|"]
    L += [f"| {a_} | {b} | {c} | {d} | {e} |" for a_, b, c, d, e in filas_r]
    if rech_impl:
        L += ["", "**Rechazadas por el PO pero presentes en el código:** " + ", ".join(rech_impl)]
    if desconocidas:
        L += ["", "**Marcadores a reglas que no existen:** " + ", ".join(desconocidas)]
    L += ["", "## 3. Implementado sin regla de origen", ""]
    if not cand:
        L.append("Ninguno.")
    else:
        L += ["| Elemento | Archivo | Clasificación | Justificación |", "|---|---|---|---|"]
        for c in cand:
            k = clasif.get(c["id"], {})
            L.append(f"| {c['id']} | {c['archivo']}:{c['linea']} | {k.get('clasificacion', '**SIN CLASIFICAR**')} | {k.get('justificacion', '')} |")
    L += ["", "## 4. ¿Hace lo mismo que el código viejo?", ""]
    if filas_e is None:
        L.append(f"No se pudo ejecutar la comparación. {err_e}")
    else:
        L += ["| Escenario | Regla | Fuente del esperado | Estado |", "|---|---|---|---|"]
        L += [f"| {x['id']} | {x.get('regla','')} | {x.get('fuente_esperado','')} | {x['estado']} |" for x in filas_e]
        dn = [x for x in filas_e if x["estado"] != "IGUAL"]
        if dn:
            L += ["", "### Diferencias", ""]
            for x in dn:
                L += [f"- **{x['id']}** ({x['estado']}): esperado `{json.dumps(x['esperado'], ensure_ascii=False)}`, "
                      f"obtenido `{json.dumps(x['obtenido'], ensure_ascii=False)}`. Cita: {x.get('cita','')}"]
    if sin_esc:
        L += ["", "Reglas legacy sin escenario: " + ", ".join(sin_esc)]
    L += ["", "### Nivel de evidencia", "",
          "- *Ejecución del legacy o golden master entregado*: demuestra equivalencia en esos escenarios.",
          "- *Lectura del código*: indica equivalencia, pero no la demuestra.",
          "- La equivalencia aplica solo a los escenarios listados; no es una prueba exhaustiva.", ""]
    if narr.get("observaciones"):
        L += ["## 5. Observaciones", ""] + [f"- {x}" for x in narr["observaciones"]] + [""]
    if rc != 0:
        L += ["## Salida de pytest (últimas líneas)", "", "```", cola, "```"]
    open(salida, "w", encoding="utf-8").write("\n".join(L))
    print(veredicto)
    print(f"informe: {salida}")
    return 0 if veredicto.startswith("EQUIVALENTE") else 1


if __name__ == "__main__":
    sys.exit(main())
