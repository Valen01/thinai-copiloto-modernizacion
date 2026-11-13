/*******************************************************************************
 * ARCHIVO      : datos_prueba.sql
 * DESCRIPCION  : Datos de entrada de prueba para el proceso de liquidacion
 *                de siniestros. Fecha de proceso de referencia: 31/03/2026.
 *
 * Cada siniestro pendiente (estado REGISTRADO) esta disenado para ejercitar
 * una o varias reglas de negocio. Ver evaluacion/RESULTADOS_ESPERADOS.md.
 ******************************************************************************/

ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';

-------------------------------------------------------------------------------
-- CLIENTES
-------------------------------------------------------------------------------
INSERT INTO ls_clientes VALUES (1, 'ANA TORRES',   'CC', '10000001', 'VIP',        DATE '2010-04-12');
INSERT INTO ls_clientes VALUES (2, 'LUIS PEREZ',   'CC', '10000002', 'ESTANDAR',   DATE '2018-08-01');
INSERT INTO ls_clientes VALUES (3, 'MARIA GOMEZ',  'CC', '10000003', 'PREFERENTE', DATE '2015-02-20');
INSERT INTO ls_clientes VALUES (4, 'CARLOS RUIZ',  'CC', '10000004', 'ESTANDAR',   DATE '2021-11-30');
INSERT INTO ls_clientes VALUES (5, 'SOFIA DIAZ',   'CC', '10000005', 'VIP',        DATE '2008-01-15');

-------------------------------------------------------------------------------
-- POLIZAS
-- (poliza_id, numero, cliente, ramo, inicio, fin, estado, suma_aseg,
--  ded_tipo, ded_valor, prima_pendiente)
-------------------------------------------------------------------------------
INSERT INTO ls_polizas VALUES (101, 'AUTO-0001',  1, 'AUTO',  DATE '2025-06-01', DATE '2026-05-31', 'VIGENTE',    80000,  'PORCENTAJE', 5,    0);
INSERT INTO ls_polizas VALUES (102, 'HOGAR-0001', 2, 'HOGAR', DATE '2025-01-01', DATE '2025-12-31', 'VIGENTE',    150000, 'FIJO',       500,  0);
INSERT INTO ls_polizas VALUES (103, 'SALUD-0001', 3, 'SALUD', DATE '2026-01-01', DATE '2026-12-31', 'VIGENTE',    100000, 'FIJO',       200,  0);
INSERT INTO ls_polizas VALUES (104, 'AUTO-0002',  4, 'AUTO',  DATE '2025-09-01', DATE '2026-08-31', 'CANCELADA',  60000,  'FIJO',       300,  0);
INSERT INTO ls_polizas VALUES (105, 'VIDA-0001',  5, 'VIDA',  DATE '2020-01-01', DATE '2030-12-31', 'VIGENTE',    200000, 'FIJO',       0,    0);
INSERT INTO ls_polizas VALUES (106, 'HOGAR-0002', 4, 'HOGAR', DATE '2025-07-01', DATE '2026-06-30', 'VIGENTE',    50000,  'PORCENTAJE', 2,    1200);
INSERT INTO ls_polizas VALUES (107, 'AUTO-0003',  1, 'AUTO',  DATE '2025-10-01', DATE '2026-09-30', 'VIGENTE',    40000,  'PORCENTAJE', 10,   300);
INSERT INTO ls_polizas VALUES (108, 'AUTO-0004',  2, 'AUTO',  DATE '2025-04-01', DATE '2026-03-31', 'VIGENTE',    30000,  'FIJO',       400,  0);
INSERT INTO ls_polizas VALUES (109, 'HOGAR-0003', 3, 'HOGAR', DATE '2025-11-01', DATE '2026-10-31', 'VIGENTE',    20000,  'FIJO',       250,  0);
INSERT INTO ls_polizas VALUES (110, 'AUTO-0005',  5, 'AUTO',  DATE '2026-03-01', DATE '2027-02-28', 'VIGENTE',    90000,  'PORCENTAJE', 5,    0);
INSERT INTO ls_polizas VALUES (111, 'SALUD-0002', 2, 'SALUD', DATE '2026-02-01', DATE '2027-01-31', 'VIGENTE',    50000,  'FIJO',       150,  0);
INSERT INTO ls_polizas VALUES (112, 'HOGAR-0004', 4, 'HOGAR', DATE '2025-05-01', DATE '2026-04-30', 'VIGENTE',    300000, 'FIJO',       1000, 0);
INSERT INTO ls_polizas VALUES (113, 'AUTO-0006',  3, 'AUTO',  DATE '2025-08-01', DATE '2026-07-31', 'SUSPENDIDA', 45000,  'FIJO',       350,  0);

-------------------------------------------------------------------------------
-- COBERTURAS
-- (poliza_id, cod_cobertura, limite, % cobertura, dias carencia)
-------------------------------------------------------------------------------
INSERT INTO ls_coberturas VALUES (101, 'DANOS_PROPIOS',   60000,  100, 0);
INSERT INTO ls_coberturas VALUES (101, 'RC',              50000,  100, 0);
INSERT INTO ls_coberturas VALUES (101, 'ROBO',            40000,  80,  30);
INSERT INTO ls_coberturas VALUES (102, 'INCENDIO',        150000, 100, 0);
INSERT INTO ls_coberturas VALUES (103, 'HOSPITALIZACION', 50000,  90,  30);
INSERT INTO ls_coberturas VALUES (103, 'AMBULATORIO',     5000,   80,  60);
INSERT INTO ls_coberturas VALUES (104, 'DANOS_PROPIOS',   50000,  100, 0);
INSERT INTO ls_coberturas VALUES (105, 'FALLECIMIENTO',   200000, 100, 0);
INSERT INTO ls_coberturas VALUES (105, 'INVALIDEZ',       100000, 100, 0);
INSERT INTO ls_coberturas VALUES (106, 'AGUA',            20000,  100, 0);
INSERT INTO ls_coberturas VALUES (107, 'DANOS_PROPIOS',   35000,  100, 0);
INSERT INTO ls_coberturas VALUES (108, 'DANOS_PROPIOS',   25000,  100, 0);
INSERT INTO ls_coberturas VALUES (109, 'ROBO',            20000,  100, 0);
INSERT INTO ls_coberturas VALUES (110, 'DANOS_PROPIOS',   80000,  100, 0);
INSERT INTO ls_coberturas VALUES (111, 'HOSPITALIZACION', 40000,  90,  90);
INSERT INTO ls_coberturas VALUES (112, 'INCENDIO',        300000, 100, 0);
INSERT INTO ls_coberturas VALUES (112, 'TERREMOTO',       200000, 90,  0);
INSERT INTO ls_coberturas VALUES (113, 'DANOS_PROPIOS',   40000,  100, 0);

-------------------------------------------------------------------------------
-- HISTORICO: siniestros ya procesados en periodos anteriores
-- (no son tomados por el lote porque su estado no es REGISTRADO, pero
--  intervienen en las reglas de siniestralidad y suma asegurada remanente)
-------------------------------------------------------------------------------
INSERT INTO ls_siniestros VALUES (900, 108, 'DANOS_PROPIOS', DATE '2025-05-10', DATE '2025-05-12', 1900,  'LIQUIDADO', 'Choque leve en estacionamiento');
INSERT INTO ls_siniestros VALUES (901, 108, 'DANOS_PROPIOS', DATE '2025-08-15', DATE '2025-08-16', 2600,  'LIQUIDADO', 'Rayadura y abolladura puerta');
INSERT INTO ls_siniestros VALUES (902, 108, 'DANOS_PROPIOS', DATE '2025-12-01', DATE '2025-12-03', 1200,  'LIQUIDADO', 'Rotura de espejo lateral');
INSERT INTO ls_siniestros VALUES (903, 109, 'ROBO',          DATE '2025-12-10', DATE '2025-12-11', 18250, 'LIQUIDADO', 'Robo de electrodomesticos');
INSERT INTO ls_siniestros VALUES (904, 101, 'DANOS_PROPIOS', DATE '2025-09-01', DATE '2025-11-20', 7000,  'RECHAZADO', 'Denuncia fuera de plazo');

INSERT INTO ls_liquidaciones (liquidacion_id, siniestro_id, fecha_liquidacion, monto_reclamado, monto_base, monto_deducible, monto_cubierto, monto_retencion, monto_neto, estado, motivo, observaciones)
VALUES (9001, 900, DATE '2025-05-31', 1900,  1900,  400, 1500,  0, 1500,  'APROBADA',  'LIQUIDACION_AUTOMATICA', NULL);
INSERT INTO ls_liquidaciones (liquidacion_id, siniestro_id, fecha_liquidacion, monto_reclamado, monto_base, monto_deducible, monto_cubierto, monto_retencion, monto_neto, estado, motivo, observaciones)
VALUES (9002, 901, DATE '2025-08-31', 2600,  2600,  400, 2200,  0, 2200,  'APROBADA',  'LIQUIDACION_AUTOMATICA', NULL);
INSERT INTO ls_liquidaciones (liquidacion_id, siniestro_id, fecha_liquidacion, monto_reclamado, monto_base, monto_deducible, monto_cubierto, monto_retencion, monto_neto, estado, motivo, observaciones)
VALUES (9003, 902, DATE '2025-12-31', 1200,  1200,  400, 800,   0, 800,   'APROBADA',  'LIQUIDACION_AUTOMATICA', NULL);
INSERT INTO ls_liquidaciones (liquidacion_id, siniestro_id, fecha_liquidacion, monto_reclamado, monto_base, monto_deducible, monto_cubierto, monto_retencion, monto_neto, estado, motivo, observaciones)
VALUES (9004, 903, DATE '2025-12-31', 18250, 18250, 250, 18000, 360, 17640, 'APROBADA',  'LIQUIDACION_AUTOMATICA', 'RETENCION_APLICADA');
INSERT INTO ls_liquidaciones (liquidacion_id, siniestro_id, fecha_liquidacion, monto_reclamado, monto_base, monto_deducible, monto_cubierto, monto_retencion, monto_neto, estado, motivo, observaciones)
VALUES (9005, 904, DATE '2025-11-30', 7000,  0,     0,   0,     0, 0,     'RECHAZADA', 'DENUNCIA_EXTEMPORANEA',  NULL);

-------------------------------------------------------------------------------
-- SINIESTROS PENDIENTES DE LIQUIDAR (estado REGISTRADO)
-------------------------------------------------------------------------------
INSERT INTO ls_siniestros VALUES (1001, 101, 'DANOS_PROPIOS',   DATE '2026-02-10', DATE '2026-02-12', 12345.67, 'REGISTRADO', 'Colision trasera en avenida principal');
INSERT INTO ls_siniestros VALUES (1002, 102, 'INCENDIO',        DATE '2026-01-15', DATE '2026-01-20', 30000,    'REGISTRADO', 'Incendio en cocina');
INSERT INTO ls_siniestros VALUES (1003, 103, 'HOSPITALIZACION', DATE '2026-03-05', DATE '2026-03-06', 8123.45,  'REGISTRADO', 'Hospitalizacion por apendicitis');
INSERT INTO ls_siniestros VALUES (1004, 104, 'DANOS_PROPIOS',   DATE '2026-01-10', DATE '2026-01-11', 5000,     'REGISTRADO', 'Golpe en parachoques');
INSERT INTO ls_siniestros VALUES (1005, 105, 'FALLECIMIENTO',   DATE '2025-06-01', DATE '2026-03-01', 200000,   'REGISTRADO', 'Fallecimiento del asegurado');
INSERT INTO ls_siniestros VALUES (1006, 101, 'ROBO',            DATE '2026-01-05', DATE '2026-03-10', 9000,     'REGISTRADO', 'Robo de accesorios');
INSERT INTO ls_siniestros VALUES (1007, 101, 'GRANIZO',         DATE '2026-03-01', DATE '2026-03-02', 3000,     'REGISTRADO', 'Danos por granizo');
INSERT INTO ls_siniestros VALUES (1008, 111, 'HOSPITALIZACION', DATE '2026-03-15', DATE '2026-03-16', 10000,    'REGISTRADO', 'Cirugia programada');
INSERT INTO ls_siniestros VALUES (1009, 106, 'AGUA',            DATE '2026-02-20', DATE '2026-02-22', 4000,     'REGISTRADO', 'Filtracion de agua en bano');
INSERT INTO ls_siniestros VALUES (1010, 107, 'DANOS_PROPIOS',   DATE '2026-03-10', DATE '2026-03-11', 837.45,   'REGISTRADO', 'Rotura de faro delantero');
INSERT INTO ls_siniestros VALUES (1011, 108, 'DANOS_PROPIOS',   DATE '2026-02-14', DATE '2026-02-16', 5000,     'REGISTRADO', 'Choque contra poste');
INSERT INTO ls_siniestros VALUES (1012, 109, 'ROBO',            DATE '2026-03-01', DATE '2026-03-03', 6000,     'REGISTRADO', 'Robo de bicicleta y herramientas');
INSERT INTO ls_siniestros VALUES (1013, 110, 'DANOS_PROPIOS',   DATE '2026-03-08', DATE '2026-03-09', 70000,    'REGISTRADO', 'Volcamiento en carretera');
INSERT INTO ls_siniestros VALUES (1014, 112, 'TERREMOTO',       DATE '2026-02-25', DATE '2026-03-05', 250000,   'REGISTRADO', 'Danos estructurales por sismo');
INSERT INTO ls_siniestros VALUES (1015, 103, 'AMBULATORIO',     DATE '2026-03-20', DATE '2026-03-21', 150,      'REGISTRADO', 'Consulta medica general');
INSERT INTO ls_siniestros VALUES (1016, 101, 'RC',              DATE '2026-03-28', DATE '2026-04-05', 15000,    'REGISTRADO', 'Dano a vehiculo de tercero');
INSERT INTO ls_siniestros VALUES (1017, 113, 'DANOS_PROPIOS',   DATE '2026-02-02', DATE '2026-02-03', 2500,     'REGISTRADO', 'Rotura de parabrisas');
INSERT INTO ls_siniestros VALUES (1018, 112, 'INCENDIO',        DATE '2026-02-28', DATE '2026-03-30', 40000.50, 'REGISTRADO', 'Incendio en garaje');

COMMIT;
