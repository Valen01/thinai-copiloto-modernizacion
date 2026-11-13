import json
d = json.load(open("verificador/zip/modern_loan/docs/reglas_limpias.json", encoding="utf-8"))
print({k: v for k, v in d.items() if k != "reglas"})
for r in d["reglas"]:
    if r["rule_id"] in ("R-001","R-002","R-003","R-004","R-005","R-006","R-007","R-008","R-009","R-010"):
        continue
    print("=====", r["rule_id"], r.get("tipo"), r.get("origen"), r.get("categoria"))
    print(r["descripcion"])
    print("PARAMS:", json.dumps(r.get("parametros"), ensure_ascii=False))
    if r.get("origen") != "legacy":
        print("EXTRA:", json.dumps({k: r[k] for k in r if k in ("comportamiento_nuevo", "diferencia", "legacy_comportamiento", "mejora")}, ensure_ascii=False))
        print("VALPO:", json.dumps(r.get("validacion_po"), ensure_ascii=False)[:1500])
