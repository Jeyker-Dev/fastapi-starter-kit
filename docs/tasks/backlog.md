# Backlog

## Fase 1 — Usuarios y autenticación

- [ ] [DB] Migración inicial de `users` y `refresh_tokens` — `alembic upgrade head` crea ambas tablas con las columnas, índices y restricciones de `docs/areas/database.md`; `alembic downgrade base` las borra — depends on: Endpoint de salud
- [ ] [AUTH] Dominio y servicio de usuarios — crear un usuario normaliza el email, rechaza contraseñas de menos de 12 caracteres con `PasswordTooShort` y emails repetidos con `EmailAlreadyRegistered` (tests unitarios con repositorio falso) — depends on: Migración inicial
- [ ] [AUTH] Script de alta de usuarios — `scripts/create_user.py --email a@b.com` pide la contraseña con `getpass`, crea el usuario y, con un email repetido, termina con código distinto de 0 y sin traza — depends on: Dominio y servicio de usuarios
- [ ] [AUTH] Login — `POST /auth/token` con credenciales correctas devuelve 200 con `access_token`, `refresh_token`, `token_type` y `expires_in`; con email inexistente, contraseña incorrecta o usuario inactivo devuelve el mismo 401 — depends on: Script de alta de usuarios
- [ ] [AUTH] Usuario actual — `GET /users/me` con un access token válido devuelve el usuario sin `password_hash`; con token vencido, de mala firma, de tipo distinto de `access` o de un usuario inactivo devuelve 401 — depends on: Login
- [ ] [AUTH] Refresh con rotación — `POST /auth/refresh` con un token válido devuelve un par nuevo y el token usado ya no sirve; con un token vencido o inexistente devuelve 401 — depends on: Login
- [ ] [AUTH] Detección de reúso — reenviar a `/auth/refresh` un token ya rotado devuelve 401 y deja revocados todos los tokens de esa familia, incluido el más nuevo; los de otras familias del mismo usuario siguen funcionando — depends on: Refresh con rotación
- [ ] [AUTH] Logout — `POST /auth/logout` devuelve 204 y después ningún token de esa familia sirve para refresh; con un token inexistente también devuelve 204 — depends on: Refresh con rotación

## Fase 2 — Lista para usar como plantilla

- [ ] [DOCS] Guía para crear una API nueva — `README.md` explica cómo crear un repo con "Use this template", configurar `.env`, levantar compose, crear el primer usuario y agregar un dominio nuevo copiando la forma de `users/`; siguiendo la guía desde cero se llega a un login exitoso — depends on: Logout
- [ ] [INFRA] Marcar el repositorio como template en GitHub — el botón "Use this template" aparece en el repo — depends on: Guía para crear una API nueva

## Más adelante

- [ ] [INFRA] CI con GitHub Actions — un push ejecuta ruff, mypy y pytest contra un PostgreSQL de servicio y falla si alguno falla — depends on: Guía para crear una API nueva
- [ ] [DB] Limpieza de refresh tokens vencidos — un comando borra los tokens vencidos o revocados hace más de `REFRESH_TOKEN_TTL_DAYS` días y no toca los activos — depends on: Logout
- [ ] [AUTH] Límite de intentos de login — tras N intentos fallidos para un mismo email en una ventana de tiempo, `/auth/token` responde 429 — depends on: Login

## Documentación

- [ ] [DOCS] Corregir la visión de Ahorra — `finance/docs/00-vision.md` deja de decir que el backend es compartido y dice que la API se crea desde esta plantilla — depends on: -
