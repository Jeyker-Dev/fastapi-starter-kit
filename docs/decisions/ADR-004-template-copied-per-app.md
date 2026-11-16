# ADR-004: Plantilla que se copia por app en lugar de una API compartida

- **Date:** 2026-11-16
- **Status:** Accepted

## Context

Hay varias apps personales en camino, cada una con su propio dominio. La alternativa a una API por app es una sola API compartida, con una única autenticación para todas.

## Decision

1. Cada app tiene su propia API y su propia base de datos.
2. Cada API nueva se crea copiando este repositorio con "Use this template" de GitHub, al estilo de los starter kits de Laravel.
3. La plantilla solo contiene lo común (autenticación, usuarios, salud, infraestructura y herramientas), nunca reglas de negocio de una app concreta.

## Alternatives considered

- Una API compartida por todas las apps: la autenticación se escribe una sola vez, pero acopla los despliegues, los esquemas y los ciclos de cambio de apps que no tienen nada que ver entre sí.
- Un paquete de Python con la autenticación, instalado en cada API: evita duplicar la corrección de un fallo, pero obliga a versionar y publicar un paquete antes de tener una sola app funcionando. Queda para más adelante.

## Consequences

- Cada copia evoluciona por su cuenta: un fallo de seguridad en la autenticación se corrige en la plantilla y después en cada API creada a partir de ella.
- Cada app se despliega, migra y versiona de forma independiente.
- Si las copias se vuelven difíciles de mantener, el núcleo de la autenticación pasa a un paquete compartido y este ADR se reemplaza.
