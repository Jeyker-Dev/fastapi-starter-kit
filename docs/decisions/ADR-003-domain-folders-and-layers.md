# ADR-003: Carpetas por dominio y capas con puertos

- **Date:** 2026-11-16
- **Status:** Accepted

## Context

La plantilla es la base de varias APIs, y cada una suma sus propios dominios (por ejemplo tasas, compras o metas). La estructura tiene que dejar claro dónde va cada cosa, permitir testear las reglas de negocio sin base de datos y pasar `mypy --strict`.

## Decision

1. El código vive en `src/app/` y se organiza en una carpeta por dominio (`users/`, `auth/`, `health/`). No hay carpetas por rol técnico (`models/`, `utils/`, `helpers/`).
2. Dentro de cada dominio, los archivos separan las capas: `domain.py` (dataclasses congeladas y puertos como `typing.Protocol`), `service.py` (casos de uso), `models.py` y `repository.py` (SQLAlchemy), y `schemas.py` y `api.py` (borde HTTP).
3. Los servicios reciben sus colaboradores (repositorios, hasher, emisor de tokens, reloj) por `__init__`. FastAPI los arma con `Depends` en el borde.
4. Un dominio solo usa el servicio de otro, nunca sus modelos ni su repositorio.
5. Los tests unitarios usan implementaciones falsas de los puertos; los de integración usan PostgreSQL real.

## Alternatives considered

- Carpetas por capa (`routers/`, `models/`, `schemas/`, `services/`): es lo más común en los tutoriales, pero cada dominio termina repartido en cuatro carpetas y la estructura no dice de qué trata la app.
- Una arquitectura hexagonal completa, con un paquete por capa y adaptadores separados: demasiada ceremonia para APIs personales de pocos dominios.

## Consequences

- Agregar un dominio es agregar una carpeta con los mismos archivos; se copia la forma de `users/`.
- Los servicios se testean sin base de datos y sin FastAPI.
- Hay que mantener la disciplina de no importar SQLAlchemy ni Pydantic en `domain.py`.
