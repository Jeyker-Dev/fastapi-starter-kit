# Visión

## Qué es

Plantilla (repositorio template de GitHub) para crear el backend de cada app personal: una API en FastAPI con autenticación, base de datos, migraciones, Docker y tests ya resueltos. Cada app nueva parte de una copia de este repositorio y le agrega solo su dominio.

El primer consumidor es la API de Ahorra (finanzas personales); las siguientes apps se crean igual.

## Problema

- Cada app personal tiene su propia API y todas necesitan lo mismo antes de la primera regla de negocio: login, tokens, usuarios, conexión a la base, migraciones, configuración y despliegue con Docker.
- Rehacer la autenticación en cada proyecto es lento y es justo el código donde un error cuesta más.
- Sin una base común, cada API termina con una estructura, unas herramientas y unas convenciones distintas.

## Usuario objetivo

Uso personal: un desarrollador que crea varias apps (móviles con Flutter, o web) y despliega sus APIs con Docker en su propio VPS. Cada app tiene un solo usuario o muy pocos, creados a mano desde el servidor.

## Alcance de la plantilla

- **Autenticación**: login con email y contraseña (flujo OAuth2 password), access token JWT de vida corta, refresh token rotativo con detección de reúso y logout.
- **Usuarios**: alta desde la línea de comandos, sin registro público; endpoint para consultar el usuario actual.
- **Salud**: endpoint que confirma que la API y la base responden.
- **Infraestructura**: PostgreSQL, SQLAlchemy 2.0 async, Alembic, configuración por variables de entorno, `Dockerfile` y `docker-compose.yml`.
- **Calidad**: uv, ruff, mypy estricto y pytest con tests unitarios y de integración.
- **Guía de uso**: cómo crear una API nueva a partir de la plantilla.

## Fuera de alcance

- Registro público, verificación de email y recuperación de contraseña.
- Login social (Google, Apple) y OAuth2 con proveedores externos.
- Roles y permisos: todo usuario autenticado puede todo.
- Multi-tenant.
- Reglas de negocio de cualquier app concreta.
- Un frontend o un template de Flutter (se extrae más adelante desde Ahorra).

## Objetivos

- Crear la API de una app nueva y tener login funcionando en minutos, sin escribir código de autenticación.
- Que toda API creada desde la plantilla pase `ruff`, `mypy --strict` y `pytest` desde el primer commit.
- Que el mismo `docker compose up` sirva en local y en el VPS.

## Visión a largo plazo

- Workflow de CI (GitHub Actions) incluido en la plantilla.
- Límite de intentos de login por IP y por email.
- Si las copias crecen, mover el núcleo de la autenticación a un paquete de Python compartido para corregir un fallo una sola vez.
