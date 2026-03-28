# Protocolo Operativo Semanal — DGIn (Convocatorias y Matching)

## 1) Propósito

Estandarizar el uso semanal del módulo **Convocatorias y Matching CCHEN** para que DGIn pase de visualización a gestión operativa de oportunidades.

## 2) Alcance

Aplica al seguimiento semanal de convocatorias en estado:

- Abierto
- Próximo

Y al uso de los exportables operativos:

- `dgin_cola_operativa_convocatorias.csv`
- `dgin_cola_operativa_template.csv`
- `convocatorias_curadas.csv`
- `convocatorias_matching_rules.csv`

Y del soporte documental mínimo de cierre:

- `Docs/reports/acta_semanal_dgin_template_2026-03-24.md`

## 3) Cadencia

- Frecuencia: semanal
- Duración sugerida: 30 minutos
- Día sugerido: lunes (o primer día hábil)
- Ventana sugerida: 09:00–09:30
- Zona horaria operativa: America/Santiago

## 4) Roles mínimos

- Responsable DGIn (owner semanal): lidera revisión, prioriza y asigna acciones.
- Analista Observatorio: prepara datos, verifica consistencia del panel y exportables.
- Apoyo temático (según perfil): valida elegibilidad/requisitos técnicos cuando aplique.

### Asignación operativa vigente del piloto

- Owner DGIn titular (provisorio piloto): Bastián Ayala Inostroza
- Owner DGIn respaldo (provisorio piloto): Bastián Ayala Inostroza
- Canal oficial semanal (provisorio piloto): correo `b.ayalainostroza@gmail.com`
- Regla de reemplazo vigente: si no hay disponibilidad del titular, la sesión se reprograma dentro de 48h hábiles.

## 5) Flujo operativo (checklist 3 pasos)

## Paso 1 — Revisar tablero operativo DGIn (10 min)

- Ingresar a sección: **Convocatorias y Matching CCHEN**.
- Seleccionar **Unidad objetivo** (DGIn o equivalente).
- Revisar KPIs:
- Activables hoy
- Cierre <= 45 días
- Requieren preparación
- Score medio abiertas

**Criterio de salida:** priorización preliminar de oportunidades de la semana.

## Paso 2 — Exportar y actualizar cola de gestión (10 min)

- Exportar `dgin_cola_operativa_convocatorias.csv`.
- Completar/actualizar columnas de gestión:
- `estado_gestion` (Pendiente / En evaluación / Postulación en curso / Cerrada)
- `responsable_dgin`
- `fecha_revision`
- `comentarios`

**Criterio de salida:** cola semanal actualizada y compartida al equipo.

## Paso 3 — Cerrar decisiones y seguimiento (10 min)

- Confirmar top oportunidades accionables de la semana.
- Registrar decisiones mínimas:
- seguir
- preparar
- descartar (con motivo)
- Definir responsables y fecha de próximo control.
- Completar la plantilla `acta_semanal_dgin_template_2026-03-24.md`.

**Criterio de salida:** acta breve semanal con decisiones y dueños.

## 6) KPIs de adopción (baseline semanas 1-2)

- `convocatorias_revisadas_semana`: total revisadas en sesión.
- `activables_gestionadas_semana`: oportunidades “activables hoy” con estado actualizado.
- `acciones_ejecutadas_semana`: recomendaciones accionadas (contacto, preparación, postulación).
- `tiempo_sesion_min`: duración real de la sesión semanal.

Meta inicial sugerida (primer mes):

- >= 80% de activables con `estado_gestion` actualizado.
- >= 1 acción ejecutada por semana en oportunidades top score.

## 7) Criterios de calidad operativa

- No cerrar sesión sin exportable semanal actualizado.
- Toda oportunidad priorizada debe tener responsable DGIn asignado.
- Toda oportunidad descartada debe tener motivo breve en comentarios.

## 8) Riesgos y mitigación

- Riesgo: sobrecarga de oportunidades sin priorización.
- Mitigación: usar filtro de unidad + score + cierre <= 45 días.

- Riesgo: pérdida de continuidad semanal.
- Mitigación: owner DGIn fijo por semana y respaldo definido.

- Riesgo: decisiones sin trazabilidad.
- Mitigación: mantener archivo de cola operativa versionado por fecha.

## 9) Entregable semanal mínimo

- Archivo actualizado: `dgin_cola_operativa_convocatorias_YYYYMMDD_HHMM.csv`
- Acta breve: `Docs/reports/acta_dgin_semana_XX_YYYY-MM-DD.md`
- Resumen breve (3 líneas):
- principales oportunidades
- acciones definidas
- responsables y fecha de control

## 10) Inicio de operación

- Fecha de arranque sugerida: próxima semana hábil.
- Revisión de ajuste del protocolo: al cierre de la semana 2.

## 11) Registro de ejecución del piloto

- Semana 1 ejecutada:
  - Acta: `Docs/reports/acta_dgin_semana_01_2026-03-30.md`
  - Exportable operativo: `Docs/reports/dgin_cola_operativa_convocatorias_20260324_1547.csv`
  - Registro KPI: `Docs/reports/dgin_piloto_kpi_tracking_2026-03-24.csv`
- Semana 2 ejecutada:
  - Acta: `Docs/reports/acta_dgin_semana_02_2026-04-06.md`
  - Exportable operativo: `Docs/reports/dgin_cola_operativa_convocatorias_20260406_0900.csv`
  - Registro KPI: `Docs/reports/dgin_piloto_kpi_tracking_2026-03-24.csv`
  - Comparativo semanas 1-2: `Docs/reports/resumen_comparativo_dgin_semana_01_vs_02_2026-04-06.md`

## 12) Consistencia documental validada

- Semana 1: acta, exportable y tracker consistentes en 18 convocatorias revisadas, 2 activables, 2 acciones, 30 min.
- Semana 2: acta, exportable y tracker consistentes en 18 convocatorias revisadas, 2 activables, 3 acciones, 27 min.
- Gobernanza operativa vigente: owner y respaldo provisorios activos para continuidad del piloto; formalización DGIn nominal sigue pendiente para la decisión de semana 4.

---

**Documento operativo para uso interno CCHEN.**
**Responsable de edición inicial:** Bastián Ayala
**Fecha:** 2026-03-24
