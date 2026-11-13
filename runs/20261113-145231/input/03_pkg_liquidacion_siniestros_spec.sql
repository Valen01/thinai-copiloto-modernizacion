CREATE OR REPLACE PACKAGE pkg_liquidacion_siniestros AS
/*******************************************************************************
 * SISTEMA      : SIGSE - Sistema Integral de Gestion de Seguros
 * MODULO       : SINIESTROS
 * OBJETO       : PKG_LIQUIDACION_SINIESTROS (especificacion)
 * DESCRIPCION  : Motor de liquidacion de siniestros. Evalua la procedencia de
 *                cada siniestro registrado, calcula la indemnizacion a pagar
 *                (monto base, deducible, monto cubierto, retencion y neto) y
 *                determina su estado final (aprobado, rechazado o pendiente
 *                de aprobacion manual).
 *
 * DEPENDENCIAS : LS_SINIESTROS, LS_POLIZAS, LS_CLIENTES, LS_COBERTURAS,
 *                LS_LIQUIDACIONES, LS_PARAMETROS, LS_LOG_PROCESO,
 *                SEQ_LS_LIQUIDACION, SEQ_LS_LOG.
 * -----------------------------------------------------------------------------
 * HISTORIAL DE CAMBIOS
 * Fecha       Autor        Ticket     Descripcion
 * ----------  -----------  ---------  -----------------------------------------
 * 2009-03-14  JRAMIREZ     SIN-0001   Version inicial.
 * 2011-05-09  JRAMIREZ     SIN-0118   Proceso batch por fecha de corte.
 * 2013-06-20  MCASTRO      SIN-0310   Beneficios para clientes VIP.
 * 2017-02-08  LORTEGA      SIN-0577   Periodo de carencia por cobertura.
 * 2019-10-15  LORTEGA      SIN-0744   Penalizacion por siniestralidad.
 * 2021-09-30  PVARGAS      SIN-0912   Alerta de fraude y observaciones.
 * 2023-04-03  PVARGAS      SIN-1050   Retencion impositiva parametrizable.
 ******************************************************************************/

    ----------------------------------------------------------------------------
    -- Estados del siniestro
    ----------------------------------------------------------------------------
    c_sin_registrado     CONSTANT VARCHAR2(20) := 'REGISTRADO';
    c_sin_liquidado      CONSTANT VARCHAR2(20) := 'LIQUIDADO';
    c_sin_rechazado      CONSTANT VARCHAR2(20) := 'RECHAZADO';
    c_sin_pend_revision  CONSTANT VARCHAR2(20) := 'PENDIENTE_REVISION';

    ----------------------------------------------------------------------------
    -- Estados de la liquidacion
    ----------------------------------------------------------------------------
    c_liq_aprobada       CONSTANT VARCHAR2(25) := 'APROBADA';
    c_liq_rechazada      CONSTANT VARCHAR2(25) := 'RECHAZADA';
    c_liq_pend_aprob     CONSTANT VARCHAR2(25) := 'PENDIENTE_APROBACION';

    ----------------------------------------------------------------------------
    -- PR_LIQUIDAR_SINIESTRO
    --   Liquida un unico siniestro en estado REGISTRADO.
    --   Inserta un registro en LS_LIQUIDACIONES y actualiza el estado del
    --   siniestro. NO realiza COMMIT (lo controla el llamador).
    --
    --   p_siniestro_id  : identificador del siniestro a liquidar.
    --   p_fecha_proceso : fecha de corte / fecha de liquidacion.
    --
    --   Errores:
    --     ORA-20001  El siniestro no se encuentra en estado REGISTRADO.
    --     ORA-20010  Parametro de negocio inexistente en LS_PARAMETROS.
    --     NO_DATA_FOUND  El siniestro, la poliza o el cliente no existen.
    ----------------------------------------------------------------------------
    PROCEDURE pr_liquidar_siniestro (
        p_siniestro_id   IN ls_siniestros.siniestro_id%TYPE,
        p_fecha_proceso  IN DATE
    );

    ----------------------------------------------------------------------------
    -- PR_PROCESAR_LOTE
    --   Proceso batch: liquida todos los siniestros en estado REGISTRADO cuya
    --   fecha de denuncia sea menor o igual a la fecha de proceso, en orden
    --   ascendente de SINIESTRO_ID. Cada siniestro se procesa de forma
    --   aislada (SAVEPOINT): un error en uno no detiene el lote.
    --   Al finalizar realiza COMMIT y emite un resumen por DBMS_OUTPUT.
    --
    --   p_fecha_proceso : fecha de corte (por defecto, la fecha del sistema).
    ----------------------------------------------------------------------------
    PROCEDURE pr_procesar_lote (
        p_fecha_proceso  IN DATE DEFAULT TRUNC(SYSDATE)
    );

END pkg_liquidacion_siniestros;
/
