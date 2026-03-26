# Repositorios de datos y publicaciones explorados y automatizados

Actualmente se han implementado scripts robustos y documentados para la descarga y actualización periódica de outputs institucionales desde los siguientes repositorios:

| Repositorio      | Tipo de datos         | Estrategia de búsqueda/descarga | Frecuencia recomendada | Script asociado                                 |
|------------------|----------------------|----------------------------------|-----------------------|-----------------------------------------------|
| Zenodo           | Publicaciones, datos | Comunidad + afiliación           | Mensual               | Scripts/download_zenodo_cchen_combined.py      |
| Europe PMC       | Publicaciones        | Afiliación (variante)            | Mensual               | Scripts/download_europepmc_cchen.py            |
| OpenAIRE         | Publicaciones, datos, software, proyectos | Organización + país (variante) | Mensual | Scripts/download_openaire_cchen_full.py         |

Todos los scripts están preparados para ejecutarse de forma periódica (ej. cron, GitHub Actions, scheduler local) para mantener el observatorio actualizado.

## Siguiente paso sugerido

- Integrar la ejecución automática de estos scripts (por ejemplo, con un workflow de GitHub Actions o un cron local en un servidor institucional).
- Registrar logs y resultados de cada corrida para trazabilidad.
- Documentar el flujo de actualización y monitoreo en el runbook del observatorio.

---

**Nota:** Si se identifican nuevos repositorios relevantes (ej. ORCID, PatentsView, CKAN, Figshare, Dryad, OSF), se recomienda agregar scripts y documentar su integración en esta matriz.
# Plan de trabajo preliminar para el Observatorio CCHEN (basado en análisis comparativo de herramientas)

## 1. Objetivo general
Desarrollar un Observatorio institucional robusto, interoperable y sostenible, priorizando herramientas abiertas, APIs y flujos automatizables para la gestión, análisis y publicación de datos científicos y tecnológicos de CCHEN.

## 2. Principios de priorización
- **Alto impacto institucional y bajo esfuerzo de adopción**: Se priorizan herramientas que aporten valor estratégico y sean rápidas de implementar.
- **Interoperabilidad y apertura**: Preferencia por soluciones con APIs abiertas y estándares reconocidos.
- **Escalabilidad y sostenibilidad**: Se consideran herramientas que permitan crecer y adaptarse a futuro.
- **Calidad y trazabilidad de datos**: Se incorporan procesos y herramientas para limpieza, normalización y control de calidad.

## 3. Fases y acciones recomendadas

### Fase 1: Implementación inicial (alto impacto, bajo esfuerzo)
- **OpenAlex**: Integrar como fuente bibliométrica principal para publicaciones, autores, instituciones y temas.
- **ORCID Public API**: Usar para vincular y desambiguar investigadores.
- **OpenRefine**: Adoptar para limpieza y normalización de datos antes de su publicación o análisis.
- **Zenodo**: Utilizar para depósito y preservación de datasets, software y documentos institucionales.

### Fase 2: Portal de datos y colaboración
- **CKAN**: Montar un portal de datos institucional para catálogo, búsqueda y descarga de datasets y metadatos.
- **OSF**: Usar como plataforma de colaboración interna para proyectos y gestión de archivos.

### Fase 3: Escalamiento y repositorio institucional
- **InvenioRDM** o **DSpace**: Evaluar su adopción si el Observatorio requiere un repositorio institucional propio, interoperable y escalable.
- **OpenAIRE Graph**: Integrar para enriquecer análisis y métricas, especialmente si se requiere mayor conectividad internacional.

## 4. Metodología de revisión y ajuste
- Aplicar periódicamente la Matriz de Esfuerzo-Impacto para priorizar nuevas integraciones, mejoras o cambios.
- Documentar decisiones y resultados en el runbook y en la tabla comparativa.
- Revisar el stack tecnológico al menos una vez al año o ante cambios estratégicos.

## 5. Observaciones
- El plan es flexible y se ajustará según recursos, necesidades institucionales y resultados de las primeras fases.
- Se recomienda mantener la documentación y la trazabilidad de todas las decisiones técnicas y operativas.

---

_Este plan se fundamenta en el análisis comparativo de herramientas y plataformas abiertas, priorizando la adopción progresiva y la toma de decisiones basada en evidencia y criterios objetivos._
