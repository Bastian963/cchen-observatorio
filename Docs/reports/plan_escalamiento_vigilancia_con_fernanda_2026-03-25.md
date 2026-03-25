# Plan de escalamiento — Vigilancia Tecnológica (Fernanda)

## Objetivo

Pasar el módulo de Vigilancia Tecnológica desde operación funcional a operación recurrente con responsables, SLA de actualización y control editorial mínimo.

## Alcance (fase inicial)

- Fuentes: arXiv monitor, news monitor, IAEA INIS monitor, BERTopic.
- Frecuencia inicial: semanal.
- Unidad foco: DGIn + apoyo temático.
- Horizonte de ejecución: 3 semanas (arranque).

## RACI mínimo

| Actividad | Responsable (R) | Aprobador (A) | Consultado (C) | Informado (I) |
| --- | --- | --- | --- | --- |
| Ejecución de actualización de fuentes | Analista Observatorio | Responsable DGIn | Fernanda | Equipo DGIn |
| Revisión editorial de señales relevantes | Fernanda | Responsable DGIn | Analista Observatorio | Equipo DGIn |
| Validación de calidad de dataset | Analista Observatorio | Responsable DGIn | Fernanda | Equipo DGIn |
| Priorización semanal de temas | DGIn | DGIn | Fernanda, Analista | Dirección técnica |
| Registro de bloqueos/incidentes | Analista Observatorio | DGIn | Fernanda | Equipo DGIn |

## SLA operativo sugerido

| Fuente | Frecuencia | SLA publicación | Criterio de calidad mínimo |
| --- | --- | --- | --- |
| arXiv monitor | semanal | <= 24h tras corrida | sin duplicados, fecha válida, topic no vacío |
| news monitor | semanal | <= 24h tras corrida | título, fecha, url válidos |
| IAEA INIS | semanal | <= 48h tras corrida | fuente, fecha, resumen mínimo |
| BERTopic | quincenal | <= 72h tras corrida | tópicos etiquetados y cobertura de documentos |

## Backlog de 3 semanas

### Semana A (arranque)

1. Confirmar responsables operativos (Fernanda + DGIn).
2. Ejecutar corrida base de fuentes y validar completitud mínima.
3. Publicar corte semanal con resumen de señales priorizadas.

### Semana B (estabilización)

1. Medir tiempos reales vs SLA y ajustar secuencia de corridas.
2. Estandarizar criterios editoriales de relevancia (alta/media/baja).
3. Registrar incidentes y causas (fuente caída, latencia, campos faltantes).

### Semana C (consolidación)

1. Cerrar checklist operativo semanal fijo.
2. Emitir informe breve de desempeño (cumplimiento SLA + calidad).
3. Definir mejoras de fase 2 (automatización adicional o nuevas fuentes).

## Checklist semanal de operación

- [ ] Corridas de fuentes ejecutadas en ventana definida.
- [ ] Validación de calidad mínima completada por dataset.
- [ ] Resumen de señales relevantes generado.
- [ ] Bloqueos/incidentes registrados con mitigación.
- [ ] Próxima corrida agendada.

## Riesgos y mitigaciones

- Riesgo: corte sin revisión editorial.
  - Mitigación: bloque de revisión con Fernanda antes de distribución.
- Riesgo: datos incompletos por fuente externa inestable.
  - Mitigación: registrar incidente + fallback al último corte válido.
- Riesgo: sobrecarga operativa en DGIn.
  - Mitigación: priorizar top señales por impacto y ventana de decisión.

## Entregables esperados

1. Corte semanal de vigilancia con señales priorizadas.
2. Registro de cumplimiento SLA por fuente.
3. Bitácora de incidentes y acciones correctivas.

## Estado

- Documento de arranque: listo para revisión con Fernanda.
- Fecha: 2026-03-25.
