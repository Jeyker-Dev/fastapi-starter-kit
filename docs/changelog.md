# Changelog

## 2026-11-17

- Login en `POST /auth/token` (`src/app/auth/api.py`): access token JWT y refresh token opaco guardado como hash SHA-256, con 401 uniforme para credenciales inválidas. Tests en `tests/unit/app/auth/` y `tests/integration/auth_token_test.py`.

## 2026-11-16

- Hasher Argon2 con `pwdlib` en `src/app/auth/passwords.py`, script `scripts/create_user.py`, copia de `scripts/` en `Dockerfile` y tests en `tests/unit/app/auth/passwords_test.py` y `tests/integration/create_user_script_test.py`.
- Base de errores `BusinessRuleError` (`src/app/errors.py`), `Clock`/`SystemClock` (`src/app/clock.py`), dominio, errores, servicio y repositorio de usuarios (`src/app/users/`) con tests unitarios en `tests/unit/app/`.
- Modelos `UserModel` (`src/app/users/models.py`) y `RefreshTokenModel` (`src/app/auth/models.py`), migración inicial en `migrations/versions/2e215cbe92c7_create_users_and_refresh_tokens.py` y tests en `tests/integration/migrations_test.py`.
- Movidas las tareas de Fase 1 desde `docs/tasks/backlog.md` a `docs/tasks/sprint-actual.md`.
- Endpoint `GET /health` en `src/app/health/api.py`, dependencia `get_session` en `src/app/db.py`, registro en `src/app/main.py`, `httpx` en dependencias de desarrollo y tests de integración en `tests/integration/health_test.py`.
- `Dockerfile` multi-stage con usuario no root, `.dockerignore`, `docker-compose.yml` (`db` PostgreSQL 17 y `api`), dependencia `uvicorn`, `src/app/main.py` (`create_app` y ciclo de vida) y tests en `tests/unit/app/main_test.py`.
- Conexión async con SQLAlchemy 2.0 en `src/app/db.py`, configuración async de Alembic en `alembic.ini` y `migrations/env.py`, y tests unitarios en `tests/unit/app/db_test.py`.
- Configuración con `pydantic-settings` en `src/app/config.py`, plantilla de variables `.env.example` y tests unitarios en `tests/unit/app/config_test.py`.
- Inicialización del proyecto con `uv` (`src/app/`), Python 3.13 en `.python-version`, configuración de `ruff`, `mypy --strict` y `pytest` en `pyproject.toml`, `.gitignore` y test mínimo en `tests/unit/app/init_test.py`.
- Documentación inicial de la plantilla: visión, arquitectura, roadmap, áreas de autenticación, base de datos e infraestructura, ADR-001 a ADR-004, tareas de la Fase 0 en el sprint y prompt para construir la plantilla con Antigravity.
