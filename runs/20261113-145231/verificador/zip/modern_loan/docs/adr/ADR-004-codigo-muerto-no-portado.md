# ADR-004: Codigo muerto o sin efecto del legacy (no portado)

## Estado
Aceptada (reglas aprobadas por el PO como `hallazgo_tecnico`; no se implementan como regla).

## Contexto
Varias reglas tecnicas aprobadas describen codigo del paquete PL/SQL que nunca se ejecuta o no produce
ningun efecto observable. Portarlo seria anadir comportamiento que el legacy no tiene.

## Decision
Cada regla se registra con su justificacion; ninguna genera codigo:

- R-037: no portada. `fn_es_dia_habil` (lunes a viernes, sin festivos) nunca se invoca; los plazos son en dias
  calendario (R-007, decision del PO). Por eso no hay calendario de festivos por tenant.
- R-038: no portada. `fn_calcular_deducible_v1` (version 2009, truncando) es codigo muerto; rige R-014.
- R-039: no portada. `fn_calcular_iva` nunca se invoca; el IVA (TASA_IVA=19) no interviene en ningun importe.
  Decision PO: no aplicar IVA ("negocio nuevo, no se inventa").
- R-040: no portada. `pr_recalcular_reserva_tecnica` es privada y nunca se invoca; no se crea reserva tecnica
  ni la tabla `LS_TMP_CALCULO_2009`.
- R-042: no portada. El aviso WARN para polizas SUSPENDIDAS es inalcanzable (ya se rechazo en R-005).
- R-043: no portada. El chequeo `cubierto < 0` (e_monto_invalido) y el bloque comentado SIN-0001 no se
  ejecutan nunca; el rechazo por `cubierto <= 0` (R-017) ya cubre el caso.
- R-045: no portada. El acumulado `v_total_reclamado` y el parametro `VERSION_MOTOR` no se usan en ninguna
  salida ni calculo; `VERSION_MOTOR` (valor NULL) se acepta en `parametros.dat` sin efecto.

Las reglas tecnicas R-033, R-034, R-035, R-041 y R-044 SI tienen efecto observable y se implementan con marcador
`REGLA:` (ver ADR-007 para R-041).

## Consecuencias
- Menos superficie de codigo y de pruebas; la matriz de trazabilidad marca estas reglas como justificadas
  por ADR.
- Si el negocio quisiera IVA, reserva tecnica o dias habiles, serian reglas nuevas con su propia aprobacion.

## Reglas relacionadas
R-037, R-038, R-039, R-040, R-042, R-043, R-045 (no portadas); R-044 (se conserva, ver codigo).
