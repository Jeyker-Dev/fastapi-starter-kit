# Infraestructura

## Configuración

Variables de entorno leídas con pydantic-settings en `src/app/config.py`. `.env.example` las lista todas con valores vacíos o de ejemplo, y `.env` nunca se versiona.

| Variable | Ejemplo | Regla |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@db:5432/app` | Obligatoria |
| `JWT_SECRET` | (`openssl rand -hex 32`) | Obligatoria, al menos 32 caracteres; si no, la API no arranca |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | Opcional |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Opcional |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `app` | Solo para el servicio `db` de compose |

## Docker

- `Dockerfile` multi-stage: una etapa instala las dependencias con uv a partir de `uv.lock` (sin las de desarrollo) y la final copia el entorno y el código, agrega el entorno virtual al `PATH` y corre como usuario no root.
- Dentro del contenedor los comandos se corren directo (`alembic`, `uvicorn`, `python`), sin `uv run`, para que uv no intente sincronizar las dependencias de desarrollo al arrancar.
- `docker-compose.yml`:
  - `db`: PostgreSQL 17 con volumen persistente y `healthcheck` (`pg_isready`).
  - `api`: depende de `db` en estado `healthy`, corre `alembic upgrade head` y después Uvicorn en el puerto 8000, y lee `.env`.
- El mismo compose sirve en local y en el VPS; en el VPS solo cambia el `.env`.

## Salud

`GET /health` ejecuta `SELECT 1` contra la base. Responde 200 `{"status": "ok"}` si responde y 503 `{"status": "unavailable"}` si no.

## Calidad

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Configuración en `pyproject.toml` (de la skill `python-conventions`, más `asyncio_mode` para los tests async):

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = [
  "E", "F", "I", "N", "UP", "B", "SIM",
  "C90",      # cyclomatic complexity
  "FBT",      # boolean trap: no flag parameters
  "PLR2004",  # magic value comparison
  "RET505",   # no else after return
  "PLR0913",  # too many arguments
  "PLR0915",  # too many statements
]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["PLR2004", "FBT"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
files = ["src", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["*_test.py"]
asyncio_mode = "auto"
```
