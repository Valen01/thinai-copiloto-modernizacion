# ADR-008: Auditoria autonoma, savepoint por siniestro y commit unico

## Estado
Decidida por defecto en los detalles de implementacion; el comportamiento base lo fijan R-027, R-029, R-031 y
R-033.

## Contexto
El legacy escribe la bitacora con una transaccion autonoma (persiste aunque haya ROLLBACK), aisla cada
siniestro con SAVEPOINT y confirma una sola vez al final del lote. La liquidacion individual no hace COMMIT
(lo controla el llamador).

## Decision
- R-033: puerto `AuditLog.record(tenant_id, ...)`; la implementacion en memoria no participa del rollback del
  almacen. Mensaje truncado a 1000 caracteres (limite de `VARCHAR2(1000)`, fijado por el codigo: el truncado
  es regla aprobada, no decision nuestra). Cada resultado escribe un INFO con estado, motivo y neto.
- R-029: `TransactionManager` ofrece `savepoint`, `rollback_to_savepoint` y `commit` por tenant; el lote hace
  savepoint por siniestro y, ante cualquier excepcion, rollback, cuenta del error y log ERROR; el lote sigue.
  La secuencia de liquidaciones no retrocede.
- R-031: un unico `commit` al terminar el bucle, mas INFO de inicio (con fecha de proceso) y de fin (con
  contadores).
- R-027: `SettleClaim.execute` no hace commit; `SettleOneClaim` (HTTP) controla savepoint y commit porque
  en una llamada aislada no hay llamador que confirme.
- **Decidida por defecto:** la bitacora (`bitacora.out`) escribe el id de siniestro enmascarado
  (`mask_id`) y el logger de Python solo registra tenant, nivel y referencia enmascarada, nunca el mensaje
  completo.
- **Decidida por defecto:** el formato de `bitacora.out` es `log_id|nivel|referencia_enmascarada|mensaje`;
  no hay timestamp en el archivo para que dos ejecuciones sean comparables.

## Consecuencias
- El estado de un siniestro con error sigue siendo REGISTRADO y se reintenta en el siguiente lote (decision
  del PO en R-029).
- La auditoria no puede deshacerse; por eso no contiene datos personales.

## Reglas relacionadas
R-027, R-029, R-031, R-033.
