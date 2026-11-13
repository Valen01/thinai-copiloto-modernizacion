# ADR-003: Multitenancy

## Estado
Aceptada.

## Contexto
El legacy es de un solo inquilino: los parametros de negocio estan en una unica tabla `LS_PARAMETROS` y los
datos en tablas sin discriminador. El servicio moderno debe atender varios tenants sin mezclar datos.

## Decision
- Todo metodo de `ports.py` y todo caso de uso reciben `tenant_id` como PRIMER parametro.
- Es configuracion POR tenant (nunca constantes del dominio): los parametros de negocio de `LS_PARAMETROS`
  (plazos de denuncia, deducible minimo, descuento VIP, tolerancia de mora, penalizacion, retencion, tope de
  auto aprobacion, alertas de fraude, factor de inflacion), asi como sus datos maestros y movimientos.
  En `examples/`, TENANT_B usa `DIAS_MAX_DENUNCIA=15`, `DEDUCIBLE_MINIMO=50`, `UMBRAL_RETENCION=1000`,
  `TASA_RETENCION=5` y `TOPE_AUTO_APROBACION=2000`, distintos de TENANT_A.
- Festivos y hora de corte no existen en el legacy: la logica de dias habiles es codigo muerto (R-037: no
  portada) y el corte del lote es la fecha de proceso recibida (R-028, R-032).
- `TenantDataStore` mantiene un `TenantData` aislado por tenant; un tenant desconocido produce
  `TenantNotFoundError` y nunca cae en datos de otro.
- El `tenant_id` se valida con `^[A-Za-z0-9_-]{1,40}$` (seguro para rutas de archivo); HTTP lo exige en la
  cabecera `X-Tenant-ID`.
- El `tenant_id` no es dato sensible y puede aparecer en logs; los identificadores de siniestro/poliza se
  enmascaran con `mask_id`.

## Consecuencias
- Anadir un tenant es anadir datos/parametros, no codigo.
- El almacen en memoria es de un solo proceso; para produccion se implementarian los puertos sobre una base
  de datos con discriminador de tenant (sin cambiar dominio ni casos de uso).

## Reglas relacionadas
R-003, R-007, R-028, R-032, R-037.
