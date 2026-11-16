# Documentación de FastAPI Starter Kit

## Mapa

| Archivo | Qué contiene |
|---|---|
| [00-vision.md](00-vision.md) | Qué es la plantilla, para quién, alcance y fuera de alcance |
| [01-architecture.md](01-architecture.md) | Stack, estructura de carpetas, capas, convenciones y rutas |
| [roadmap.md](roadmap.md) | Fases y referencias externas |
| [areas/auth.md](areas/auth.md) | Endpoints, reglas y errores de autenticación y usuarios |
| [areas/database.md](areas/database.md) | Tablas, reglas de migraciones y riesgos |
| [areas/infrastructure.md](areas/infrastructure.md) | Variables de entorno, Docker, salud y comandos de calidad |
| [areas/antigravity-build-prompt.md](areas/antigravity-build-prompt.md) | Prompt para construir la plantilla con Antigravity |
| [decisions/](decisions/) | ADRs, numerados en orden |
| [tasks/sprint-actual.md](tasks/sprint-actual.md) | Tareas en curso y hechas |
| [tasks/backlog.md](tasks/backlog.md) | Tareas candidatas por fase |
| [changelog.md](changelog.md) | Qué se hizo y cuándo |

## Ciclo de trabajo

1. Antes de una tarea: leer `AGENTS.md`, `00-vision.md`, `01-architecture.md` y las áreas que toca. Tomar la tarea de `tasks/sprint-actual.md`; si solo está en el backlog, moverla al sprint.
2. Implementar con test primero cuando haya una regla verificable, y dejar `ruff`, `mypy` y `pytest` en verde.
3. Al terminar: marcar la tarea con `[x]` y el commit, agregar una entrada en `changelog.md`, actualizar el área si cambió una regla y escribir un ADR si se tomó una decisión de arquitectura.
