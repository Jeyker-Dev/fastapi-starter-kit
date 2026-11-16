# Prompt para Antigravity: construir la plantilla

Copia todo lo que está debajo de la línea en el agente de Antigravity, con el workspace abierto en la raíz del repo `fastapi-starter-kit`.

---

Vas a construir el código de esta plantilla de FastAPI a partir de su documentación. Trabajas tarea por tarea y te detienes a esperar mi aprobación donde se indica.

## Contexto (leer antes de empezar)

1. `AGENTS.md`: stack, comandos y reglas del proyecto.
2. `docs/00-vision.md`: qué es la plantilla y qué queda fuera de alcance.
3. `docs/01-architecture.md`: estructura de carpetas, capas, convenciones y rutas.
4. `docs/areas/auth.md`, `docs/areas/database.md` y `docs/areas/infrastructure.md`: endpoints, reglas de negocio, tablas, variables de entorno y Docker.
5. `docs/decisions/ADR-001` a `ADR-004`: decisiones ya tomadas. No las cambies.
6. `docs/tasks/sprint-actual.md` y `docs/tasks/backlog.md`: las tareas y su criterio de aceptación.

## Reglas

- La documentación es la fuente de verdad. Si algo no está escrito, o si dos documentos se contradicen, detente y pregúntame; no lo resuelvas por tu cuenta.
- Una sola tarea por turno, en el orden del sprint. No adelantes trabajo de la tarea siguiente.
- Test primero: para cada regla verificable, escribe el test, ejecútalo y muéstrame que falla por la razón correcta antes de implementar. Los tests se llaman `<modulo>_test.py`, espejan `src/app/` y son funciones de pytest, sin clases `TestCase`.
- Antes de usar una API de FastAPI, SQLAlchemy, Alembic, PyJWT o pwdlib, consulta su documentación oficial actual. No uses `python-jose` ni `passlib`.
- Solo las dependencias que nombra `docs/01-architecture.md`. Si crees que falta una, pregúntame antes de agregarla. Usa siempre `uv add` (o `uv add --dev` para test y herramientas); nunca `pip`.
- Nada de `Any`, `float` para dinero ni `datetime.now()` fuera de `SystemClock`. Ningún `domain.py` importa FastAPI, Pydantic ni SQLAlchemy.
- No hagas commits ni push. Al cerrar cada tarea, propón un mensaje de commit en formato Conventional Commits, con título y cuerpo en inglés y sin líneas de coautoría.
- Al cerrar cada tarea, estos cuatro comandos deben terminar en 0. Muéstrame su salida:

  ```bash
  uv run ruff format --check .
  uv run ruff check .
  uv run mypy
  uv run pytest
  ```

- Después de cada tarea: dime qué criterio de aceptación cubriste, cómo lo comprobaste y qué decisiones tomaste, y **detente a esperar mi aprobación** antes de pasar a la siguiente. Si pido cambios, corrígelos en la misma tarea.

## Paso 0: Verificar el entorno

Comprueba que estén instalados `uv` y `docker` (con `docker compose`) y que el repo solo tenga la documentación. Resúmeme en cinco líneas lo que vas a construir en la Fase 0. Espera mi OK.

## Paso 1: Fase 0, base del proyecto

Haz las tareas de `docs/tasks/sprint-actual.md` en orden:

1. Proyecto con uv y herramientas de calidad. En la raíz del repo, usa `uv init --package --name app` para tener la estructura `src/app/` (no `uv init app`, que crea una subcarpeta). Fija Python 3.13 y copia tal cual la configuración de ruff, mypy y pytest de `docs/areas/infrastructure.md`.
2. Configuración con pydantic-settings y `.env.example`.
3. Conexión async (`src/app/db.py`) y Alembic con la plantilla async.
4. `Dockerfile` y `docker-compose.yml`, según `docs/areas/infrastructure.md`.
5. Endpoint `GET /health`, con test de integración para la base arriba y para la base caída.

## Paso 2: Fase 1, usuarios y autenticación

Antes de empezar, mueve las tareas de la Fase 1 del backlog al sprint, en el mismo orden, y muéstrame el cambio. Espera mi OK. Después haz cada tarea siguiendo `docs/areas/auth.md` al pie de la letra: rutas, cuerpos, códigos de estado, textos de `detail` y errores de dominio.

Para cada tarea de autenticación, los tests de integración cubren el caso exitoso y cada caso de error que nombra su criterio de aceptación. Usa `httpx.AsyncClient` con `ASGITransport` y la base `app_test`. El reloj se reemplaza por uno falso para probar los vencimientos sin esperar.

## Paso 3: Fase 2, lista para usar como plantilla

Mueve las tareas de la Fase 2 al sprint y escribe el `README.md` de la raíz con la guía para crear una API nueva. Para comprobarla, sigue la guía desde cero en un clon temporal fuera del repo hasta lograr un login exitoso, y muéstrame los comandos y las respuestas.

## Paso 4: Documentar

Cada vez que apruebe una tarea:

1. Márcala con `[x]` en `docs/tasks/sprint-actual.md` y muévela a `## Hechas en este sprint`. Yo agrego el hash del commit cuando lo haga.
2. Agrega una entrada en `docs/changelog.md` bajo la fecha del día: qué cambió y dónde (ruta, comando, archivo), no cómo.
3. Si una regla cambió, actualiza su `docs/areas/*.md`. Si tuviste que tomar una decisión de arquitectura nueva, propón un ADR y espera mi OK antes de escribirlo.
