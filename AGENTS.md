# AGENTS

## Stack

- FastAPI, Python 3.13 (uv), PostgreSQL 17, SQLAlchemy 2.0 async (asyncpg), Alembic.
- Auth: PyJWT and pwdlib (Argon2).
- Tests: pytest (`uv run pytest`). Lint: ruff (`uv run ruff check .`). Types: mypy strict (`uv run mypy`).

## Commands

```bash
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff format --check . && uv run ruff check . && uv run mypy
docker compose exec api python scripts/create_user.py --email <email>
```

## Project rules

- This repository is a template: never add business rules of a specific app.
- Never use `float` for money; use `Decimal` and `NUMERIC`.
- Never call `datetime.now()` in domain or services; use the injected `Clock`.
- Never call `Base.metadata.create_all()` outside tests; every schema change is an Alembic migration.
- Never put Pydantic, FastAPI, or SQLAlchemy imports in a `domain.py`.
- Never store a refresh token in plain text; only its SHA-256 hash.
- API error messages (`detail`) are in English; `docs/` is in Spanish.

## Documentation

`docs/` is the source of truth. Before implementing, read `docs/README.md`,
`docs/00-vision.md`, `docs/01-architecture.md`, and the affected
`docs/areas/*.md`. After finishing, follow the `project-docs` skill.

## Skills

General conventions come from installed skills (`clean-code`,
`testing-strategy`, `error-handling`, and `python-conventions`). FastAPI,
SQLAlchemy, and Alembic APIs come from their official documentation.
