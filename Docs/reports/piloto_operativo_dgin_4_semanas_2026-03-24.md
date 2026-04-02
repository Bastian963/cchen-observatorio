# Piloto operativo DGIn (4 semanas)

## Objetivo

Instalar uso semanal real del módulo `Convocatorias y Matching CCHEN` para tomar decisiones operativas con trazabilidad.

## Alcance

- Horizonte: 4 semanas consecutivas.
- Sesión fija: 30 minutos semanales.
- Unidad foco: DGIn.
- Entregable por sesión: exportable actualizado + acta semanal.

## Equipo mínimo

- Owner DGIn: conduce priorización y decisiones.
- Analista Observatorio: prepara panel, exportables y registro de KPIs.
- Apoyo temático: valida elegibilidad cuando se requiera.

### Asignación vigente del piloto

- Owner DGIn titular (provisorio piloto): Bastián Ayala Inostroza
- Owner DGIn respaldo (provisorio piloto): Bastián Ayala Inostroza
- Horario fijo semanal: lunes 09:00-09:30 (America/Santiago)
- Canal operativo vigente: correo `b.ayalainostroza@gmail.com`

## Ritual semanal (30 min)

1. Revisar tablero operativo DGIn y priorizar top oportunidades (10 min).
2. Exportar y actualizar cola operativa (10 min).
3. Cerrar decisiones, responsables y fecha de control (10 min).

## KPIs de pilotaje

- `convocatorias_revisadas_semana`
- `activables_gestionadas_semana`
- `acciones_ejecutadas_semana`
- `tiempo_sesion_min`
- `%_activables_con_estado`

## Metas mínimas por semana (mes 1)

- `tiempo_sesion_min` <= 35.
- `%_activables_con_estado` >= 80.
- `acciones_ejecutadas_semana` >= 1.

## Plan por semana

## Semana 1 — Arranque controlado

- Ejecutar sesión con protocolo completo.
- Completar `acta_dgin_semana_01_2026-03-30.md`.
- Registrar baseline en `dgin_piloto_kpi_tracking_2026-03-24.csv`.
- Verificar que el exportable use timestamp `YYYYMMDD_HHMM`.

Salida esperada:

- Baseline operativo levantado.
- Top 3 oportunidades con responsable y fecha.

## Semana 2 — Estabilización

- Comparar KPIs contra baseline.
- Corregir fricciones del flujo (campos confusos, tiempos, responsables).
- Cerrar ajuste corto al protocolo si corresponde.

Salida esperada:

- Flujo semanal sin bloqueos críticos.

## Semana 3 — Consistencia

- Mantener cadencia sin saltos.
- Auditar trazabilidad: decisión, responsable y estado por oportunidad.
- Validar continuidad de acciones definidas semanas previas.

Salida esperada:

- Evidencia de continuidad en decisiones.

## Semana 4 — Cierre y decisión

- Consolidar KPIs de 4 semanas.
- Identificar mejoras de bajo costo para fase 2.
- Emitir recomendación: continuar, ajustar o escalar.
- Completar `Docs/reports/evaluacion_cierre_piloto_dgin_semana_04_template_2026-03-28.md`.

Salida esperada:

- Informe corto de cierre de piloto con decisión operativa.

## Riesgos y mitigaciones

- Riesgo: baja asistencia semanal.
  - Mitigación: owner DGIn titular + suplente fijo.
- Riesgo: demasiadas oportunidades sin priorización.
  - Mitigación: regla top 3 por score y cierre <= 45 días.
- Riesgo: registro incompleto de decisiones.
  - Mitigación: no cerrar sesión sin acta y cola actualizada.

- Riesgo: falta de responsables DGIn nominales (titular/respaldo).
  - Mitigación: mantener asignación provisoria activa y cerrar formalización antes de la decisión de semana 4.

## Artefactos del piloto

- `Docs/reports/protocolo_operativo_semanal_dgin_2026-03-24.md`
- `Docs/reports/acta_semanal_dgin_template_2026-03-24.md`
- `Docs/reports/acta_dgin_semana_01_2026-03-30.md`
- `Docs/reports/dgin_piloto_kpi_tracking_2026-03-24.csv`
- `Docs/reports/pendientes_informacion_dgin_2026-03-24.md`
- `Docs/reports/evaluacion_cierre_piloto_dgin_semana_04_template_2026-03-28.md`

---

Responsable de coordinación: Bastián Ayala
Fecha de emisión: 2026-03-24

## Punto de revisión de planes

- Revisar formalización DGIn en la sesión de semana 4.
- Si no hay cierre nominal, documentar decisión del ciclo como `ajustar` y escalar a jefatura DGIn en acta de seguimiento.
