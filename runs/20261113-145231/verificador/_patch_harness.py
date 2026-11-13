p = "verificador/zip/modern_loan/harness_equivalencia.py"
t = open(p, encoding="utf-8").read()
t = t.replace('''def _num(x):
    return format(x, "f")
''', '''def _num(x):
    """Importe como NUMBER(x,2) de Oracle: texto con exactamente 2 decimales (mitad arriba)."""
    return format(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")
''')
t = t.replace("from decimal import Decimal\n", "from decimal import ROUND_HALF_UP, Decimal\n", 1)
open(p, "w", encoding="utf-8").write(t)
print("ok")
