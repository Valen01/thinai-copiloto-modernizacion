# ADR-001: Arquitectura hexagonal + DDD

## Estado
Aceptada.

## Contexto
El legacy es un paquete PL/SQL (`PKG_LIQUIDACION_SINIESTROS`) donde reglas de negocio, acceso a datos
(SELECT/INSERT/UPDATE), transacciones (SAVEPOINT/COMMIT), bitacora autonoma y salida (`DBMS_OUTPUT`) viven en
los mismos procedimientos. Eso impide probar las reglas sin base de datos y dificulta el multitenant.

## Decision
Se adopta arquitectura hexagonal con lenguaje ubicuo del glosario del Extractor (Claim/siniestro, Policy,
Coverage, Customer, Settlement/liquidacion, Observations):

- `domain/`: entidades y objetos de valor inmutables (`@dataclass(frozen=True)`) y servicios de dominio puros,
  uno por responsabilidad: `eligibility` (validaciones de procedencia, R-005 a R-011), `calculation`
  (importes, R-013 a R-020), `outcome` (estado final, fraude y correspondencia de estados, R-023 a R-025, R-036),
  `money` (Decimal y redondeo), `parameters` (parametros por tenant). Solo stdlib, sin E/S, sin `print()`.
- `application/`: casos de uso (`SettleClaim`, `SettleOneClaim`, `ProcessBatch`), `batch_summary` y `ports.py`
  (interfaces `Protocol`). Solo stdlib y el propio paquete.
- `adapters/inbound`: batch (archivos `|`) y HTTP (stdlib `http.server`).
- `adapters/outbound`: repositorios en memoria por tenant, bitacora autonoma y proveedor de usuario por entorno.
- `shared/masking.py`: `mask_id` y `mask_name` para logs y mensajes.
- `bootstrap.py`: raiz de composicion.

Las validaciones de procedencia se expresan como tabla de decision (`ELIGIBILITY_CHECKS`) para que el orden
(R-011) sea datos y no una cadena de `if`, manteniendo la complejidad ciclomatica <= 10.

## Consecuencias
- Las reglas se prueban sin base de datos ni red; los adaptadores se sustituyen (p. ej. Oracle real).
- El rollback por siniestro (R-029) se modela con el puerto `TransactionManager`, no con SQL.
- Un servicio HTTP stdlib simple evita dependencias, a costa de funciones de produccion (TLS, autenticacion)
  que quedan fuera de alcance y deben ponerse delante (gateway).

## Reglas relacionadas
R-005 a R-011, R-013 a R-020, R-021, R-023 a R-025, R-027, R-029, R-036.
