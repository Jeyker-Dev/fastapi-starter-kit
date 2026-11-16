# ADR-001: PostgreSQL con SQLAlchemy 2.0 async y Alembic

- **Date:** 2026-11-16
- **Status:** Accepted

## Context

Cada API creada desde la plantilla necesita una base de datos relacional, migraciones versionadas y un acceso tipado que pase `mypy --strict`. Las apps previstas manejan dinero (montos en USD, Bs y USDT) y llaman a servicios externos con `httpx`. Las APIs se despliegan con Docker en el mismo VPS.

## Decision

1. La base de datos es PostgreSQL 17, como servicio `db` en `docker-compose.yml`.
2. El acceso a datos usa SQLAlchemy 2.0 en modo async con el driver asyncpg, con modelos declarativos tipados (`Mapped[...]` y `mapped_column`).
3. Las migraciones se escriben con Alembic, usando su plantilla async. La API aplica `alembic upgrade head` antes de arrancar.
4. Los esquemas Pydantic viven solo en el borde HTTP, el dominio usa dataclasses congeladas y los modelos SQLAlchemy no salen de la capa de datos.
5. Los montos de dinero se guardan como `NUMERIC` y se manejan como `Decimal`.

## Alternatives considered

- SQLite: más simple en desarrollo, pero limitado con escrituras concurrentes y con varias APIs en producción; además, la base de desarrollo sería distinta de la de producción.
- SQLModel: une el esquema Pydantic y la tabla en una sola clase, lo que contradice la regla de Pydantic solo en el borde y expone columnas internas (como `password_hash`) en las respuestas si no se tiene cuidado. Su soporte de `mypy --strict` también es más débil.
- SQLAlchemy síncrono: bloquea el event loop de FastAPI, que es async, y obliga a mezclar modelos cuando la app llama a servicios externos con `httpx` async.

## Consequences

- Los tests de integración necesitan un PostgreSQL real (el mismo servicio `db` de compose, con una base de tests aparte).
- Las sesiones async exigen cuidado con la carga diferida de relaciones: se cargan de forma explícita (`selectinload`) y nunca de forma implícita.
- Toda tabla nueva de una app pasa por una migración de Alembic.
