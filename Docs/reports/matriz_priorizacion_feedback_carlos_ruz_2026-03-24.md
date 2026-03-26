# Matriz impacto-esfuerzo (15 min)

## Objetivo

Priorizar el feedback de Carlos Ruz para decidir:

1. Qué 2 iniciativas arrancar ahora.
2. Qué dejar en fase 2.

## Escala usada

- Impacto: 1 (bajo) a 5 (alto)
- Esfuerzo: 1 (bajo) a 5 (alto)
- Prioridad sugerida = Impacto / Esfuerzo

## Matriz resumida

| Iniciativa | Impacto | Esfuerzo | Prioridad (I/E) | Recomendación |
| --- | ---: | ---: | ---: | --- |
| Exportables CSV en Redes y Colaboración | 4 | 2 | 2.00 | Arrancar ahora |
| Operacionalizar Convocatorias y Matching para DGIn (uso + métricas de adopción) | 5 | 3 | 1.67 | Arrancar ahora |
| Escalamiento Vigilancia Tecnológica con Fernanda (RACI + cadencia) | 5 | 4 | 1.25 | Fase 2 temprana |
| Escalamiento Transferencia/Portafolio con Rodrigo | 5 | 4 | 1.25 | Fase 2 temprana |
| Validación metodológica Modelo/Gobernanza (Rodrigo + María Nieves) | 5 | 4 | 1.25 | Fase 2 temprana |
| Ampliación Capital Humano en Panel de Indicadores | 4 | 3 | 1.33 | Fase 2 temprana |
| Robustecer Asistente I+D (criterios de salida operacional) | 4 | 4 | 1.00 | Fase 2 |
| Formación de Capacidades (completar cobertura + KPIs) | 3 | 3 | 1.00 | Fase 2 |
| Sentimiento de citas (piloto) para Producción/Grafo | 4 | 5 | 0.80 | Fase 2 |
| Revisión metodológica H-index/top investigador + estandarización ORCID | 4 | 5 | 0.80 | Fase 2 |

## Decisión sugerida (arranque inmediato)

## 1) Exportables CSV en Redes y Colaboración

- Razón: alto valor de apertura de datos, implementación rápida, visibilidad inmediata.
- Entregable de 1 sprint: descargas CSV por visualización clave + diccionario mínimo de campos.
- Estado: **Implementado (2026-03-24)** en dashboard, con exportables para países, top países, red institucional y red de autores.

## 2) Convocatorias y Matching para DGIn (uso operativo)

- Razón: módulo crítico para negocio (explicitado por Carlos), impacto directo en adopción.
- Entregable de 1 sprint: tablero de uso (consultas, convocatorias revisadas, recomendaciones accionadas).
- Estado: **Implementado (2026-03-24)** en dashboard, con panel operativo DGIn (KPIs + cola de gestión descargable).

## Qué dejar en fase 2

- Escalamiento con Fernanda/Rodrigo y validación metodológica de gobernanza (requieren coordinación inter-áreas).
- Sentimiento de citas e H-index/ORCID (alto valor, pero mayor esfuerzo y dependencia metodológica).

## Agenda sugerida (15 min)

1. Confirmar las 2 iniciativas de arranque.
2. Asignar dueño y fecha objetivo por iniciativa.
3. Definir criterio de éxito medible por iniciativa.
4. Congelar backlog fase 2 para evitar dispersión.

## Registro

- Base: feedback de Carlos Ruz (24-03-2026).
- Documento relacionado: plan de trabajo detallado en `Docs/reports/plan_trabajo_feedback_carlos_ruz_2026-03-24.md`.

## Checklist de cierre (Done) — Exploración Docker

Objetivo: dejar Docker formalmente cerrado como capacidad operativa mínima para producción local/CI.

- [x] `Dashboard/Dockerfile` disponible y funcional para ejecución headless del dashboard.
- [x] Documentación de uso de contenedor y healthcheck en `Dashboard/README.md`.
- [x] CI con job `docker-smoke` en `.github/workflows/dashboard_smoke.yml` (build + run + `/_stcore/health`).
- [x] Resumen visible en Job Summary del workflow de smoke Docker.
- [ ] 1 corrida manual `workflow_dispatch` en Actions validada en verde y registrada en bitácora.

Criterio de cierre formal:

- Se considera **Done** cuando los primeros 4 checks estén vigentes en `main` y exista al menos una corrida manual verde del workflow `Dashboard Smoke Test` con job `docker-smoke` exitoso.
