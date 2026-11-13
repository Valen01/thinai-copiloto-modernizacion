# ADR-002: Dinero con Decimal frente a NUMBER y orden de redondeo

## Estado
Aceptada.

## Contexto
El legacy usa `NUMBER(14,2)` de Oracle (decimal exacto) y `ROUND(x, 2)` (mitad hacia arriba, segun la cabecera
documentada en R-022). Un `float` binario introduciria errores de representacion (p. ej. 7131.105 no es exacto).

## Decision
- Todo importe y porcentaje es `decimal.Decimal`; `domain/money.py` rechaza `float` y `bool` (`to_decimal`).
  El dominio no contiene `float` (lo verifica la compuerta).
- `round2` usa `ROUND_HALF_UP` con contexto de 38 digitos (equivalente a los 38 digitos de NUMBER).
- `percent_of(monto, pct) = round2(monto * pct / 100)`: una sola multiplicacion y division sin redondeo
  intermedio y luego redondeo inmediato a 2 decimales (R-022).
- Orden de redondeo = orden de calculo (R-021): deducible porcentual (R-014), descuento VIP (R-016), cubierto
  (R-017), penalizacion (R-018), retencion (R-020) y umbral de fraude (R-023) se redondean cada uno al calcularse,
  nunca al final. Ejemplo calculado a mano: (8123.45 - 200.00) * 90 / 100 = 7131.105 -> 7131.11.
- Salida batch/HTTP: importes sin signo con exactamente dos decimales (`format_amount`); un importe negativo no
  es representable sin signo y se rechaza con error explicito en lugar de perder el signo.

## Consecuencias
- Resultados exactos y reproducibles; el redondeo "mitad hacia arriba" es explicito y no el "mitad par" por
  defecto de Python.
- Los parametros se leen con hasta 4 decimales (NUMBER(14,4)) y los importes de entrada con 2.

## Reglas relacionadas
R-013 a R-020, R-021, R-022, R-023, R-024.
