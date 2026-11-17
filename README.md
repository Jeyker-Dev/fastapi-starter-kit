# FastAPI Starter Kit

Production-ready FastAPI backend template for personal APIs with PostgreSQL 17, async SQLAlchemy 2.0, Alembic migrations, JWT authentication with rotating refresh tokens, Docker Compose, and strict quality tooling.

## What's Included

- **Stack**: Python 3.13 (`uv`), FastAPI, Uvicorn, PostgreSQL 17, SQLAlchemy 2.0 async (`asyncpg`), Alembic, PyJWT (`HS256`), `pwdlib` (Argon2), `pydantic-settings`, `ruff`, `mypy --strict`, `pytest` (`pytest-asyncio`, `httpx`), and multi-stage Docker.
- **Endpoints**:
  - `GET /health` — checks API and PostgreSQL connectivity (`200 ok` / `503 unavailable`).
  - `POST /auth/token` — OAuth2 password login returning an access JWT and an opaque refresh token.
  - `POST /auth/refresh` — rotates the refresh token within its family and detects reuse.
  - `POST /auth/logout` — idempotently revokes the refresh token's session family (`204`).
  - `GET /users/me` — returns the authenticated user profile (`Bearer` token).
- **Token flow**: short-lived `HS256` access JWTs (`15` minutes by default) paired with opaque refresh tokens (`30` days by default) stored only as SHA-256 hashes, rotated per use with family-wide revocation on reuse. Users are created via CLI rather than public signup. See [docs/areas/auth.md](docs/areas/auth.md) for the full auth specification and rules.

## Creating a New API

1. Click **Use this template** on GitHub to create a new repository, then clone it locally.
2. Rename project metadata as needed:
   - Update `name`, `description`, and `authors` in `pyproject.toml`.
   - Update the FastAPI `title` in `src/app/main.py`.
   - Keep the `src/app/` package name or update imports, `Dockerfile`, `docker-compose.yml`, and `migrations/env.py` if you rename the package.
3. Create `.env` from `.env.example` and generate a 32+ character `JWT_SECRET`:

   ```bash
   cp .env.example .env
   openssl rand -hex 32
   ```

   Paste the generated output as the value of `JWT_SECRET=` in `.env`. Before deploying to a server, replace the default `POSTGRES_PASSWORD` and `DATABASE_URL` credentials as well.

## Running with Docker Compose

1. Start PostgreSQL and the API (Compose waits for `db` to pass its health check and runs `alembic upgrade head` automatically before starting Uvicorn):

   ```bash
   docker compose up -d --wait
   ```

2. Create your first active user (prompts twice for the password, minimum 12 characters):

   ```bash
   docker compose exec api python scripts/create_user.py --email admin@example.com
   ```

3. Verify login and `GET /users/me`:

   ```bash
   curl -sS -X POST http://localhost:8000/auth/token \
     --data-urlencode "username=admin@example.com" \
     --data-urlencode "password=your-strong-password"
   ```

   Take `access_token` from the JSON response and query `/users/me`:

   ```bash
   curl -sS http://localhost:8000/users/me \
     -H "Authorization: Bearer <access_token>"
   ```

## Local Development

Install Python dependencies (including dev tools) with `uv`:

```bash
uv sync
```

Integration tests run against a separate `app_test` database created automatically inside the `db` Compose service (make sure `.env` exists and `db` is running first):

```bash
docker compose up -d db --wait
```

Run the four quality checks before every commit:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## Adding a New Domain

Organize every new feature as a domain folder under `src/app/` by copying the layout of `src/app/users/`:

- `domain.py` — pure Python frozen dataclasses and `Protocol` ports (no FastAPI, Pydantic, or SQLAlchemy imports).
- `errors.py` — domain exceptions inheriting from `BusinessRuleError` (`src/app/errors.py`).
- `models.py` — typed SQLAlchemy 2.0 ORM models (`Mapped[...]` / `mapped_column`).
- `repository.py` — SQLAlchemy repository implementing the domain port and converting models to domain entities.
- `service.py` — application use cases taking ports and `Clock` via `__init__`.
- `schemas.py` — Pydantic request/response models for the HTTP edge.
- `api.py` — `APIRouter` translating HTTP requests/errors to and from the service.

See [docs/01-architecture.md](docs/01-architecture.md) for layer boundaries and project conventions.

After creating a domain:

1. **Register the SQLAlchemy model** in `migrations/env.py` (import it and include it in `_MODELS`) so Alembic sees the table.
2. **Generate and apply the migration** (with `db` running):

   ```bash
   DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app \
     uv run alembic revision --autogenerate -m "create <domain>"
   # Review the generated file in migrations/versions/ before applying
   DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app \
     uv run alembic upgrade head
   ```

3. **Mount the router** (and register any domain error handlers) inside `create_app()` in `src/app/main.py`.
