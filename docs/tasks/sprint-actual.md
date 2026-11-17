# Sprint actual

## En curso

Fase 2 — Lista para usar como plantilla.

## Hechas en este sprint

- [x] [DOCS] Guía para crear una API nueva — `README.md` explica cómo crear un repo con "Use this template", configurar `.env`, levantar compose, crear el primer usuario y agregar un dominio nuevo copiando la forma de `users/`; siguiendo la guía desde cero se llega a un login exitoso — depends on: Logout

- [x] [DB] Migración inicial de `users` y `refresh_tokens` — `alembic upgrade head` crea ambas tablas con las columnas, índices y restricciones de `docs/areas/database.md`; `alembic downgrade base` las borra — depends on: Endpoint de salud
- [x] [AUTH] Dominio y servicio de usuarios — crear un usuario normaliza el email, rechaza contraseñas de menos de 12 caracteres con `PasswordTooShort` y emails repetidos con `EmailAlreadyRegistered` (tests unitarios con repositorio falso) — depends on: Migración inicial
- [x] [AUTH] Script de alta de usuarios — `scripts/create_user.py --email a@b.com` pide la contraseña con `getpass`, crea el usuario y, con un email repetido, termina con código distinto de 0 y sin traza — depends on: Dominio y servicio de usuarios
- [x] [AUTH] Login — `POST /auth/token` con credenciales correctas devuelve 200 con `access_token`, `refresh_token`, `token_type` y `expires_in`; con email inexistente, contraseña incorrecta o usuario inactivo devuelve el mismo 401 — depends on: Script de alta de usuarios
- [x] [AUTH] Usuario actual — `GET /users/me` con un access token válido devuelve el usuario sin `password_hash`; con token vencido, de mala firma, de tipo distinto de `access` o de un usuario inactivo devuelve 401 — depends on: Login
- [x] [AUTH] Refresh con rotación — `POST /auth/refresh` con un token válido devuelve un par nuevo y el token usado ya no sirve; con un token vencido o inexistente devuelve 401 — depends on: Login
- [x] [AUTH] Detección de reúso — reenviar a `/auth/refresh` un token ya rotado devuelve 401 y deja revocados todos los tokens de esa familia, incluido el más nuevo; los de otras familias del mismo usuario siguen funcionando — depends on: Refresh con rotación
- [x] [AUTH] Logout — `POST /auth/logout` devuelve 204 y después ningún token de esa familia sirve para refresh; con un token inexistente también devuelve 204 — depends on: Refresh con rotación

- [x] [INFRA] Proyecto con uv y herramientas de calidad — `uv run ruff check .`, `uv run mypy` y `uv run pytest` terminan en 0 con un test mínimo; `pyproject.toml` tiene la configuración de `python-conventions` y Python 3.13 fijado — depends on: -
- [x] [INFRA] Configuración con pydantic-settings — la API no arranca y muestra qué variable falta si `DATABASE_URL` o `JWT_SECRET` no están, o si `JWT_SECRET` tiene menos de 32 caracteres; `.env.example` lista todas las variables — depends on: Proyecto con uv
- [x] [DB] Conexión async y Alembic — `alembic upgrade head` corre contra el `db` de compose sin errores con el `env.py` async; existe la fábrica de sesiones en `src/app/db.py` — depends on: Configuración
- [x] [INFRA] Docker y compose — `docker compose up` levanta `db` y `api`; `api` espera a que `db` esté healthy y aplica las migraciones antes de arrancar; el contenedor corre como usuario no root — depends on: Conexión async y Alembic
- [x] [API] Endpoint de salud — `GET /health` responde 200 `{"status": "ok"}` con la base arriba y 503 `{"status": "unavailable"}` con la base detenida (test de integración) — depends on: Docker y compose
