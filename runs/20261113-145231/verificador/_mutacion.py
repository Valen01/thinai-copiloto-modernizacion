"""Control de sensibilidad: copia el proyecto, introduce mutaciones de borde y comprueba
que los escenarios las detectan. No modifica el proyecto original."""
import json
import os
import shutil
import subprocess
import sys

SRC = "verificador/zip/modern_loan"
TMP = "verificador/_mut_proyecto"

MUTS = [
    ("domain/eligibility.py", "if days > ctx.params.require(code):", "if days >= ctx.params.require(code):", "R-007 > a >="),
    ("domain/eligibility.py", "< ctx.coverage.waiting_days", "<= ctx.coverage.waiting_days", "R-009 < a <="),
    ("domain/calculation.py", "if claimed > limit:", "if claimed >= limit:", "R-013 > a >="),
    ("domain/calculation.py", "if deductible < minimum:", "if deductible <= minimum:", "R-015 < a <="),
    ("domain/calculation.py", "covered > params.require(P.WITHHOLDING_THRESHOLD)", "covered >= params.require(P.WITHHOLDING_THRESHOLD)", "R-020 > a >="),
    ("domain/outcome.py", "if net > params.require(P.AUTO_APPROVAL_LIMIT):", "if net >= params.require(P.AUTO_APPROVAL_LIMIT):", "R-024 > a >="),
    ("domain/outcome.py", "return within_days and claimed >= threshold", "return within_days and claimed > threshold", "R-023 >= a >"),
    ("domain/calculation.py", "if prior_claims >= params.require(P.MAX_CLAIMS_PER_YEAR):", "if prior_claims > params.require(P.MAX_CLAIMS_PER_YEAR):", "R-018 >= a >"),
    ("domain/calculation.py", "if covered > remaining:", "if covered >= remaining:", "R-019 tope > a >= (marca)"),
]

esc = json.load(open(f"{SRC}/escenarios_equivalencia.json", encoding="utf-8"))["escenarios"]
for rel, a, b, nombre in MUTS:
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    shutil.copytree(SRC, TMP, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    f = f"{TMP}/src/claims_settlement/{rel}"
    t = open(f, encoding="utf-8").read()
    if a not in t:
        print("NO APLICA", nombre)
        continue
    open(f, "w", encoding="utf-8").write(t.replace(a, b, 1))
    subprocess.run([sys.executable, f"{TMP}/harness_equivalencia.py", f"{TMP}/escenarios_equivalencia.json",
                    "verificador/_mut_out.json"], env=dict(os.environ, PYTHONPATH=f"{TMP}/src"), check=True,
                   capture_output=True)
    obt = json.load(open("verificador/_mut_out.json", encoding="utf-8"))
    det = [e["id"] for e in esc if obt[e["id"]] != e["esperado"]]
    print(("DETECTADA " if det else "NO DETECTADA ") + nombre, det)
shutil.rmtree(TMP, ignore_errors=True)
