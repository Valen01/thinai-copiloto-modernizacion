/*******************************************************************************
 * ARCHIVO      : ejecutar_lote.sql
 * DESCRIPCION  : Ejecuta el proceso batch de liquidacion con fecha de corte
 *                31/03/2026 (fecha de referencia de los datos de prueba).
 ******************************************************************************/
SET SERVEROUTPUT ON SIZE UNLIMITED

BEGIN
    pkg_liquidacion_siniestros.pr_procesar_lote(p_fecha_proceso => DATE '2026-03-31');
END;
/
