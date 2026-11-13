import json, sys
lo, hi = sys.argv[1], sys.argv[2]
d = json.load(open("validador/reglas_limpias.json", encoding="utf-8"))
if lo == "G":
    print(json.dumps(d["glosario"], ensure_ascii=False, indent=1))
    sys.exit()
for r in d["reglas"]:
    if not (lo <= r["rule_id"] <= hi):
        continue
    print("=====", r["rule_id"], r["tipo"], r["categoria"], r["estado_revision"], r.get("origen"))
    print("DESC:", r["descripcion"])
    print("COND:", r.get("condicion"))
    print("ACC:", r.get("accion"))
    print("PAR:", json.dumps(r.get("parametros"), ensure_ascii=False))
    v = r.get("validacion_po") or {}
    print("PO:", v.get("decision"), "|", v.get("justificacion"))
    for q in v.get("preguntas_cerradas") or []:
        print("  Q:", q["pregunta"], "->", q["respuesta"])
