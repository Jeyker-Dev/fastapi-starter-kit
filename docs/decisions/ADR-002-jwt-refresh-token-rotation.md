# ADR-002: JWT de vida corta y refresh token rotativo con detección de reúso

- **Date:** 2026-11-16
- **Status:** Accepted

## Context

Las APIs las consumen apps móviles (Flutter, publicadas en Play Store) que funcionan offline-first: la app guarda los tokens en el almacenamiento seguro del teléfono y solo los usa para sincronizar. Cualquier secreto incluido en un APK se puede extraer. Cada app tiene uno o muy pocos usuarios, creados a mano en el servidor.

## Decision

1. El login usa el flujo OAuth2 password de FastAPI (`OAuth2PasswordRequestForm`): `username` es el email y `password` la contraseña.
2. Las contraseñas se guardan con pwdlib usando Argon2 (`PasswordHash.recommended()`). Cuando el email no existe, igual se verifica contra un hash ficticio para que el tiempo de respuesta no revele qué emails existen.
3. El access token es un JWT firmado con HS256 mediante PyJWT, con los claims `sub` (id del usuario), `type` (`"access"`), `iat` y `exp`. Dura 15 minutos por defecto.
4. El refresh token es un valor aleatorio opaco (`secrets.token_urlsafe(32)`), no un JWT. En la base solo se guarda su hash SHA-256, con su familia, su vencimiento (30 días por defecto) y su fecha de revocación.
5. Cada uso de un refresh token lo revoca y entrega uno nuevo de la misma familia (rotación).
6. Si llega un refresh token ya revocado, se considera robado: se revoca toda su familia y se responde 401.
7. No hay registro público. Los usuarios se crean con `scripts/create_user.py`.

## Alternatives considered

- API key fija por app: cualquiera que descompile el APK la obtiene, no vence y da acceso a todos los datos.
- Token de dispositivo generado en el servidor y pegado en la app: más simple, pero no vence, deja sin uso la pantalla de login y, si se filtra, sirve hasta que se revoque a mano.
- Refresh token como JWT: no se puede revocar sin guardarlo igual en la base, así que suma complejidad sin aportar nada.
- python-jose y passlib: la documentación actual de FastAPI los reemplazó por PyJWT y pwdlib.

## Consequences

- La tabla `refresh_tokens` crece con cada rotación; hace falta limpiar los tokens vencidos (tarea en el backlog).
- Un access token robado sirve hasta que vence (15 minutos como máximo); no hay lista de revocación para access tokens.
- El cliente debe reemplazar el refresh token guardado cada vez que lo usa. Si reenvía uno viejo, pierde la sesión completa.
- `JWT_SECRET` es crítico: si cambia, todos los access tokens vigentes dejan de ser válidos.
