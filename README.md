# Copiloto de Modernización — flujo de 4 agentes con interfaz

Entrada: tus archivos legacy (COBOL / PL-SQL). Salidas (solo dos):
1. `informe_verificacion.md` — qué reglas se cumplen, qué se implementó sin regla y si el código nuevo hace lo mismo que el viejo.
2. `modern_loan.zip` — el proyecto de código moderno.

Flujo: Extractor (dos pasadas independientes) → aprobación automática → Validador (PO bancario) → Generador → Verificador.

## Cómo correrlo en Windows (PowerShell)
```
pip install pytest pyyaml
$env:ANTHROPIC_API_KEY = "sk-ant-..."     # o pégala en la pantalla
python app.py
```
Se abre http://127.0.0.1:8765. Arrastra los archivos legacy, elige modelo y pulsa **Ejecutar flujo**.
Cada ejecución queda en `runs/<fecha-hora>/` (todos los archivos intermedios, para auditoría).

## Qué hay que saber
- Necesita una clave de API de Anthropic con saldo. Cada ejecución hace muchas llamadas (los 5 pasos, con reintentos); la pantalla muestra los tokens usados.
- Los agentes solo pueden leer/escribir dentro de `runs/<id>/` y ejecutar scripts de ese espacio o pytest.
- El código legacy se trata como datos. No se ejecuta COBOL ni PL/SQL: la equivalencia sale "por lectura" salvo que se agregue un compilador.
- La aprobación automática y el PO bancario son decisiones de agentes, no de personas.
- Hecho para COBOL de formato fijo y PL/SQL; RPG todavía no tiene validador de cobertura.

## Reanudar una corrida

Cada etapa guarda un punto de control en `runs/<fecha-hora>/estado.json` (y el registro en `log.txt`).
Si una corrida falla o cierras la app, abre la pantalla, elige la corrida en **Reanudar una corrida guardada**
y pulsa **Reanudar**. Las etapas ya superadas aparecen marcadas y no se repiten; el flujo sigue en la primera
pendiente. También puedes elegir «Continuar desde» una etapa concreta (por ejemplo, volver a correr el Generador);
las etapas siguientes se rehacen. Necesitas escribir la clave de nuevo, porque no se guarda.
