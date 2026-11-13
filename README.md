# ThinAi — Copiloto de Modernización

Cuatro agentes de IA leen código legacy (COBOL, PL/SQL), lo convierten en un servicio moderno y comprueban que hace lo mismo. Proyecto del Hackathon AI 2026, reto 05.

**Entrada:** archivos de código legacy.
**Salidas:** el proyecto moderno (ZIP) y un informe de verificación.

```
Extractor (dos pasadas) → aprobación automática → Validador PO → Generador → Verificador
```

Entre cada agente hay un control automático que no usa el modelo: verifica las citas, aplica una política de aprobación, valida la calidad del código y cruza las reglas con los escenarios.

## Resultados de una corrida real

Sistema de liquidación de siniestros en Oracle PL/SQL: 6 archivos, 1.098 líneas. Corrida `20261113-145231`.

| Etapa | Resultado |
|---|---|
| Extractor | 45 reglas (32 de negocio y 13 técnicas) con 208 citas verificadas contra el código |
| Aprobación automática | 16 aprobadas, 16 a revisión humana, 13 hallazgos técnicos |
| Validador PO | 43 aprobadas, 2 mejoradas por seguridad e integridad, 0 rechazadas |
| Generador | Compuerta aprobada: 133 pruebas, 85,8 % de cobertura, complejidad máxima 9, 10 ADR |
| Verificador | 34 de 34 reglas cumplidas, 85 de 85 escenarios iguales, 9 de 9 cambios de borde detectados |

**Veredicto del Verificador:** equivalente **por lectura** del código. El legacy no se ejecutó, así que la equivalencia no está demostrada por ejecución. Los límites completos están en [Resultados y limitaciones](https://github.com/Valen01/thinai-copiloto-modernizacion/wiki/Resultados).

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Manual técnico | [`docs/Manual_tecnico_ThinAi.pdf`](docs/Manual_tecnico_ThinAi.pdf) y [`docs/manual_tecnico.md`](docs/manual_tecnico.md) |
| Presentación | [`docs/Presentacion_ThinAi.pdf`](docs/Presentacion_ThinAi.pdf) |
| Wiki | [github.com/Valen01/thinai-copiloto-modernizacion/wiki](https://github.com/Valen01/thinai-copiloto-modernizacion/wiki) |
| Informe de verificación de la corrida | [`runs/20261113-145231/salida/informe_verificacion.md`](runs/20261113-145231/salida/informe_verificacion.md) |
| Proyecto generado (ZIP) | [`runs/20261113-145231/salida/modern_loan.zip`](runs/20261113-145231/salida/modern_loan.zip) |
| Código generado, sin comprimir | [`runs/20261113-145231/generador/modern_loan/`](runs/20261113-145231/generador/modern_loan/) |
| Política de seguridad | [`SECURITY.md`](SECURITY.md) |

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
- Los agentes solo pueden leer y escribir dentro de `runs/<id>/` y ejecutar scripts de ese espacio o pytest.
- El código legacy se trata como datos. No se ejecuta COBOL ni PL/SQL: la equivalencia sale «por lectura» salvo que se agregue un compilador.
- La aprobación automática y el PO bancario son decisiones de agentes, no de personas.
- Hecho para COBOL de formato fijo y PL/SQL; RPG todavía no tiene validador de cobertura.
- El código legacy se envía a la API de Anthropic. No uses código ni datos de clientes sin confirmar que tu organización lo permite.

## Reanudar una corrida

Cada etapa guarda un punto de control en `runs/<fecha-hora>/estado.json` (y el registro en `log.txt`).
Si una corrida falla o cierras la app, abre la pantalla, elige la corrida en **Reanudar una corrida guardada**
y pulsa **Reanudar**. Las etapas ya superadas aparecen marcadas y no se repiten; el flujo sigue en la primera
pendiente. También puedes elegir «Continuar desde» una etapa concreta (por ejemplo, volver a correr el Generador);
las etapas siguientes se rehacen. Necesitas escribir la clave de nuevo, porque no se guarda.

## Equipo

ThinAi: Valentina Burbano (QA Lead) y Claude.
