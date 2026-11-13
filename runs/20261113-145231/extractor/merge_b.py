import json, glob
reglas, tec, glo = [], {}, {}
for f in sorted(glob.glob("extractor/parts_b/p*.json")):
    d = json.load(open(f, encoding="utf-8"))
    reglas += d["reglas"]
    tec.update(d.get("tecnicos", {}))
    glo.update(d.get("glosario", {}))
json.dump({"reglas": reglas, "tecnicos": tec, "glosario": glo},
          open("extractor/rules_b.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(reglas))
