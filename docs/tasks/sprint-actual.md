# Sprint actual

## En curso

Fase 0 — Base del proyecto.

- [ ] [INFRA] Proyecto con uv y herramientas de calidad — `uv run ruff check .`, `uv run mypy` y `uv run pytest` terminan en 0 con un test mínimo; `pyproject.toml` tiene la configuración de `python-conventions` y Python 3.13 fijado — depends on: -
- [ ] [INFRA] Configuración con pydantic-settings — la API no arranca y muestra qué variable falta si `DATABASE_URL` o `JWT_SECRET` no están, o si `JWT_SECRET` tiene menos de 32 caracteres; `.env.example` lista todas las variables — depends on: Proyecto con uv
- [ ] [DB] Conexión async y Alembic — `alembic upgrade head` corre contra el `db` de compose sin errores con el `env.py` async; existe la fábrica de sesiones en `src/app/db.py` — depends on: Configuración
- [ ] [INFRA] Docker y compose — `docker compose up` levanta `db` y `api`; `api` espera a que `db` esté healthy y aplica las migraciones antes de arrancar; el contenedor corre como usuario no root — depends on: Conexión async y Alembic
- [ ] [API] Endpoint de salud — `GET /health` responde 200 `{"status": "ok"}` con la base arriba y 503 `{"status": "unavailable"}` con la base detenida (test de integración) — depends on: Docker y compose

## Hechas en este sprint
