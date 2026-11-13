# ADR-005: Mejoras del PO (origen `po_mejorada`): R-036 y R-041

## Estado
Aceptada.

## Contexto
El Validador (PO bancario) mejoro dos reglas respecto al legacy.

## Decision
- R-036: diverge del legacy. El `CASE` sin `ELSE` dejaria el estado del siniestro en NULL ante un estado de
  liquidacion desconocido. El servicio traduce el estado ANTES de escribir (`claim_status_for`) y, si es
  desconocido, lanza `UnknownSettlementStatusError`: no se inserta liquidacion ni se actualiza el siniestro, y
  en el lote el savepoint (R-029) revierte todo y cuenta un error. Hoy solo llegan tres estados, asi que no
  cambia ningun resultado con datos validos.
- R-041: diverge del legacy. El modo debug esta apagado (`c_modo_debug = FALSE`) y la notificacion no hace nada
  mas que imprimir texto. Se conserva apagado (`debug_trace=False` por defecto) y, si se habilitara, la traza
  (`build_debug_trace`) usa identificadores enmascarados con `mask_id` y el nombre del asegurado reducido a
  iniciales con `mask_name`, evitando exponer datos personales.

## Consecuencias
- Con entradas validas el comportamiento es igual al legacy; solo cambia ante estados desconocidos (error
  explicito en vez de NULL) y en la traza de depuracion (enmascarada).

## Reglas relacionadas
R-036 (diverge), R-041 (diverge), R-025, R-029.
