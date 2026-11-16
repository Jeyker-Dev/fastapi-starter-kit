# Base de datos

Decisión de base: [ADR-001](../decisions/ADR-001-postgresql-sqlalchemy-async.md).

## Tablas de dominio

### `users`

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | `UUID` | Clave primaria, generada por la aplicación |
| `email` | `VARCHAR(320)` | Único, normalizado en minúsculas |
| `password_hash` | `TEXT` | Hash Argon2 de pwdlib |
| `is_active` | `BOOLEAN` | `true` por defecto |
| `created_at` | `TIMESTAMPTZ` | UTC |
| `updated_at` | `TIMESTAMPTZ` | UTC |

### `refresh_tokens`

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | `UUID` | Clave primaria |
| `user_id` | `UUID` | FK a `users.id`, `ON DELETE CASCADE`, con índice |
| `family_id` | `UUID` | Una por login, con índice |
| `token_hash` | `CHAR(64)` | SHA-256 en hexadecimal del token, único |
| `expires_at` | `TIMESTAMPTZ` | UTC |
| `revoked_at` | `TIMESTAMPTZ` | `NULL` mientras está activo |
| `created_at` | `TIMESTAMPTZ` | UTC |

## Reglas

- Una migración de Alembic por cambio de esquema, con un mensaje descriptivo (`alembic revision --autogenerate -m "create users"`), revisada a mano antes de aplicarla.
- La migración inicial crea `users` y `refresh_tokens`.
- Los tests de integración usan una base aparte (`app_test`) en el mismo servicio `db`, nunca la de desarrollo.
- La URL de conexión usa el driver async: `postgresql+asyncpg://...`.

## Riesgos conocidos

- `refresh_tokens` crece con cada rotación y no hay limpieza automática todavía (está en el backlog).
- Cambiar `JWT_SECRET` invalida todas las sesiones de access token, pero no los refresh tokens.
