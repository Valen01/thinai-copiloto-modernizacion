CREATE OR REPLACE PACKAGE BODY pkg_liquidacion_siniestros AS
/*******************************************************************************
 * SISTEMA      : SIGSE - Sistema Integral de Gestion de Seguros
 * MODULO       : SINIESTROS
 * OBJETO       : PKG_LIQUIDACION_SINIESTROS (cuerpo)
 * DESCRIPCION  : Implementacion del motor de liquidacion de siniestros.
 *
 * FLUJO GENERAL DE LIQUIDACION (pr_liquidar_siniestro)
 * -----------------------------------------------------------------------------
 *   1. Validaciones de procedencia (cualquier fallo => RECHAZADO):
 *        a) Estado de la poliza.
 *        b) Ocurrencia dentro de la vigencia.
 *        c) Plazo de denuncia.
 *        d) Cobertura contratada.
 *        e) Periodo de carencia.
 *        f) Morosidad de prima.
 *   2. Calculo de la indemnizacion:
 *        a) Monto base (tope por limite de cobertura).
 *        b) Deducible (fijo / porcentual, minimo, beneficio VIP).
 *        c) Monto cubierto (% de cobertura).
 *        d) Penalizacion por siniestralidad.
 *        e) Tope por suma asegurada remanente.
 *        f) Retencion impositiva y monto neto.
 *   3. Determinacion del estado final:
 *        a) Alerta de fraude          => PENDIENTE_APROBACION.
 *        b) Supera tope automatico    => PENDIENTE_APROBACION.
 *        c) Caso contrario            => APROBADA.
 *
 * CODIGOS DE MOTIVO (LS_LIQUIDACIONES.MOTIVO)
 * -----------------------------------------------------------------------------
 *   LIQUIDACION_AUTOMATICA  Liquidacion aprobada sin intervencion.
 *   SUPERA_TOPE_AUTOMATICO  Neto mayor al tope de aprobacion automatica.
 *   SOSPECHA_FRAUDE         Siniestro con alerta de fraude.
 *   POLIZA_NO_VIGENTE       Poliza cancelada o suspendida.
 *   FUERA_DE_VIGENCIA       Ocurrencia fuera del periodo de vigencia.
 *   DENUNCIA_EXTEMPORANEA   Denuncia presentada fuera de plazo.
 *   COBERTURA_NO_CONTRATADA La poliza no tiene la cobertura reclamada.
 *   EN_PERIODO_CARENCIA     Ocurrencia dentro del periodo de carencia.
 *   PRIMA_EN_MORA           Poliza con prima pendiente de pago.
 *   BAJO_DEDUCIBLE          El monto cubierto resultante es <= 0.
 *   SUMA_ASEGURADA_AGOTADA  No queda suma asegurada disponible.
 *
 * MARCAS DE OBSERVACION (LS_LIQUIDACIONES.OBSERVACIONES, separadas por ';')
 * -----------------------------------------------------------------------------
 *   TOLERANCIA_MORA_VIP, LIMITE_COBERTURA, DEDUCIBLE_MINIMO, DESCUENTO_VIP,
 *   PENALIZACION_SINIESTRALIDAD, TOPE_SUMA_ASEGURADA, RETENCION_APLICADA
 *
 * CONVENCION DE REDONDEO
 * -----------------------------------------------------------------------------
 *   Todos los importes calculados se redondean a 2 decimales con ROUND
 *   (mitad hacia arriba) inmediatamente despues de cada operacion de
 *   porcentaje.
 ******************************************************************************/

    ----------------------------------------------------------------------------
    -- Tipos y constantes privadas
    ----------------------------------------------------------------------------
    TYPE t_tab_coberturas IS TABLE OF ls_coberturas%ROWTYPE INDEX BY PLS_INTEGER;

    c_modo_debug      CONSTANT BOOLEAN       := FALSE;
    c_separador_obs   CONSTANT VARCHAR2(1)   := ';';
    c_cat_vip         CONSTANT VARCHAR2(15)  := 'VIP';
    c_ramo_vida       CONSTANT VARCHAR2(10)  := 'VIDA';
    c_poliza_vigente  CONSTANT VARCHAR2(12)  := 'VIGENTE';

    e_monto_invalido  EXCEPTION;

    -- Siniestros de anos anteriores para recalculo de reservas.
    CURSOR cur_siniestros_historicos (p_anio NUMBER) IS
        SELECT s.siniestro_id, s.monto_reclamado
          FROM ls_siniestros s
         WHERE EXTRACT(YEAR FROM s.fecha_ocurrencia) < p_anio
           AND s.estado = 'LIQUIDADO';

    ----------------------------------------------------------------------------
    -- PR_LOG
    --   Registra un mensaje en la bitacora LS_LOG_PROCESO.
    --   Usa transaccion autonoma para que el log persista aun si la
    --   liquidacion del siniestro se revierte.
    ----------------------------------------------------------------------------
    PROCEDURE pr_log (
        p_nivel         IN VARCHAR2,
        p_siniestro_id  IN NUMBER,
        p_mensaje       IN VARCHAR2
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO ls_log_proceso (log_id, fecha_log, nivel, siniestro_id, mensaje)
        VALUES (seq_ls_log.NEXTVAL, SYSDATE, p_nivel, p_siniestro_id, SUBSTR(p_mensaje, 1, 1000));
        COMMIT;
    END pr_log;

    ----------------------------------------------------------------------------
    -- FN_PARAM_NUM
    --   Obtiene el valor numerico de un parametro de negocio.
    --   Lanza ORA-20010 si el parametro no existe.
    ----------------------------------------------------------------------------
    FUNCTION fn_param_num (
        p_cod_parametro IN ls_parametros.cod_parametro%TYPE
    ) RETURN NUMBER IS
        v_valor  ls_parametros.valor_numerico%TYPE;
    BEGIN
        SELECT valor_numerico
          INTO v_valor
          FROM ls_parametros
         WHERE cod_parametro = p_cod_parametro;

        RETURN v_valor;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20010, 'Parametro no definido: ' || p_cod_parametro);
    END fn_param_num;

    ----------------------------------------------------------------------------
    -- PR_AGREGAR_OBS
    --   Agrega una marca al texto de observaciones de la liquidacion.
    ----------------------------------------------------------------------------
    PROCEDURE pr_agregar_obs (
        p_observaciones  IN OUT VARCHAR2,
        p_marca          IN     VARCHAR2
    ) IS
    BEGIN
        IF p_observaciones IS NULL THEN
            p_observaciones := p_marca;
        ELSE
            p_observaciones := p_observaciones || c_separador_obs || p_marca;
        END IF;
    END pr_agregar_obs;

    ----------------------------------------------------------------------------
    -- FN_ES_DIA_HABIL
    --   Indica si una fecha corresponde a un dia habil (lunes a viernes).
    ----------------------------------------------------------------------------
    FUNCTION fn_es_dia_habil (p_fecha IN DATE) RETURN BOOLEAN IS
        v_dia  VARCHAR2(3);
    BEGIN
        v_dia := TO_CHAR(p_fecha, 'DY', 'NLS_DATE_LANGUAGE=ENGLISH');
        RETURN v_dia NOT IN ('SAT', 'SUN');
    END fn_es_dia_habil;

    ----------------------------------------------------------------------------
    -- FN_CALCULAR_DEDUCIBLE_V1
    --   Calculo de deducible (version 2009).
    --   Deducible fijo o porcentual sobre el monto reclamado, sin minimo.
    ----------------------------------------------------------------------------
    FUNCTION fn_calcular_deducible_v1 (
        p_deducible_tipo   IN VARCHAR2,
        p_deducible_valor  IN NUMBER,
        p_monto_reclamado  IN NUMBER
    ) RETURN NUMBER IS
        v_deducible  NUMBER := 0;
    BEGIN
        IF p_deducible_tipo = 'FIJO' THEN
            v_deducible := p_deducible_valor;
        ELSIF p_deducible_tipo = 'PORCENTAJE' THEN
            v_deducible := p_monto_reclamado * p_deducible_valor / 100;
        END IF;

        RETURN TRUNC(v_deducible, 2);

        -- Ajuste por moneda extranjera
        v_deducible := v_deducible * 1.0;
        RETURN v_deducible;
    END fn_calcular_deducible_v1;

    ----------------------------------------------------------------------------
    -- FN_CALCULAR_DEDUCIBLE
    --   Calcula el deducible aplicable a un siniestro.
    --
    --   * Deducible FIJO       : se toma el valor fijo de la poliza.
    --   * Deducible PORCENTAJE : % sobre el MONTO BASE (no sobre el reclamado),
    --                            redondeado a 2 decimales. Si el resultado es
    --                            menor al parametro DEDUCIBLE_MINIMO se aplica
    --                            el minimo (marca DEDUCIBLE_MINIMO).
    --   * Cliente VIP          : si el deducible resultante es > 0 se reduce en
    --                            PCT_DESCUENTO_DED_VIP % (marca DESCUENTO_VIP).
    --                            El descuento se aplica DESPUES del minimo.
    ----------------------------------------------------------------------------
    FUNCTION fn_calcular_deducible (
        p_poliza         IN            ls_polizas%ROWTYPE,
        p_categoria_cli  IN            ls_clientes.categoria%TYPE,
        p_monto_base     IN            NUMBER,
        p_observaciones  IN OUT NOCOPY VARCHAR2
    ) RETURN NUMBER IS
        v_deducible      NUMBER(14,2);
        v_ded_minimo     NUMBER;
        v_pct_desc_vip   NUMBER;
    BEGIN
        IF p_poliza.deducible_tipo = 'FIJO' THEN
            v_deducible := p_poliza.deducible_valor;
        ELSE
            v_ded_minimo := fn_param_num('DEDUCIBLE_MINIMO');
            v_deducible  := ROUND(p_monto_base * p_poliza.deducible_valor / 100, 2);

            IF v_deducible < v_ded_minimo THEN
                v_deducible := v_ded_minimo;
                pr_agregar_obs(p_observaciones, 'DEDUCIBLE_MINIMO');
            END IF;
        END IF;

        IF p_categoria_cli = c_cat_vip AND v_deducible > 0 THEN
            v_pct_desc_vip := fn_param_num('PCT_DESCUENTO_DED_VIP');
            v_deducible    := ROUND(v_deducible * (100 - v_pct_desc_vip) / 100, 2);
            pr_agregar_obs(p_observaciones, 'DESCUENTO_VIP');
        END IF;

        RETURN v_deducible;
    END fn_calcular_deducible;

    ----------------------------------------------------------------------------
    -- FN_CALCULAR_IVA
    --   Calcula el IVA sobre un monto segun el parametro TASA_IVA.
    ----------------------------------------------------------------------------
    FUNCTION fn_calcular_iva (p_monto IN NUMBER) RETURN NUMBER IS
        v_tasa  NUMBER;
    BEGIN
        v_tasa := fn_param_num('TASA_IVA');
        RETURN ROUND(p_monto * v_tasa / 100, 2);
    END fn_calcular_iva;

    ----------------------------------------------------------------------------
    -- PR_RECALCULAR_RESERVA_TECNICA
    --   Recalcula la reserva tecnica de siniestros historicos aplicando el
    --   factor de inflacion, y la deja en LS_TMP_CALCULO_2009.
    ----------------------------------------------------------------------------
    PROCEDURE pr_recalcular_reserva_tecnica (p_anio IN NUMBER) IS
        v_factor  NUMBER;
    BEGIN
        v_factor := fn_param_num('FACTOR_INFLACION');

        DELETE FROM ls_tmp_calculo_2009;

        FOR r IN cur_siniestros_historicos(p_anio) LOOP
            INSERT INTO ls_tmp_calculo_2009 (siniestro_id, reserva_tecnica, fecha_calculo)
            VALUES (r.siniestro_id, ROUND(r.monto_reclamado * v_factor, 2), SYSDATE);
        END LOOP;
    END pr_recalcular_reserva_tecnica;

    ----------------------------------------------------------------------------
    -- PR_ENVIAR_NOTIFICACION
    --   Notifica al asegurado el resultado de la liquidacion.
    ----------------------------------------------------------------------------
    PROCEDURE pr_enviar_notificacion (
        p_siniestro_id  IN NUMBER,
        p_estado        IN VARCHAR2
    ) IS
        v_mensaje  VARCHAR2(500);
    BEGIN
        v_mensaje := 'Su siniestro ' || p_siniestro_id || ' fue ' || LOWER(p_estado);
        -- UTL_MAIL.SEND(sender => 'siniestros@aseguradora.com', recipients => ..., message => v_mensaje);
        DBMS_OUTPUT.PUT_LINE('[NOTIFICACION] ' || v_mensaje);
    END pr_enviar_notificacion;

    ----------------------------------------------------------------------------
    -- PR_REGISTRAR_RESULTADO
    --   Inserta la liquidacion y actualiza el estado del siniestro.
    ----------------------------------------------------------------------------
    PROCEDURE pr_registrar_resultado (
        p_siniestro       IN ls_siniestros%ROWTYPE,
        p_fecha_proceso   IN DATE,
        p_monto_base      IN NUMBER,
        p_deducible       IN NUMBER,
        p_cubierto        IN NUMBER,
        p_retencion       IN NUMBER,
        p_neto            IN NUMBER,
        p_estado_liq      IN VARCHAR2,
        p_motivo          IN VARCHAR2,
        p_observaciones   IN VARCHAR2
    ) IS
        v_estado_sin  ls_siniestros.estado%TYPE;
    BEGIN
        INSERT INTO ls_liquidaciones (
            liquidacion_id, siniestro_id, fecha_liquidacion, monto_reclamado,
            monto_base, monto_deducible, monto_cubierto, monto_retencion,
            monto_neto, estado, motivo, observaciones, usuario_proceso
        ) VALUES (
            seq_ls_liquidacion.NEXTVAL, p_siniestro.siniestro_id, p_fecha_proceso,
            p_siniestro.monto_reclamado, p_monto_base, p_deducible, p_cubierto,
            p_retencion, p_neto, p_estado_liq, p_motivo, p_observaciones, USER
        );

        -- Correspondencia estado liquidacion -> estado siniestro
        v_estado_sin := CASE p_estado_liq
                            WHEN c_liq_aprobada   THEN c_sin_liquidado
                            WHEN c_liq_rechazada  THEN c_sin_rechazado
                            WHEN c_liq_pend_aprob THEN c_sin_pend_revision
                        END;

        UPDATE ls_siniestros
           SET estado = v_estado_sin
         WHERE siniestro_id = p_siniestro.siniestro_id;

        pr_log('INFO', p_siniestro.siniestro_id,
               'Resultado: ' || p_estado_liq || ' / ' || p_motivo ||
               ' / neto=' || TO_CHAR(p_neto, 'FM999999990.00'));
    END pr_registrar_resultado;

    ----------------------------------------------------------------------------
    -- PR_RECHAZAR
    --   Registra un rechazo: liquidacion con importes en cero, estado
    --   RECHAZADA y el motivo indicado. El siniestro pasa a RECHAZADO.
    ----------------------------------------------------------------------------
    PROCEDURE pr_rechazar (
        p_siniestro      IN ls_siniestros%ROWTYPE,
        p_fecha_proceso  IN DATE,
        p_motivo         IN VARCHAR2,
        p_observaciones  IN VARCHAR2 DEFAULT NULL
    ) IS
    BEGIN
        pr_registrar_resultado(
            p_siniestro     => p_siniestro,
            p_fecha_proceso => p_fecha_proceso,
            p_monto_base    => 0,
            p_deducible     => 0,
            p_cubierto      => 0,
            p_retencion     => 0,
            p_neto          => 0,
            p_estado_liq    => c_liq_rechazada,
            p_motivo        => p_motivo,
            p_observaciones => p_observaciones
        );
    END pr_rechazar;

    ----------------------------------------------------------------------------
    -- PR_LIQUIDAR_SINIESTRO  (publico)
    ----------------------------------------------------------------------------
    PROCEDURE pr_liquidar_siniestro (
        p_siniestro_id   IN ls_siniestros.siniestro_id%TYPE,
        p_fecha_proceso  IN DATE
    ) IS
        v_sin                ls_siniestros%ROWTYPE;
        v_pol                ls_polizas%ROWTYPE;
        v_cli                ls_clientes%ROWTYPE;
        v_cob                ls_coberturas%ROWTYPE;

        v_dias_denuncia      NUMBER;
        v_dias_max_denuncia  NUMBER;
        v_dias_desde_inicio  NUMBER;
        v_tolerancia_mora    NUMBER;
        v_cant_siniestros    NUMBER;
        v_total_indemnizado  NUMBER;
        v_suma_remanente     NUMBER;
        v_umbral_fraude      NUMBER;

        v_monto_base         NUMBER(14,2) := 0;
        v_deducible          NUMBER(14,2) := 0;
        v_cubierto           NUMBER(14,2) := 0;
        v_retencion          NUMBER(14,2) := 0;
        v_neto               NUMBER(14,2) := 0;
        v_estado_liq         ls_liquidaciones.estado%TYPE;
        v_motivo             ls_liquidaciones.motivo%TYPE;
        v_observaciones      VARCHAR2(400);

        v_factor_inflacion   NUMBER;
        v_contador_aux       PLS_INTEGER := 0;
        v_fecha_proceso_ant  DATE;
    BEGIN
        ------------------------------------------------------------------------
        -- Carga de datos del siniestro, poliza y cliente
        ------------------------------------------------------------------------
        SELECT *
          INTO v_sin
          FROM ls_siniestros
         WHERE siniestro_id = p_siniestro_id
           FOR UPDATE;

        IF v_sin.estado <> c_sin_registrado THEN
            RAISE_APPLICATION_ERROR(-20001,
                'El siniestro ' || p_siniestro_id || ' no esta en estado REGISTRADO (' || v_sin.estado || ')');
        END IF;

        SELECT * INTO v_pol FROM ls_polizas  WHERE poliza_id  = v_sin.poliza_id;
        SELECT * INTO v_cli FROM ls_clientes WHERE cliente_id = v_pol.cliente_id;

        v_factor_inflacion := fn_param_num('FACTOR_INFLACION');

        IF c_modo_debug THEN
            DBMS_OUTPUT.PUT_LINE('DEBUG siniestro=' || v_sin.siniestro_id ||
                                 ' poliza=' || v_pol.numero_poliza ||
                                 ' cliente=' || v_cli.nombre);
        END IF;

        ------------------------------------------------------------------------
        -- 1.a  Estado de la poliza: solo se liquidan polizas VIGENTES.
        ------------------------------------------------------------------------
        IF v_pol.estado <> c_poliza_vigente THEN
            pr_rechazar(v_sin, p_fecha_proceso, 'POLIZA_NO_VIGENTE');
            RETURN;
        END IF;

        ------------------------------------------------------------------------
        -- 1.b  La fecha de ocurrencia debe estar dentro de la vigencia
        --      [fecha_inicio, fecha_fin] (ambos extremos inclusive).
        ------------------------------------------------------------------------
        IF v_sin.fecha_ocurrencia < v_pol.fecha_inicio
           OR v_sin.fecha_ocurrencia > v_pol.fecha_fin
        THEN
            pr_rechazar(v_sin, p_fecha_proceso, 'FUERA_DE_VIGENCIA');
            RETURN;
        END IF;

        ------------------------------------------------------------------------
        -- 1.c  Plazo de denuncia: dias entre ocurrencia y denuncia no puede
        --      superar DIAS_MAX_DENUNCIA (VIDA: DIAS_MAX_DENUNCIA_VIDA).
        --      El dia limite es inclusive.
        ------------------------------------------------------------------------
        v_dias_denuncia := TRUNC(v_sin.fecha_denuncia) - TRUNC(v_sin.fecha_ocurrencia);

        IF v_pol.ramo = c_ramo_vida THEN
            v_dias_max_denuncia := fn_param_num('DIAS_MAX_DENUNCIA_VIDA');
        ELSE
            v_dias_max_denuncia := fn_param_num('DIAS_MAX_DENUNCIA');
        END IF;

        IF v_dias_denuncia > v_dias_max_denuncia THEN
            pr_rechazar(v_sin, p_fecha_proceso, 'DENUNCIA_EXTEMPORANEA');
            RETURN;
        END IF;

        ------------------------------------------------------------------------
        -- 1.d  La cobertura reclamada debe estar contratada en la poliza.
        ------------------------------------------------------------------------
        BEGIN
            SELECT *
              INTO v_cob
              FROM ls_coberturas
             WHERE poliza_id     = v_sin.poliza_id
               AND cod_cobertura = v_sin.cod_cobertura;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                pr_rechazar(v_sin, p_fecha_proceso, 'COBERTURA_NO_CONTRATADA');
                RETURN;
        END;

        ------------------------------------------------------------------------
        -- 1.e  Periodo de carencia: la cobertura se activa cuando han
        --      transcurrido al menos DIAS_CARENCIA dias desde el inicio de la
        --      poliza hasta la ocurrencia.
        ------------------------------------------------------------------------
        v_dias_desde_inicio := TRUNC(v_sin.fecha_ocurrencia) - TRUNC(v_pol.fecha_inicio);

        IF v_dias_desde_inicio < v_cob.dias_carencia THEN
            pr_rechazar(v_sin, p_fecha_proceso, 'EN_PERIODO_CARENCIA');
            RETURN;
        END IF;

        ------------------------------------------------------------------------
        -- 1.f  Morosidad: con prima pendiente > 0 se rechaza, salvo clientes
        --      VIP cuya deuda sea <= TOLERANCIA_MORA_VIP.
        ------------------------------------------------------------------------
        IF v_pol.prima_pendiente > 0 THEN
            v_tolerancia_mora := fn_param_num('TOLERANCIA_MORA_VIP');

            IF v_cli.categoria = c_cat_vip
               AND v_pol.prima_pendiente <= v_tolerancia_mora
            THEN
                pr_agregar_obs(v_observaciones, 'TOLERANCIA_MORA_VIP');
            ELSE
                pr_rechazar(v_sin, p_fecha_proceso, 'PRIMA_EN_MORA', v_observaciones);
                RETURN;
            END IF;
        END IF;

        -- Polizas suspendidas: registrar advertencia en bitacora
        IF v_pol.estado = 'SUSPENDIDA' THEN
            pr_log('WARN', v_sin.siniestro_id, 'Poliza suspendida: ' || v_pol.numero_poliza);
            v_contador_aux := v_contador_aux + 1;
        END IF;

        /*
        -- SIN-0001 (2009): calculo original, reemplazado en SIN-0310
        v_monto_base := v_sin.monto_reclamado;
        v_deducible  := fn_calcular_deducible_v1(v_pol.deducible_tipo,
                                                 v_pol.deducible_valor,
                                                 v_sin.monto_reclamado);
        v_cubierto   := v_monto_base - v_deducible;
        IF v_cubierto > v_pol.suma_asegurada THEN
            v_cubierto := v_pol.suma_asegurada;
        END IF;
        v_neto := v_cubierto;
        */

        ------------------------------------------------------------------------
        -- 2.a  Monto base: el menor entre lo reclamado y el limite de la
        --      cobertura (marca LIMITE_COBERTURA si se topa).
        ------------------------------------------------------------------------
        IF v_sin.monto_reclamado > v_cob.limite_cobertura THEN
            v_monto_base := v_cob.limite_cobertura;
            pr_agregar_obs(v_observaciones, 'LIMITE_COBERTURA');
        ELSE
            v_monto_base := v_sin.monto_reclamado;
        END IF;

        ------------------------------------------------------------------------
        -- 2.b  Deducible (ver fn_calcular_deducible).
        ------------------------------------------------------------------------
        v_deducible := fn_calcular_deducible(v_pol, v_cli.categoria, v_monto_base, v_observaciones);

        ------------------------------------------------------------------------
        -- 2.c  Monto cubierto = (monto base - deducible) * % cobertura.
        --      Si el resultado es <= 0, se rechaza por BAJO_DEDUCIBLE.
        ------------------------------------------------------------------------
        v_cubierto := ROUND((v_monto_base - v_deducible) * v_cob.porcentaje_cobertura / 100, 2);

        IF v_cubierto <= 0 THEN
            pr_rechazar(v_sin, p_fecha_proceso, 'BAJO_DEDUCIBLE', v_observaciones);
            RETURN;
        END IF;

        IF v_cubierto < 0 THEN
            v_cubierto := 0;
            RAISE e_monto_invalido;
        END IF;

        ------------------------------------------------------------------------
        -- 2.d  Siniestralidad: si la poliza registra MAX_SINIESTROS_ANUAL o
        --      mas siniestros LIQUIDADOS con ocurrencia en los 365 dias
        --      previos a la ocurrencia actual, se reduce el monto cubierto
        --      en PCT_PENALIZACION_SINIEST %.
        ------------------------------------------------------------------------
        SELECT COUNT(*)
          INTO v_cant_siniestros
          FROM ls_siniestros s
         WHERE s.poliza_id         = v_sin.poliza_id
           AND s.siniestro_id     <> v_sin.siniestro_id
           AND s.estado            = c_sin_liquidado
           AND s.fecha_ocurrencia >= v_sin.fecha_ocurrencia - 365
           AND s.fecha_ocurrencia <  v_sin.fecha_ocurrencia;

        IF v_cant_siniestros >= fn_param_num('MAX_SINIESTROS_ANUAL') THEN
            v_cubierto := ROUND(v_cubierto * (100 - fn_param_num('PCT_PENALIZACION_SINIEST')) / 100, 2);
            pr_agregar_obs(v_observaciones, 'PENALIZACION_SINIESTRALIDAD');
        END IF;

        ------------------------------------------------------------------------
        -- 2.e  Suma asegurada remanente = suma asegurada - suma de montos
        --      cubiertos de liquidaciones APROBADAS o PENDIENTES de la poliza.
        --      Si no hay remanente se rechaza; si el cubierto lo excede se
        --      topa al remanente (marca TOPE_SUMA_ASEGURADA).
        ------------------------------------------------------------------------
        SELECT NVL(SUM(l.monto_cubierto), 0)
          INTO v_total_indemnizado
          FROM ls_liquidaciones l
          JOIN ls_siniestros    s ON s.siniestro_id = l.siniestro_id
         WHERE s.poliza_id = v_sin.poliza_id
           AND l.estado IN (c_liq_aprobada, c_liq_pend_aprob);

        v_suma_remanente := v_pol.suma_asegurada - v_total_indemnizado;

        IF v_suma_remanente <= 0 THEN
            pr_rechazar(v_sin, p_fecha_proceso, 'SUMA_ASEGURADA_AGOTADA', v_observaciones);
            RETURN;
        END IF;

        IF v_cubierto > v_suma_remanente THEN
            v_cubierto := v_suma_remanente;
            pr_agregar_obs(v_observaciones, 'TOPE_SUMA_ASEGURADA');
        END IF;

        ------------------------------------------------------------------------
        -- 2.f  Retencion impositiva: si el ramo no es VIDA y el monto
        --      cubierto supera UMBRAL_RETENCION, se retiene TASA_RETENCION %.
        --      Neto = cubierto - retencion.
        ------------------------------------------------------------------------
        IF v_pol.ramo <> c_ramo_vida
           AND v_cubierto > fn_param_num('UMBRAL_RETENCION')
        THEN
            v_retencion := ROUND(v_cubierto * fn_param_num('TASA_RETENCION') / 100, 2);
            pr_agregar_obs(v_observaciones, 'RETENCION_APLICADA');
        ELSE
            v_retencion := 0;
        END IF;

        v_neto := v_cubierto - v_retencion;

        ------------------------------------------------------------------------
        -- 3.  Estado final
        --   a) Fraude: ocurrencia dentro de los primeros DIAS_ALERTA_FRAUDE
        --      dias de la poliza y reclamo >= PCT_ALERTA_FRAUDE % del limite
        --      de la cobertura => PENDIENTE_APROBACION / SOSPECHA_FRAUDE.
        --   b) Neto > TOPE_AUTO_APROBACION
        --      => PENDIENTE_APROBACION / SUPERA_TOPE_AUTOMATICO.
        --   c) Resto => APROBADA / LIQUIDACION_AUTOMATICA.
        --   La regla de fraude tiene prioridad sobre la de tope.
        ------------------------------------------------------------------------
        v_umbral_fraude := ROUND(v_cob.limite_cobertura * fn_param_num('PCT_ALERTA_FRAUDE') / 100, 2);

        IF v_dias_desde_inicio <= fn_param_num('DIAS_ALERTA_FRAUDE')
           AND v_sin.monto_reclamado >= v_umbral_fraude
        THEN
            v_estado_liq := c_liq_pend_aprob;
            v_motivo     := 'SOSPECHA_FRAUDE';
        ELSIF v_neto > fn_param_num('TOPE_AUTO_APROBACION') THEN
            v_estado_liq := c_liq_pend_aprob;
            v_motivo     := 'SUPERA_TOPE_AUTOMATICO';
        ELSE
            v_estado_liq := c_liq_aprobada;
            v_motivo     := 'LIQUIDACION_AUTOMATICA';
        END IF;

        pr_registrar_resultado(
            p_siniestro     => v_sin,
            p_fecha_proceso => p_fecha_proceso,
            p_monto_base    => v_monto_base,
            p_deducible     => v_deducible,
            p_cubierto      => v_cubierto,
            p_retencion     => v_retencion,
            p_neto          => v_neto,
            p_estado_liq    => v_estado_liq,
            p_motivo        => v_motivo,
            p_observaciones => v_observaciones
        );

        IF c_modo_debug THEN
            pr_enviar_notificacion(v_sin.siniestro_id, v_estado_liq);
        END IF;
    END pr_liquidar_siniestro;

    ----------------------------------------------------------------------------
    -- PR_PROCESAR_LOTE  (publico)
    ----------------------------------------------------------------------------
    PROCEDURE pr_procesar_lote (
        p_fecha_proceso  IN DATE DEFAULT TRUNC(SYSDATE)
    ) IS
        CURSOR cur_pendientes IS
            SELECT s.siniestro_id, s.monto_reclamado
              FROM ls_siniestros s
             WHERE s.estado = c_sin_registrado
               AND s.fecha_denuncia <= p_fecha_proceso
             ORDER BY s.siniestro_id;

        v_estado_final     ls_siniestros.estado%TYPE;
        v_cant_procesados  PLS_INTEGER  := 0;
        v_cant_liquidados  PLS_INTEGER  := 0;
        v_cant_rechazados  PLS_INTEGER  := 0;
        v_cant_pendientes  PLS_INTEGER  := 0;
        v_cant_errores     PLS_INTEGER  := 0;
        v_total_neto_aprob NUMBER(16,2) := 0;
        v_total_reclamado  NUMBER(16,2) := 0;
        v_neto_sin         NUMBER(14,2);
    BEGIN
        pr_log('INFO', NULL, 'Inicio lote de liquidacion. Fecha proceso: ' ||
                             TO_CHAR(p_fecha_proceso, 'YYYY-MM-DD'));

        FOR r IN cur_pendientes LOOP
            v_cant_procesados := v_cant_procesados + 1;
            v_total_reclamado := v_total_reclamado + r.monto_reclamado;

            SAVEPOINT sp_siniestro;
            BEGIN
                pr_liquidar_siniestro(r.siniestro_id, p_fecha_proceso);

                SELECT estado INTO v_estado_final
                  FROM ls_siniestros
                 WHERE siniestro_id = r.siniestro_id;

                IF v_estado_final = c_sin_liquidado THEN
                    v_cant_liquidados := v_cant_liquidados + 1;

                    SELECT monto_neto INTO v_neto_sin
                      FROM ls_liquidaciones
                     WHERE siniestro_id = r.siniestro_id
                       AND estado       = c_liq_aprobada;

                    v_total_neto_aprob := v_total_neto_aprob + v_neto_sin;
                ELSIF v_estado_final = c_sin_rechazado THEN
                    v_cant_rechazados := v_cant_rechazados + 1;
                ELSIF v_estado_final = c_sin_pend_revision THEN
                    v_cant_pendientes := v_cant_pendientes + 1;
                END IF;
            EXCEPTION
                WHEN OTHERS THEN
                    ROLLBACK TO sp_siniestro;
                    v_cant_errores := v_cant_errores + 1;
                    pr_log('ERROR', r.siniestro_id, SQLERRM);
            END;
        END LOOP;

        COMMIT;

        pr_log('INFO', NULL, 'Fin lote. Procesados=' || v_cant_procesados ||
                             ' Liquidados=' || v_cant_liquidados ||
                             ' Rechazados=' || v_cant_rechazados ||
                             ' Pendientes=' || v_cant_pendientes ||
                             ' Errores=' || v_cant_errores);

        DBMS_OUTPUT.PUT_LINE('=========================================');
        DBMS_OUTPUT.PUT_LINE(' RESUMEN LOTE DE LIQUIDACION');
        DBMS_OUTPUT.PUT_LINE(' Fecha de proceso   : ' || TO_CHAR(p_fecha_proceso, 'YYYY-MM-DD'));
        DBMS_OUTPUT.PUT_LINE(' Procesados         : ' || v_cant_procesados);
        DBMS_OUTPUT.PUT_LINE(' Liquidados         : ' || v_cant_liquidados);
        DBMS_OUTPUT.PUT_LINE(' Rechazados         : ' || v_cant_rechazados);
        DBMS_OUTPUT.PUT_LINE(' Pendientes revision: ' || v_cant_pendientes);
        DBMS_OUTPUT.PUT_LINE(' Errores            : ' || v_cant_errores);
        DBMS_OUTPUT.PUT_LINE(' Total neto aprobado: ' || TO_CHAR(v_total_neto_aprob, 'FM999999990.00'));
        DBMS_OUTPUT.PUT_LINE('=========================================');
    END pr_procesar_lote;

END pkg_liquidacion_siniestros;
/
