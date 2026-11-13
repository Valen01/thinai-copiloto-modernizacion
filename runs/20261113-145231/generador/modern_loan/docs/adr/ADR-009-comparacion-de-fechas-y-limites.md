# ADR-009: Comparacion de fechas, limites inclusivos/estrictos y orden del lote

## Estado
Decidida por defecto en lo no cubierto por las reglas; el comportamiento base esta aprobado (R-006, R-007,
R-009, R-018, R-023, R-028).

## Contexto
Las columnas DATE de Oracle admiten hora. Algunas reglas truncan (TRUNC) y otras comparan directo; los limites
mezclan `<`, `<=`, `>` y `>=`.

## Decision
- R-006: vigencia con comparacion directa sin truncar (`ocurrencia < inicio` o `ocurrencia > fin`); ambos
  extremos inclusive. Se conserva la hora si el archivo la trae. Decision del PO: "se porta exactamente esa
  comparacion directa". R-006 es la unica que NO trunca.
- R-007: dias = TRUNC(denuncia) - TRUNC(ocurrencia) en dias calendario; rechaza solo si `dias > maximo`
  (30 general, 365 VIDA), de modo que el dia limite se acepta.
- R-009: carencia rechaza si `dias_desde_inicio < dias_carencia` (estricto).
- R-018: ventana de siniestralidad `[ocurrencia - 365, ocurrencia)` (inferior inclusive, superior exclusivo),
  por poliza y cualquier cobertura, solo estado LIQUIDADO.
- R-023: fraude con `dias <= DIAS_ALERTA_FRAUDE` y `reclamado >= umbral`, ambos inclusive.
- R-028: lote con `fecha_denuncia <= fecha de proceso` (inclusive), orden por id ascendente. **Decidida por
  defecto:** la comparacion de la fecha de denuncia con el corte conserva la hora de la denuncia (sin TRUNC),
  igual que el cursor Oracle; una denuncia con hora posterior a la medianoche del corte queda fuera.
- R-032: la fecha de proceso solo fija la fecha de liquidacion y el corte del lote.
- **Dias > 999 / fechas lejanas**: no hay limite artificial; `datetime` de Python admite el rango completo y
  los dias son enteros sin desborde. No se trunca nada.

## Consecuencias
- Las pruebas cubren los bordes: `>` contra `>=`, dia limite de denuncia, carencia exacta, ventana de 365
  dias, extremos de vigencia.

## Reglas relacionadas
R-006, R-007, R-009, R-018, R-023, R-028, R-032.
