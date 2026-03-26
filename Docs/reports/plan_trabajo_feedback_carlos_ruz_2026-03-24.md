# Plan de trabajo — Feedback Carlos Ruz (2026-03-24)

## 1) Contexto

Documento de planificación derivado de la revisión integral de la beta del Observatorio CCHEN y su documentación, realizada por **Carlos Ruz**.

**Fuente:** correo de retroalimentación formal enviado a Bastián Ayala.

## 2) Síntesis ejecutiva del feedback

- La beta fue evaluada de forma completa y la percepción general es positiva.
- Se reconocen módulos con alto nivel de madurez: Panel de indicadores, Financiamiento I+D, Convocatorias y matching.
- Se identifican líneas de mejora estratégicas en: Producción científica, Redes/colaboración, Vigilancia tecnológica, Transferencia/portafolio, Modelo/gobernanza.
- Se confirma estado en construcción para: Formación de capacidades, Asistente I+D y parte de Capital humano.
- Se solicita definir estrategia de escalamiento coordinada con contrapartes funcionales (Fernanda, Rodrigo, María Nieves).
- Se incorpora feedback ejecutivo de **Felipe Antonio Guevara Pezoa**: el Observatorio se considera un **quick win** para CCHEN y se solicita ruta clara para entrada a producción y criterios para una eventual evolución fuera de Streamlit.

## 3) Plan de trabajo por módulo

## a) Panel de indicadores

- Estado actual: Bueno.
- Gap principal: Profundizar dimensión de capital humano con nueva data compartida.
- Acciones:
- Integrar nuevas fuentes de capital humano al pipeline estándar.
- Agregar KPIs de completitud y actualización por fuente.
- Entregable: versión de panel con bloque de capital humano ampliado y trazable.
- Prioridad: Alta.

## b) Producción científica

- Estado actual: Avanzado, con oportunidades analíticas.
- Gap principal: análisis de sentimiento de citas, revisión de H-index/top investigador, estandarización de perfiles ORCID.
- Acciones:
- Diseñar piloto de análisis de sentimiento sobre citas (alcance, modelo, validación humana).
- Revisar definición metodológica de H-index y ranking para evitar sesgos.
- Normalizar perfiles ORCID (deduplicación, esquema canónico, reglas de matching).
- Entregable: propuesta metodológica + versión inicial de métricas ajustadas.
- Prioridad: Alta.

## c) Redes y colaboración

- Estado actual: Visualmente sólido.
- Gap principal: disponibilidad de datos en CSV para apertura progresiva.
- Acciones:
- Publicar exportables CSV por visualización clave.
- Incluir diccionario de campos mínimo por dataset exportado.
- Entregable: botón de descarga CSV + carpeta de salidas versionadas.
- Prioridad: Media-Alta.

## d) Vigilancia tecnológica

- Estado actual: Funcional.
- Gap principal: escalamiento operativo con Fernanda.
- Acciones:
- Definir esquema de operación conjunta (roles, frecuencia, calidad, revisión editorial).
- Formalizar backlog de fuentes/temas priorizados y SLA de actualización.
- Entregable: plan de escalamiento del módulo con Fernanda (RACI + cronograma).
- Prioridad: Alta.

## e) Financiamiento I+D

- Estado actual: Excelente detalle y precisión.
- Gap principal: consolidar continuidad y monitoreo.
- Acciones:
- Mantener control de calidad y refresco periódico.
- Establecer alertas ante quiebres de actualización.
- Entregable: checklist de operación recurrente.
- Prioridad: Media.

## f) Convocatorias y matching CCHEN

- Estado actual: Estratégico y esencial para DGIn.
- Gap principal: institucionalizar su uso.
- Acciones:
- Definir flujo de uso con usuarios DGIn (descubrimiento, priorización, seguimiento).
- Incorporar métricas de adopción y efectividad del matching.
- Entregable: tablero de uso del módulo para DGIn.
- Prioridad: Alta.

## g) Transferencia y portafolio

- Estado actual: útil, con necesidad de escalamiento.
- Gap principal: estrategia conjunta con Rodrigo.
- Acciones:
- Definir ruta de escalamiento con Rodrigo (casos, taxonomía, gobernanza de activos).
- Priorizar indicadores de madurez tecnológica (TRL) y trazabilidad de portafolio.
- Entregable: plan de escalamiento del módulo con Rodrigo.
- Prioridad: Alta.

## h) Modelo y gobernanza

- Estado actual: alineado a trabajo previo de Rodrigo y María Nieves.
- Gap principal: validación metodológica formal.
- Acciones:
- Ejecutar mesa de validación metodológica con contrapartes.
- Cerrar criterios de calidad, consistencia e interoperabilidad del modelo.
- Entregable: acta de validación metodológica + ajustes acordados.
- Prioridad: Alta.

## i) Formación de capacidades

- Estado actual: En construcción.
- Gap principal: completar cobertura y calidad de datos.
- Acciones:
- Completar datasets faltantes y normalización de campos críticos.
- Definir KPIs mínimos del módulo para salida beta estable.
- Entregable: versión funcional con indicadores base y notas metodológicas.
- Prioridad: Media.

## j) Asistente I+D

- Estado actual: En construcción.
- Gap principal: robustez de producto para uso operativo.
- Acciones:
- Fortalecer evaluación de respuestas (grounding, accionabilidad, trazabilidad).
- Definir batería de pruebas funcionales y de calidad en escenarios reales.
- Entregable: criterio de salida a beta operacional del asistente.
- Prioridad: Media-Alta.

## k) Grafo de citas

- Estado actual: En evolución.
- Gap principal: incorporar componente de análisis de sentimientos en citas (alineado a b).
- Acciones:
- Integrar resultados del piloto de sentimiento de citas al grafo.
- Definir visualización de polaridad/tono por clúster o relación de citación.
- Entregable: grafo enriquecido con capa de sentimiento (fase piloto).
- Prioridad: Media-Alta.

## 4) Coordinaciones clave

- Fernanda: escalamiento de Vigilancia tecnológica.
- Rodrigo: escalamiento de Transferencia y Portafolio.
- Rodrigo + María Nieves: validación metodológica de Modelo y Gobernanza.
- DGIn: adopción operativa de Convocatorias y matching.

## 5) Priorización transversal sugerida (próximas 4-6 semanas)

- Prioridad 1 (crítica): d, f, g, h.
- Prioridad 2 (alto valor analítico): b, c, k.
- Prioridad 3 (maduración de producto): a, i, j.
- Prioridad 4 (continuidad operacional): e.

## 6) Entrada a producción (quick win CCHEN)

### Objetivo

Habilitar salida a producción en corto plazo sin bloquear valor por rediseño de UX/arquitectura, manteniendo una ruta de evolución posterior.

### Decisión recomendada

- **Fase 1 (salida rápida):** producción con Streamlit, bajo estándares institucionales de seguridad y operación.
- **Fase 2 (evolución):** desacoplar backend + frontend dedicado cuando existan evidencia de adopción y requerimientos de escalamiento UX.

### Fase 1 — checklist mínimo de producción (1-2 semanas)

- Infraestructura estable con dominio institucional y HTTPS.
- Control de acceso (idealmente SSO/Entra ID o, en su defecto, acceso restringido por rol).
- Gestión de secretos y credenciales fuera de código.
- Automatización de actualización de datos (jobs programados y monitoreados).
- Monitoreo básico: disponibilidad, latencia y errores.
- Respaldos y procedimiento de recuperación.
- Runbook operativo corto (incidentes, reinicio, contacto responsable).

### Fase 2 — evolución fuera de Streamlit (mediano plazo)

- Separar capa de datos/servicios en API.
- Mantener continuidad de métricas y trazabilidad ya validadas.
- Rediseñar frontend para UX avanzada y permisos más granulares.
- Definir hito de migración en función de uso real y demanda institucional.

### Criterios de éxito de la salida rápida

- Entorno productivo activo con acceso controlado.
- Cadencia semanal de operación DGIn ejecutada con acta y exportables.
- Sin incidentes críticos en las primeras 2 semanas.
- Evidencia de uso real por equipos objetivo.

### Pendiente de información para revisión

- La formalización de responsables DGIn titular y respaldo queda registrada en:
  - `Docs/reports/pendientes_informacion_dgin_2026-03-24.md`
- Este pendiente debe revisarse en comité de seguimiento para cerrar continuidad operativa.

## 7) Registro de origen

- Este plan se construye sobre feedback explícito de **Carlos Ruz**.
- Se amplía con feedback ejecutivo de **Felipe Antonio Guevara Pezoa** (quick win + consulta de paso a producción).
- Fecha de registro del plan: 2026-03-24.
- Responsable de documentación: Bastián Ayala.
