# Informe de verificación — 2026-11-13

## Veredicto

**EQUIVALENTE POR LECTURA (no demostrado por ejecucion del legacy)**

| Control | Resultado |
|---|---|
| Reglas cumplidas (código + prueba que pasa) | 34 de 34 |
| Reglas no portadas y documentadas | 0 |
| Reglas con incumplimiento | 0 |
| Pruebas del proyecto | todas pasan (81 casos) |
| Código implementado sin regla | 40 elementos (0 sin clasificar) |
| Reglas rechazadas pero implementadas | 0 |
| Escenarios de equivalencia | 85: 85 iguales, 0 diferencias esperadas, 0 no esperadas |

## 1. Qué interpreto del legacy

- Sistema SIGSE, modulo de siniestros (Oracle PL/SQL: 01_ddl_tablas.sql, 02_parametros.sql, 03 spec y 04 body del paquete PKG_LIQUIDACION_SINIESTROS, datos_prueba.sql, ejecutar_lote.sql). Evalua cada siniestro REGISTRADO, calcula la indemnizacion y lo deja LIQUIDADO, RECHAZADO o PENDIENTE_REVISION (04_body:327-617).
- Un siniestro solo se liquida si esta REGISTRADO; se lee con bloqueo de fila y, si tiene otro estado, se lanza ORA-20001 sin escribir nada (04_body:361-370). Si faltan siniestro, poliza o cliente se propaga NO_DATA_FOUND (04_body:372-373).
- Los parametros de negocio se leen al usarse; si el codigo no existe se lanza ORA-20010 (04_body:98-112). Ademas FACTOR_INFLACION se lee al inicio sin usarse: si falta, todo siniestro falla antes de cualquier validacion (04_body:375).
- Validaciones de procedencia, en este orden y cortando en el primer fallo, cada una con RETURN tras registrar un rechazo con importes en cero: poliza no VIGENTE (386), ocurrencia fuera de [inicio, fin] ambos inclusive y sin TRUNC (395-396), denuncia tardia si dias calendario > 30 (365 en VIDA) con el dia limite aceptado (407-415), cobertura no contratada (423-433), carencia si dias desde inicio < dias de carencia (440-442), mora si prima pendiente > 0 salvo VIP con deuda <= 500 que continua con marca (451-462).
- Calculo en orden: monto base = menor entre reclamado y limite de cobertura, con marca solo si reclamado > limite (487-492); deducible FIJO tal cual o porcentual sobre el monto base con minimo de 100 y marca (189-199); descuento VIP del 50% sobre el deducible > 0, aplicado despues del minimo (201-205); cubierto = ROUND((base - deducible) * % cobertura / 100, 2) y rechazo BAJO_DEDUCIBLE si <= 0 (503-508).
- Penalizacion del 10% al cubierto si la poliza tiene 3 o mas otros siniestros LIQUIDADOS con ocurrencia en [ocurrencia - 365, ocurrencia) (521-533). Suma asegurada remanente = suma asegurada - cubiertos de liquidaciones APROBADA o PENDIENTE de la poliza: sin remanente se rechaza, si el cubierto lo excede se topa (541-558).
- Retencion de 2% sobre todo el cubierto si el ramo no es VIDA y el cubierto > 10000 (estricto); neto = cubierto - retencion (565-574). Estado final: alerta de fraude (ocurrencia a <= 15 dias del inicio y RECLAMADO >= 80% del limite) gana a tope; si no, neto > 50000 queda PENDIENTE_APROBACION; si no, APROBADA (586-599).
- Cada importe porcentual se redondea de inmediato a 2 decimales con ROUND mitad hacia arriba (cabecera 48-52, 193, 203, 503, 531, 568, 586).
- El resultado se guarda en LS_LIQUIDACIONES con la fecha de proceso recibida (no SYSDATE), importes, estado, motivo y marcas separadas por ';'; el siniestro pasa a LIQUIDADO/RECHAZADO/PENDIENTE_REVISION segun el estado (272-295). Cada resultado escribe un log INFO por transaccion autonoma (81-91, 293-295).
- El lote toma los siniestros REGISTRADO con denuncia <= fecha de corte (inclusive) por siniestro_id ascendente; cada uno va tras un SAVEPOINT: ante cualquier error se deshace ese siniestro, se cuenta como error y se registra en bitacora, y el lote sigue (625-676). Los liquidados antes en el lote afectan siniestralidad y suma asegurada de los siguientes porque se lee de las tablas. Hace un unico COMMIT al final, escribe INFO de inicio y fin y un resumen por DBMS_OUTPUT con procesados, liquidados, rechazados, pendientes, errores y total neto aprobado; solo el neto de los APROBADOS suma al total (642-696).
- Codigo que no se ejecuta o no influye: fn_es_dia_habil, fn_calcular_deducible_v1, fn_calcular_iva, pr_recalcular_reserva_tecnica (nunca invocadas), el WARN para polizas SUSPENDIDAS (inalcanzable tras el rechazo previo), la comprobacion cubierto < 0 con e_monto_invalido (inalcanzable), el bloque comentado SIN-0001, pr_enviar_notificacion y la traza DEBUG (c_modo_debug = FALSE). El legacy no usa TASA_IVA, VERSION_MOTOR ni la categoria PREFERENTE.
- Datos sensibles en el legacy: nombre de clientes y numeros de documento (01_ddl:29-30, datos_prueba:15-19); la traza DEBUG apagada imprimiria el nombre (04_body:377-381). Se citan aqui sin esos valores; los escenarios usan nombres ficticios o iniciales.

Archivos legacy encontrados: ._01_ddl_tablas.sql, ._02_parametros.sql, ._03_pkg_liquidacion_siniestros_spec.sql, ._04_pkg_liquidacion_siniestros_body.sql, ._datos_prueba.sql, ._ejecutar_lote.sql, 01_ddl_tablas.sql, 02_parametros.sql, 03_pkg_liquidacion_siniestros_spec.sql, 04_pkg_liquidacion_siniestros_body.sql, datos_prueba.sql, ejecutar_lote.sql

## 2. Reglas de negocio contra el código nuevo

| Regla | Categoría | Origen | Estado | Pruebas |
|---|---|---|---|---|
| R-001 | error | legacy | CUMPLIDA | 1 |
| R-002 | error | legacy | CUMPLIDA | 1 |
| R-003 | error | legacy | CUMPLIDA | 3 |
| R-004 | validacion | legacy | CUMPLIDA | 3 |
| R-005 | validacion | legacy | CUMPLIDA | 1 |
| R-006 | fechas | legacy | CUMPLIDA | 1 |
| R-007 | fechas | legacy | CUMPLIDA | 3 |
| R-008 | validacion | legacy | CUMPLIDA | 1 |
| R-009 | fechas | legacy | CUMPLIDA | 1 |
| R-010 | validacion | legacy | CUMPLIDA | 4 |
| R-011 | orden | legacy | CUMPLIDA | 3 |
| R-012 | efecto_secundario | legacy | CUMPLIDA | 3 |
| R-013 | calculo | legacy | CUMPLIDA | 1 |
| R-014 | calculo | legacy | CUMPLIDA | 3 |
| R-015 | calculo | legacy | CUMPLIDA | 2 |
| R-016 | calculo | legacy | CUMPLIDA | 2 |
| R-017 | calculo | legacy | CUMPLIDA | 2 |
| R-018 | calculo | legacy | CUMPLIDA | 3 |
| R-019 | calculo | legacy | CUMPLIDA | 3 |
| R-020 | calculo | legacy | CUMPLIDA | 2 |
| R-021 | orden | legacy | CUMPLIDA | 1 |
| R-022 | redondeo | legacy | CUMPLIDA | 2 |
| R-023 | validacion | legacy | CUMPLIDA | 4 |
| R-024 | orden | legacy | CUMPLIDA | 2 |
| R-025 | efecto_secundario | legacy | CUMPLIDA | 2 |
| R-026 | efecto_secundario | legacy | CUMPLIDA | 2 |
| R-027 | efecto_secundario | legacy | CUMPLIDA | 1 |
| R-028 | orden | legacy | CUMPLIDA | 2 |
| R-029 | error | legacy | CUMPLIDA | 3 |
| R-030 | calculo | legacy | CUMPLIDA | 2 |
| R-031 | efecto_secundario | legacy | CUMPLIDA | 3 |
| R-032 | fechas | legacy | CUMPLIDA | 2 |
| R-036 | efecto_secundario | po_mejorada | CUMPLIDA | 2 |
| R-041 | efecto_secundario | po_mejorada | CUMPLIDA | 2 |

## 3. Implementado sin regla de origen

| Elemento | Archivo | Clasificación | Justificación |
|---|---|---|---|
| domain/dates.py::as_datetime | domain\dates.py:7 | tecnico necesario | Normaliza date/datetime del adaptador de entrada a datetime; no decide nada de negocio. Es la base tecnica de las comparaciones sin TRUNC de R-006. |
| domain/dates.py::trunc | domain\dates.py:16 | tecnico necesario | Equivale a TRUNC(fecha) de Oracle, usado por day_diff en R-007 y R-009; sin comportamiento propio. |
| domain/dates.py::day_diff | domain\dates.py:21 | tecnico necesario | Diferencia de dias calendario TRUNC(a)-TRUNC(b); ayuda tecnica de los calculos de R-007, R-009 y R-023, sin regla propia. |
| domain/dates.py::minus_days | domain\dates.py:26 | tecnico necesario | Resta dias a una fecha para fijar el inicio de la ventana de 365 dias de R-018; aritmetica de fechas sin criterio de negocio. |
| domain/eligibility.py::EligibilityContext | domain\eligibility.py:13 | tecnico necesario | Contenedor de datos (siniestro, poliza, cliente, cobertura, parametros) que se pasa a las validaciones; sin logica. |
| domain/eligibility.py::Verdict | domain\eligibility.py:24 | tecnico necesario | Objeto de valor que transporta motivo de rechazo y marcas de cada validacion; sin logica propia. |
| domain/eligibility.py::days_since_start | domain\eligibility.py:34 | tecnico necesario | Calcula TRUNC(ocurrencia)-TRUNC(inicio) que consumen R-009 y R-023 (legacy 04_body:440); es la variable v_dias_desde_inicio, no una regla nueva. |
| domain/enums.py::CodeEnum | domain\enums.py:7 | tecnico necesario | Clase base de enumeraciones con parseo estricto del dominio de valores (R-004); infraestructura de validacion. |
| domain/enums.py::CustomerCategory | domain\enums.py:22 | tecnico necesario | Vocabulario de categorias de cliente del CHECK de la base (R-004); PREFERENTE se acepta sin beneficio, sin comportamiento nuevo. |
| domain/enums.py::Branch | domain\enums.py:28 | tecnico necesario | Vocabulario de ramos del CHECK de la base; no agrega comportamiento. |
| domain/enums.py::PolicyStatus | domain\enums.py:35 | tecnico necesario | Vocabulario de estados de poliza del CHECK de la base; no agrega comportamiento. |
| domain/enums.py::DeductibleType | domain\enums.py:41 | tecnico necesario | Vocabulario de tipos de deducible del CHECK de la base; no agrega comportamiento. |
| domain/enums.py::ClaimStatus | domain\enums.py:46 | tecnico necesario | Vocabulario de estados de siniestro del CHECK de la base; no agrega comportamiento. |
| domain/enums.py::SettlementStatus | domain\enums.py:53 | tecnico necesario | Vocabulario de estados de liquidacion del CHECK de la base; no agrega comportamiento. |
| domain/enums.py::Reason | domain\enums.py:59 | tecnico necesario | Catalogo de codigos de motivo documentados en la cabecera del paquete legacy (04_body:29-41); solo nombres. |
| domain/enums.py::Mark | domain\enums.py:75 | tecnico necesario | Catalogo de marcas de observacion documentadas en la cabecera del paquete legacy (04_body:43-46); solo nombres. |
| domain/errors.py::DomainError | domain\errors.py:5 | tecnico necesario | Excepcion base con codigo simbolico; infraestructura de errores que enmascara identificadores. |
| domain/errors.py::ClaimNotRegisteredError | domain\errors.py:14 | tecnico necesario | Representa ORA-20001 de R-001; clase de error, la decision esta en ensure_registered. |
| domain/errors.py::ParameterNotDefinedError | domain\errors.py:24 | tecnico necesario | Representa ORA-20010 de R-003; clase de error. |
| domain/errors.py::ParameterNullError | domain\errors.py:33 | tecnico necesario | Error explicito cuando un parametro con NULL se usa en un calculo: decision tecnica por defecto documentada en ADR-006 (R-003); en el legacy una comparacion con NULL no se cumpliria. Solo se alcanza con parametros NULL, que en los datos legacy solo ocurre en VERSION_MOTOR, no usado. Se anota como observacion. |
| domain/errors.py::EntityNotFoundError | domain\errors.py:42 | tecnico necesario | Representa NO_DATA_FOUND de R-002; clase de error con id enmascarado. |
| domain/errors.py::UnknownSettlementStatusError | domain\errors.py:51 | tecnico necesario | Error de la mejora PO R-036 (estado de liquidacion desconocido); la regla si esta respaldada, falta solo el marcador en la clase. |
| domain/errors.py::InvalidValueError | domain\errors.py:60 | tecnico necesario | Error de validacion de entradas (CHECK de la base, tipos); infraestructura de R-004. |
| domain/errors.py::ObservationsOverflowError | domain\errors.py:69 | tecnico necesario | Hace explicito el limite VARCHAR2(400) de las observaciones (R-034); el legacy fallaria en Oracle al insertar, aqui es un error de dominio. |
| domain/errors.py::StorageConflictError | domain\errors.py:78 | tecnico necesario | Conflicto de clave unica en el repositorio en memoria; equivale a ORA-00001; infraestructura de persistencia. |
| domain/errors.py::TenantNotFoundError | domain\errors.py:87 | tecnico necesario | Error de multitenancy (ADR-003): el tenant no existe. Es un requisito de arquitectura, no de negocio. |
| domain/model.py::Customer | domain\model.py:18 | tecnico necesario | Entidad inmutable de datos del cliente (LS_CLIENTES) con validacion de categoria; sin logica de negocio. |
| domain/model.py::Policy | domain\model.py:30 | tecnico necesario | Entidad inmutable de datos de la poliza (LS_POLIZAS) con validacion de dominios y conversion decimal; sin logica de negocio. |
| domain/model.py::Coverage | domain\model.py:57 | tecnico necesario | Entidad inmutable de la cobertura (LS_COBERTURAS); sin logica de negocio. |
| domain/model.py::Claim | domain\model.py:72 | tecnico necesario | Entidad inmutable del siniestro (LS_SINIESTROS); sin logica de negocio. |
| domain/model.py::Settlement | domain\model.py:91 | tecnico necesario | Entidad inmutable de la liquidacion (LS_LIQUIDACIONES) registrada por R-026; sin logica de negocio. |
| domain/model.py::Amounts | domain\model.py:110 | tecnico necesario | Objeto de valor con base, deducible, cubierto, retencion y neto; transporta importes ya calculados por otras reglas. |
| domain/money.py::to_decimal | domain\money.py:13 | tecnico necesario | Convierte a Decimal y rechaza coma flotante (ADR-002); asegura precision monetaria, no agrega regla. |
| domain/money.py::subtract | domain\money.py:38 | tecnico necesario | Resta con el contexto de alta precision, usada en R-017 y R-019; aritmetica sin criterio de negocio. |
| domain/money.py::format_amount | domain\money.py:42 | tecnico necesario | Formato de salida del neto, equivalente a TO_CHAR(..., 'FM999999990.00') del log (04_body:295); solo presentacion. |
| application/process_batch.py::BatchSummary | application\process_batch.py:17 | tecnico necesario | Objeto de valor con los contadores del resumen del lote (R-030, R-035); sin logica. |
| application/process_batch.py::describe_error | application\process_batch.py:42 | tecnico necesario | Arma el mensaje seguro para la bitacora de errores sin filtrar datos internos; enmascaramiento, no negocio. |
| application/process_batch.py::format_process_date | application\process_batch.py:49 | tecnico necesario | Formatea la fecha YYYY-MM-DD del mensaje de inicio del lote (04_body:642-643); solo formato. |
| application/process_batch.py::SettleOneClaim | application\process_batch.py:113 | tecnico necesario | Adaptador transaccional que hace savepoint/commit alrededor de SettleClaim para exponer la liquidacion individual (la spec dice que el llamador controla el COMMIT, 03_spec:47). Hace commit al terminar bien y rollback si falla: es decision de la arquitectura hexagonal, sin regla de negocio nueva. Se anota como observacion. |
| application/tenant.py::validate_tenant_id | application\tenant.py:9 | tecnico necesario | Valida el formato del identificador de tenant para rutas y logs (ADR-003); seguridad de entrada, sin comportamiento de negocio. |

## 4. ¿Hace lo mismo que el código viejo?

| Escenario | Regla | Fuente del esperado | Estado |
|---|---|---|---|
| E01 | R-001 | lectura_codigo | IGUAL |
| E02 | R-001 | lectura_codigo | IGUAL |
| E03 | R-002 | lectura_codigo | IGUAL |
| E04 | R-002 | lectura_codigo | IGUAL |
| E05 | R-003 | lectura_codigo | IGUAL |
| E06 | R-003 | lectura_codigo | IGUAL |
| E07 | R-004 | lectura_codigo | IGUAL |
| E08 | R-004 | lectura_codigo | IGUAL |
| E09 | R-005 | lectura_codigo | IGUAL |
| E10 | R-005 | lectura_codigo | IGUAL |
| E11 | R-006 | lectura_codigo | IGUAL |
| E12 | R-006 | lectura_codigo | IGUAL |
| E13 | R-006 | lectura_codigo | IGUAL |
| E14 | R-006 | lectura_codigo | IGUAL |
| E15 | R-007 | lectura_codigo | IGUAL |
| E16 | R-007 | lectura_codigo | IGUAL |
| E17 | R-007 | lectura_codigo | IGUAL |
| E18 | R-007 | lectura_codigo | IGUAL |
| E19 | R-008 | lectura_codigo | IGUAL |
| E20 | R-009 | lectura_codigo | IGUAL |
| E21 | R-009 | lectura_codigo | IGUAL |
| E22 | R-010 | lectura_codigo | IGUAL |
| E23 | R-010 | lectura_codigo | IGUAL |
| E24 | R-010 | lectura_codigo | IGUAL |
| E25 | R-011 | lectura_codigo | IGUAL |
| E26 | R-011 | lectura_codigo | IGUAL |
| E27 | R-011 | lectura_codigo | IGUAL |
| E28 | R-011 | lectura_codigo | IGUAL |
| E29 | R-012 | lectura_codigo | IGUAL |
| E30 | R-013 | lectura_codigo | IGUAL |
| E31 | R-013 | lectura_codigo | IGUAL |
| E32 | R-014 | lectura_codigo | IGUAL |
| E33 | R-014 | lectura_codigo | IGUAL |
| E34 | R-014 | lectura_codigo | IGUAL |
| E35 | R-014 | lectura_codigo | IGUAL |
| E36 | R-015 | lectura_codigo | IGUAL |
| E37 | R-015 | lectura_codigo | IGUAL |
| E38 | R-015 | lectura_codigo | IGUAL |
| E39 | R-016 | lectura_codigo | IGUAL |
| E40 | R-016 | lectura_codigo | IGUAL |
| E41 | R-016 | lectura_codigo | IGUAL |
| E42 | R-017 | lectura_codigo | IGUAL |
| E43 | R-017 | lectura_codigo | IGUAL |
| E44 | R-017 | lectura_codigo | IGUAL |
| E45 | R-017 | lectura_codigo | IGUAL |
| E46 | R-018 | lectura_codigo | IGUAL |
| E47 | R-018 | lectura_codigo | IGUAL |
| E48 | R-018 | lectura_codigo | IGUAL |
| E49 | R-018 | lectura_codigo | IGUAL |
| E50 | R-018 | lectura_codigo | IGUAL |
| E51 | R-018 | lectura_codigo | IGUAL |
| E52 | R-019 | lectura_codigo | IGUAL |
| E53 | R-019 | lectura_codigo | IGUAL |
| E54 | R-019 | lectura_codigo | IGUAL |
| E55 | R-019 | lectura_codigo | IGUAL |
| E56 | R-019 | lectura_codigo | IGUAL |
| E57 | R-020 | lectura_codigo | IGUAL |
| E58 | R-020 | lectura_codigo | IGUAL |
| E59 | R-020 | lectura_codigo | IGUAL |
| E60 | R-021 | lectura_codigo | IGUAL |
| E61 | R-022 | lectura_codigo | IGUAL |
| E62 | R-022 | lectura_codigo | IGUAL |
| E63 | R-023 | lectura_codigo | IGUAL |
| E64 | R-023 | lectura_codigo | IGUAL |
| E65 | R-023 | lectura_codigo | IGUAL |
| E66 | R-023 | lectura_codigo | IGUAL |
| E67 | R-024 | lectura_codigo | IGUAL |
| E68 | R-024 | lectura_codigo | IGUAL |
| E69 | R-024 | lectura_codigo | IGUAL |
| E70 | R-025 | lectura_codigo | IGUAL |
| E71 | R-026 | lectura_codigo | IGUAL |
| E72 | R-032 | lectura_codigo | IGUAL |
| E73 | R-032 | lectura_codigo | IGUAL |
| E74 | R-027 | lectura_codigo | IGUAL |
| E75 | R-028 | lectura_codigo | IGUAL |
| E76 | R-028 | lectura_codigo | IGUAL |
| E77 | R-028 | lectura_codigo | IGUAL |
| E78 | R-030 | lectura_codigo | IGUAL |
| E79 | R-019 | lectura_codigo | IGUAL |
| E80 | R-018 | lectura_codigo | IGUAL |
| E81 | R-029 | lectura_codigo | IGUAL |
| E82 | R-031 | lectura_codigo | IGUAL |
| E83 | R-030 | lectura_codigo | IGUAL |
| E84 | R-036 | lectura_codigo | IGUAL |
| E85 | R-036 | lectura_codigo | IGUAL |

### Nivel de evidencia

- *Ejecución del legacy o golden master entregado*: demuestra equivalencia en esos escenarios.
- *Lectura del código*: indica equivalencia, pero no la demuestra.
- La equivalencia aplica solo a los escenarios listados; no es una prueba exhaustiva.

## 5. Observaciones

- Nivel de evidencia: TODOS los esperados salen de la LECTURA del codigo PL/SQL legacy con cita de archivo y linea (fuente_esperado = lectura_codigo). En este entorno no se pudo ejecutar el legacy ni se recibio golden master, asi que la equivalencia es POR LECTURA y no esta demostrada por ejecucion.
- La equivalencia aplica solo a los 85 escenarios probados (liquidacion individual y lote) y no es prueba exhaustiva; quedan sin probar combinaciones masivas, fechas con componente hora, valores de NUMBER fuera de 2 decimales y desborde de observaciones.
- Criterio de comparacion de importes: el harness normaliza cada importe a texto con exactamente 2 decimales (mitad hacia arriba), equivalente a NUMBER(14,2) de Oracle; en el codigo nuevo un Decimal de entrada sin decimales (p. ej. 1000) se muestra como 1000, y esa diferencia es solo de representacion, no de valor.
- Control de sensibilidad (no forma parte del informe automatico): se aplicaron en una copia 9 mutaciones de borde (> por >=, < por <=, y viceversa) en R-007, R-009, R-013, R-015, R-018, R-019, R-020, R-023 y R-024 y los escenarios detectaron las 9, lo que indica que los casos de borde discriminan. La copia no modifica el proyecto entregado.
- Errores propios corregidos durante la verificacion (no del codigo nuevo): dos escenarios (E13, E14) declaraban mal la fecha de liquidacion esperada, que el legacy toma del parametro de proceso (04_body:277); un escenario de lote (E76) usaba un plazo de denuncia de 49 dias que el legacy tambien rechazaria; y los esperados de lote se completaron con commits, bitacora y liquidaciones. En ninguno se ajusto un esperado para igualar la salida del codigo nuevo: se re-derivo del legacy.
- Reglas tecnicas de codigo muerto o inalcanzable (R-037 a R-040, R-042, R-043, R-045) no tienen escenario: no hay comportamiento observable. Se verifica por lectura que el codigo nuevo no las implementa (ADR-004). R-044 (FACTOR_INFLACION leido al inicio) si queda cubierta por el escenario E05.
- R-004: el legacy impone los dominios con CHECK de la base, no con codigo; el escenario E07 prueba que PREFERENTE no recibe beneficio y E08 es el caso feliz. La validacion de valores fuera de dominio (p. ej. categoria 'X') no tiene esperado legacy ejecutable por lectura de PL/SQL y no se prueba por escenario.
- R-036 y R-041 son mejoras del PO (po_mejorada) y reglas_limpias.json no declara diferencias_esperadas (lista vacia): ninguna de las dos cambia un resultado de los datos actuales, por lo que se prueba que el mapeo de estados sigue igual (E84, E85) y no se usa diferencia_esperada_de. La traza enmascarada de R-041 y el error por estado desconocido de R-036 solo son alcanzables con debug activo o con un estado imposible; estan cubiertos por las pruebas del propio proyecto y no por escenarios de equivalencia.
- Hallazgo menor, comportamiento adicional no pedido: ParameterNullError (ADR-006) hace fallar con error un calculo que usa un parametro con valor NULL; en el legacy una comparacion con NULL no se cumple y el flujo sigue en silencio (R-003, pregunta cerrada por el PO: se queda como viene). Solo afectaria a un parametro con NULL usado en un calculo; en los datos legacy el unico NULL es VERSION_MOTOR, que ninguna regla usa. No cambia ningun escenario probado, pero se reporta para decision del PO.
- SettleOneClaim hace COMMIT tras liquidar un siniestro individual, mientras el legacy pr_liquidar_siniestro NO hace COMMIT y deja el control al llamador (03_spec:47, R-027). El comportamiento nuevo vive en el adaptador transaccional (el dominio no hace commit), por lo que R-027 se cumple en SettleClaim; se reporta como diferencia de arquitectura a confirmar.
