---
title: "Manual técnico — Copiloto de Modernización (ThinAi)"
author: "Valentina Burbano"
date: "13 de noviembre de 2026"
lang: es
---

## Propósito y alcance

El Copiloto de Modernización (equipo ThinAi) convierte código legacy en un servicio moderno y comprueba si ambos hacen lo mismo. Este manual explica cómo está construido, cómo se instala y se usa, y qué garantiza y qué no.

- **Entrada:** archivos de código legacy (extensiones `.cbl`, `.cob`, `.cobol`, `.sql`, `.pls`, `.pks`, `.pkb`, `.rpg`, `.rpgle`).
- **Salida 1:** el proyecto moderno en Python 3.11+, con pruebas, API documentada y decisiones de arquitectura, en un ZIP.
- **Salida 2:** un informe de verificación que dice qué reglas se cumplen, qué código no tiene regla de origen y si el código nuevo hace lo mismo que el viejo.
- **Audiencia:** ingenieros y QA que van a operar, mantener o auditar el copiloto.

La evidencia de este manual proviene de una corrida real sobre un sistema de siniestros en PL/SQL (sección 14). Las cifras de otros casos no se incluyen.

## Visión general

El copiloto recorre cinco etapas en orden. Cada etapa guarda su resultado en la carpeta de la corrida antes de pasar a la siguiente.

| # | Etapa | Qué hace | Qué entrega |
|---|---|---|---|
| 1 | Extractor | Lee el legacy en dos pasadas independientes y extrae reglas de negocio con cita literal de línea | Reglas con citas |
| 2 | Aprobación automática | Aplica la política v1.0 (cinco criterios) y clasifica cada regla | Reglas aprobadas, en revisión o técnicas |
| 3 | Validador PO | Simula a un Product Owner: aprueba, mejora o rechaza | Un solo archivo de reglas limpias |
| 4 | Generador | Escribe el proyecto moderno y lo revisa con la compuerta de calidad | Proyecto con pruebas, OpenAPI y ADR |
| 5 | Verificador | Compara el código nuevo con el legacy y con las reglas | Informe de verificación |

**Entradas.** Los archivos legacy y la clave de API de Anthropic.

**Salidas.** El ZIP del proyecto generado y el informe de verificación, ambos descargables desde la pantalla.

**Principio de honestidad.** La equivalencia se demuestra por lectura del código, salvo que el legacy se ejecute. La aprobación automática no es una validación del negocio, y las decisiones del Product Owner son simuladas.

## Arquitectura del copiloto

El copiloto es una aplicación local en Python (biblioteca estándar, sin framework web) con cinco capas.

| Capa | Responsabilidad | Archivo |
|---|---|---|
| Pantalla | Página única con progreso por etapa, métricas, descargas y panel de reanudar | `ui/index.html` |
| Servidor | Servidor `http.server` en `127.0.0.1:8765`; expone los endpoints de la pantalla | `app.py` |
| Orquestador | Ejecuta las etapas en orden, guarda `estado.json` y `log.txt`, y reanuda corridas | `pipeline.py` |
| Agentes | Llamadas a la API de mensajes de Anthropic con uso de herramientas | `agent.py` |
| Controles | Scripts que verifican cada etapa sin usar el modelo | `trace_rules.py`, `autoaprobar.py`, `consolidar_reglas.py`, `gate_codigo.py`, `verificar.py` |

**Herramientas del agente.** Cada agente puede usar `list_files`, `read_file`, `write_file` y `run_python`. Las rutas están confinadas a la carpeta de la corrida, hay archivos con lectura denegada y `run_python` solo ejecuta el módulo `pytest`.

**Por qué esta separación.** El modelo propone; los controles deterministas deciden si lo propuesto cumple. Así, un error del modelo no pasa a la siguiente etapa sin que un script lo detecte.

## Instalación y puesta en marcha en Windows

**Requisitos**

- Windows con PowerShell y Python 3.11 o superior (la corrida de referencia usó Python 3.14).
- Paquetes `pytest` y `pyyaml`. La aplicación los comprueba al arrancar y avisa si faltan.
- Una clave de API creada en la Consola de Claude, con saldo.
- Conexión a internet para llamar a la API.

**Pasos**

1. Descomprima `pipeline_app.zip` y abra PowerShell dentro de la carpeta `pipeline_app`.
2. Instale las dependencias: `pip install pytest pyyaml`.
3. Defina la clave en esa ventana: `$env:ANTHROPIC_API_KEY = "su-clave"`.
4. Arranque: `python app.py`.
5. Abra `http://127.0.0.1:8765` en el navegador.

La clave solo vive en la ventana de PowerShell. No se escribe en archivos ni en el registro de la corrida.

**Comprobación rápida.** `python tests/prueba_de_flujo.py` corre el flujo completo contra un servidor falso de la API, sin gastar saldo. Termina con el mensaje de reanudación correcta.

## Uso de la pantalla

1. **Panel de corridas anteriores.** Aparece arriba. Lista las carpetas de `runs` y marca qué etapas ya pasaron. Elija una y pulse **Reanudar** para continuar sin repetir lo hecho.
2. **Entrada.** Cargue los archivos legacy de un caso nuevo y pulse el botón de ejecutar.
3. **Progreso.** Cada etapa muestra su estado. Una etiqueta de actividad indica qué hace el modelo en ese momento (por ejemplo, leyendo un archivo o escribiendo código), y el registro muestra los reintentos.
4. **Métricas.** Una ficha muestra los tokens de salida y los leídos desde caché.
5. **Resultados.** Al terminar se habilitan dos descargas: el ZIP del proyecto y el informe de verificación.

Si una etapa falla, la corrida queda guardada. Corrija la causa (por ejemplo, saldo o red) y reanude desde ese punto.

## La carpeta de cada corrida y la reanudación

Cada corrida vive en `runs/<fecha>-<hora>/`, por ejemplo `20261113-145231`. El orquestador escribe allí tres tipos de información:

- `estado.json`: qué etapas terminaron, con sus métricas. Se guarda al cerrar cada etapa (punto de control).
- `log.txt`: el registro, incluidos los reintentos y las pausas.
- Los productos de cada etapa: reglas, reglas limpias, proyecto generado e informe.

**Cómo reanuda.** Al elegir una corrida, el orquestador lee `estado.json` y retoma desde la primera etapa sin terminar (parámetro `desde`). Las etapas anteriores no se vuelven a pagar. En la corrida de referencia, la etapa 4 falló una vez y se retomó así, sin repetir las tres primeras.

**Corridas sin `estado.json`.** Si la carpeta es de una versión anterior, `reconstruir_estado` deduce las etapas ya pasadas a partir de los archivos que existen. Los archivos `._*` y `.DS_Store` (basura de macOS al comprimir) se ignoran.

**Nota de reanudación.** Al retomar, el agente recibe una nota (`NOTA_REANUDAR`) que le dice que parte del trabajo ya existe y debe revisarlo en lugar de rehacerlo.

## Los cuatro agentes

| Agente | Recibe | Entrega | Control que lo revisa |
|---|---|---|---|
| Extractor | Archivos legacy con líneas numeradas | Reglas de negocio en JSON, cada una con cita literal, más preguntas abiertas y glosario | `trace_rules.py`: cada cita debe existir en el código |
| Validador PO | Reglas aprobadas automáticamente y las que requieren revisión | Un solo `reglas_limpias.json` con decisión por regla | `consolidar_reglas.py` |
| Generador | Reglas limpias | Proyecto hexagonal con pruebas, OpenAPI y ADR | `gate_codigo.py` (compuerta de calidad) |
| Verificador | Código legacy y ZIP del generador | Informe de verificación | `verificar.py` |

**Extractor.** Trabaja en dos pasadas independientes, A y B. La segunda sirve de contraste: si ambas llegan a la misma regla, hay consenso.

**Validador PO.** Simula a un Product Owner bancario técnico. Solo las reglas de seguridad, integridad de datos o regulación pueden cambiar el comportamiento del legacy, y cada cambio se declara como `diferencia_esperada`.

**Generador.** Itera hasta que la compuerta aprueba: estructura, dominio puro y sin `float`, complejidad ≤ 10, secretos y enmascaramiento, `tenant_id` en puertos y OpenAPI, al menos tres ADR, marcadores `REGLA`, y pruebas con cobertura ≥ 80 %.

**Verificador.** Recibe dos entradas, los archivos legacy y el ZIP, y arma escenarios leyendo el legacy.

## Controles automáticos

Son scripts de Python que no usan el modelo. Dan el mismo resultado cada vez que se ejecutan sobre los mismos archivos.

| Script | Etapa | Qué comprueba |
|---|---|---|
| `trace_rules.py` | Extractor | Que cada cita de cada regla aparezca literalmente en el archivo y la línea indicados |
| `autoaprobar.py` | Aprobación automática | Los cinco criterios de la política v1.0 (sección siguiente) |
| `consolidar_reglas.py` | Validador PO | Que las decisiones queden en un único `reglas_limpias.json` coherente |
| `gate_codigo.py` | Generador | La compuerta de calidad del código (sección 10) |
| `verificar.py` | Verificador | Que el informe cruce reglas, escenarios y código sin regla |

Si un control rechaza el resultado, el orquestador devuelve los hallazgos al agente y le pide corregir. Esto se repite por un número limitado de rondas (`loop(s, task, check, rounds)`).

## Aprobación automática y gobierno del Validador

La política v1.0 aprueba una regla sin intervención solo si cumple los cinco criterios:

| Criterio | Exige |
|---|---|
| C1 | Citas presentes y verificadas |
| C2 | Confianza alta |
| C3 | Evidencia en al menos dos archivos |
| C4 | Consenso con la segunda pasada del Extractor |
| C5 | La regla no está marcada «no probado por ejecución» |

Resultado posible por regla:

- `aprobada_automatica`: cumple los cinco criterios.
- `requiere_revision_humana`: falla alguno de C1 a C5.
- `hallazgo_tecnico`: elemento técnico (no de negocio), que no pasa por aprobación de negocio.

**Alcance.** La aprobación automática reduce trabajo, pero no equivale a una validación del negocio.

**Gobierno del Validador.** El Validador PO decide si cada regla es aprobada, mejorada o rechazada. Solo las reglas de seguridad, integridad de datos o regulación pueden cambiar el comportamiento del legacy, y cada cambio queda declarado como `diferencia_esperada`, de modo que el Verificador no lo cuente como error. Sus decisiones son simuladas: un Product Owner real debe confirmarlas antes de producción.

## El código generado

El Generador produce un paquete Python con arquitectura hexagonal, diseño guiado por el dominio y multitenencia.

| Carpeta | Contenido |
|---|---|
| `domain/` | Entidades y reglas de negocio puras, sin acceso a base de datos ni a la red; dinero con `Decimal`, nunca `float` |
| `application/` | Casos de uso que orquestan el dominio a través de puertos |
| `adapters/inbound/` | Entradas: proceso por lotes y API HTTP |
| `adapters/outbound/` | Salidas: repositorios en memoria y auditoría |
| `shared/` | Utilidades comunes, como el enmascaramiento de datos |
| `bootstrap.py` | Ensamblado de las piezas |

Además incluye `openapi`, ADR numerados, pruebas con `pytest`, un `Makefile` y los scripts `run_demo.ps1` y `run_demo.sh`.

**Convenciones.** Cada función que implementa una regla lleva un marcador `REGLA` con su identificador. El `tenant_id` aparece en todos los puertos y en la API. Los datos sensibles se enmascaran antes de registrarse.

**Compuerta de calidad.** `gate_codigo.py` rechaza el proyecto si falla alguna de estas comprobaciones: estructura de carpetas, pureza del dominio, complejidad mayor que 10, secretos o falta de enmascaramiento, `tenant_id` ausente, menos de tres ADR, marcadores `REGLA` faltantes, o pruebas con cobertura inferior a 80 %.

## Informe de verificación y niveles de evidencia

El Verificador emite un solo informe con tres respuestas:

1. **Reglas cumplidas.** Para cada regla de negocio, si el código nuevo la cumple.
2. **Código sin regla.** Clases y funciones que no tienen regla de origen, con una nota de si son necesarios (apoyo técnico) o sospechosos.
3. **Equivalencia funcional.** Para cada escenario, si el resultado del código nuevo es igual al esperado según el legacy.

Además hace una prueba de sensibilidad: cambia a propósito comparaciones de borde (por ejemplo `>` por `>=`) y comprueba que las pruebas lo detecten.

**Niveles de evidencia.** Cada escenario declara de dónde sale su resultado esperado:

| Nivel | Significado |
|---|---|
| Ejecución | Se corrió el legacy y se comparó la salida |
| Lectura | El resultado esperado se dedujo leyendo el código legacy |

Si ningún escenario se ejecutó contra el legacy, el veredicto es **«EQUIVALENTE POR LECTURA (no demostrado por ejecución del legacy)»**. Es el único veredicto honesto cuando no existe un entorno donde correr el legacy.

**Diferencias esperadas.** Las que el Validador declaró (cambios por seguridad, integridad o regulación) no cuentan como diferencia inesperada.

## Seguridad y privacidad

**Clave de API.** Se lee de la variable de entorno `ANTHROPIC_API_KEY`. No se guarda en archivos ni en `log.txt`.

**Alcance del agente.** Las herramientas están confinadas a la carpeta de la corrida: las rutas se validan, algunos archivos tienen lectura denegada y `run_python` solo permite el módulo `pytest`. El agente no puede ejecutar comandos arbitrarios.

**Servidor local.** La pantalla escucha solo en `127.0.0.1`, así que no es accesible desde otras máquinas.

**Datos enviados al modelo.** El código legacy sale de su equipo hacia la API de Anthropic. Antes de usar un legacy real con datos de clientes, confirme que la política de su organización lo permite.

**En el código generado.**

- La compuerta busca patrones de secretos y exige enmascaramiento de datos personales.
- En la corrida de referencia, la regla R-041 cambió una traza de depuración que imprimiría el nombre del cliente para que lo enmascare.
- El `tenant_id` es obligatorio en puertos y API para aislar a cada cliente.

**Límite.** El escaneo de la compuerta se basa en patrones. No reemplaza un análisis de vulnerabilidades ni una revisión de seguridad independiente.

## Costos, límites y robustez

**Qué consume saldo.** Solo las llamadas al modelo de las etapas 1, 3, 4 y 5. Los controles automáticos no cuestan nada.

**Caché de instrucciones.** Se marca con `cache_control` el sistema y el último mensaje, de modo que las lecturas repetidas se facturan como caché. En la corrida de referencia hubo 73.189 tokens de salida y 5.377.379 leídos desde caché. Sin caché, una corrida anterior superó los 6,4 millones de tokens de entrada.

**Robustez de las llamadas.**

- Respuesta en streaming (SSE), con etiqueta de actividad en la pantalla.
- Reintentos ante errores 429 y 5xx, respetando `retry-after`, hasta 5 veces.
- Tiempo máximo de 120 s sin recibir datos.
- `max_tokens` de 32.000. Si una respuesta se corta, las herramientas pendientes reciben un resultado de error y el agente continúa.
- Soporte de `pause_turn`.

**Conversaciones largas.** Al superar 450.000 caracteres, la conversación se reinicia con un resumen. No se modifican mensajes anteriores: las firmas de los bloques de razonamiento están ligadas al contenido previo y alterarlas produce un error 400.

**Razonamiento.** El parámetro `thinking` usa el modo `between_tools`. Si la API no lo acepta, se vuelve a intentar sin él.

## Resultados de la corrida de referencia 20261113-145231

El caso fue SIGSE, un módulo Oracle PL/SQL de liquidación de siniestros: 6 archivos y 1.098 líneas.

| Etapa | Resultado |
|---|---|
| Extractor | 45 reglas (32 de negocio y 13 técnicas) con 208 citas verificadas |
| Aprobación automática | 16 `aprobada_automatica`, 16 `requiere_revision_humana`, 13 `hallazgo_tecnico`. De las 16 en revisión, 15 no tienen evidencia en al menos dos archivos |
| Validador PO | 43 aprobadas, 2 mejoradas, 0 rechazadas, 0 diferencias esperadas |
| Generador | Paquete `claims_settlement`, 10 ADR, compuerta aprobada, complejidad máxima 9, cobertura 85,8 %, 133 pruebas |
| Verificador | 34 de 34 reglas cumplidas; 85 de 85 escenarios iguales; 0 diferencias inesperadas; 9 de 9 cambios de borde detectados |

**Mejoras del Validador.** R-036: un `CASE` sin `ELSE` pasa a dar error explícito. R-041: la traza de depuración enmascara el nombre del cliente.

**Veredicto.** Equivalente por lectura, no demostrado por ejecución del legacy.

**Hallazgos del Verificador.**

- `SettleOneClaim` hace COMMIT; el legacy lo deja al llamador (R-027).
- Un parámetro NULL ahora da `ParameterNullError` (ADR-006); el legacy seguía en silencio.
- 40 elementos sin regla, todos técnicos.
- Sin probar: lotes masivos, fechas con hora, más de 2 decimales y desborde de observaciones.
- Las reglas técnicas de código muerto (R-037 a R-040, R-042, R-043 y R-045) no tienen escenarios.

**Uso y tiempos.** 192 s en la etapa de generación y 369 s en la de verificación. La etapa 4 falló una vez y se reanudó.

**Nota sobre el conteo de pruebas.** El informe del Verificador menciona 81 casos, pero al ejecutar la suite se contaron 133 pruebas. Es una discrepancia pendiente de revisar en el Verificador.

## Limitaciones conocidas

- **Equivalencia por lectura.** El legacy no se ejecutó; no hay comparación contra salidas reales (golden master). Para demostrarla por ejecución se necesita un entorno donde correr el legacy con datos de prueba.
- **Aprobación automática.** Es una decisión de la IA aplicando criterios fijos, no una validación del negocio.
- **Product Owner simulado.** Sus decisiones deben ser confirmadas por un PO real.
- **Decisiones pendientes con el negocio.** El COMMIT dentro de `SettleOneClaim` y el error ante parámetros NULL.
- **Seguridad por patrones.** La compuerta no reemplaza un análisis de vulnerabilidades.
- **Escenarios no cubiertos.** Lotes masivos, fechas con hora, más de dos decimales y desborde de observaciones.
- **Reglas técnicas de código muerto.** Sin escenarios de prueba.
- **Un solo caso real.** Los resultados provienen de un sistema PL/SQL; con COBOL o RPG las cifras pueden ser distintas.
- **Persistencia.** El código generado usa repositorios en memoria; conectar una base de datos real es un trabajo posterior.
- **Pendiente.** Informe ejecutivo y análisis de vulnerabilidades completo.

## Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Falta `pytest` o `pyyaml` al arrancar | Dependencias sin instalar | `pip install pytest pyyaml` |
| Error 401 | Clave ausente o mal copiada | Revise `$env:ANTHROPIC_API_KEY` en esa misma ventana |
| Error 429 o 5xx | Límite de uso o servicio saturado | El copiloto reintenta solo (hasta 5 veces). Si persiste, espere y reanude |
| Error 400 «thinking block» o «invalid signature» | Historial de la conversación alterado | Use la versión actual: reinicia la conversación en vez de editarla |
| Error 400 en `tool_use` sin `tool_result` | Respuesta cortada por `max_tokens` | Corregido: ahora se devuelve un error de herramienta y el agente continúa |
| La pantalla parece detenida | El modelo trabaja sin salida de texto | Mire la etiqueta de actividad y `log.txt`; hay límite de 120 s sin datos |
| Una etapa falló | Red, saldo o error del modelo | Abra la corrida en el panel superior y pulse Reanudar |
| No aparece la corrida en el panel | Carpeta sin `estado.json` | Se reconstruye desde los archivos; verifique que esté dentro de `runs` |
| Cuesta más de lo esperado | Caché desactivada o conversación muy larga | Revise la ficha de tokens y la cifra de lecturas de caché |

## Referencia técnica

**Endpoints** (servidor en `127.0.0.1:8765`)

| Método y ruta | Función |
|---|---|
| `GET /api/state` | Estado de la corrida en curso |
| `POST /api/run` | Inicia una corrida nueva |
| `GET /api/runs` | Lista las corridas de la carpeta `runs` |
| `POST /api/resume` | Reanuda una corrida elegida |
| `GET /api/report` | Informe de verificación |
| `GET /api/download/zip` | Descarga el proyecto generado |
| `GET /api/download/report` | Descarga el informe |

**Archivos principales**

| Archivo | Rol |
|---|---|
| `app.py` | Servidor y endpoints; comprueba `pytest` y `pyyaml` al arrancar |
| `pipeline.py` | Orquestador, puntos de control, reanudación |
| `agent.py` | Llamadas a la API, herramientas, streaming, reintentos, caché |
| `ui/index.html` | Pantalla |
| `tests/prueba_de_flujo.py` | Prueba del flujo contra un servidor falso |

**Glosario**

- **ADR:** registro de una decisión de arquitectura.
- **Compuerta:** conjunto de comprobaciones que el código generado debe pasar.
- **Golden master:** salida real del legacy usada como referencia de comparación.
- **Hexagonal:** arquitectura que separa el dominio de sus entradas y salidas mediante puertos.
- **PO:** Product Owner, quien decide qué reglas de negocio valen.
- **Tenant:** cliente o inquilino aislado dentro de un mismo sistema.
