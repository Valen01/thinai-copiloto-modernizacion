/*******************************************************************************
 * SISTEMA      : SIGSE - Sistema Integral de Gestion de Seguros
 * MODULO       : SINIESTROS
 * ARCHIVO      : 01_ddl_tablas.sql
 * DESCRIPCION  : Estructuras de datos (tablas, secuencias, indices) del
 *                modulo de liquidacion de siniestros.
 * BASE DE DATOS: Oracle 11gR2 o superior
 * -----------------------------------------------------------------------------
 * HISTORIAL DE CAMBIOS
 * Fecha       Autor        Ticket     Descripcion
 * ----------  -----------  ---------  -----------------------------------------
 * 2009-03-14  JRAMIREZ     SIN-0001   Version inicial.
 * 2009-11-02  JRAMIREZ     SIN-0042   Se agrega LS_TMP_CALCULO_2009 para
 *                                     recalculo de reservas tecnicas.
 * 2013-06-20  MCASTRO      SIN-0310   Se agrega categoria de cliente (VIP).
 * 2017-02-08  LORTEGA      SIN-0577   Se agrega periodo de carencia por
 *                                     cobertura.
 * 2021-09-30  PVARGAS      SIN-0912   Se agrega columna OBSERVACIONES a
 *                                     liquidaciones (trazabilidad de ajustes).
 ******************************************************************************/

-------------------------------------------------------------------------------
-- LS_CLIENTES : Asegurados / tomadores de polizas.
--   CATEGORIA : 'VIP' | 'PREFERENTE' | 'ESTANDAR'
-------------------------------------------------------------------------------
CREATE TABLE ls_clientes (
    cliente_id      NUMBER(10)      NOT NULL,
    nombre          VARCHAR2(120)   NOT NULL,
    tipo_documento  VARCHAR2(5)     NOT NULL,
    num_documento   VARCHAR2(20)    NOT NULL,
    categoria       VARCHAR2(15)    DEFAULT 'ESTANDAR' NOT NULL,
    fecha_alta      DATE            NOT NULL,
    CONSTRAINT pk_ls_clientes PRIMARY KEY (cliente_id),
    CONSTRAINT ck_ls_cli_categoria CHECK (categoria IN ('VIP','PREFERENTE','ESTANDAR'))
);

-------------------------------------------------------------------------------
-- LS_POLIZAS : Contratos de seguro.
--   RAMO           : 'AUTO' | 'HOGAR' | 'SALUD' | 'VIDA'
--   ESTADO         : 'VIGENTE' | 'CANCELADA' | 'SUSPENDIDA'
--   DEDUCIBLE_TIPO : 'FIJO' (monto) | 'PORCENTAJE' (sobre monto base)
--   PRIMA_PENDIENTE: monto de prima vencida y no pagada (mora).
-------------------------------------------------------------------------------
CREATE TABLE ls_polizas (
    poliza_id        NUMBER(10)     NOT NULL,
    numero_poliza    VARCHAR2(20)   NOT NULL,
    cliente_id       NUMBER(10)     NOT NULL,
    ramo             VARCHAR2(10)   NOT NULL,
    fecha_inicio     DATE           NOT NULL,
    fecha_fin        DATE           NOT NULL,
    estado           VARCHAR2(12)   NOT NULL,
    suma_asegurada   NUMBER(14,2)   NOT NULL,
    deducible_tipo   VARCHAR2(10)   NOT NULL,
    deducible_valor  NUMBER(14,2)   DEFAULT 0 NOT NULL,
    prima_pendiente  NUMBER(14,2)   DEFAULT 0 NOT NULL,
    CONSTRAINT pk_ls_polizas PRIMARY KEY (poliza_id),
    CONSTRAINT uk_ls_pol_numero UNIQUE (numero_poliza),
    CONSTRAINT fk_ls_pol_cliente FOREIGN KEY (cliente_id) REFERENCES ls_clientes (cliente_id),
    CONSTRAINT ck_ls_pol_ramo CHECK (ramo IN ('AUTO','HOGAR','SALUD','VIDA')),
    CONSTRAINT ck_ls_pol_estado CHECK (estado IN ('VIGENTE','CANCELADA','SUSPENDIDA')),
    CONSTRAINT ck_ls_pol_ded_tipo CHECK (deducible_tipo IN ('FIJO','PORCENTAJE'))
);

-------------------------------------------------------------------------------
-- LS_COBERTURAS : Coberturas contratadas por poliza.
--   LIMITE_COBERTURA     : monto maximo indemnizable por evento.
--   PORCENTAJE_COBERTURA : % del monto (neto de deducible) que paga la cia.
--   DIAS_CARENCIA        : dias desde el inicio de la poliza durante los
--                          cuales la cobertura aun no esta activa.
-------------------------------------------------------------------------------
CREATE TABLE ls_coberturas (
    poliza_id             NUMBER(10)    NOT NULL,
    cod_cobertura         VARCHAR2(20)  NOT NULL,
    limite_cobertura      NUMBER(14,2)  NOT NULL,
    porcentaje_cobertura  NUMBER(5,2)   NOT NULL,
    dias_carencia         NUMBER(4)     DEFAULT 0 NOT NULL,
    CONSTRAINT pk_ls_coberturas PRIMARY KEY (poliza_id, cod_cobertura),
    CONSTRAINT fk_ls_cob_poliza FOREIGN KEY (poliza_id) REFERENCES ls_polizas (poliza_id)
);

-------------------------------------------------------------------------------
-- LS_SINIESTROS : Reclamos presentados por los asegurados.
--   ESTADO : 'REGISTRADO' | 'LIQUIDADO' | 'RECHAZADO' | 'PENDIENTE_REVISION'
-------------------------------------------------------------------------------
CREATE TABLE ls_siniestros (
    siniestro_id      NUMBER(10)     NOT NULL,
    poliza_id         NUMBER(10)     NOT NULL,
    cod_cobertura     VARCHAR2(20)   NOT NULL,
    fecha_ocurrencia  DATE           NOT NULL,
    fecha_denuncia    DATE           NOT NULL,
    monto_reclamado   NUMBER(14,2)   NOT NULL,
    estado            VARCHAR2(20)   DEFAULT 'REGISTRADO' NOT NULL,
    descripcion       VARCHAR2(400),
    CONSTRAINT pk_ls_siniestros PRIMARY KEY (siniestro_id),
    CONSTRAINT fk_ls_sin_poliza FOREIGN KEY (poliza_id) REFERENCES ls_polizas (poliza_id),
    CONSTRAINT ck_ls_sin_estado CHECK (estado IN ('REGISTRADO','LIQUIDADO','RECHAZADO','PENDIENTE_REVISION'))
);

CREATE INDEX ix_ls_sin_estado ON ls_siniestros (estado, fecha_denuncia);
CREATE INDEX ix_ls_sin_poliza ON ls_siniestros (poliza_id, fecha_ocurrencia);

-------------------------------------------------------------------------------
-- LS_LIQUIDACIONES : Resultado del calculo de indemnizacion por siniestro.
--   ESTADO : 'APROBADA' | 'RECHAZADA' | 'PENDIENTE_APROBACION'
--   MOTIVO : codigo de resultado (ver documentacion del paquete).
--   OBSERVACIONES : marcas de ajustes aplicados, separadas por ';'.
-------------------------------------------------------------------------------
CREATE TABLE ls_liquidaciones (
    liquidacion_id      NUMBER(12)     NOT NULL,
    siniestro_id        NUMBER(10)     NOT NULL,
    fecha_liquidacion   DATE           NOT NULL,
    monto_reclamado     NUMBER(14,2)   NOT NULL,
    monto_base          NUMBER(14,2)   DEFAULT 0 NOT NULL,
    monto_deducible     NUMBER(14,2)   DEFAULT 0 NOT NULL,
    monto_cubierto      NUMBER(14,2)   DEFAULT 0 NOT NULL,
    monto_retencion     NUMBER(14,2)   DEFAULT 0 NOT NULL,
    monto_neto          NUMBER(14,2)   DEFAULT 0 NOT NULL,
    estado              VARCHAR2(25)   NOT NULL,
    motivo              VARCHAR2(40)   NOT NULL,
    observaciones       VARCHAR2(400),
    usuario_proceso     VARCHAR2(30)   DEFAULT USER NOT NULL,
    CONSTRAINT pk_ls_liquidaciones PRIMARY KEY (liquidacion_id),
    CONSTRAINT fk_ls_liq_siniestro FOREIGN KEY (siniestro_id) REFERENCES ls_siniestros (siniestro_id),
    CONSTRAINT ck_ls_liq_estado CHECK (estado IN ('APROBADA','RECHAZADA','PENDIENTE_APROBACION'))
);

CREATE INDEX ix_ls_liq_siniestro ON ls_liquidaciones (siniestro_id);

-------------------------------------------------------------------------------
-- LS_PARAMETROS : Parametrizacion del negocio (valores configurables).
-------------------------------------------------------------------------------
CREATE TABLE ls_parametros (
    cod_parametro   VARCHAR2(40)   NOT NULL,
    valor_numerico  NUMBER(14,4),
    valor_texto     VARCHAR2(200),
    descripcion     VARCHAR2(200),
    CONSTRAINT pk_ls_parametros PRIMARY KEY (cod_parametro)
);

-------------------------------------------------------------------------------
-- LS_LOG_PROCESO : Bitacora de ejecucion del proceso batch.
-------------------------------------------------------------------------------
CREATE TABLE ls_log_proceso (
    log_id        NUMBER(12)      NOT NULL,
    fecha_log     DATE            DEFAULT SYSDATE NOT NULL,
    nivel         VARCHAR2(10)    NOT NULL,
    siniestro_id  NUMBER(10),
    mensaje       VARCHAR2(1000),
    CONSTRAINT pk_ls_log_proceso PRIMARY KEY (log_id)
);

-------------------------------------------------------------------------------
-- LS_TMP_CALCULO_2009 : Tabla de trabajo para recalculo de reservas tecnicas.
-------------------------------------------------------------------------------
CREATE TABLE ls_tmp_calculo_2009 (
    siniestro_id     NUMBER(10),
    reserva_tecnica  NUMBER(14,2),
    fecha_calculo    DATE
);

-------------------------------------------------------------------------------
-- Secuencias
-------------------------------------------------------------------------------
CREATE SEQUENCE seq_ls_liquidacion START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_ls_log         START WITH 1 INCREMENT BY 1 NOCACHE;
