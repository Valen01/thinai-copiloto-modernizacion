/*******************************************************************************
 * SISTEMA      : SIGSE - Sistema Integral de Gestion de Seguros
 * MODULO       : SINIESTROS
 * ARCHIVO      : 02_parametros.sql
 * DESCRIPCION  : Carga de parametros de negocio utilizados por el paquete
 *                PKG_LIQUIDACION_SINIESTROS.
 ******************************************************************************/

-- Plazos de denuncia (dias calendario entre ocurrencia y denuncia)
INSERT INTO ls_parametros VALUES ('DIAS_MAX_DENUNCIA',        30,     NULL, 'Plazo maximo de denuncia (dias) - ramos generales');
INSERT INTO ls_parametros VALUES ('DIAS_MAX_DENUNCIA_VIDA',   365,    NULL, 'Plazo maximo de denuncia (dias) - ramo VIDA');

-- Deducibles
INSERT INTO ls_parametros VALUES ('DEDUCIBLE_MINIMO',         100,    NULL, 'Deducible minimo cuando el deducible es porcentual');
INSERT INTO ls_parametros VALUES ('PCT_DESCUENTO_DED_VIP',    50,     NULL, '% de descuento sobre el deducible para clientes VIP');

-- Morosidad
INSERT INTO ls_parametros VALUES ('TOLERANCIA_MORA_VIP',      500,    NULL, 'Monto de prima pendiente tolerado a clientes VIP');

-- Siniestralidad
INSERT INTO ls_parametros VALUES ('MAX_SINIESTROS_ANUAL',     3,      NULL, 'Cantidad de siniestros liquidados en 365 dias que activa penalizacion');
INSERT INTO ls_parametros VALUES ('PCT_PENALIZACION_SINIEST', 10,     NULL, '% de reduccion por alta siniestralidad');

-- Retencion impositiva
INSERT INTO ls_parametros VALUES ('UMBRAL_RETENCION',         10000,  NULL, 'Monto cubierto a partir del cual se aplica retencion');
INSERT INTO ls_parametros VALUES ('TASA_RETENCION',           2,      NULL, '% de retencion impositiva');

-- Aprobacion y fraude
INSERT INTO ls_parametros VALUES ('TOPE_AUTO_APROBACION',     50000,  NULL, 'Monto neto maximo para aprobacion automatica');
INSERT INTO ls_parametros VALUES ('DIAS_ALERTA_FRAUDE',       15,     NULL, 'Dias desde inicio de poliza para evaluar alerta de fraude');
INSERT INTO ls_parametros VALUES ('PCT_ALERTA_FRAUDE',        80,     NULL, '% del limite de cobertura que activa alerta de fraude');

-- Otros
INSERT INTO ls_parametros VALUES ('FACTOR_INFLACION',         1.035,  NULL, 'Factor de ajuste inflacionario de reservas');
INSERT INTO ls_parametros VALUES ('TASA_IVA',                 19,     NULL, 'Tasa de IVA vigente');
INSERT INTO ls_parametros VALUES ('VERSION_MOTOR',            NULL,   '3.2.0', 'Version del motor de liquidacion');

COMMIT;
