#!/usr/bin/env python3
"""
Compuerta de calidad del Generador (solo libreria estandar).

Uso:  python3 -I gate_codigo.py <carpeta_proyecto> <rules_final.json> [--min-cov 80]

Comprueba, sobre el proyecto generado:
  1 estructura hexagonal      5 multitenant (puertos + OpenAPI)
  2 dominio puro y sin float   6 ADRs
  3 complejidad <= 10          7 trazabilidad regla -> codigo -> prueba
  4 secretos y enmascaramiento 8 pruebas y cobertura de lineas
Escribe <proyecto>/docs/matriz_trazabilidad.md y sale con 1 si algo falla.
"""
import ast, json, os, re, subprocess, sys

CAPAS = ["domain", "application", "adapters/inbound", "adapters/outbound"]
MAX_CC = 10
PROHIBIDOS_DOMINIO = {"flask", "fastapi", "pydantic", "sqlalchemy", "requests",
                      "uvicorn", "django", "starlette", "oracledb", "cx_Oracle"}
SECRETOS = [r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]",
            r"AKIA[0-9A-Z]{16}", r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
            r"sk-[A-Za-z0-9]{20,}", r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"]
fallos, avisos, info = [], [], []


def ok(c, msg_fallo):
    if not c:
        fallos.append(msg_fallo)
    return c


def archivos(base, ext):
    for r, _, fs in os.walk(base):
        if any(p in r for p in ("__pycache__", ".git", ".venv", "node_modules")):
            continue
        for f in fs:
            if f.endswith(ext):
                yield os.path.join(r, f)


def leer(p):
    return open(p, encoding="utf-8", errors="replace").read()


def complejidad(fn):
    n = 1
    for x in ast.walk(fn):
        if isinstance(x, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler,
                          ast.With, ast.IfExp, ast.Assert, ast.comprehension)):
            n += 1
        elif isinstance(x, ast.BoolOp):
            n += len(x.values) - 1
        elif isinstance(x, ast.Match):
            n += len(x.cases)
    return n


def src_dir(p):
    for c in (os.path.join(p, "src"), p):
        for d in os.listdir(c) if os.path.isdir(c) else []:
            if os.path.isdir(os.path.join(c, d, "domain")):
                return os.path.join(c, d)
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    proy, rj = sys.argv[1], sys.argv[2]
    minc = float(sys.argv[sys.argv.index("--min-cov") + 1]) if "--min-cov" in sys.argv else 80.0
    pkg = src_dir(proy)
    if not ok(pkg, "1. No hay paquete con carpeta domain/ (src/<paquete>/domain)"):
        return fin()
    pyfiles = list(archivos(pkg, ".py"))

    # 1 estructura
    for c in CAPAS:
        ok(os.path.isdir(os.path.join(pkg, c)), f"1. Falta la capa {c}/")
    for f in ("Makefile", "README.md", "docs/openapi.yaml"):
        ok(os.path.exists(os.path.join(proy, f)), f"1. Falta {f}")
    mk = leer(os.path.join(proy, "Makefile")) if os.path.exists(os.path.join(proy, "Makefile")) else ""
    ok(re.search(r"^demo:", mk, re.M), "1. El Makefile no tiene el objetivo 'demo' (comando unico)")

    # 2 dominio puro, sin float
    propios = {os.path.basename(pkg)}
    permitidos = set(sys.stdlib_module_names) | propios
    for capa in ("domain", "application"):
        for f in archivos(os.path.join(pkg, capa), ".py"):
            t = ast.parse(leer(f))
            for n in ast.walk(t):
                mods = []
                if isinstance(n, ast.Import):
                    mods = [a.name.split(".")[0] for a in n.names]
                elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    mods = [n.module.split(".")[0]]
                for m in mods:
                    ok(m in permitidos and m not in PROHIBIDOS_DOMINIO,
                       f"2. {os.path.relpath(f, proy)}: importa '{m}' (dominio/aplicacion solo stdlib)")
                if capa == "domain":
                    if isinstance(n, ast.Name) and n.id == "float":
                        fallos.append(f"2. {os.path.relpath(f, proy)}:{n.lineno}: usa float (usar Decimal)")
                    if isinstance(n, ast.Constant) and isinstance(n.value, float):
                        fallos.append(f"2. {os.path.relpath(f, proy)}:{n.lineno}: literal float (usar Decimal)")
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("open", "print"):
                    fallos.append(f"2. {os.path.relpath(f, proy)}:{n.lineno}: {n.func.id}() en {capa} (E/S solo en adaptadores)")

    # 3 complejidad
    peor = (0, "")
    for f in pyfiles + list(archivos(os.path.join(proy, "tests"), ".py")):
        for n in ast.walk(ast.parse(leer(f))):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cc = complejidad(n)
                peor = max(peor, (cc, f"{os.path.relpath(f, proy)}:{n.name}"))
                ok(cc <= MAX_CC, f"3. Complejidad {cc} > {MAX_CC} en {os.path.relpath(f, proy)}:{n.lineno} {n.name}")
    info.append(f"complejidad maxima {peor[0]} ({peor[1]})")

    # 4 secretos y enmascaramiento
    for f in list(archivos(proy, ".py")) + list(archivos(proy, ".yaml")) + list(archivos(proy, ".md")) + list(archivos(proy, ".env")):
        for i, ln in enumerate(leer(f).splitlines(), 1):
            if any(re.search(p, ln) for p in SECRETOS):
                fallos.append(f"4. Posible secreto en {os.path.relpath(f, proy)}:{i}")
    mk_ = [f for f in pyfiles if re.search(r"mask", os.path.basename(f))]
    if ok(mk_, "4. No existe un modulo de enmascaramiento (*mask*.py)"):
        fns = [n.name for n in ast.walk(ast.parse(leer(mk_[0]))) if isinstance(n, ast.FunctionDef)]
        ok(any("mask" in n for n in fns), "4. El modulo de enmascaramiento no define funciones mask_*")
        usado = [f for f in pyfiles if f != mk_[0] and re.search(r"\bmask_\w+\(", leer(f))]
        ok(usado, "4. El enmascaramiento existe pero ningun adaptador lo usa")
    for f in pyfiles:
        for n in ast.walk(ast.parse(leer(f))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in (
                    "info", "debug", "warning", "error", "exception") and getattr(n.func.value, "id", "") in ("log", "logger", "logging"):
                txt = ast.unparse(n)
                if re.search(r"loan_id|account|customer|cliente|nombre", txt) and "mask_" not in txt:
                    fallos.append(f"4. {os.path.relpath(f, proy)}:{n.lineno}: log con dato sensible sin mask_*")

    # 5 multitenant
    ports = [f for f in archivos(os.path.join(pkg, "application"), ".py") if "port" in os.path.basename(f)]
    if ok(ports, "5. No hay application/ports.py"):
        for f in ports:
            for n in ast.walk(ast.parse(leer(f))):
                if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
                    args = [a.arg for a in n.args.args + n.args.kwonlyargs]
                    ok("tenant_id" in args, f"5. Puerto {n.name} ({os.path.relpath(f, proy)}:{n.lineno}) sin parametro tenant_id")
    oa = os.path.join(proy, "docs", "openapi.yaml")
    if os.path.exists(oa):
        try:
            import yaml
            d = yaml.safe_load(leer(oa))
        except Exception as e:
            d = None
            fallos.append(f"5. openapi.yaml no se puede leer: {e}")
        if d:
            ok(str(d.get("openapi", "")).startswith("3."), "5. openapi.yaml no declara openapi: 3.x")
            ok(d.get("paths"), "5. openapi.yaml sin paths")
            for p, ops in (d.get("paths") or {}).items():
                for m, op in ops.items():
                    if m not in ("get", "post", "put", "patch", "delete"):
                        continue
                    ok(op.get("responses"), f"5. {m.upper()} {p} sin responses")
                    cab = json.dumps(op.get("parameters", [])) + json.dumps(d.get("components", {}).get("parameters", {}))
                    ok("tenant" in cab.lower(), f"5. {m.upper()} {p} sin cabecera de tenant (X-Tenant-ID)")

    # 6 ADRs
    adrs = sorted(archivos(os.path.join(proy, "docs", "adr"), ".md")) if os.path.isdir(os.path.join(proy, "docs", "adr")) else []
    ok(len(adrs) >= 3, f"6. Se esperan >= 3 ADRs en docs/adr/ (hay {len(adrs)})")
    textos_adr = ""
    for f in adrs:
        t = leer(f)
        textos_adr += t
        for s in ("Estado", "Contexto", "Decisi", "Consecuencias"):
            ok(s in t, f"6. {os.path.basename(f)} sin seccion '{s}'")

    # 7 trazabilidad
    reglas = json.load(open(rj, encoding="utf-8"))["reglas"]
    APR = ("aprobada", "aprobada_automatica", "aprobada_po")
    aprob = [r for r in reglas if r["estado_revision"] in APR]
    otras = [r["rule_id"] for r in reglas if r["estado_revision"] not in APR and r.get("tipo") != "tecnico"]
    if otras:
        avisos.append("Reglas sin aprobar (no se implementan; van a cola de revision): " + ", ".join(otras))
    src_t = "\n".join(leer(f) for f in pyfiles)
    tst_t = "\n".join(leer(f) for f in archivos(os.path.join(proy, "tests"), ".py"))
    filas = []
    for r in aprob:
        rid = r["rule_id"]
        mark = re.compile(rf"REGLA:[^\n]*\b{rid}\b")
        en_src, en_tst = bool(mark.search(src_t)), bool(mark.search(tst_t))
        en_adr = bool(re.search(rf"{rid}[^\n]*(no portada|no aplica|diverge)", textos_adr, re.I))
        ok((en_src and en_tst) or en_adr,
           f"7. {rid}: falta marcador 'REGLA: {rid}' en codigo ({en_src}) o prueba ({en_tst}), o ADR que justifique")
        filas.append(f"| {rid} | {'si' if en_src else 'no'} | {'si' if en_tst else 'no'} | {'ADR' if en_adr else ''} |")
    for r in re.findall(r"REGLA:[^\n]*", src_t + tst_t):
        for rid in re.findall(r"R-\d{3}", r):
            ok(rid in {x["rule_id"] for x in reglas}, f"7. Marcador a regla inexistente {rid}")
            ok(rid not in otras, f"7. {rid} se implementa pero NO esta aprobada")
    os.makedirs(os.path.join(proy, "docs"), exist_ok=True)
    open(os.path.join(proy, "docs", "matriz_trazabilidad.md"), "w", encoding="utf-8").write(
        "# Matriz de trazabilidad regla -> codigo -> prueba\n\n| Regla | Codigo | Prueba | Justificada en ADR |\n|---|---|---|---|\n" + "\n".join(filas) + "\n")

    # 8 pruebas y cobertura
    cov = medir(proy, pkg)
    if cov is None:
        fallos.append("8. Las pruebas fallan o no se pudieron ejecutar (corra: python3 -m pytest tests -q)")
    else:
        info.append(f"cobertura de lineas {cov:.1f}% (minimo {minc}%)")
        ok(cov >= minc, f"8. Cobertura {cov:.1f}% < {minc}%")
    return fin()


def medir(proy, pkg):
    """Corre pytest dentro del proceso midiendo lineas de src con sys.settrace."""
    import threading
    sys.path.insert(0, os.path.dirname(pkg))
    sys.path.insert(0, proy)
    pkg_abs = os.path.abspath(pkg)
    ejecutadas = {}

    def tracer(frame, ev, arg):
        fn = frame.f_code.co_filename
        if not fn.startswith(pkg_abs):
            return None
        def local(fr, e, a):
            if e == "line":
                ejecutadas.setdefault(fn, set()).add(fr.f_lineno)
            return local
        ejecutadas.setdefault(fn, set()).add(frame.f_lineno)
        return local
    try:
        import pytest
    except ImportError:
        return None
    for m in [m for m in sys.modules if m.split(".")[0] == os.path.basename(pkg)]:
        del sys.modules[m]
    sys.settrace(tracer)
    threading.settrace(tracer)
    try:
        rc = pytest.main(["-q", "-p", "no:cacheprovider", os.path.join(proy, "tests")])
    finally:
        sys.settrace(None)
        threading.settrace(None)
    if rc != 0:
        return None
    tot = hit = 0
    for f in archivos(pkg_abs, ".py"):
        code = compile(leer(f), f, "exec")
        lines, pila = set(), [code]
        while pila:
            c = pila.pop()
            lines |= {l for _, _, l in c.co_lines() if l}
            pila += [k for k in c.co_consts if hasattr(k, "co_lines")]
        # ignora lineas de docstring/def puras no ejecutables en cuerpo: se cuentan igual (conservador)
        tot += len(lines)
        hit += len(lines & ejecutadas.get(os.path.abspath(f), set()))
    return 100.0 * hit / tot if tot else 0.0


def fin():
    print("\n=== COMPUERTA DE CALIDAD ===")
    for i in info:
        print("  info:", i)
    for a in avisos:
        print("  AVISO:", a)
    for f in fallos:
        print("  FALLA:", f)
    print("RESULTADO:", "APROBADA" if not fallos else f"RECHAZADA ({len(fallos)} fallas)")
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
