# Autenticación y usuarios

Decisión de base: [ADR-002](../decisions/ADR-002-jwt-refresh-token-rotation.md).

## Endpoints

### `POST /auth/token`

- Cuerpo: formulario `application/x-www-form-urlencoded` de OAuth2 (`username` = email, `password`).
- 200:

  ```json
  {
    "access_token": "<jwt>",
    "refresh_token": "<opaque>",
    "token_type": "bearer",
    "expires_in": 900
  }
  ```

- 401 con `{"detail": "Incorrect email or password"}` y la cabecera `WWW-Authenticate: Bearer`, tanto si el email no existe, como si la contraseña es incorrecta o el usuario está inactivo.

### `POST /auth/refresh`

- Cuerpo JSON: `{"refresh_token": "<opaque>"}`.
- 200: un par nuevo, con el mismo formato que `/auth/token`.
- 401 con `{"detail": "Invalid refresh token"}` si el token no existe, venció, fue revocado o su usuario está inactivo.

### `POST /auth/logout`

- Cuerpo JSON: `{"refresh_token": "<opaque>"}`.
- 204 siempre, aunque el token no exista o ya esté revocado (es idempotente y no revela nada).

### `GET /users/me`

- Cabecera `Authorization: Bearer <access_token>`.
- 200: `{"id": "<uuid>", "email": "...", "is_active": true, "created_at": "<ISO 8601 UTC>"}`. Nunca incluye `password_hash`.
- 401 con `{"detail": "Could not validate credentials"}` y `WWW-Authenticate: Bearer` si el token falta, tiene mala firma, venció, no es de tipo `access` o el usuario no existe o está inactivo.

## Reglas de negocio vigentes

1. El email se normaliza antes de guardarlo y antes de buscarlo: sin espacios al inicio ni al final y en minúsculas. Es único.
2. La contraseña de un usuario nuevo tiene al menos 12 caracteres.
3. Si el email no existe, el login igual verifica la contraseña contra un hash ficticio, para que el tiempo de respuesta sea el mismo.
4. Un usuario con `is_active = false` no puede hacer login, ni refresh, ni usar sus access tokens.
5. El access token dura `ACCESS_TOKEN_TTL_MINUTES` (15 por defecto) y lleva `sub` (id del usuario), `type = "access"`, `iat` y `exp`.
6. El refresh token dura `REFRESH_TOKEN_TTL_DAYS` (30 por defecto). Solo se guarda su hash SHA-256; el valor en claro se devuelve una sola vez.
7. Cada login crea una familia nueva de refresh tokens (`family_id`), una por sesión o dispositivo.
8. Cada refresh exitoso revoca el token usado y emite uno nuevo de la misma familia, que vence a los `REFRESH_TOKEN_TTL_DAYS` contados desde el refresh.
9. Si llega a `/auth/refresh` un token ya revocado, se revocan todos los tokens activos de su familia y se responde 401. El error de dominio es `RefreshTokenReused`.
10. El logout revoca todos los tokens activos de la familia del token recibido.
11. Toda hora se toma del `Clock` inyectado, en UTC.

## Alta de usuarios

`uv run python scripts/create_user.py --email <email>` pide la contraseña dos veces con `getpass` (nunca como argumento, para que no quede en el historial del shell), aplica las reglas 1 y 2 y crea el usuario activo. Si el email ya existe, termina con un mensaje claro y código de salida distinto de 0. Dentro de Docker: `docker compose exec api python scripts/create_user.py --email <email>`.

## Errores de dominio

Todos heredan de `BusinessRuleError` (`src/app/errors.py`):

| Error | Cuándo | Respuesta HTTP |
|---|---|---|
| `InvalidCredentials` | Email inexistente, contraseña incorrecta o usuario inactivo en el login | 401 |
| `InvalidRefreshToken` | Refresh token inexistente, vencido o de un usuario inactivo | 401 |
| `RefreshTokenReused` | Refresh token ya revocado | 401 (después de revocar la familia) |
| `EmailAlreadyRegistered` | Alta con un email existente | Solo en el script |
| `PasswordTooShort` | Alta con menos de 12 caracteres | Solo en el script |

Los errores esperados no se registran en el log. Un reúso detectado (`RefreshTokenReused`) sí se registra como `warning`, con el `family_id` y sin el token.
