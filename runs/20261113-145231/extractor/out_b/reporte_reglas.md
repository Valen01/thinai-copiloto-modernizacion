# Reporte de reglas — estado tras el dictamen

- Aprobadas: **0**
- Corregidas, requieren reaprobación: **0**
- Pendientes: **46**

Cada línea citada fue verificada automáticamente contra el código. «Aprobada» valida la extracción del comportamiento existente, no que sea un requisito de negocio deseable.

## Reglas de negocio (36)

| ID | Categoría | Confianza | Estado |
|---|---|---|---|
| R-001 | validacion | alta | pendiente |
| R-002 | efecto_secundario | alta | pendiente |
| R-003 | error | alta | pendiente |
| R-005 | orden | alta | pendiente |
| R-006 | validacion | alta | pendiente |
| R-007 | fechas | media | pendiente |
| R-008 | validacion | alta | pendiente |
| R-009 | validacion | alta | pendiente |
| R-010 | fechas | alta | pendiente |
| R-011 | validacion | alta | pendiente |
| R-013 | calculo | alta | pendiente |
| R-014 | calculo | alta | pendiente |
| R-015 | calculo | alta | pendiente |
| R-016 | calculo | alta | pendiente |
| R-018 | calculo | alta | pendiente |
| R-019 | calculo | alta | pendiente |
| R-020 | calculo | alta | pendiente |
| R-021 | validacion | alta | pendiente |
| R-022 | calculo | alta | pendiente |
| R-023 | calculo | alta | pendiente |
| R-024 | validacion | alta | pendiente |
| R-025 | validacion | alta | pendiente |
| R-026 | orden | alta | pendiente |
| R-027 | efecto_secundario | alta | pendiente |
| R-028 | efecto_secundario | alta | pendiente |
| R-029 | efecto_secundario | alta | pendiente |
| R-030 | efecto_secundario | alta | pendiente |
| R-031 | efecto_secundario | alta | pendiente |
| R-032 | orden | alta | pendiente |
| R-033 | error | alta | pendiente |
| R-034 | calculo | alta | pendiente |
| R-035 | efecto_secundario | alta | pendiente |
| R-037 | redondeo | media | pendiente |
| R-038 | calculo | alta | pendiente |
| R-039 | tasas | alta | pendiente |
| R-040 | validacion | alta | pendiente |

## Hallazgos técnicos (10)

| ID | Categoría | Confianza | Estado |
|---|---|---|---|
| R-004 | efecto_secundario | alta | pendiente |
| R-012 | efecto_secundario | alta | pendiente |
| R-017 | error | alta | pendiente |
| R-036 | efecto_secundario | alta | pendiente |
| R-041 | fechas | alta | pendiente |
| R-042 | calculo | alta | pendiente |
| R-043 | efecto_secundario | alta | pendiente |
| R-044 | calculo | alta | pendiente |
| R-045 | efecto_secundario | alta | pendiente |
| R-046 | calculo | alta | pendiente |

### R-001 — validacion (alta) · pendiente

Solo se liquida un siniestro que esté en estado REGISTRADO. Si tiene cualquier otro estado, el procedimiento lanza el error ORA-20001 con un mensaje que incluye el id y el estado actual; no escribe liquidación ni cambia el siniestro.

- **Condición:** estado del siniestro distinto de REGISTRADO
- **Acción:** RAISE_APPLICATION_ERROR(-20001) y termina sin efectos
- **Parámetros:** `{"codigo_error": -20001, "estado_requerido": "REGISTRADO", "operador": "<>"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 367: `IF v_sin.estado <> c_sin_registrado THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 368: `RAISE_APPLICATION_ERROR(-20001,`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 53: `ORA-20001 El siniestro no se encuentra en estado REGISTRADO.`
- **Preguntas para el dueño del negocio:**
  - ¿Se espera poder reliquidar siniestros en PENDIENTE_REVISION tras la aprobación manual?

### R-002 — efecto_secundario (alta) · pendiente

Al liquidar, el siniestro se lee con bloqueo de fila (FOR UPDATE); luego se leen la póliza del siniestro y el cliente de la póliza. Si alguno no existe se propaga NO_DATA_FOUND (no se rechaza con motivo de negocio).

- **Condición:** inicio de pr_liquidar_siniestro
- **Acción:** SELECT ... FOR UPDATE del siniestro; SELECT de póliza y cliente
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 365: `FOR UPDATE;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 372: `SELECT * INTO v_pol FROM ls_polizas WHERE poliza_id = v_sin.poliza_id;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 373: `SELECT * INTO v_cli FROM ls_clientes WHERE cliente_id = v_pol.cliente_id;`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 55: `NO_DATA_FOUND El siniestro, la poliza o el cliente no existen.`
- **Preguntas para el dueño del negocio:**
  - ¿Un siniestro sin póliza o cliente debe quedar como error de lote (como hoy) o rechazado?

### R-003 — error (alta) · pendiente

Los parámetros de negocio se leen de LS_PARAMETROS por código (columna valor numérico). Si el código no existe se lanza ORA-20010 'Parametro no definido: <código>'. Los parámetros se consultan de forma perezosa, en el punto donde se usan, salvo FACTOR_INFLACION (ver R-004).

- **Condición:** parámetro inexistente
- **Acción:** RAISE_APPLICATION_ERROR(-20010)
- **Parámetros:** `{"codigo_error": -20010}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 103: `SELECT valor_numerico`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 110: `WHEN NO_DATA_FOUND THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 111: `RAISE_APPLICATION_ERROR(-20010, 'Parametro no definido: ' || p_cod_parametro);`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 54: `ORA-20010 Parametro de negocio inexistente en LS_PARAMETROS.`

### R-005 — orden (alta) · pendiente

Orden de evaluación: póliza vigente, vigencia, plazo de denuncia, cobertura contratada, carencia, mora, y luego cálculo (bajo deducible, suma asegurada agotada). El primer fallo registra el rechazo y termina (RETURN); los siguientes no se evalúan, por lo que el motivo reportado es el del primer control que falla.

- **Condición:** siempre
- **Acción:** cadena de controles con salida anticipada
- **Parámetros:** `{"orden": ["POLIZA_NO_VIGENTE", "FUERA_DE_VIGENCIA", "DENUNCIA_EXTEMPORANEA", "COBERTURA_NO_CONTRATADA", "EN_PERIODO_CARENCIA", "PRIMA_EN_MORA", "BAJO_DEDUCIBLE", "SUMA_ASEGURADA_AGOTADA"]}`
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 387: `pr_rechazar(v_sin, p_fecha_proceso, 'POLIZA_NO_VIGENTE');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 398: `pr_rechazar(v_sin, p_fecha_proceso, 'FUERA_DE_VIGENCIA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 416: `pr_rechazar(v_sin, p_fecha_proceso, 'DENUNCIA_EXTEMPORANEA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 431: `pr_rechazar(v_sin, p_fecha_proceso, 'COBERTURA_NO_CONTRATADA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 443: `pr_rechazar(v_sin, p_fecha_proceso, 'EN_PERIODO_CARENCIA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 459: `pr_rechazar(v_sin, p_fecha_proceso, 'PRIMA_EN_MORA', v_observaciones);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 506: `pr_rechazar(v_sin, p_fecha_proceso, 'BAJO_DEDUCIBLE', v_observaciones);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 551: `pr_rechazar(v_sin, p_fecha_proceso, 'SUMA_ASEGURADA_AGOTADA', v_observaciones);`
- **Preguntas para el dueño del negocio:**
  - ¿El orden de prioridad de motivos de rechazo es requisito de negocio (afecta reportes)?

### R-006 — validacion (alta) · pendiente

Solo se liquidan pólizas en estado VIGENTE. Cualquier otro estado (CANCELADA, SUSPENDIDA) se rechaza con POLIZA_NO_VIGENTE y observaciones vacías.

- **Condición:** estado de póliza <> 'VIGENTE'
- **Acción:** pr_rechazar(... 'POLIZA_NO_VIGENTE') y RETURN
- **Parámetros:** `{"estado_requerido": "VIGENTE", "motivo": "POLIZA_NO_VIGENTE"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 386: `IF v_pol.estado <> c_poliza_vigente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 64: `c_poliza_vigente CONSTANT VARCHAR2(12) := 'VIGENTE';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 387: `pr_rechazar(v_sin, p_fecha_proceso, 'POLIZA_NO_VIGENTE');`

### R-007 — fechas (media) · pendiente

La fecha de ocurrencia debe caer en [fecha_inicio, fecha_fin] de la póliza, ambos extremos incluidos. Se rechaza si es estrictamente menor al inicio o estrictamente mayor al fin. La comparación no aplica TRUNC: si las fechas llevaran hora podría afectar el borde (no probado por ejecución).

- **Condición:** ocurrencia < inicio OR ocurrencia > fin
- **Acción:** pr_rechazar(... 'FUERA_DE_VIGENCIA') y RETURN
- **Parámetros:** `{"operador_inicio": "<", "operador_fin": ">", "extremos": "inclusivos"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 395: `IF v_sin.fecha_ocurrencia < v_pol.fecha_inicio`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 396: `OR v_sin.fecha_ocurrencia > v_pol.fecha_fin`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 398: `pr_rechazar(v_sin, p_fecha_proceso, 'FUERA_DE_VIGENCIA');`
- **Preguntas para el dueño del negocio:**
  - ¿Las fechas de póliza/siniestro pueden traer hora?

### R-008 — validacion (alta) · pendiente

Plazo de denuncia: días = TRUNC(denuncia) - TRUNC(ocurrencia). El máximo es DIAS_MAX_DENUNCIA (30) y para ramo VIDA DIAS_MAX_DENUNCIA_VIDA (365). Se rechaza si días > máximo (estricto), es decir, el día límite es aceptado. Rechazo: DENUNCIA_EXTEMPORANEA.

- **Condición:** dias_denuncia > máximo del ramo
- **Acción:** pr_rechazar(... 'DENUNCIA_EXTEMPORANEA') y RETURN
- **Parámetros:** `{"dias_max": 30, "dias_max_vida": 365, "operador": ">"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 407: `v_dias_denuncia := TRUNC(v_sin.fecha_denuncia) - TRUNC(v_sin.fecha_ocurrencia);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 409: `IF v_pol.ramo = c_ramo_vida THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 410: `v_dias_max_denuncia := fn_param_num('DIAS_MAX_DENUNCIA_VIDA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 412: `v_dias_max_denuncia := fn_param_num('DIAS_MAX_DENUNCIA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 415: `IF v_dias_denuncia > v_dias_max_denuncia THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 416: `pr_rechazar(v_sin, p_fecha_proceso, 'DENUNCIA_EXTEMPORANEA');`
  - `02_parametros.sql` línea 10: `('DIAS_MAX_DENUNCIA', 30,`
  - `02_parametros.sql` línea 11: `('DIAS_MAX_DENUNCIA_VIDA', 365,`
- **Preguntas para el dueño del negocio:**
  - ¿Los días son calendario (como hoy) o hábiles?

### R-009 — validacion (alta) · pendiente

La cobertura reclamada debe existir para la póliza (clave póliza + código de cobertura). Si no existe se rechaza con COBERTURA_NO_CONTRATADA. Esta consulta ocurre después de vigencia y denuncia.

- **Condición:** no hay fila en ls_coberturas para (poliza, cobertura)
- **Acción:** pr_rechazar(... 'COBERTURA_NO_CONTRATADA') y RETURN
- **Parámetros:** `{"motivo": "COBERTURA_NO_CONTRATADA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 428: `AND cod_cobertura = v_sin.cod_cobertura;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 430: `WHEN NO_DATA_FOUND THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 431: `pr_rechazar(v_sin, p_fecha_proceso, 'COBERTURA_NO_CONTRATADA');`

### R-010 — fechas (alta) · pendiente

Carencia: días desde inicio de póliza = TRUNC(ocurrencia) - TRUNC(inicio). Se rechaza si es estrictamente menor a dias_carencia de la cobertura; con días iguales a la carencia la cobertura ya está activa. Esta variable se reutiliza luego para la alerta de fraude.

- **Condición:** dias_desde_inicio < dias_carencia
- **Acción:** pr_rechazar(... 'EN_PERIODO_CARENCIA') y RETURN
- **Parámetros:** `{"operador": "<", "campo": "dias_carencia"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 440: `v_dias_desde_inicio := TRUNC(v_sin.fecha_ocurrencia) - TRUNC(v_pol.fecha_inicio);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 442: `IF v_dias_desde_inicio < v_cob.dias_carencia THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 443: `pr_rechazar(v_sin, p_fecha_proceso, 'EN_PERIODO_CARENCIA');`

### R-011 — validacion (alta) · pendiente

Morosidad: si la prima pendiente es > 0 se rechaza con PRIMA_EN_MORA, salvo que el cliente sea VIP y la deuda sea <= TOLERANCIA_MORA_VIP (500); en ese caso continúa y se agrega la marca TOLERANCIA_MORA_VIP. Con prima pendiente 0 no hay marca. En el rechazo se pasa v_observaciones, que en ese punto aún está vacía (NULL).

- **Condición:** prima_pendiente > 0
- **Acción:** VIP y deuda <= 500: marca y sigue; si no, rechazo PRIMA_EN_MORA
- **Parámetros:** `{"tolerancia_vip": 500, "operador_deuda": ">", "operador_tolerancia": "<="}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 451: `IF v_pol.prima_pendiente > 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 452: `v_tolerancia_mora := fn_param_num('TOLERANCIA_MORA_VIP');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 454: `IF v_cli.categoria = c_cat_vip`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 455: `AND v_pol.prima_pendiente <= v_tolerancia_mora`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 457: `pr_agregar_obs(v_observaciones, 'TOLERANCIA_MORA_VIP');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 459: `pr_rechazar(v_sin, p_fecha_proceso, 'PRIMA_EN_MORA', v_observaciones);`
  - `02_parametros.sql` línea 18: `('TOLERANCIA_MORA_VIP', 500,`
- **Preguntas para el dueño del negocio:**
  - ¿La tolerancia VIP es por póliza o acumulada por cliente?

### R-013 — calculo (alta) · pendiente

Monto base = el menor entre lo reclamado y el límite de la cobertura. Si el reclamado es estrictamente mayor al límite, la base es el límite y se agrega la marca LIMITE_COBERTURA; si es igual o menor, la base es el reclamado.

- **Condición:** monto_reclamado > limite_cobertura
- **Acción:** monto_base := limite_cobertura + marca LIMITE_COBERTURA
- **Parámetros:** `{"operador": ">"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 487: `IF v_sin.monto_reclamado > v_cob.limite_cobertura THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 488: `v_monto_base := v_cob.limite_cobertura;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 489: `pr_agregar_obs(v_observaciones, 'LIMITE_COBERTURA');`

### R-014 — calculo (alta) · pendiente

Deducible: si el tipo de póliza es FIJO se usa el valor de la póliza tal cual (sin mínimo). Cualquier otro tipo (en la práctica PORCENTAJE, por el CHECK de la tabla) se calcula como ROUND(monto_base * valor / 100, 2) sobre el MONTO BASE (no sobre el reclamado); si el resultado es estrictamente menor a DEDUCIBLE_MINIMO (100) se sustituye por el mínimo y se marca DEDUCIBLE_MINIMO. El deducible fijo puede superar la base y dar cubierto negativo (ver R-016).

- **Condición:** siempre; rama según deducible_tipo
- **Acción:** calcula deducible y marca DEDUCIBLE_MINIMO si aplica el mínimo
- **Parámetros:** `{"deducible_minimo": 100, "operador_minimo": "<", "decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 189: `IF p_poliza.deducible_tipo = 'FIJO' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 190: `v_deducible := p_poliza.deducible_valor;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 192: `v_ded_minimo := fn_param_num('DEDUCIBLE_MINIMO');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 193: `v_deducible := ROUND(p_monto_base * p_poliza.deducible_valor / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 195: `IF v_deducible < v_ded_minimo THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 196: `v_deducible := v_ded_minimo;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 197: `pr_agregar_obs(p_observaciones, 'DEDUCIBLE_MINIMO');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 497: `v_deducible := fn_calcular_deducible(v_pol, v_cli.categoria, v_monto_base, v_observaciones);`
  - `02_parametros.sql` línea 14: `('DEDUCIBLE_MINIMO', 100,`
- **Preguntas para el dueño del negocio:**
  - ¿El mínimo debería aplicar también al deducible fijo?

### R-015 — calculo (alta) · pendiente

Beneficio VIP: si el cliente es VIP y el deducible resultante (tras el mínimo) es > 0, se reduce en PCT_DESCUENTO_DED_VIP (50) %: ROUND(deducible * (100 - 50) / 100, 2), y se marca DESCUENTO_VIP. Aplica tanto a deducible fijo como porcentual y se hace DESPUÉS del mínimo; con deducible 0 no hay descuento ni marca.

- **Condición:** categoria = 'VIP' AND deducible > 0
- **Acción:** deducible reducido y marca DESCUENTO_VIP
- **Parámetros:** `{"pct_descuento": 50, "operador": ">", "decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 201: `IF p_categoria_cli = c_cat_vip AND v_deducible > 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 202: `v_pct_desc_vip := fn_param_num('PCT_DESCUENTO_DED_VIP');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 203: `v_deducible := ROUND(v_deducible * (100 - v_pct_desc_vip) / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 204: `pr_agregar_obs(p_observaciones, 'DESCUENTO_VIP');`
  - `02_parametros.sql` línea 15: `('PCT_DESCUENTO_DED_VIP', 50,`

### R-016 — calculo (alta) · pendiente

Monto cubierto = ROUND((monto_base - deducible) * porcentaje_cobertura / 100, 2). Si resulta <= 0 (incluye 0) se rechaza con BAJO_DEDUCIBLE: importes en cero pero con las observaciones acumuladas hasta ese punto.

- **Condición:** cubierto <= 0
- **Acción:** pr_rechazar(... 'BAJO_DEDUCIBLE', observaciones) y RETURN
- **Parámetros:** `{"operador": "<=", "valor": 0, "decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 503: `v_cubierto := ROUND((v_monto_base - v_deducible) * v_cob.porcentaje_cobertura / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 505: `IF v_cubierto <= 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 506: `pr_rechazar(v_sin, p_fecha_proceso, 'BAJO_DEDUCIBLE', v_observaciones);`

### R-018 — calculo (alta) · pendiente

Conteo de siniestralidad: cuenta siniestros de la MISMA póliza, distintos del actual, en estado LIQUIDADO (no cuentan PENDIENTE_REVISION ni RECHAZADO), con ocurrencia >= (ocurrencia actual - 365 días) y < ocurrencia actual. Se basa en el estado del siniestro al momento, por lo que los liquidados antes dentro del mismo lote cuentan (el orden por id importa).

- **Condición:** siempre, tras calcular el cubierto
- **Acción:** v_cant_siniestros := COUNT(*)
- **Parámetros:** `{"ventana_dias": 365, "limite_inferior": ">= inclusive", "limite_superior": "< exclusive", "estado_contado": "LIQUIDADO"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 525: `AND s.siniestro_id <> v_sin.siniestro_id`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 526: `AND s.estado = c_sin_liquidado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 527: `AND s.fecha_ocurrencia >= v_sin.fecha_ocurrencia - 365`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 528: `AND s.fecha_ocurrencia < v_sin.fecha_ocurrencia;`
- **Preguntas para el dueño del negocio:**
  - ¿Deben contar también los PENDIENTE_REVISION?

### R-019 — calculo (alta) · pendiente

Penalización por siniestralidad: si la cantidad contada es >= MAX_SINIESTROS_ANUAL (3), el cubierto se reduce PCT_PENALIZACION_SINIEST (10) %: ROUND(cubierto * 90 / 100, 2), con marca PENALIZACION_SINIESTRALIDAD. Se aplica antes del tope de suma asegurada y de la retención.

- **Condición:** conteo >= 3
- **Acción:** cubierto := ROUND(cubierto * (100 - 10) / 100, 2)
- **Parámetros:** `{"max_siniestros": 3, "pct_penalizacion": 10, "operador": ">="}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 530: `IF v_cant_siniestros >= fn_param_num('MAX_SINIESTROS_ANUAL') THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 531: `v_cubierto := ROUND(v_cubierto * (100 - fn_param_num('PCT_PENALIZACION_SINIEST')) / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 532: `pr_agregar_obs(v_observaciones, 'PENALIZACION_SINIESTRALIDAD');`
  - `02_parametros.sql` línea 21: `('MAX_SINIESTROS_ANUAL', 3,`
  - `02_parametros.sql` línea 22: `('PCT_PENALIZACION_SINIEST', 10,`

### R-020 — calculo (alta) · pendiente

Suma asegurada remanente = suma asegurada de la póliza - suma de monto_cubierto de todas las liquidaciones APROBADA o PENDIENTE_APROBACION de los siniestros de esa póliza (sin límite de fecha; incluye las del mismo lote ya procesadas). Las RECHAZADAS no cuentan.

- **Condición:** siempre, tras la penalización
- **Acción:** v_suma_remanente := suma_asegurada - total_indemnizado
- **Parámetros:** `{"estados_sumados": ["APROBADA", "PENDIENTE_APROBACION"]}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 541: `SELECT NVL(SUM(l.monto_cubierto), 0)`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 546: `AND l.estado IN (c_liq_aprobada, c_liq_pend_aprob);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 548: `v_suma_remanente := v_pol.suma_asegurada - v_total_indemnizado;`
- **Preguntas para el dueño del negocio:**
  - ¿La suma asegurada se repone por año/vigencia?

### R-021 — validacion (alta) · pendiente

Si el remanente es <= 0 se rechaza con SUMA_ASEGURADA_AGOTADA (importes cero, con observaciones acumuladas). Si el cubierto es estrictamente mayor al remanente, el cubierto se topa al remanente y se marca TOPE_SUMA_ASEGURADA.

- **Condición:** remanente <= 0; o cubierto > remanente
- **Acción:** rechazo o tope del cubierto
- **Parámetros:** `{"operador_agotada": "<=", "operador_tope": ">"}`
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 550: `IF v_suma_remanente <= 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 551: `pr_rechazar(v_sin, p_fecha_proceso, 'SUMA_ASEGURADA_AGOTADA', v_observaciones);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 555: `IF v_cubierto > v_suma_remanente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 556: `v_cubierto := v_suma_remanente;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 557: `pr_agregar_obs(v_observaciones, 'TOPE_SUMA_ASEGURADA');`

### R-022 — calculo (alta) · pendiente

Retención impositiva: si el ramo no es VIDA y el cubierto final (tras penalización y tope) es estrictamente mayor a UMBRAL_RETENCION (10000), retención = ROUND(cubierto * TASA_RETENCION(2) / 100, 2) y marca RETENCION_APLICADA; si no, retención 0. Con cubierto exactamente 10000 no se retiene. VIDA nunca retiene.

- **Condición:** ramo <> 'VIDA' AND cubierto > 10000
- **Acción:** v_retencion calculada o 0
- **Parámetros:** `{"umbral": 10000, "tasa_pct": 2, "operador": ">", "ramo_excluido": "VIDA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 565: `IF v_pol.ramo <> c_ramo_vida`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 566: `AND v_cubierto > fn_param_num('UMBRAL_RETENCION')`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 568: `v_retencion := ROUND(v_cubierto * fn_param_num('TASA_RETENCION') / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 569: `pr_agregar_obs(v_observaciones, 'RETENCION_APLICADA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 571: `v_retencion := 0;`
  - `02_parametros.sql` línea 25: `('UMBRAL_RETENCION', 10000,`
  - `02_parametros.sql` línea 26: `('TASA_RETENCION', 2,`
- **Preguntas para el dueño del negocio:**
  - ¿La retención es sobre el cubierto completo o solo el exceso del umbral?

### R-023 — calculo (alta) · pendiente

Monto neto = cubierto - retención (sin más redondeo). El neto es el valor que se compara con el tope de aprobación automática.

- **Condición:** siempre, tras la retención
- **Acción:** v_neto := v_cubierto - v_retencion
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 574: `v_neto := v_cubierto - v_retencion;`

### R-024 — validacion (alta) · pendiente

Alerta de fraude: umbral = ROUND(limite_cobertura * PCT_ALERTA_FRAUDE(80) / 100, 2). Si los días desde inicio de póliza son <= DIAS_ALERTA_FRAUDE (15, inclusive) Y el monto RECLAMADO (no la base) es >= umbral, el estado es PENDIENTE_APROBACION con motivo SOSPECHA_FRAUDE. Los importes calculados se registran igual.

- **Condición:** dias_desde_inicio <= 15 AND monto_reclamado >= umbral
- **Acción:** estado PENDIENTE_APROBACION / SOSPECHA_FRAUDE
- **Parámetros:** `{"dias_alerta": 15, "pct_limite": 80, "operador_dias": "<=", "operador_monto": ">="}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 586: `v_umbral_fraude := ROUND(v_cob.limite_cobertura * fn_param_num('PCT_ALERTA_FRAUDE') / 100, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 588: `IF v_dias_desde_inicio <= fn_param_num('DIAS_ALERTA_FRAUDE')`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 589: `AND v_sin.monto_reclamado >= v_umbral_fraude`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 591: `v_estado_liq := c_liq_pend_aprob;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 592: `v_motivo := 'SOSPECHA_FRAUDE';`
  - `02_parametros.sql` línea 30: `('DIAS_ALERTA_FRAUDE', 15,`
  - `02_parametros.sql` línea 31: `('PCT_ALERTA_FRAUDE', 80,`
- **Preguntas para el dueño del negocio:**
  - ¿Debe compararse contra el monto base en vez del reclamado?

### R-025 — validacion (alta) · pendiente

Tope de aprobación automática: si el neto es estrictamente mayor a TOPE_AUTO_APROBACION (50000), el estado es PENDIENTE_APROBACION con motivo SUPERA_TOPE_AUTOMATICO. Con neto exactamente 50000 se aprueba. Si ninguna condición aplica: APROBADA con motivo LIQUIDACION_AUTOMATICA.

- **Condición:** neto > 50000 (y no hay alerta de fraude)
- **Acción:** PENDIENTE_APROBACION / SUPERA_TOPE_AUTOMATICO; si no, APROBADA / LIQUIDACION_AUTOMATICA
- **Parámetros:** `{"tope": 50000, "operador": ">"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 593: `ELSIF v_neto > fn_param_num('TOPE_AUTO_APROBACION') THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 594: `v_estado_liq := c_liq_pend_aprob;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 595: `v_motivo := 'SUPERA_TOPE_AUTOMATICO';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 597: `v_estado_liq := c_liq_aprobada;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 598: `v_motivo := 'LIQUIDACION_AUTOMATICA';`
  - `02_parametros.sql` línea 29: `('TOPE_AUTO_APROBACION', 50000,`

### R-026 — orden (alta) · pendiente

Prioridad del estado final: primero fraude, luego tope automático, y por último aprobada. Si un caso cumple fraude y tope, el motivo es SOSPECHA_FRAUDE.

- **Condición:** tras el cálculo del neto
- **Acción:** IF fraude / ELSIF tope / ELSE aprobada
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 588: `IF v_dias_desde_inicio <= fn_param_num('DIAS_ALERTA_FRAUDE')`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 593: `ELSIF v_neto > fn_param_num('TOPE_AUTO_APROBACION') THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 597: `v_estado_liq := c_liq_aprobada;`

### R-027 — efecto_secundario (alta) · pendiente

Un rechazo registra una liquidación con base, deducible, cubierto, retención y neto en 0, estado RECHAZADA y el motivo dado; las observaciones son opcionales (NULL por defecto). Los rechazos de pasos tempranos no llevan observaciones; BAJO_DEDUCIBLE y SUMA_ASEGURADA_AGOTADA sí arrastran las marcas acumuladas.

- **Condición:** cualquier rechazo
- **Acción:** pr_registrar_resultado con importes 0 y estado RECHAZADA
- **Parámetros:** `{"estado": "RECHAZADA"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 307: `p_observaciones IN VARCHAR2 DEFAULT NULL`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 313: `p_monto_base => 0,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 317: `p_neto => 0,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 318: `p_estado_liq => c_liq_rechazada,`

### R-028 — efecto_secundario (alta) · pendiente

Se inserta una fila en ls_liquidaciones con: id de secuencia, siniestro, fecha de liquidación = fecha de proceso (parámetro), monto reclamado original, base, deducible, cubierto, retención, neto, estado, motivo, observaciones y usuario de sesión (USER).

- **Condición:** toda liquidación (aprobada, pendiente o rechazada)
- **Acción:** INSERT INTO ls_liquidaciones
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 272: `INSERT INTO ls_liquidaciones (`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 277: `seq_ls_liquidacion.NEXTVAL, p_siniestro.siniestro_id, p_fecha_proceso,`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 279: `p_retencion, p_neto, p_estado_liq, p_motivo, p_observaciones, USER`

### R-029 — efecto_secundario (alta) · pendiente

El estado de la liquidación se traduce al del siniestro: APROBADA -> LIQUIDADO, RECHAZADA -> RECHAZADO, PENDIENTE_APROBACION -> PENDIENTE_REVISION. Solo se actualiza la columna ESTADO de ls_siniestros (es el único UPDATE del cuerpo del paquete). Al final se escribe una línea INFO en la bitácora con estado, motivo y neto.

- **Condición:** siempre al registrar el resultado
- **Acción:** UPDATE ls_siniestros SET estado; pr_log INFO
- **Parámetros:** `{"mapa": {"APROBADA": "LIQUIDADO", "RECHAZADA": "RECHAZADO", "PENDIENTE_APROBACION": "PENDIENTE_REVISION"}}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 284: `WHEN c_liq_aprobada THEN c_sin_liquidado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 285: `WHEN c_liq_rechazada THEN c_sin_rechazado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 286: `WHEN c_liq_pend_aprob THEN c_sin_pend_revision`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 290: `SET estado = v_estado_sin`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 295: `' / neto=' || TO_CHAR(p_neto, 'FM999999990.00'));`
- **Comprobación de ausencia:** Solo hay un UPDATE en el cuerpo del paquete (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `^\s*UPDATE\s`: 1 coincidencias, esperado 1)

### R-030 — efecto_secundario (alta) · pendiente

pr_liquidar_siniestro y pr_registrar_resultado no hacen COMMIT: la transacción la controla el llamador (el lote).

- **Condición:** siempre
- **Acción:** sin COMMIT en la liquidación individual
- **Evidencia:**
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 47: `siniestro. NO realiza COMMIT (lo controla el llamador).`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 327: `PROCEDURE pr_liquidar_siniestro (`
- **Comprobación de ausencia:** Sin COMMIT en pr_liquidar_siniestro (`04_pkg_liquidacion_siniestros_body.sql`, líneas 327-617, patrón `\bCOMMIT\b`: 0 coincidencias, esperado 0)
- **Comprobación de ausencia:** Sin COMMIT en pr_registrar_resultado (`04_pkg_liquidacion_siniestros_body.sql`, líneas 258-296, patrón `\bCOMMIT\b`: 0 coincidencias, esperado 0)

### R-031 — efecto_secundario (alta) · pendiente

La bitácora se escribe con transacción autónoma y COMMIT propio, de modo que los logs persisten aunque la liquidación se revierta. El mensaje se trunca a 1000 caracteres.

- **Condición:** cada llamada a pr_log
- **Acción:** INSERT en ls_log_proceso + COMMIT autónomo
- **Parámetros:** `{"max_mensaje": 1000}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 86: `PRAGMA AUTONOMOUS_TRANSACTION;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 89: `VALUES (seq_ls_log.NEXTVAL, SYSDATE, p_nivel, p_siniestro_id, SUBSTR(p_mensaje, 1, 1000));`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 90: `COMMIT;`

### R-032 — orden (alta) · pendiente

El lote toma siniestros REGISTRADO con fecha de denuncia <= fecha de proceso (inclusive), en orden ascendente de siniestro_id. Los denunciados después de la fecha de corte quedan sin tocar. Sin fecha, el valor por defecto es TRUNC(SYSDATE). El script de ejecución usa la fecha de corte 2026-03-31.

- **Condición:** pr_procesar_lote
- **Acción:** cursor ordenado por siniestro_id
- **Parámetros:** `{"operador": "<=", "orden": "siniestro_id ASC", "fecha_corte_script": "2026-03-31"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 628: `WHERE s.estado = c_sin_registrado`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 629: `AND s.fecha_denuncia <= p_fecha_proceso`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 630: `ORDER BY s.siniestro_id;`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 73: `p_fecha_proceso IN DATE DEFAULT TRUNC(SYSDATE)`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 72: `PROCEDURE pr_procesar_lote (`
  - `ejecutar_lote.sql` línea 9: `pkg_liquidacion_siniestros.pr_procesar_lote(p_fecha_proceso => DATE '2026-03-31');`
- **Preguntas para el dueño del negocio:**
  - ¿La fecha de proceso puede llevar hora? Afecta el borde <=.

### R-033 — error (alta) · pendiente

Cada siniestro del lote se procesa aislado con SAVEPOINT. Cualquier excepción (WHEN OTHERS) revierte solo ese siniestro al savepoint, suma 1 a errores, escribe un log ERROR con SQLERRM y el lote continúa. El siniestro queda en REGISTRADO.

- **Condición:** excepción al liquidar un siniestro
- **Acción:** ROLLBACK TO savepoint, contador de errores, log ERROR
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 649: `SAVEPOINT sp_siniestro;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 651: `pr_liquidar_siniestro(r.siniestro_id, p_fecha_proceso);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 672: `WHEN OTHERS THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 673: `ROLLBACK TO sp_siniestro;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 674: `v_cant_errores := v_cant_errores + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 675: `pr_log('ERROR', r.siniestro_id, SQLERRM);`
  - `03_pkg_liquidacion_siniestros_spec.sql` línea 57: `PROCEDURE pr_liquidar_siniestro (`

### R-034 — calculo (alta) · pendiente

Tras cada siniestro el lote relee su estado final y lo cuenta: LIQUIDADO -> liquidados (y suma el monto neto de su liquidación APROBADA al total neto aprobado), RECHAZADO -> rechazados, PENDIENTE_REVISION -> pendientes. Los pendientes NO suman al total neto. También se acumula el monto reclamado procesado, que no se imprime.

- **Condición:** después de cada liquidación sin error
- **Acción:** actualiza contadores y total neto aprobado
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 646: `v_cant_procesados := v_cant_procesados + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 647: `v_total_reclamado := v_total_reclamado + r.monto_reclamado;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 657: `IF v_estado_final = c_sin_liquidado THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 658: `v_cant_liquidados := v_cant_liquidados + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 663: `AND estado = c_liq_aprobada;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 665: `v_total_neto_aprob := v_total_neto_aprob + v_neto_sin;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 666: `ELSIF v_estado_final = c_sin_rechazado THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 667: `v_cant_rechazados := v_cant_rechazados + 1;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 668: `ELSIF v_estado_final = c_sin_pend_revision THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 669: `v_cant_pendientes := v_cant_pendientes + 1;`
- **Comprobación de ausencia:** El total reclamado no se imprime en el resumen (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `PUT_LINE.*v_total_reclamado`: 0 coincidencias, esperado 0)
- **Preguntas para el dueño del negocio:**
  - ¿El resumen debería mostrar el total reclamado y el neto pendiente?

### R-035 — efecto_secundario (alta) · pendiente

Al terminar el bucle el lote hace COMMIT único de todo lo procesado y registra en bitácora INFO el inicio y el fin (con los contadores).

- **Condición:** fin del lote
- **Acción:** COMMIT; pr_log INFO de inicio y fin
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 642: `pr_log('INFO', NULL, 'Inicio lote de liquidacion. Fecha proceso: ' ||`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 679: `COMMIT;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 681: `pr_log('INFO', NULL, 'Fin lote. Procesados=' || v_cant_procesados ||`

### R-037 — redondeo (media) · pendiente

Convención de redondeo: cada operación de porcentaje (deducible porcentual, descuento VIP, cubierto, penalización, retención, umbral de fraude) se redondea a 2 decimales con ROUND inmediatamente; los importes locales y de tabla son NUMBER(14,2). El neto no se redondea de nuevo. Se asume que ROUND de Oracle es mitad hacia arriba (no probado por ejecución).

- **Condición:** cada cálculo porcentual
- **Acción:** ROUND(x, 2)
- **Parámetros:** `{"decimales": 2}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 50: `* Todos los importes calculados se redondean a 2 decimales con ROUND`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 347: `v_cubierto NUMBER(14,2) := 0;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 185: `v_deducible NUMBER(14,2);`
- **Preguntas para el dueño del negocio:**
  - ¿Se confirma redondeo mitad hacia arriba?

### R-038 — calculo (alta) · pendiente

Las marcas de observación se concatenan con ';': la primera sin separador (observaciones NULL), las siguientes con ';' delante. La variable v_observaciones (VARCHAR2(400)) empieza vacía.

- **Condición:** cada vez que se agrega una marca
- **Acción:** concatenar marca
- **Parámetros:** `{"separador": ";"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 61: `c_separador_obs CONSTANT VARCHAR2(1) := ';';`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 123: `IF p_observaciones IS NULL THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 124: `p_observaciones := p_marca;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 126: `p_observaciones := p_observaciones || c_separador_obs || p_marca;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 352: `v_observaciones VARCHAR2(400);`

### R-039 — tasas (alta) · pendiente

Tabla de parámetros cargada: DIAS_MAX_DENUNCIA 30, DIAS_MAX_DENUNCIA_VIDA 365, DEDUCIBLE_MINIMO 100, PCT_DESCUENTO_DED_VIP 50, TOLERANCIA_MORA_VIP 500, MAX_SINIESTROS_ANUAL 3, PCT_PENALIZACION_SINIEST 10, UMBRAL_RETENCION 10000, TASA_RETENCION 2, TOPE_AUTO_APROBACION 50000, DIAS_ALERTA_FRAUDE 15, PCT_ALERTA_FRAUDE 80, FACTOR_INFLACION 1.035, TASA_IVA 19, VERSION_MOTOR '3.2.0' (texto). TASA_IVA y FACTOR_INFLACION no afectan el resultado de la liquidación (ver R-004 y R-042/R-043).

- **Condición:** carga de parámetros
- **Acción:** INSERT en ls_parametros
- **Parámetros:** `{"TASA_IVA": 19, "VERSION_MOTOR": "3.2.0"}`
- **Evidencia:**
  - `02_parametros.sql` línea 35: `('TASA_IVA', 19,`
  - `02_parametros.sql` línea 36: `('VERSION_MOTOR', NULL, '3.2.0'`
- **Preguntas para el dueño del negocio:**
  - ¿Los parámetros son configurables por ambiente o fijos?

### R-040 — validacion (alta) · pendiente

Dominios de valores impuestos por la base de datos: categoría de cliente (VIP, PREFERENTE, ESTANDAR), ramo (AUTO, HOGAR, SALUD, VIDA), estado de póliza (VIGENTE, CANCELADA, SUSPENDIDA), tipo de deducible (FIJO, PORCENTAJE), estado de siniestro (REGISTRADO, LIQUIDADO, RECHAZADO, PENDIENTE_REVISION) y de liquidación (APROBADA, RECHAZADA, PENDIENTE_APROBACION). Por el CHECK de tipo de deducible, la rama 'distinto de FIJO' del cálculo equivale a PORCENTAJE.

- **Condición:** inserción/actualización en tablas
- **Acción:** CHECK constraints
- **Evidencia:**
  - `01_ddl_tablas.sql` línea 34: `CONSTRAINT ck_ls_cli_categoria CHECK (categoria IN ('VIP','PREFERENTE','ESTANDAR'))`
  - `01_ddl_tablas.sql` línea 59: `CONSTRAINT ck_ls_pol_ramo CHECK (ramo IN ('AUTO','HOGAR','SALUD','VIDA'))`
  - `01_ddl_tablas.sql` línea 60: `CONSTRAINT ck_ls_pol_estado CHECK (estado IN ('VIGENTE','CANCELADA','SUSPENDIDA'))`
  - `01_ddl_tablas.sql` línea 61: `CONSTRAINT ck_ls_pol_ded_tipo CHECK (deducible_tipo IN ('FIJO','PORCENTAJE'))`
  - `01_ddl_tablas.sql` línea 96: `CONSTRAINT ck_ls_sin_estado CHECK (estado IN ('REGISTRADO','LIQUIDADO','RECHAZADO','PENDIENTE_REVISION'))`
  - `01_ddl_tablas.sql` línea 124: `CONSTRAINT ck_ls_liq_estado CHECK (estado IN ('APROBADA','RECHAZADA','PENDIENTE_APROBACION'))`

### R-004 — efecto_secundario (alta) · pendiente

FACTOR_INFLACION se lee al inicio de cada liquidación, antes de cualquier validación, pero la variable no se usa después en pr_liquidar_siniestro. Efecto real: si el parámetro falta, TODO siniestro falla con ORA-20010 aunque fuera a rechazarse.

- **Condición:** siempre, tras cargar siniestro/póliza/cliente
- **Acción:** v_factor_inflacion := fn_param_num('FACTOR_INFLACION')
- **Parámetros:** `{"parametro": "FACTOR_INFLACION", "valor": 1.035}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 375: `v_factor_inflacion := fn_param_num('FACTOR_INFLACION');`
  - `02_parametros.sql` línea 34: `('FACTOR_INFLACION', 1.035,`
- **Preguntas para el dueño del negocio:**
  - ¿Es intencional leer el factor sin usarlo?

### R-012 — efecto_secundario (alta) · pendiente

Código inalcanzable: el bloque que registra advertencia WARN en bitácora y cuenta pólizas SUSPENDIDA nunca se ejecuta, porque antes (R-006) toda póliza distinta de VIGENTE ya fue rechazada. En la práctica una póliza suspendida se rechaza sin log WARN.

- **Condición:** póliza SUSPENDIDA tras superar el control de vigente (imposible)
- **Acción:** pr_log('WARN') y contador auxiliar (v_contador_aux no se usa después)
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 386: `IF v_pol.estado <> c_poliza_vigente THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 465: `IF v_pol.estado = 'SUSPENDIDA' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 466: `pr_log('WARN', v_sin.siniestro_id, 'Poliza suspendida: ' || v_pol.numero_poliza);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 467: `v_contador_aux := v_contador_aux + 1;`
- **Preguntas para el dueño del negocio:**
  - ¿Debe registrarse el WARN para suspendidas o se rechazan siempre?

### R-017 — error (alta) · pendiente

Código inalcanzable: tras rechazar cuando cubierto <= 0, la comprobación cubierto < 0 que lanzaría e_monto_invalido nunca puede cumplirse. La excepción no tiene manejador propio.

- **Condición:** cubierto < 0 (imposible tras R-016)
- **Acción:** poner cubierto en 0 y RAISE e_monto_invalido
- **Evidencia:** (en orden de ejecución)
  - `04_pkg_liquidacion_siniestros_body.sql` línea 505: `IF v_cubierto <= 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 510: `IF v_cubierto < 0 THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 512: `RAISE e_monto_invalido;`

### R-036 — efecto_secundario (alta) · pendiente

Resumen del lote por DBMS_OUTPUT: líneas de texto con fecha de proceso (YYYY-MM-DD) y contadores; el total neto aprobado se formatea FM999999990.00. Es formato de salida, sin regla de negocio.

- **Condición:** fin del lote
- **Acción:** DBMS_OUTPUT.PUT_LINE
- **Parámetros:** `{"formato_importe": "FM999999990.00"}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 688: `DBMS_OUTPUT.PUT_LINE(' RESUMEN LOTE DE LIQUIDACION');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 695: `DBMS_OUTPUT.PUT_LINE(' Total neto aprobado: ' || TO_CHAR(v_total_neto_aprob, 'FM999999990.00'));`

### R-041 — fechas (alta) · pendiente

fn_es_dia_habil (lunes a viernes, sin tabla de festivos) está definida pero nunca se invoca y es privada (no está en la especificación). No influye en ningún resultado: los plazos son días calendario. La función depende del idioma NLS forzado a ENGLISH (no probado por ejecución).

- **Condición:** nunca se ejecuta
- **Acción:** devuelve TRUE si el día no es SAT ni SUN
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 137: `v_dia := TO_CHAR(p_fecha, 'DY', 'NLS_DATE_LANGUAGE=ENGLISH');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 138: `RETURN v_dia NOT IN ('SAT', 'SUN');`
- **Comprobación de ausencia:** Solo la definición de fn_es_dia_habil; ninguna llamada (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `fn_es_dia_habil\s*\(`: 1 coincidencias, esperado 1)
- **Comprobación de ausencia:** Funciones privadas ausentes de la especificación (`03_pkg_liquidacion_siniestros_spec.sql`, líneas 1-77, patrón `fn_es_dia_habil|fn_calcular_iva|pr_recalcular_reserva_tecnica|pr_enviar_notificacion|fn_calcular_deducible`: 0 coincidencias, esperado 0)
- **Preguntas para el dueño del negocio:**
  - ¿Debería usarse el día hábil en algún plazo?

### R-042 — calculo (alta) · pendiente

fn_calcular_iva (ROUND(monto * TASA_IVA / 100, 2)) existe pero nunca se invoca. No hay IVA en el resultado de la liquidación.

- **Condición:** nunca se ejecuta
- **Acción:** calcula IVA
- **Parámetros:** `{"tasa_iva": 19}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 217: `v_tasa := fn_param_num('TASA_IVA');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 218: `RETURN ROUND(p_monto * v_tasa / 100, 2);`
- **Comprobación de ausencia:** Solo la definición de fn_calcular_iva (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `fn_calcular_iva\s*\(`: 1 coincidencias, esperado 1)
- **Preguntas para el dueño del negocio:**
  - ¿Se prevé aplicar IVA a la indemnización?

### R-043 — efecto_secundario (alta) · pendiente

pr_recalcular_reserva_tecnica (borra ls_tmp_calculo_2009 y la llena con reserva = ROUND(reclamado * FACTOR_INFLACION, 2) de siniestros LIQUIDADO de años anteriores) nunca se invoca; no afecta la liquidación.

- **Condición:** nunca se ejecuta
- **Acción:** DELETE y INSERT en tabla temporal
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 229: `v_factor := fn_param_num('FACTOR_INFLACION');`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 231: `DELETE FROM ls_tmp_calculo_2009;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 235: `VALUES (r.siniestro_id, ROUND(r.monto_reclamado * v_factor, 2), SYSDATE);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 72: `WHERE EXTRACT(YEAR FROM s.fecha_ocurrencia) < p_anio`
- **Comprobación de ausencia:** Solo la definición del procedimiento (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `pr_recalcular_reserva_tecnica\s*\(`: 1 coincidencias, esperado 1)

### R-044 — calculo (alta) · pendiente

fn_calcular_deducible_v1 (versión 2009) no se invoca: solo aparece su definición y una llamada dentro de comentario. Truncaba (TRUNC a 2) en vez de redondear, sin mínimo; las líneas posteriores al RETURN son inalcanzables.

- **Condición:** nunca se ejecuta
- **Acción:** deducible fijo/porcentaje truncado
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 153: `IF p_deducible_tipo = 'FIJO' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 155: `ELSIF p_deducible_tipo = 'PORCENTAJE' THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 159: `RETURN TRUNC(v_deducible, 2);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 162: `v_deducible := v_deducible * 1.0;`
- **Comprobación de ausencia:** Definición y llamada comentada solamente (`04_pkg_liquidacion_siniestros_body.sql`, líneas 1-700, patrón `fn_calcular_deducible_v1\s*\(`: 2 coincidencias, esperado 2)

### R-045 — efecto_secundario (alta) · pendiente

Modo debug: c_modo_debug es constante FALSE, por lo que nunca se imprime la traza DEBUG ni se llama pr_enviar_notificacion (que solo imprime por DBMS_OUTPUT, sin envío real). La traza de debug incluiría el nombre del cliente (dato personal) si se activara: hallazgo de seguridad menor.

- **Condición:** c_modo_debug = TRUE (nunca)
- **Acción:** DBMS_OUTPUT de traza y notificación
- **Parámetros:** `{"c_modo_debug": false}`
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 60: `c_modo_debug CONSTANT BOOLEAN := FALSE;`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 377: `IF c_modo_debug THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 380: `' cliente=' || v_cli.nombre);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 614: `IF c_modo_debug THEN`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 249: `v_mensaje := 'Su siniestro ' || p_siniestro_id || ' fue ' || LOWER(p_estado);`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 251: `DBMS_OUTPUT.PUT_LINE('[NOTIFICACION] ' || v_mensaje);`

### R-046 — calculo (alta) · pendiente

Bloque comentado /* ... */ con el cálculo original de 2009 (reemplazado en SIN-0310). No se ejecuta; su línea IF dentro del comentario no es decisión real.

- **Condición:** nunca (comentado)
- **Acción:** ninguna
- **Evidencia:**
  - `04_pkg_liquidacion_siniestros_body.sql` línea 471: `-- SIN-0001 (2009): calculo original, reemplazado en SIN-0310`
  - `04_pkg_liquidacion_siniestros_body.sql` línea 477: `IF v_cubierto > v_pol.suma_asegurada THEN`

## Glosario de variables

| Variable | Significado |
|---|---|
| `v_monto_base` | monto reclamado topado por el límite de la cobertura |
| `v_dias_desde_inicio` | días entre inicio de póliza y ocurrencia; sirve para carencia y alerta de fraude |
| `v_suma_remanente` | suma asegurada disponible tras indemnizaciones aprobadas o pendientes |
| `v_cubierto` | monto que paga la aseguradora antes de retención |
| `v_neto` | cubierto menos retención impositiva |
| `PRIMA_PENDIENTE` | prima vencida no pagada (mora) |
| `DIAS_CARENCIA` | días desde inicio de póliza en que la cobertura aún no está activa |
| `TOLERANCIA_MORA_VIP` | deuda de prima tolerada a clientes VIP |
| `SOSPECHA_FRAUDE` | siniestro temprano de monto alto, pasa a revisión manual |
| `PENDIENTE_REVISION` | estado del siniestro cuya liquidación espera aprobación |
