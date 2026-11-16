# Changelog

## 2026-11-16

- Conexión async con SQLAlchemy 2.0 en `src/app/db.py`, configuración async de Alembic en `alembic.ini` y `migrations/env.py`, y tests unitarios en `tests/unit/app/db_test.py`.
- Configuración con `pydantic-settings` en `src/app/config.py`, plantilla de variables `.env.example` y tests unitarios en `tests/unit/app/config_test.py`.
- Inicialización del proyecto con `uv` (`src/app/`), Python 3.13 en `.python-version`, configuración de `ruff`, `mypy --strict` y `pytest` en `pyproject.toml`, `.gitignore` y test mínimo en `tests/unit/app/init_test.py`.
- Documentación inicial de la plantilla: visión, arquitectura, roadmap, áreas de autenticación, base de datos e infraestructura, ADR-001 a ADR-004, tareas de la Fase 0 en el sprint y prompt para construir la plantilla con Antigravity.
