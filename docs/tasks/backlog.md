# Backlog

## Fase 2 — Lista para usar como plantilla

- [ ] [DOCS] Guía para crear una API nueva — `README.md` explica cómo crear un repo con "Use this template", configurar `.env`, levantar compose, crear el primer usuario y agregar un dominio nuevo copiando la forma de `users/`; siguiendo la guía desde cero se llega a un login exitoso — depends on: Logout
- [ ] [INFRA] Marcar el repositorio como template en GitHub — el botón "Use this template" aparece en el repo — depends on: Guía para crear una API nueva

## Más adelante

- [ ] [INFRA] CI con GitHub Actions — un push ejecuta ruff, mypy y pytest contra un PostgreSQL de servicio y falla si alguno falla — depends on: Guía para crear una API nueva
- [ ] [DB] Limpieza de refresh tokens vencidos — un comando borra los tokens vencidos o revocados hace más de `REFRESH_TOKEN_TTL_DAYS` días y no toca los activos — depends on: Logout
- [ ] [AUTH] Límite de intentos de login — tras N intentos fallidos para un mismo email en una ventana de tiempo, `/auth/token` responde 429 — depends on: Login

## Documentación

- [ ] [DOCS] Corregir la visión de Ahorra — `finance/docs/00-vision.md` deja de decir que el backend es compartido y dice que la API se crea desde esta plantilla — depends on: -
