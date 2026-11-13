# Política de seguridad

ThinAi — Copiloto de Modernización es un prototipo creado para el Hackathon AI 2026. Esta página explica cómo reportar un problema de seguridad, qué controles tiene el proyecto y cuáles son sus límites.

## Cómo reportar una vulnerabilidad

No abra un *issue* público para reportar una vulnerabilidad.

Use el reporte privado de GitHub: en la pestaña **Security** del repositorio, pulse **Report a vulnerability**. Incluya:

- Qué componente afecta (`app.py`, `agent.py`, `pipeline.py`, `tools/` o `ui/`).
- Los pasos para reproducirlo.
- El impacto que usted ve.

Se confirmará la recepción y se informará de la corrección o de la decisión de no corregir. Es un proyecto de hackathon mantenido por una persona, así que no hay plazos garantizados.

## Versiones con soporte

Solo la última versión de la rama `main`.

## Controles que existen

**Clave de API**
- Se lee de la variable de entorno `ANTHROPIC_API_KEY`.
- No se escribe en archivos del proyecto ni en el registro de la corrida (`log.txt`).
- `.gitignore` excluye `.env`.

**Servidor local**
- La pantalla escucha solo en `127.0.0.1:8765`, por lo que no es accesible desde otras máquinas.

**Alcance de los agentes**
- Las herramientas (`list_files`, `read_file`, `write_file`, `run_python`) están confinadas a la carpeta de la corrida: las rutas se validan.
- Algunos archivos tienen lectura denegada para evitar que un agente vea el trabajo del otro.
- `run_python` solo permite el módulo `pytest` y los scripts de control; no ejecuta comandos arbitrarios.

**Controles automáticos sobre el código generado** (`gate_codigo.py`)
- Búsqueda de secretos por patrones.
- Exigencia de enmascaramiento de datos personales en trazas y registros.
- `tenant_id` obligatorio en los puertos y en la API, para aislar a cada cliente.
- Dominio sin `float` para dinero, complejidad máxima de 10 por función y cobertura de pruebas de al menos 80 %.

**Decisiones de seguridad del Validador PO**
- Solo las reglas de seguridad, integridad de datos o regulación pueden cambiar el comportamiento del legacy, y cada cambio queda declarado.
- Ejemplo real: en la corrida de referencia, la regla R-041 cambió una traza de depuración que habría impreso el nombre del cliente, para que lo enmascare.

## Límites conocidos

Este proyecto **no** ha pasado por una auditoría de seguridad.

- La búsqueda de secretos y de datos sin enmascarar se basa en patrones. No reemplaza un análisis de vulnerabilidades, un análisis estático de seguridad ni una revisión independiente.
- El código legacy que se procesa se envía a la API de Anthropic. No use código ni datos de clientes sin confirmar que la política de su organización lo permite.
- El código generado es un punto de partida: usa repositorios en memoria y no incluye autenticación ni autorización. Antes de producción necesita ambas, además de una base de datos real y una revisión de seguridad.
- La aprobación automática de reglas y las decisiones del Product Owner son de IA. Un Product Owner real debe confirmarlas.
- La equivalencia entre legacy y código nuevo se demostró por lectura del código, no ejecutando el legacy.

## Recomendaciones para quien lo use

- No suba claves de API al repositorio. Si una se expone, revóquela en la Consola de Claude y cree otra.
- Revise la carpeta `runs/` antes de publicar un repositorio: contiene el código legacy de entrada y todo lo que generaron los agentes.
- Use datos de ejemplo o anonimizados en `examples/` y en las pruebas.
- Mantenga el repositorio en privado mientras no confirme que puede publicar el código legacy usado como caso de prueba.
