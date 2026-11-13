# ADR-007: Formato del adaptador batch y tratamiento de entradas invalidas

## Estado
Decidida por defecto. El legacy no tiene archivo de entrada `LOANREQ`-equivalente: lee tablas Oracle. El
formato de archivos lo define este adaptador a partir del DDL (`01_ddl_tablas.sql`) y de R-026, R-035.

## Contexto
Hay que alimentar el servicio con archivos de ejemplo y producir una salida comparable. Las reglas aprobadas
fijan los campos de LS_LIQUIDACIONES (R-026), el separador `|` y el formato del resumen (R-035,
`FM999999990.00`), pero no el formato de entrada ni como tratar datos invalidos.

## Decision
- Entrada: una carpeta por tenant con `clientes.dat`, `polizas.dat`, `coberturas.dat`, `siniestros.dat`,
  `liquidaciones.dat` (historico) y `parametros.dat`; campos separados por `|`, `#` inicia comentario, fechas
  `YYYY-MM-DD` o `YYYY-MM-DD HH:MM:SS` (las columnas DATE de Oracle admiten hora, R-006).
- Salida por tenant en `out/<tenant>/`: `liquidaciones.out` (13 campos: id, siniestro, fecha, reclamado, base,
  deducible, cubierto, retencion, neto, estado, motivo, observaciones, usuario), `siniestros.out`
  (`id|estado`), `bitacora.out` y `resumen.txt`. Importes sin signo con dos decimales.
- **Importe negativo**: se rechaza todo el archivo con `BatchFormatError` (importes sin signo, NUMBER(14,2));
  no se acepta ni se trunca el signo.
- **Mas de dos decimales** (p. ej. `10.123`) o mas de 12 enteros: se rechaza el archivo, nunca se trunca ni
  redondea en silencio.
- **Fecha inexistente** (p. ej. `2026-02-30`): se rechaza el archivo con linea y archivo indicados.
- **Dominios** (categoria, ramo, estado de poliza, tipo de deducible; R-004): un valor fuera del CHECK de la
  base se rechaza igual que lo haria la base. `PREFERENTE` se acepta sin beneficio (decision del PO).
- **Campos de mas o de menos**: se rechaza el archivo.
- **Fecha de proceso**: `--process-date YYYY-MM-DD`; si falta, es la fecha del sistema sin hora
  (`TRUNC(SYSDATE)`, R-028). Fecha invalida: codigo de salida 2 con mensaje claro.
- **Codigos de salida**: 0 correcto, 2 error de configuracion o formato.
- **Usuario de proceso** (R-026, `USER`): variable de entorno `CLAIMS_PROCESS_USER` (defecto `BATCH`, maximo
  30 caracteres, como `VARCHAR2(30)`); las liquidaciones historicas usan `HIST`.
- El identificador de liquidacion es una secuencia por tenant que no retrocede con el rollback (como una
  secuencia Oracle); el historico de `liquidaciones.dat` fija el punto de partida.

## Consecuencias
- Ningun dato invalido se corrige en silencio: el lote no arranca y el mensaje indica archivo y linea.
- Si en produccion la entrada fuera otra (p. ej. Oracle), solo cambia el adaptador inbound/outbound.

## Reglas relacionadas
R-004, R-006, R-026, R-028, R-035. Decisiones del PO cerradas: PREFERENTE sin beneficio; fechas con hora
comparadas sin TRUNC.
