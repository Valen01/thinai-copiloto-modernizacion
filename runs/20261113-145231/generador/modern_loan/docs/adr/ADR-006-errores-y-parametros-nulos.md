# ADR-006: Errores de dominio, parametros ausentes o NULL y entidades inexistentes

## Estado
Decidida por defecto (R-001, R-002, R-003, R-044 definen el comportamiento base; los detalles de
representacion no estaban definidos).

## Contexto
El legacy usa `RAISE_APPLICATION_ERROR` (ORA-20001, ORA-20010) y deja propagar `NO_DATA_FOUND`. Python no tiene
esos codigos; ademas R-003 permite que un parametro con valor NULL se devuelva sin error, pero ninguna regla
define que ocurre si un calculo usa ese NULL (en SQL, las comparaciones con NULL no se cumplen).

## Decision
- R-001: `ClaimNotRegisteredError` (codigo `ORA-20001`) con el id enmascarado y el estado actual; no se
  escribe nada. HTTP 409. Decision del PO: un siniestro PENDIENTE_REVISION sigue dando este error (sin flujo
  de reproceso inventado).
- R-002: `EntityNotFoundError` (codigo `NO_DATA_FOUND`) para siniestro, poliza o cliente inexistente; en el
  lote se cuenta como error y el siniestro sigue REGISTRADO (R-029). HTTP 404.
- R-003: `ParameterNotDefinedError` (`ORA-20010`) si el parametro no existe en el tenant. Un parametro con
  valor NULL se devuelve sin error con `num()` (decision del PO). **Decidida por defecto:** si un calculo
  usa un parametro NULL con `require()`, se lanza `ParameterNullError` en lugar de dejar que el NULL haga
  que una comparacion "no se cumpla" en silencio. No afecta a los datos de ejemplo: el unico NULL es
  `VERSION_MOTOR`, que ninguna regla usa (R-045).
- R-044: se lee `FACTOR_INFLACION` al inicio sin usarlo; si falta, todo siniestro falla con ORA-20010 antes de
  cualquier validacion (comportamiento observable conservado).
- Los mensajes de error y la bitacora enmascaran identificadores con `mask_id`. En la bitacora de errores
  del lote, una excepcion que no es de dominio se registra solo como `<Tipo>: error interno` para no filtrar
  datos.

## Consecuencias
- Los consumidores distinguen el error por `code`; el codigo simbolico conserva el del legacy.
- Un parametro NULL usado en calculo detiene el siniestro (queda REGISTRADO y se reintenta) en vez de
  producir un importe silenciosamente incorrecto.

## Reglas relacionadas
R-001, R-002, R-003, R-029, R-044, R-045.
