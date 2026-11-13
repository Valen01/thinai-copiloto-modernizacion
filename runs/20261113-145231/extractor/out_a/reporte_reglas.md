# Reporte de reglas — estado tras el dictamen

- Aprobadas: **0**
- Corregidas, requieren reaprobación: **0**
- Pendientes: **45**

Cada línea citada fue verificada automáticamente contra el código. «Aprobada» valida la extracción del comportamiento existente, no que sea un requisito de negocio deseable.

## Reglas de negocio (32)

| ID | Categoría | Confianza | Estado |
|---|---|---|---|
| R-001 | error | alta | pendiente |
| R-002 | error | alta | pendiente |
| R-003 | error | alta | pendiente |
| R-004 | validacion | alta | pendiente |
| R-005 | validacion | alta | pendiente |
| R-006 | fechas | media | pendiente |
| R-007 | fechas | alta | pendiente |
| R-008 | validacion | alta | pendiente |
| R-009 | fechas | alta | pendiente |
| R-010 | validacion | alta | pendiente |
| R-011 | orden | alta | pendiente |
| R-012 | efecto_secundario | alta | pendiente |
| R-013 | calculo | alta | pendiente |
| R-014 | calculo | alta | pendiente |
| R-015 | calculo | alta | pendiente |
| R-016 | calculo | alta | pendiente |
| R-017 | calculo | alta | pendiente |
| R-018 | calculo | alta | pendiente |
| R-019 | calculo | alta | pendiente |
| R-020 | calculo | alta | pendiente |
| R-021 | orden | alta | pendiente |
| R-022 | redondeo | alta | pendiente |
| R-023 | validacion | alta | pendiente |
| R-024 | orden | alta | pendiente |
| R-025 | efecto_secundario | alta | pendiente |
| R-026 | efecto_secundario | alta | pendiente |
| R-027 | efecto_secundario | alta | pendiente |
| R-028 | orden | alta | pendiente |
| R-029 | error | alta | pendiente |
| R-030 | calculo | alta | pendiente |
| R-031 | efecto_secundario | alta | pendiente |
| R-032 | fechas | alta | pendiente |

## Hallazgos técnicos (13)

| ID | Categoría | Confianza | Estado |
|---|---|---|---|
| R-033 | efecto_secundario | alta | pendiente |
| R-034 | efecto_secundario | media | pendiente |
| R-035 | efecto_secundario | alta | pendiente |
| R-036 | efecto_secundario | media | pendiente |
| R-037 | calculo | alta | pendiente |
| R-038 | calculo | alta | pendiente |
| R-039 | calculo | alta | pendiente |
| R-040 | calculo | alta | pendiente |
| R-041 | efecto_secundario | alta | pendiente |
| R-042 | efecto_secundario | alta | pendiente |
| R-043 | validacion | alta | pendiente |
| R-044 | error | alta | pendiente |
| R-045 | calculo | alta | pendiente |

### R-001 — error (alta) · pendiente

Un siniestro solo se liquida si su estado es REGISTRADO. El siniestro se lee con bloqueo de fila (FOR UPDATE). Si el estado es otro, se lanza el error ORA-20001 con el id y el estado actual, y no se escribe nada.

- **Condición:** estado del siniestro distinto de REGISTRADO al inicio de pr_liquidar_siniestro
- **Acción:** RAISE_APPLICATION_ERROR -20001
- **Parámetros:** `{"codigo_error": -20001, "operador": "<>", "estado_esperado": "REGISTRADO"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 365: `FOR UPDATE;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 367: `IF v_sin.estado <> c_sin_registrado THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 368: `RAISE_APPLICATION_ERROR(-20001,`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 57: `PROCEDURE pr_liquidar_siniestro (`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 53: `ORA-20001 El siniestro no se encuentra en estado REGISTRADO.`
- **Preguntas para el dueño del negocio:**
  - ¿Se espera reprocesar siniestros PENDIENTE_REVISION tras la aprobacion manual? Hoy darian ORA-20001.

### R-002 — error (alta) · pendiente

Si el siniestro, la poliza o el cliente asociado no existen, el SELECT INTO no tiene manejador y la excepcion NO_DATA_FOUND se propaga al llamador (en el lote se cuenta como error). La unica excepcion NO_DATA_FOUND capturada dentro de pr_liquidar_siniestro es la de la cobertura.

- **Condición:** falta el registro de siniestro, poliza o cliente
- **Acción:** propaga NO_DATA_FOUND; no se registra liquidacion
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 372: `SELECT * INTO v_pol FROM ls_polizas`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 373: `SELECT * INTO v_cli FROM ls_clientes`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 55: `NO_DATA_FOUND El siniestro, la poliza o el cliente no existen.`
- **Comprobación de ausencia:** dentro de pr_liquidar_siniestro solo hay un manejador NO_DATA_FOUND (cobertura) (`04_pkg_liquidacion_siniestros_body.sql`, líneas 327-617, patrón `WHEN\s+NO_DATA_FOUND`: 1 coincidencias, esperado 1)

### R-003 — error (alta) · pendiente

Los parametros de negocio se leen de LS_PARAMETROS en el momento de usarse (lectura perezosa). Si el codigo no existe se lanza ORA-20010 'Parametro no definido'. Si existe con valor numerico NULL (p. ej. VERSION_MOTOR) no hay error y se devuelve NULL.

- **Condición:** cada llamada a fn_param_num
- **Acción:** devuelve valor_numerico o lanza ORA-20010
- **Parámetros:** `{"codigo_error": -20010}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 103: `SELECT valor_numerico`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 111: `RAISE_APPLICATION_ERROR(-20010, 'Parametro no definido: ' || p_cod_parametro);`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 54: `ORA-20010 Parametro de negocio inexistente en LS_PARAMETROS.`
  - `02_parametros.sql` línea 36: `('VERSION_MOTOR', NULL, '3.2.0'`
- **Preguntas para el dueño del negocio:**
  - ¿Un parametro con valor NULL debe tratarse como error? Hoy las comparaciones con NULL no se cumplen y el flujo sigue.

### R-004 — validacion (alta) · pendiente

Dominios de valores impuestos por la base: categoria de cliente (VIP, PREFERENTE, ESTANDAR), ramo (AUTO, HOGAR, SALUD, VIDA), estado de poliza, tipo de deducible (FIJO, PORCENTAJE), estado de siniestro y estado de liquidacion. El codigo solo da trato diferenciado a VIP; PREFERENTE no tiene ningun beneficio en el paquete.

- **Condición:** insercion/actualizacion de datos maestros
- **Acción:** CHECK de la tabla
- **Parámetros:** `{"categorias": ["VIP", "PREFERENTE", "ESTANDAR"]}`
- **Evidencia:**
  - `01_ddl_tablas.sql` línea 34: `CONSTRAINT ck_ls_cli_categoria CHECK (categoria IN ('VIP','PREFERENTE','ESTANDAR'))`
  - `01_ddl_tablas.sql` línea 59: `CONSTRAINT ck_ls_pol_ramo CHECK (ramo IN ('AUTO','HOGAR','SALUD','VIDA'))`
  - `01_ddl_tablas.sql` línea 60: `CONSTRAINT ck_ls_pol_estado CHECK (estado IN ('VIGENTE','CANCELADA','SUSPENDIDA'))`
  - `01_ddl_tablas.sql` línea 61: `CONSTRAINT ck_ls_pol_ded_tipo CHECK (deducible_tipo IN ('FIJO','PORCENTAJE'))`
  - `01_ddl_tablas.sql` línea 124: `CONSTRAINT ck_ls_liq_estado CHECK (estado IN ('APROBADA','RECHAZADA','PENDIENTE_APROBACION'))`
- **Comprobación de ausencia:** el paquete nunca menciona la categoria PREFERENTE (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `PREFERENTE`: 0 coincidencias, esperado 0)
- **Preguntas para el dueño del negocio:**
  - ¿La categoria PREFERENTE deberia tener beneficios?

### R-005 — validacion (alta) · pendiente

Solo se liquidan polizas VIGENTES. Cualquier otro estado (CANCELADA, SUSPENDIDA u otro) se rechaza con motivo POLIZA_NO_VIGENTE y se termina el proceso del siniestro.

- **Condición:** estado de poliza <> 'VIGENTE'
- **Acción:** pr_rechazar con POLIZA_NO_VIGENTE y RETURN
- **Parámetros:** `{"operador": "<>", "valor": "VIGENTE", "motivo": "POLIZA_NO_VIGENTE"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 64: `c_poliza_vigente CONSTANT VARCHAR2(12) := 'VIGENTE';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 386: `IF v_pol.estado <> c_poliza_vigente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 387: `pr_rechazar(v_sin, p_fecha_proceso, 'POLIZA_NO_VIGENTE');`

### R-006 — fechas (media) · pendiente

La fecha de ocurrencia debe estar dentro de [fecha_inicio, fecha_fin] de la poliza, ambos extremos inclusive. Se rechaza con FUERA_DE_VIGENCIA si es menor al inicio o mayor al fin. A diferencia del plazo de denuncia, estas comparaciones NO truncan las fechas (si hubiera componente hora podria afectar el borde; no probado por ejecucion).

- **Condición:** ocurrencia < fecha_inicio OR ocurrencia > fecha_fin
- **Acción:** pr_rechazar con FUERA_DE_VIGENCIA y RETURN
- **Parámetros:** `{"operadores": ["<", ">"], "motivo": "FUERA_DE_VIGENCIA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 395: `IF v_sin.fecha_ocurrencia < v_pol.fecha_inicio`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 396: `OR v_sin.fecha_ocurrencia > v_pol.fecha_fin`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 398: `pr_rechazar(v_sin, p_fecha_proceso, 'FUERA_DE_VIGENCIA');`
- **Comprobación de ausencia:** la validacion de vigencia no usa TRUNC (`04_pkg_liquidacion_siniestros_body.sql`, líneas 395-398, patrón `TRUNC`: 0 coincidencias, esperado 0)
- **Preguntas para el dueño del negocio:**
  - ¿Las fechas almacenan hora?

### R-007 — fechas (alta) · pendiente

Plazo de denuncia: dias = TRUNC(denuncia) - TRUNC(ocurrencia). El maximo es DIAS_MAX_DENUNCIA (30) para ramos generales y DIAS_MAX_DENUNCIA_VIDA (365) para VIDA. Se rechaza con DENUNCIA_EXTEMPORANEA solo si dias > maximo (estricto), de modo que el dia limite es aceptado.

- **Condición:** v_dias_denuncia > maximo segun ramo
- **Acción:** pr_rechazar con DENUNCIA_EXTEMPORANEA y RETURN
- **Parámetros:** `{"DIAS_MAX_DENUNCIA": 30, "DIAS_MAX_DENUNCIA_VIDA": 365, "operador": ">", "motivo": "DENUNCIA_EXTEMPORANEA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 407: `v_dias_denuncia := TRUNC(v_sin.fecha_denuncia) - TRUNC(v_sin.fecha_ocurrencia);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 409: `IF v_pol.ramo = c_ramo_vida THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 410: `v_dias_max_denuncia := fn_param_num('DIAS_MAX_DENUNCIA_VIDA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 412: `v_dias_max_denuncia := fn_param_num('DIAS_MAX_DENUNCIA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 415: `IF v_dias_denuncia > v_dias_max_denuncia THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 416: `pr_rechazar(v_sin, p_fecha_proceso, 'DENUNCIA_EXTEMPORANEA');`
  - `02_parametros.sql` línea 10: `('DIAS_MAX_DENUNCIA', 30, NULL`
  - `02_parametros.sql` línea 11: `('DIAS_MAX_DENUNCIA_VIDA', 365, NULL`
- **Preguntas para el dueño del negocio:**
  - ¿Los 30 dias son calendario o habiles? El codigo usa calendario.

### R-008 — validacion (alta) · pendiente

La cobertura reclamada debe existir en LS_COBERTURAS para la poliza (clave poliza + codigo de cobertura). Si no existe se rechaza con COBERTURA_NO_CONTRATADA.

- **Condición:** no hay fila de cobertura para poliza y cod_cobertura del siniestro
- **Acción:** pr_rechazar con COBERTURA_NO_CONTRATADA y RETURN
- **Parámetros:** `{"motivo": "COBERTURA_NO_CONTRATADA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 428: `AND cod_cobertura = v_sin.cod_cobertura;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 430: `WHEN NO_DATA_FOUND THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 431: `pr_rechazar(v_sin, p_fecha_proceso, 'COBERTURA_NO_CONTRATADA');`

### R-009 — fechas (alta) · pendiente

Periodo de carencia: dias_desde_inicio = TRUNC(ocurrencia) - TRUNC(fecha_inicio de la poliza). Se rechaza con EN_PERIODO_CARENCIA si dias_desde_inicio < dias_carencia de la cobertura (estricto): con exactamente dias_carencia dias la cobertura ya esta activa.

- **Condición:** dias_desde_inicio < dias_carencia
- **Acción:** pr_rechazar con EN_PERIODO_CARENCIA y RETURN
- **Parámetros:** `{"operador": "<", "motivo": "EN_PERIODO_CARENCIA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 440: `v_dias_desde_inicio := TRUNC(v_sin.fecha_ocurrencia) - TRUNC(v_pol.fecha_inicio);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 442: `IF v_dias_desde_inicio < v_cob.dias_carencia THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 443: `pr_rechazar(v_sin, p_fecha_proceso, 'EN_PERIODO_CARENCIA');`
  - `01_ddl_tablas.sql` línea 76: `dias_carencia NUMBER(4) DEFAULT 0 NOT NULL,`

### R-010 — validacion (alta) · pendiente

Morosidad: si la poliza tiene prima_pendiente > 0 se rechaza con PRIMA_EN_MORA, salvo que el cliente sea VIP y la deuda sea <= TOLERANCIA_MORA_VIP (500); en ese caso se continua y se agrega la marca TOLERANCIA_MORA_VIP a las observaciones. El parametro solo se lee si hay deuda. En el rechazo por mora las observaciones aun estan vacias (la marca solo se agrega en la rama de tolerancia).

- **Condición:** prima_pendiente > 0
- **Acción:** VIP con deuda <= 500: marca y continua; resto: rechazo PRIMA_EN_MORA
- **Parámetros:** `{"TOLERANCIA_MORA_VIP": 500, "operador_deuda": "<=", "operador_umbral": ">", "motivo": "PRIMA_EN_MORA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 451: `IF v_pol.prima_pendiente > 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 452: `v_tolerancia_mora := fn_param_num('TOLERANCIA_MORA_VIP');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 454: `IF v_cli.categoria = c_cat_vip`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 455: `AND v_pol.prima_pendiente <= v_tolerancia_mora`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 457: `pr_agregar_obs(v_observaciones, 'TOLERANCIA_MORA_VIP');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 459: `pr_rechazar(v_sin, p_fecha_proceso, 'PRIMA_EN_MORA', v_observaciones);`
  - `02_parametros.sql` línea 18: `('TOLERANCIA_MORA_VIP', 500, NULL`
- **Preguntas para el dueño del negocio:**
  - ¿La tolerancia VIP es por poliza o acumulada por cliente?

### R-011 — orden (alta) · pendiente

Orden de las validaciones de procedencia: 1) poliza vigente, 2) vigencia, 3) plazo de denuncia, 4) cobertura contratada, 5) carencia, 6) morosidad. El primer fallo gana: se registra el rechazo con ese motivo y se hace RETURN sin evaluar las siguientes.

- **Condición:** siempre, en cada liquidacion
- **Acción:** evalua en secuencia y corta en el primer rechazo
- **Parámetros:** `{"orden": ["POLIZA_NO_VIGENTE", "FUERA_DE_VIGENCIA", "DENUNCIA_EXTEMPORANEA", "COBERTURA_NO_CONTRATADA", "EN_PERIODO_CARENCIA", "PRIMA_EN_MORA"]}`
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 386: `IF v_pol.estado <> c_poliza_vigente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 395: `IF v_sin.fecha_ocurrencia < v_pol.fecha_inicio`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 415: `IF v_dias_denuncia > v_dias_max_denuncia THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 431: `pr_rechazar(v_sin, p_fecha_proceso, 'COBERTURA_NO_CONTRATADA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 442: `IF v_dias_desde_inicio < v_cob.dias_carencia THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 451: `IF v_pol.prima_pendiente > 0 THEN`

### R-012 — efecto_secundario (alta) · pendiente

Todo rechazo registra una liquidacion con monto base, deducible, cubierto, retencion y neto en cero, estado RECHAZADA y el motivo indicado; el siniestro pasa a RECHAZADO. Las observaciones son opcionales (por defecto NULL); solo BAJO_DEDUCIBLE, SUMA_ASEGURADA_AGOTADA y PRIMA_EN_MORA las pasan, y en ellas los importes calculados hasta ese punto NO se guardan (siempre cero).

- **Condición:** cualquier llamada a pr_rechazar
- **Acción:** inserta liquidacion con importes 0 y estado RECHAZADA
- **Parámetros:** `{"importes": 0, "estado": "RECHAZADA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 307: `p_observaciones IN VARCHAR2 DEFAULT NULL`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 313: `p_monto_base => 0,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 317: `p_neto => 0,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 318: `p_estado_liq => c_liq_rechazada,`
- **Preguntas para el dueño del negocio:**
  - ¿Debe guardarse el monto calculado en rechazos por BAJO_DEDUCIBLE o SUMA_ASEGURADA_AGOTADA?

### R-013 — calculo (alta) · pendiente

Monto base = menor entre lo reclamado y el limite de la cobertura. Solo si lo reclamado supera estrictamente el limite se usa el limite y se agrega la marca LIMITE_COBERTURA; si es igual no hay tope ni marca.

- **Condición:** monto_reclamado > limite_cobertura
- **Acción:** monto_base = limite_cobertura con marca; si no, monto_base = monto_reclamado
- **Parámetros:** `{"operador": ">", "marca": "LIMITE_COBERTURA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 487: `IF v_sin.monto_reclamado > v_cob.limite_cobertura THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 488: `v_monto_base := v_cob.limite_cobertura;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 489: `pr_agregar_obs(v_observaciones, 'LIMITE_COBERTURA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 491: `v_monto_base := v_sin.monto_reclamado;`

### R-014 — calculo (alta) · pendiente

Deducible: si el tipo de la poliza es FIJO se usa el valor tal cual (sin minimo); cualquier otro tipo (en la practica PORCENTAJE) se calcula como ROUND(monto_base * valor / 100, 2), sobre el MONTO BASE (ya topado) y no sobre lo reclamado.

- **Condición:** siempre tras el monto base
- **Acción:** calcula deducible via fn_calcular_deducible
- **Parámetros:** `{"base": "monto_base", "decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 497: `v_deducible := fn_calcular_deducible(v_pol, v_cli.categoria, v_monto_base, v_observaciones);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 189: `IF p_poliza.deducible_tipo = 'FIJO' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 190: `v_deducible := p_poliza.deducible_valor;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 193: `v_deducible := ROUND(p_monto_base * p_poliza.deducible_valor / 100, 2);`

### R-015 — calculo (alta) · pendiente

Deducible minimo: solo para deducible porcentual, si el calculado es < DEDUCIBLE_MINIMO (100) se sustituye por el minimo y se agrega la marca DEDUCIBLE_MINIMO. El minimo puede superar el monto base (resultara luego BAJO_DEDUCIBLE). El parametro solo se lee en la rama porcentual.

- **Condición:** deducible porcentual y deducible < DEDUCIBLE_MINIMO
- **Acción:** deducible = DEDUCIBLE_MINIMO con marca
- **Parámetros:** `{"DEDUCIBLE_MINIMO": 100, "operador": "<"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 192: `v_ded_minimo := fn_param_num('DEDUCIBLE_MINIMO');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 195: `IF v_deducible < v_ded_minimo THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 196: `v_deducible := v_ded_minimo;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 197: `pr_agregar_obs(p_observaciones, 'DEDUCIBLE_MINIMO');`
  - `02_parametros.sql` línea 14: `('DEDUCIBLE_MINIMO', 100, NULL`
- **Preguntas para el dueño del negocio:**
  - ¿El minimo debe aplicar tambien al deducible FIJO?

### R-016 — calculo (alta) · pendiente

Descuento VIP sobre el deducible: si el cliente es VIP y el deducible (ya con el minimo aplicado) es > 0, se reduce en PCT_DESCUENTO_DED_VIP (50) %: ROUND(deducible * (100 - pct) / 100, 2), con marca DESCUENTO_VIP. Aplica a deducibles FIJO y porcentuales y se aplica DESPUES del minimo.

- **Condición:** categoria = VIP y deducible > 0
- **Acción:** deducible = ROUND(deducible*(100-50)/100, 2)
- **Parámetros:** `{"PCT_DESCUENTO_DED_VIP": 50, "operador": ">", "marca": "DESCUENTO_VIP"}`
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 62: `c_cat_vip CONSTANT VARCHAR2(15) := 'VIP';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 196: `v_deducible := v_ded_minimo;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 201: `IF p_categoria_cli = c_cat_vip AND v_deducible > 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 202: `v_pct_desc_vip := fn_param_num('PCT_DESCUENTO_DED_VIP');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 203: `v_deducible := ROUND(v_deducible * (100 - v_pct_desc_vip) / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 204: `pr_agregar_obs(p_observaciones, 'DESCUENTO_VIP');`
  - `02_parametros.sql` línea 15: `('PCT_DESCUENTO_DED_VIP', 50, NULL`

### R-017 — calculo (alta) · pendiente

Monto cubierto = ROUND((monto_base - deducible) * porcentaje_cobertura / 100, 2). Si el resultado es <= 0 se rechaza con BAJO_DEDUCIBLE (el cero tambien rechaza), conservando las marcas de observacion acumuladas.

- **Condición:** siempre tras el deducible
- **Acción:** calcula cubierto; si <= 0 rechaza BAJO_DEDUCIBLE
- **Parámetros:** `{"operador": "<=", "valor": 0, "motivo": "BAJO_DEDUCIBLE", "decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 503: `v_cubierto := ROUND((v_monto_base - v_deducible) * v_cob.porcentaje_cobertura / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 505: `IF v_cubierto <= 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 506: `pr_rechazar(v_sin, p_fecha_proceso, 'BAJO_DEDUCIBLE', v_observaciones);`

### R-018 — calculo (alta) · pendiente

Penalizacion por siniestralidad: se cuentan los OTROS siniestros de la misma poliza (cualquier cobertura) en estado LIQUIDADO con fecha_ocurrencia en [ocurrencia_actual - 365, ocurrencia_actual) (limite inferior inclusive, superior exclusivo). Si la cuenta es >= MAX_SINIESTROS_ANUAL (3), el cubierto se reduce en PCT_PENALIZACION_SINIEST (10) %: ROUND(cubierto*(100-10)/100, 2), con marca PENALIZACION_SINIESTRALIDAD. Solo cuenta el estado LIQUIDADO del siniestro (no PENDIENTE_REVISION); siniestros liquidados antes en el mismo lote cuentan porque la cuenta lee la tabla.

- **Condición:** cantidad >= 3
- **Acción:** reduce monto cubierto 10 %
- **Parámetros:** `{"MAX_SINIESTROS_ANUAL": 3, "PCT_PENALIZACION_SINIEST": 10, "ventana_dias": 365, "operador": ">="}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 525: `AND s.siniestro_id <> v_sin.siniestro_id`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 526: `AND s.estado = c_sin_liquidado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 527: `AND s.fecha_ocurrencia >= v_sin.fecha_ocurrencia - 365`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 528: `AND s.fecha_ocurrencia < v_sin.fecha_ocurrencia;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 530: `IF v_cant_siniestros >= fn_param_num('MAX_SINIESTROS_ANUAL') THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 531: `v_cubierto := ROUND(v_cubierto * (100 - fn_param_num('PCT_PENALIZACION_SINIEST')) / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 532: `pr_agregar_obs(v_observaciones, 'PENALIZACION_SINIESTRALIDAD');`
  - `02_parametros.sql` línea 21: `('MAX_SINIESTROS_ANUAL', 3, NULL`
  - `02_parametros.sql` línea 22: `('PCT_PENALIZACION_SINIEST', 10, NULL`
- **Preguntas para el dueño del negocio:**
  - ¿La ventana de 365 dias debe ser por cobertura o por poliza (hoy por poliza)?

### R-019 — calculo (alta) · pendiente

Suma asegurada remanente = suma_asegurada - suma de monto_cubierto de TODAS las liquidaciones APROBADA o PENDIENTE_APROBACION de la poliza (sin filtro de fechas; monto cubierto antes de retencion). Si remanente <= 0 se rechaza con SUMA_ASEGURADA_AGOTADA (con las observaciones acumuladas). Si el cubierto (ya penalizado) excede el remanente se topa al remanente con marca TOPE_SUMA_ASEGURADA.

- **Condición:** siempre tras la penalizacion
- **Acción:** rechaza si remanente <= 0; topa cubierto si cubierto > remanente
- **Parámetros:** `{"operador_rechazo": "<=", "operador_tope": ">", "estados_sumados": ["APROBADA", "PENDIENTE_APROBACION"]}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 541: `SELECT NVL(SUM(l.monto_cubierto), 0)`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 546: `AND l.estado IN (c_liq_aprobada, c_liq_pend_aprob);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 548: `v_suma_remanente := v_pol.suma_asegurada - v_total_indemnizado;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 550: `IF v_suma_remanente <= 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 551: `pr_rechazar(v_sin, p_fecha_proceso, 'SUMA_ASEGURADA_AGOTADA', v_observaciones);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 555: `IF v_cubierto > v_suma_remanente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 556: `v_cubierto := v_suma_remanente;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 557: `pr_agregar_obs(v_observaciones, 'TOPE_SUMA_ASEGURADA');`
- **Preguntas para el dueño del negocio:**
  - ¿La suma asegurada es por evento, por vigencia o total de la poliza (hoy: acumulado de toda la historia)?

### R-020 — calculo (alta) · pendiente

Retencion impositiva: si el ramo no es VIDA y el cubierto final (tras penalizacion y tope de suma asegurada) es > UMBRAL_RETENCION (10000, estricto), la retencion es ROUND(cubierto * TASA_RETENCION (2) / 100, 2) sobre todo el cubierto, con marca RETENCION_APLICADA; si no, 0. Neto = cubierto - retencion.

- **Condición:** ramo <> VIDA y cubierto > 10000
- **Acción:** retencion 2 % del cubierto; neto = cubierto - retencion
- **Parámetros:** `{"UMBRAL_RETENCION": 10000, "TASA_RETENCION": 2, "operador": ">", "ramo_excluido": "VIDA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 565: `IF v_pol.ramo <> c_ramo_vida`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 566: `AND v_cubierto > fn_param_num('UMBRAL_RETENCION')`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 568: `v_retencion := ROUND(v_cubierto * fn_param_num('TASA_RETENCION') / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 569: `pr_agregar_obs(v_observaciones, 'RETENCION_APLICADA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 571: `v_retencion := 0;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 574: `v_neto := v_cubierto - v_retencion;`
  - `02_parametros.sql` línea 25: `('UMBRAL_RETENCION', 10000, NULL`
  - `02_parametros.sql` línea 26: `('TASA_RETENCION', 2, NULL`
- **Preguntas para el dueño del negocio:**
  - ¿La retencion debe aplicarse sobre el total o solo sobre el exceso del umbral?

### R-021 — orden (alta) · pendiente

Orden de calculo: monto base, deducible, cubierto (rechazo si <= 0), penalizacion por siniestralidad, suma asegurada remanente (rechazo/tope), retencion y neto, umbral de fraude y estado final, y por ultimo el registro del resultado. Cambiar el orden altera los importes (p. ej. la penalizacion se aplica antes del tope y la retencion despues).

- **Condición:** siempre
- **Acción:** secuencia fija de calculo
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 487: `IF v_sin.monto_reclamado > v_cob.limite_cobertura THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 497: `v_deducible := fn_calcular_deducible(v_pol, v_cli.categoria, v_monto_base, v_observaciones);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 503: `v_cubierto := ROUND((v_monto_base - v_deducible) * v_cob.porcentaje_cobertura / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 521: `SELECT COUNT(*)`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 531: `v_cubierto := ROUND(v_cubierto * (100 - fn_param_num('PCT_PENALIZACION_SINIEST')) / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 541: `SELECT NVL(SUM(l.monto_cubierto), 0)`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 556: `v_cubierto := v_suma_remanente;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 568: `v_retencion := ROUND(v_cubierto * fn_param_num('TASA_RETENCION') / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 574: `v_neto := v_cubierto - v_retencion;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 586: `v_umbral_fraude := ROUND(v_cob.limite_cobertura * fn_param_num('PCT_ALERTA_FRAUDE') / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 601: `pr_registrar_resultado(`

### R-022 — redondeo (alta) · pendiente

Convencion de redondeo: cada operacion de porcentaje se redondea de inmediato a 2 decimales con ROUND (la cabecera documenta 'mitad hacia arriba'): deducible porcentual, descuento VIP, cubierto, penalizacion, retencion y umbral de fraude. No hay redondeo intermedio a mas decimales; las variables de importe son NUMBER(14,2).

- **Condición:** cada calculo de porcentaje
- **Acción:** ROUND(..., 2) tras cada paso
- **Parámetros:** `{"decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 50: `Todos los importes calculados se redondean a 2 decimales con ROUND`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 193: `v_deducible := ROUND(p_monto_base * p_poliza.deducible_valor / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 203: `v_deducible := ROUND(v_deducible * (100 - v_pct_desc_vip) / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 568: `v_retencion := ROUND(v_cubierto * fn_param_num('TASA_RETENCION') / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 586: `v_umbral_fraude := ROUND(v_cob.limite_cobertura * fn_param_num('PCT_ALERTA_FRAUDE') / 100, 2);`

### R-023 — validacion (alta) · pendiente

Alerta de fraude: umbral = ROUND(limite_cobertura * PCT_ALERTA_FRAUDE(80)/100, 2). Si dias_desde_inicio <= DIAS_ALERTA_FRAUDE (15, inclusive) Y el monto RECLAMADO (no el base ni el cubierto) es >= umbral (inclusive), el estado es PENDIENTE_APROBACION con motivo SOSPECHA_FRAUDE. Los importes calculados si se guardan.

- **Condición:** dias_desde_inicio <= 15 y monto_reclamado >= umbral
- **Acción:** estado PENDIENTE_APROBACION / SOSPECHA_FRAUDE
- **Parámetros:** `{"DIAS_ALERTA_FRAUDE": 15, "PCT_ALERTA_FRAUDE": 80, "operador_dias": "<=", "operador_monto": ">="}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 588: `IF v_dias_desde_inicio <= fn_param_num('DIAS_ALERTA_FRAUDE')`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 589: `AND v_sin.monto_reclamado >= v_umbral_fraude`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 591: `v_estado_liq := c_liq_pend_aprob;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 592: `v_motivo := 'SOSPECHA_FRAUDE';`
  - `02_parametros.sql` línea 30: `('DIAS_ALERTA_FRAUDE', 15, NULL`
  - `02_parametros.sql` línea 31: `('PCT_ALERTA_FRAUDE', 80, NULL`
- **Preguntas para el dueño del negocio:**
  - ¿El umbral de fraude debe compararse con el monto reclamado o con el cubierto?

### R-024 — orden (alta) · pendiente

Estado final: primero fraude (prioridad), luego si el NETO es > TOPE_AUTO_APROBACION (50000, estricto) queda PENDIENTE_APROBACION con SUPERA_TOPE_AUTOMATICO; en otro caso APROBADA con LIQUIDACION_AUTOMATICA. Un neto igual al tope se aprueba.

- **Condición:** liquidacion que paso todas las validaciones
- **Acción:** asigna estado y motivo
- **Parámetros:** `{"TOPE_AUTO_APROBACION": 50000, "operador": ">"}`
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 588: `IF v_dias_desde_inicio <= fn_param_num('DIAS_ALERTA_FRAUDE')`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 593: `ELSIF v_neto > fn_param_num('TOPE_AUTO_APROBACION') THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 595: `v_motivo := 'SUPERA_TOPE_AUTOMATICO';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 597: `v_estado_liq := c_liq_aprobada;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 598: `v_motivo := 'LIQUIDACION_AUTOMATICA';`
  - `02_parametros.sql` línea 29: `('TOPE_AUTO_APROBACION', 50000, NULL`

### R-025 — efecto_secundario (alta) · pendiente

Correspondencia estado liquidacion -> estado del siniestro: APROBADA -> LIQUIDADO, RECHAZADA -> RECHAZADO, PENDIENTE_APROBACION -> PENDIENTE_REVISION. El siniestro se actualiza con esa correspondencia.

- **Condición:** al registrar cualquier resultado
- **Acción:** UPDATE ls_siniestros SET estado
- **Parámetros:** `{"APROBADA": "LIQUIDADO", "RECHAZADA": "RECHAZADO", "PENDIENTE_APROBACION": "PENDIENTE_REVISION"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 284: `WHEN c_liq_aprobada THEN c_sin_liquidado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 285: `WHEN c_liq_rechazada THEN c_sin_rechazado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 286: `WHEN c_liq_pend_aprob THEN c_sin_pend_revision`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 290: `SET estado = v_estado_sin`

### R-026 — efecto_secundario (alta) · pendiente

Se inserta una fila en LS_LIQUIDACIONES por siniestro con: id de secuencia, fecha_liquidacion = fecha de proceso recibida (no SYSDATE), monto reclamado original, base, deducible, cubierto, retencion, neto, estado, motivo, observaciones (marcas separadas por ';') y usuario USER.

- **Condición:** al registrar cualquier resultado
- **Acción:** INSERT en ls_liquidaciones
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 272: `INSERT INTO ls_liquidaciones (`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 277: `seq_ls_liquidacion.NEXTVAL, p_siniestro.siniestro_id, p_fecha_proceso,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 278: `p_siniestro.monto_reclamado, p_monto_base, p_deducible, p_cubierto,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 279: `p_retencion, p_neto, p_estado_liq, p_motivo, p_observaciones, USER`
  - `01_ddl_tablas.sql` línea 121: `usuario_proceso VARCHAR2(30) DEFAULT USER NOT NULL,`

### R-027 — efecto_secundario (alta) · pendiente

Efectos NO realizados por la liquidacion: no hace COMMIT (lo controla el llamador), no modifica polizas, coberturas, clientes ni liquidaciones existentes; el unico UPDATE es el estado del siniestro. No se actualiza prima_pendiente ni la suma asegurada: el remanente se deriva sumando liquidaciones.

- **Condición:** siempre
- **Acción:** solo INSERT de liquidacion y UPDATE de estado de siniestro
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 289: `UPDATE ls_siniestros`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 47: `NO realiza COMMIT (lo controla el llamador)`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 46: `Inserta un registro en LS_LIQUIDACIONES y actualiza el estado del`
- **Comprobación de ausencia:** sin COMMIT desde pr_registrar_resultado hasta el fin de pr_liquidar_siniestro (`04_pkg_liquidacion_siniestros_body.sql`, líneas 258-617, patrón `\bCOMMIT\b`: 0 coincidencias, esperado 0)
- **Comprobación de ausencia:** ningun UPDATE sobre polizas, coberturas, liquidaciones ni clientes (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `UPDATE\s+ls_(polizas|coberturas|liquidaciones|clientes)`: 0 coincidencias, esperado 0)
- **Comprobación de ausencia:** un unico UPDATE sobre siniestros (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `UPDATE\s+ls_siniestros`: 1 coincidencias, esperado 1)

### R-028 — orden (alta) · pendiente

Seleccion y orden del lote: se procesan los siniestros en estado REGISTRADO con fecha_denuncia <= fecha de proceso (inclusive), en orden ascendente de siniestro_id. El orden importa porque los liquidados antes afectan siniestralidad y suma asegurada de los siguientes. La fecha por defecto es TRUNC(SYSDATE); el script de ejecucion usa 2026-03-31. Siniestros con denuncia posterior al corte no se tocan.

- **Condición:** pr_procesar_lote
- **Acción:** recorre el cursor por siniestro_id ascendente
- **Parámetros:** `{"operador": "<=", "orden": "siniestro_id ASC", "fecha_corte_script": "2026-03-31"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 628: `WHERE s.estado = c_sin_registrado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 629: `AND s.fecha_denuncia <= p_fecha_proceso`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 630: `ORDER BY s.siniestro_id;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 623: `p_fecha_proceso IN DATE DEFAULT TRUNC(SYSDATE)`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 72: `PROCEDURE pr_procesar_lote (`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 65: `fecha de denuncia sea menor o igual a la fecha de proceso, en orden`
  - `ejecutar_lote.sql` línea 9: `pkg_liquidacion_siniestros.pr_procesar_lote(p_fecha_proceso => DATE '2026-03-31');`

### R-029 — error (alta) · pendiente

Aislamiento por siniestro: cada uno se procesa tras un SAVEPOINT; ante cualquier excepcion se hace ROLLBACK al savepoint (se deshacen liquidacion y cambio de estado, el siniestro sigue REGISTRADO), se cuenta como error y se escribe un log ERROR con el mensaje de la excepcion. El lote continua con el siguiente.

- **Condición:** cualquier excepcion en pr_liquidar_siniestro o en la lectura posterior
- **Acción:** rollback parcial, contar error, log ERROR
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 649: `SAVEPOINT sp_siniestro;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 672: `WHEN OTHERS THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 673: `ROLLBACK TO sp_siniestro;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 674: `v_cant_errores := v_cant_errores + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 675: `pr_log('ERROR', r.siniestro_id, SQLERRM);`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 67: `un error en uno no detiene el lote`
- **Preguntas para el dueño del negocio:**
  - ¿Un siniestro con error se reintenta en el siguiente lote o requiere intervencion?

### R-030 — calculo (alta) · pendiente

Contadores del lote segun el estado final del siniestro: LIQUIDADO suma a liquidados y acumula el monto neto de su liquidacion APROBADA al total neto aprobado; RECHAZADO suma a rechazados; PENDIENTE_REVISION suma a pendientes (su neto NO entra en el total). Procesados se incrementa antes de procesar cada siniestro, tambien los que fallan.

- **Condición:** tras cada liquidacion exitosa
- **Acción:** actualiza contadores y total neto aprobado
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 657: `IF v_estado_final = c_sin_liquidado THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 658: `v_cant_liquidados := v_cant_liquidados + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 663: `AND estado = c_liq_aprobada;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 665: `v_total_neto_aprob := v_total_neto_aprob + v_neto_sin;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 666: `ELSIF v_estado_final = c_sin_rechazado THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 667: `v_cant_rechazados := v_cant_rechazados + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 668: `ELSIF v_estado_final = c_sin_pend_revision THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 669: `v_cant_pendientes := v_cant_pendientes + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 646: `v_cant_procesados := v_cant_procesados + 1;`

### R-031 — efecto_secundario (alta) · pendiente

El lote hace un unico COMMIT al terminar el bucle (no por siniestro) y escribe en bitacora un INFO de inicio (con la fecha de proceso) y un INFO de fin con los contadores.

- **Condición:** fin de pr_procesar_lote
- **Acción:** COMMIT y logs INFO
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 679: `COMMIT;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 642: `pr_log('INFO', NULL, 'Inicio lote de liquidacion. Fecha proceso: ' ||`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 681: `pr_log('INFO', NULL, 'Fin lote. Procesados=' || v_cant_procesados ||`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 68: `Al finalizar realiza COMMIT y emite un resumen por DBMS_OUTPUT.`

### R-032 — fechas (alta) · pendiente

La fecha de proceso solo se usa en pr_liquidar_siniestro como fecha_liquidacion registrada y para filtrar el lote por fecha de denuncia; no participa en ninguna validacion de vigencia, plazo ni carencia (esas usan solo fechas del siniestro y de la poliza).

- **Condición:** siempre
- **Acción:** sin comparaciones ni aritmetica con p_fecha_proceso
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 603: `p_fecha_proceso => p_fecha_proceso,`
- **Comprobación de ausencia:** sin comparaciones ni aritmetica con p_fecha_proceso dentro de pr_liquidar_siniestro (`04_pkg_liquidacion_siniestros_body.sql`, líneas 327-617, patrón `p_fecha_proceso\s*[-+<>]|[-+<]=?\s*p_fecha_proceso|(?<!=)>=?\s*p_fecha_proceso`: 0 coincidencias, esperado 0)
- **Preguntas para el dueño del negocio:**
  - ¿La vigencia debe evaluarse contra la fecha de proceso?

### R-033 — efecto_secundario (alta) · pendiente

La bitacora LS_LOG_PROCESO se escribe con transaccion autonoma y COMMIT propio: los logs persisten aunque se haga ROLLBACK al savepoint del siniestro o falle el lote. El mensaje se trunca a 1000 caracteres. Cada registro de resultado escribe un log INFO con estado, motivo y neto.

- **Condición:** cada llamada a pr_log
- **Acción:** INSERT + COMMIT autonomo
- **Parámetros:** `{"max_mensaje": 1000}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 86: `PRAGMA AUTONOMOUS_TRANSACTION;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 90: `COMMIT;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 89: `SUBSTR(p_mensaje, 1, 1000)`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 294: `'Resultado: ' || p_estado_liq || ' / ' || p_motivo ||`

### R-034 — efecto_secundario (media) · pendiente

Las marcas de observacion se concatenan con ';' en el orden en que se generan (si el texto es NULL, la primera marca va sola). La columna es VARCHAR2(400); un desborde no esta probado por ejecucion.

- **Condición:** cada pr_agregar_obs
- **Acción:** concatena marca
- **Parámetros:** `{"separador": ";", "longitud_max": 400}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 61: `c_separador_obs CONSTANT VARCHAR2(1) := ';';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 123: `IF p_observaciones IS NULL THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 124: `p_observaciones := p_marca;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 126: `p_observaciones := p_observaciones || c_separador_obs || p_marca;`

### R-035 — efecto_secundario (alta) · pendiente

El resumen del lote se imprime por DBMS_OUTPUT con procesados, liquidados, rechazados, pendientes, errores y total neto aprobado (formato FM999999990.00). Es solo salida; no hay logica.

- **Condición:** fin del lote
- **Acción:** imprime resumen
- **Parámetros:** `{"formato_neto": "FM999999990.00"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 688: `DBMS_OUTPUT.PUT_LINE(' RESUMEN LOTE DE LIQUIDACION');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 695: `DBMS_OUTPUT.PUT_LINE(' Total neto aprobado: ' || TO_CHAR(v_total_neto_aprob, 'FM999999990.00'));`

### R-036 — efecto_secundario (media) · pendiente

La correspondencia estado liquidacion -> estado siniestro es un CASE sin ELSE: un estado distinto de los tres conocidos dejaria el estado en NULL (no probado por ejecucion). Hoy solo se invocan los tres estados conocidos.

- **Condición:** estado de liquidacion fuera de los tres conocidos
- **Acción:** estado NULL en UPDATE (no probado por ejecucion)
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 283: `v_estado_sin := CASE p_estado_liq`

### R-037 — calculo (alta) · pendiente

Codigo muerto: fn_es_dia_habil (lunes a viernes, sin festivos) esta definida pero nunca se invoca y no esta en la especificacion; ninguna regla depende de dias habiles.

- **Condición:** nunca se ejecuta
- **Acción:** ninguna
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 138: `RETURN v_dia NOT IN ('SAT', 'SUN');`
- **Comprobación de ausencia:** solo la definicion, sin llamadas (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `fn_es_dia_habil\s*\(`: 1 coincidencias, esperado 1)
- **Comprobación de ausencia:** la especificacion publica solo los dos procedimientos (`03_pkg_liquidacion_siniestros_spec.sql`, líneas 1-77, patrón `fn_es_dia_habil|fn_calcular_iva|fn_calcular_deducible|pr_recalcular_reserva_tecnica|pr_enviar_notificacion`: 0 coincidencias, esperado 0)

### R-038 — calculo (alta) · pendiente

Codigo muerto: fn_calcular_deducible_v1 (version 2009) calcula el deducible sobre el monto reclamado, sin minimo ni VIP, truncando (TRUNC) a 2 decimales en lugar de redondear. Solo se referencia en un bloque comentado; las dos lineas posteriores al RETURN son inalcanzables.

- **Condición:** nunca se ejecuta
- **Acción:** ninguna (la version vigente es fn_calcular_deducible)
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 153: `IF p_deducible_tipo = 'FIJO' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 155: `ELSIF p_deducible_tipo = 'PORCENTAJE' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 159: `RETURN TRUNC(v_deducible, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 162: `v_deducible := v_deducible * 1.0;`
- **Comprobación de ausencia:** solo la definicion y la llamada dentro del bloque comentado (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `fn_calcular_deducible_v1\s*\(`: 2 coincidencias, esperado 2)

### R-039 — calculo (alta) · pendiente

Codigo muerto: fn_calcular_iva (ROUND(monto * TASA_IVA / 100, 2)) nunca se invoca; el IVA (parametro TASA_IVA = 19) no interviene en ningun importe de la liquidacion.

- **Condición:** nunca se ejecuta
- **Acción:** ninguna
- **Parámetros:** `{"TASA_IVA": 19}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 218: `RETURN ROUND(p_monto * v_tasa / 100, 2);`
  - `02_parametros.sql` línea 35: `('TASA_IVA', 19, NULL`
- **Comprobación de ausencia:** solo la definicion, sin llamadas (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `fn_calcular_iva\s*\(`: 1 coincidencias, esperado 1)
- **Preguntas para el dueño del negocio:**
  - ¿Debe aplicarse IVA a algun importe?

### R-040 — calculo (alta) · pendiente

Codigo muerto: pr_recalcular_reserva_tecnica (siniestros LIQUIDADOS de anos anteriores, reserva = ROUND(monto_reclamado * FACTOR_INFLACION, 2) en LS_TMP_CALCULO_2009 tras vaciarla) es privada y nunca se invoca.

- **Condición:** nunca se ejecuta
- **Acción:** ninguna
- **Parámetros:** `{"FACTOR_INFLACION": 1.035}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 231: `DELETE FROM ls_tmp_calculo_2009;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 235: `VALUES (r.siniestro_id, ROUND(r.monto_reclamado * v_factor, 2), SYSDATE);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 72: `WHERE EXTRACT(YEAR FROM s.fecha_ocurrencia) < p_anio`
  - `01_ddl_tablas.sql` línea 155: `CREATE TABLE ls_tmp_calculo_2009 (`
  - `02_parametros.sql` línea 34: `('FACTOR_INFLACION', 1.035, NULL`
- **Comprobación de ausencia:** solo la definicion, sin llamadas (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `pr_recalcular_reserva_tecnica\s*\(`: 1 coincidencias, esperado 1)
- **Preguntas para el dueño del negocio:**
  - ¿Se ejecuta fuera del paquete?

### R-041 — efecto_secundario (alta) · pendiente

Modo debug y notificacion desactivados: c_modo_debug es constante FALSE, por lo que nunca se ejecutan la traza DEBUG (que incluiria nombre del cliente, dato personal) ni pr_enviar_notificacion (solo imprime por DBMS_OUTPUT; el envio de correo esta comentado).

- **Condición:** c_modo_debug = TRUE (no ocurre)
- **Acción:** ninguna en produccion
- **Parámetros:** `{"c_modo_debug": false}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 60: `c_modo_debug CONSTANT BOOLEAN := FALSE;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 377: `IF c_modo_debug THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 614: `IF c_modo_debug THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 615: `pr_enviar_notificacion(v_sin.siniestro_id, v_estado_liq);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 251: `DBMS_OUTPUT.PUT_LINE('[NOTIFICACION] ' || v_mensaje);`

### R-042 — efecto_secundario (alta) · pendiente

Codigo inalcanzable: el aviso WARN para polizas SUSPENDIDAS (y el contador v_contador_aux, que nunca se lee) no se ejecuta porque una poliza no VIGENTE ya fue rechazada antes.

- **Condición:** estado = SUSPENDIDA tras pasar la validacion de vigente (imposible)
- **Acción:** ninguna
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 386: `IF v_pol.estado <> c_poliza_vigente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 465: `IF v_pol.estado = 'SUSPENDIDA' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 467: `v_contador_aux := v_contador_aux + 1;`
- **Comprobación de ausencia:** solo declaracion e incremento, nunca leida (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `v_contador_aux`: 2 coincidencias, esperado 2)

### R-043 — validacion (alta) · pendiente

Codigo inalcanzable o comentado: IF v_cubierto < 0 con e_monto_invalido nunca se cumple porque cubierto <= 0 ya se rechazo; e_monto_invalido no tiene otro manejador. El bloque comentado SIN-0001 (calculo original sin penalizacion, retencion ni remanente) no se ejecuta.

- **Condición:** nunca se ejecuta
- **Acción:** ninguna
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 471: `-- SIN-0001 (2009): calculo original, reemplazado en SIN-0310`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 477: `IF v_cubierto > v_pol.suma_asegurada THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 505: `IF v_cubierto <= 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 510: `IF v_cubierto < 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 512: `RAISE e_monto_invalido;`
- **Comprobación de ausencia:** solo declaracion y RAISE, sin manejador propio (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `e_monto_invalido`: 2 coincidencias, esperado 2)

### R-044 — error (alta) · pendiente

pr_liquidar_siniestro lee FACTOR_INFLACION al inicio aunque nunca lo usa: su unico efecto es que, si el parametro no existe, TODO siniestro falla con ORA-20010 antes de cualquier validacion.

- **Condición:** siempre, tras cargar siniestro, poliza y cliente
- **Acción:** lectura sin uso
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 375: `v_factor_inflacion := fn_param_num('FACTOR_INFLACION');`
- **Comprobación de ausencia:** solo declaracion y asignacion (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `v_factor_inflacion`: 2 coincidencias, esperado 2)

### R-045 — calculo (alta) · pendiente

El lote acumula v_total_reclamado pero nunca lo imprime ni lo registra; el parametro VERSION_MOTOR tampoco se usa en el paquete.

- **Condición:** siempre
- **Acción:** acumulacion sin uso
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 647: `v_total_reclamado := v_total_reclamado + r.monto_reclamado;`
- **Comprobación de ausencia:** solo declaracion y acumulacion (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `v_total_reclamado`: 2 coincidencias, esperado 2)
- **Comprobación de ausencia:** VERSION_MOTOR no se usa (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `VERSION_MOTOR`: 0 coincidencias, esperado 0)

## Glosario de variables

| Variable | Significado |
|---|---|
| `v_sin` | registro del siniestro que se liquida |
| `v_pol` | registro de la poliza del siniestro |
| `v_cli` | registro del cliente (asegurado) de la poliza |
| `v_cob` | cobertura contratada reclamada (limite, porcentaje, dias de carencia) |
| `v_dias_denuncia` | dias calendario entre ocurrencia y denuncia |
| `v_dias_desde_inicio` | dias entre inicio de la poliza y la ocurrencia (usado en carencia y fraude) |
| `v_monto_base` | monto reclamado topado por el limite de la cobertura |
| `v_deducible` | monto que el asegurado asume antes de la indemnizacion |
| `v_cubierto` | monto que paga la aseguradora antes de retencion |
| `v_retencion` | retencion impositiva sobre el monto cubierto |
| `v_neto` | monto cubierto menos retencion; lo que se paga |
| `v_suma_remanente` | suma asegurada menos lo cubierto en liquidaciones aprobadas o pendientes |
| `v_umbral_fraude` | porcentaje del limite de cobertura que dispara la alerta de fraude |
| `v_observaciones` | marcas de ajustes aplicados separadas por ';' |
| `c_modo_debug` | constante que apaga trazas y notificaciones |
| `DIAS_CARENCIA` | dias desde el inicio de la poliza en que la cobertura aun no esta activa |
| `PRIMA_PENDIENTE` | prima vencida y no pagada (mora) de la poliza |
