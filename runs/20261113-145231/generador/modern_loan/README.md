# Claims Settlement (liquidacion de siniestros)

Servicio moderno que reimplementa, a partir de **reglas de negocio aprobadas por el PO**
(`validador/reglas_limpias.json`), el paquete PL/SQL `PKG_LIQUIDACION_SINIESTROS`: valida la procedencia de un
siniestro, calcula deducible, cubierto, penalizacion, retencion y neto, decide el estado final (APROBADA,
RECHAZADA, PENDIENTE_APROBACION) y procesa lotes por tenant. Python 3.11+, dinero con `Decimal`, solo biblioteca
estandar en ejecucion (`pytest` y `PyYAML` para pruebas y compuerta).

> Este documento no afirma equivalencia con el legacy: eso lo demuestra el Verificador con su golden master.

## Ejecutar con un comando

```
make demo            # Linux/macOS
./run_demo.sh        # equivalente sin make
.\run_demo.ps1       # Windows (PowerShell)
```

Procesa los dos tenants de `examples/` (corte `2026-03-31`) y deja la salida en `out/<TENANT>/`:
`liquidaciones.out`, `siniestros.out`, `bitacora.out` y `resumen.txt`. Otras fechas: `PROCESS_DATE=2026-04-30 make demo`.

```
make test            # pytest
make gate            # compuerta de calidad (tools/gate_codigo.py)
```

Servidor HTTP opcional (stdlib): `PYTHONPATH=src python -m claims_settlement.adapters.inbound.http_api`
(variables `CLAIMS_DATA_DIR`, `CLAIMS_HTTP_HOST`, `CLAIMS_HTTP_PORT`). Contrato en `docs/openapi.yaml`.

## Arquitectura (hexagonal + DDD, ver ADR-001)

```
src/claims_settlement/
  domain/        entidades, objetos de valor y servicios de dominio puros (solo stdlib, sin E/S)
                 eligibility (R-005..R-011) | calculation (R-013..R-020) | outcome (R-023..R-025, R-036)
                 money (Decimal, R-022) | parameters (por tenant, R-003) | observations (R-034)
  application/   casos de uso (SettleClaim, SettleOneClaim, ProcessBatch), batch_summary y ports.py
  adapters/
    inbound/     batch (archivos '|') y http_api
    outbound/    repositorios en memoria por tenant, auditoria autonoma, usuario de proceso
  shared/        masking.py (mask_id, mask_name)
  bootstrap.py   raiz de composicion
```

- **Multitenant** (ADR-003): `tenant_id` es el primer parametro de todo puerto y caso de uso; parametros,
  topes y datos son por tenant (`X-Tenant-ID` en HTTP, `--tenant` en batch). TENANT_B demuestra otra
  configuracion (denuncia 15 dias, retencion 5 %).
- **Seguridad**: sin secretos en codigo; configuracion por variables de entorno (`CLAIMS_PROCESS_USER`,
  `CLAIMS_DATA_DIR`, `CLAIMS_OUT_DIR`, `CLAIMS_HTTP_HOST`, `CLAIMS_HTTP_PORT`); identificadores enmascarados con
  `mask_*` en logs y mensajes.
- **Trazabilidad**: cada regla implementada deja `REGLA: R-0xx` en el codigo y en el docstring de una prueba;
  la compuerta genera `docs/matriz_trazabilidad.md`.

## Formato batch

Entrada por tenant en `examples/<TENANT>/`: `clientes.dat`, `polizas.dat`, `coberturas.dat`,
`siniestros.dat`, `liquidaciones.dat` (historico) y `parametros.dat`; campos separados por `|`, `#` comenta.
Salida `liquidaciones.out`: `id|siniestro|fecha|reclamado|base|deducible|cubierto|retencion|neto|estado|motivo|observaciones|usuario`,
importes sin signo con dos decimales. Entradas invalidas (negativos, 3 decimales, fecha inexistente, dominios)
se rechazan con codigo de salida 2 y mensaje con archivo y linea (ADR-007).

## Decisiones (docs/adr/)

| ADR | Tema |
|---|---|
| 001 | Arquitectura hexagonal + DDD |
| 002 | Dinero con Decimal y orden de redondeo |
| 003 | Multitenancy |
| 004 | Codigo muerto no portado (R-037, R-038, R-039, R-040, R-042, R-043, R-045) |
| 005 | Mejoras del PO: R-036, R-041 |
| 006 | Errores, parametros ausentes o NULL (decidida por defecto) |
| 007 | Formato batch y entradas invalidas (decidida por defecto) |
| 008 | Auditoria autonoma, savepoint y commit unico |
| 009 | Fechas y limites inclusivos/estrictos |
| 010 | Reglas bloqueadas (ninguna) |
