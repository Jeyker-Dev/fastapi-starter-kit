# Arquitectura

## Stack

- Python 3.13, gestionado con uv (`uv python pin 3.13`).
- FastAPI y Uvicorn.
- PostgreSQL 17, con SQLAlchemy 2.0 async (driver asyncpg) y Alembic para las migraciones. Ver [ADR-001](decisions/ADR-001-postgresql-sqlalchemy-async.md).
- Autenticación: PyJWT (access token) y pwdlib con Argon2 (contraseñas). Ver [ADR-002](decisions/ADR-002-jwt-refresh-token-rotation.md).
- Configuración: pydantic-settings, leída de variables de entorno.
- Calidad: ruff, mypy `--strict` y pytest (con pytest-asyncio y httpx para los tests de la API).
- Docker: `Dockerfile` multi-stage con uv y `docker-compose.yml` con los servicios `api` y `db`.

## Capas y responsabilidades

Código organizado por dominio y no por rol técnico. Ver [ADR-003](decisions/ADR-003-domain-folders-and-layers.md).

```
pyproject.toml
uv.lock
alembic.ini
migrations/                  Alembic: env.py async y versions/
src/app/
├── main.py                  create_app(): routers, manejadores de errores, ciclo de vida
├── config.py                Settings (pydantic-settings), cargadas una vez al arrancar
├── db.py                    Engine async, fábrica de sesiones y Base declarativa
├── errors.py                BusinessRuleError, la base de todos los errores de negocio
├── clock.py                 Protocolo Clock y SystemClock (la hora se inyecta)
├── users/
│   ├── domain.py            User (dataclass congelada) y el puerto UserRepository
│   ├── errors.py            EmailAlreadyRegistered, PasswordTooShort
│   ├── models.py            UserModel (SQLAlchemy)
│   ├── repository.py        SqlAlchemyUserRepository
│   ├── service.py           Casos de uso: crear usuario, obtener por id
│   ├── schemas.py           Esquemas Pydantic de entrada y salida HTTP
│   └── api.py               Router: GET /users/me
├── auth/
│   ├── domain.py            TokenPair, RefreshToken y el puerto RefreshTokenRepository
│   ├── errors.py            InvalidCredentials, InvalidRefreshToken, RefreshTokenReused
│   ├── passwords.py         PasswordHasher (pwdlib, Argon2)
│   ├── tokens.py            AccessTokenIssuer (PyJWT) y generación de refresh tokens
│   ├── models.py            RefreshTokenModel (SQLAlchemy)
│   ├── repository.py        SqlAlchemyRefreshTokenRepository
│   ├── service.py           Casos de uso: login, refresh, logout
│   ├── dependencies.py      get_current_user para proteger endpoints
│   ├── schemas.py           Esquemas Pydantic de entrada y salida HTTP
│   └── api.py               Router: /auth/token, /auth/refresh, /auth/logout
└── health/
    └── api.py               Router: GET /health
scripts/
└── create_user.py           Alta de usuario por línea de comandos
tests/
├── unit/app/                Espeja src/app/; sin base de datos ni red
└── integration/             API completa contra PostgreSQL real
Dockerfile
docker-compose.yml
.env.example
```

Reglas entre capas:

1. `domain.py` es Python puro: no importa FastAPI, SQLAlchemy ni Pydantic.
2. `service.py` depende de los puertos de `domain.py` (protocolos), nunca de una implementación concreta. Los colaboradores se inyectan por `__init__`.
3. `repository.py` y `models.py` implementan los puertos con SQLAlchemy. Los modelos no salen de esa capa: el repositorio devuelve dataclasses de dominio.
4. `api.py` y `schemas.py` son el borde HTTP: traducen Pydantic a dominio, llaman al servicio y traducen los errores de negocio a respuestas HTTP.
5. Un dominio puede usar el `service.py` de otro (por ejemplo, `auth` usa `users`), nunca sus modelos ni su repositorio.

## Convenciones críticas

- Los montos de dinero, cuando una app los agregue, se guardan como `NUMERIC` y se manejan con `Decimal`. Nunca `float`.
- Toda fecha y hora se guarda en UTC (`TIMESTAMP WITH TIME ZONE`) y se obtiene del `Clock` inyectado, nunca de `datetime.now()` directo en el dominio o los servicios.
- Los ids son UUID generados por la aplicación.
- Cada cambio de esquema es una migración de Alembic versionada; nunca `create_all()` fuera de los tests.
- Los errores de negocio heredan de `BusinessRuleError`, uno por regla. Solo el borde HTTP los convierte en códigos de estado.
- Los secretos solo vienen del entorno. `.env.example` lista todas las variables con valores vacíos y `.env` nunca se versiona.
- Los textos que devuelve la API (`detail` de los errores) van en inglés.

## Mapa de rutas

| Método | Ruta | Autenticación | Qué hace |
|---|---|---|---|
| GET | `/health` | No | Confirma que la API y la base responden |
| POST | `/auth/token` | No | Login con email y contraseña; devuelve el par de tokens |
| POST | `/auth/refresh` | No (usa el refresh token) | Rota el refresh token y devuelve un par nuevo |
| POST | `/auth/logout` | No (usa el refresh token) | Revoca la sesión del refresh token |
| GET | `/users/me` | Bearer | Devuelve el usuario autenticado |

El detalle de cada ruta y sus reglas está en [areas/auth.md](areas/auth.md).

## Decisiones

- [ADR-001](decisions/ADR-001-postgresql-sqlalchemy-async.md): PostgreSQL con SQLAlchemy 2.0 async y Alembic.
- [ADR-002](decisions/ADR-002-jwt-refresh-token-rotation.md): JWT de vida corta y refresh token rotativo con detección de reúso.
- [ADR-003](decisions/ADR-003-domain-folders-and-layers.md): carpetas por dominio y capas con puertos.
- [ADR-004](decisions/ADR-004-template-copied-per-app.md): plantilla que se copia por app en lugar de una API compartida.
