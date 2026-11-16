# Roadmap

## Principios

- Primero lo que toda API necesita para arrancar; nada de reglas de negocio de una app concreta.
- Cada fase termina con `ruff`, `mypy --strict` y `pytest` en verde, y con `docker compose up` funcionando.
- La plantilla se valida creando la API de Ahorra a partir de ella; lo que falte se corrige primero en la plantilla.

## Fase 0 — Base del proyecto

Proyecto con uv, herramientas de calidad, configuración, conexión a PostgreSQL, Alembic, Docker y el endpoint `/health`.

## Fase 1 — Usuarios y autenticación

Usuarios con alta por línea de comandos, login, refresh token rotativo con detección de reúso, logout y `GET /users/me`.

## Fase 2 — Lista para usar como plantilla

Guía para crear una API nueva desde la plantilla, `README.md` y la marca de template en GitHub.

## Más adelante

- CI con GitHub Actions (ruff, mypy, pytest contra PostgreSQL).
- Límite de intentos de login.
- Paquete compartido para el núcleo de la autenticación, si las copias se vuelven difíciles de mantener.

## Referencias externas

- FastAPI, seguridad con OAuth2 y JWT: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- SQLAlchemy 2.0, extensión asyncio: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Alembic, plantilla async: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- OAuth 2.0 Security Best Current Practice (rotación de refresh tokens): https://datatracker.ietf.org/doc/html/rfc9700
