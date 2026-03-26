# Comparativa y evaluación de herramientas para el Observatorio CCHEN

Se presenta una tabla comparativa de plataformas y herramientas relevantes para el Observatorio CCHEN, considerando objetivo, dificultad de instalación, API, costo y prioridad recomendada.

| Herramienta/Plataforma | Objetivo principal | Dificultad instalación/uso | API disponible | Costo real | Prioridad recomendada | Observaciones |
|------------------------|-------------------|----------------------------|---------------|------------|----------------------|--------------|
| CKAN                   | Portal de datos institucional, catálogo de datasets y metadatos | Media/Alta (requiere servidor propio, configuración) | Sí (Action API) | Open source, requiere servidor y mantención | Alta (para portal público) | Muy usado en portales open data; flexible y extensible |
| OpenAlex               | Fuente bibliométrica abierta (publicaciones, autores, instituciones, temas) | Baja (solo API) | Sí (REST API) | Gratuito | Alta (para análisis bibliométrico) | Ideal para observatorios científicos; datos abiertos |
| ORCID Public API       | Identidad y desambiguación de investigadores | Baja | Sí (REST API) | Gratuito | Alta (para vincular personas) | Permite enriquecer perfiles y vincular outputs |
| OpenRefine             | Limpieza y normalización de datos | Baja/Media (app de escritorio o servidor) | Sí (API local) | Gratuito | Alta (para calidad de datos) | Muy útil para cleaning y reconciliación |
| Zenodo                 | Depósito y preservación de outputs (datasets, software, docs) | Baja (cuenta y API) | Sí (REST API) | Gratuito | Media/Alta (para publicación y archivo) | No es portal institucional, pero excelente para outputs abiertos |
| OSF                    | Colaboración interna de proyectos | Baja (web) | Sí (REST API) | Gratuito (limitado) | Media (para gestión interna) | Útil para equipos pequeños, gestión de proyectos |
| InvenioRDM             | Repositorio institucional escalable | Alta (infraestructura, docker, config) | Sí (API-first) | Open source, requiere servidor y mantención | Baja/Media (para futuro escalamiento) | Potente, pero más complejo de instalar |
| DSpace                 | Repositorio institucional clásico | Alta (infraestructura, config) | Sí (REST, OAI-PMH) | Open source, requiere servidor y mantención | Baja/Media (si se requiere repositorio tradicional) | Muy usado en universidades, integración con ORCID/ROR |
| OpenAIRE Graph         | Enriquecimiento de descubrimiento y métricas | Baja (solo API) | Sí (REST API) | Gratuito | Media (para métricas y conexiones) | Complementa OpenAlex, útil para análisis avanzados |

## Metodología de evaluación y priorización

Para decidir la incorporación de estas herramientas al plan de trabajo del Observatorio, se aplicará una Matriz de Esfuerzo-Impacto:

1. **Identificación de iniciativas:** Cada herramienta o integración se considera una iniciativa.
2. **Evaluación:** Se estima el esfuerzo (instalación, integración, mantención) y el impacto (valor para el Observatorio, alineación estratégica).
3. **Priorización:**
   - Bajo esfuerzo / alto impacto: implementar primero.
   - Alto esfuerzo / alto impacto: planificar y buscar recursos.
   - Bajo esfuerzo / bajo impacto: considerar si hay capacidad.
   - Alto esfuerzo / bajo impacto: descartar o dejar en espera.

Esta matriz se revisará periódicamente y se documentarán las decisiones en el runbook.
