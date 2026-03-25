# Plan de escalamiento — Transferencia y Portafolio (Rodrigo)

## Objetivo

Escalar el módulo Transferencia y Portafolio desde un estado semilla analítico a una operación institucional con taxonomía estable, trazabilidad de activos y ciclo de validación periódica.

## Alcance (fase inicial)

- Horizonte: 4 semanas.
- Foco: portafolio semilla + convenios/acuerdos + outputs asociados.
- Contraparte clave: Rodrigo.

## Resultado esperado

1. Definición de taxonomía mínima de activos tecnológicos.
2. Criterios operativos para clasificación TRL.
3. Flujo mensual de validación y actualización del portafolio.
4. KPIs operativos para seguimiento de madurez y trazabilidad.

## Taxonomía mínima propuesta

Campos base por activo:

- `asset_id`
- `nombre_activo`
- `tipo_activo` (know-how, prototipo, servicio, software, proceso)
- `unidad_responsable`
- `estado_madurez`
- `trl_actual`
- `evidencia_trl`
- `potencial_transferencia`
- `socios_relacionados`
- `fecha_ultima_revision`
- `responsable_revision`

## Flujo operativo mensual

1. Consolidación de cambios (Analista Observatorio).
2. Revisión técnica de activos y TRL (Rodrigo + unidad dueña).
3. Validación de trazabilidad y consistencia (DGIn + Observatorio).
4. Publicación de corte mensual del portafolio.

## RACI mínimo

| Actividad | R | A | C | I |
| --- | --- | --- | --- | --- |
| Consolidar datos del portafolio | Analista Observatorio | DGIn | Rodrigo | Equipo DGIn |
| Validar TRL y estado de madurez | Rodrigo | DGIn | Unidad técnica | Observatorio |
| Definir prioridades de transferencia | DGIn | DGIn | Rodrigo | Dirección técnica |
| Publicar corte mensual | Analista Observatorio | DGIn | Rodrigo | Equipo DGIn |

## KPIs propuestos

- `n_activos_portafolio`
- `n_activos_con_trl_definido`
- `pct_activos_con_evidencia_trl`
- `n_activos_actualizados_mes`
- `n_activos_priorizados_transferencia`

## Backlog 4 semanas

### Semana 1

- Acordar taxonomía mínima con Rodrigo.
- Identificar campos faltantes críticos.

### Semana 2

- Aplicar normalización inicial sobre portafolio semilla.
- Definir criterios TRL operativos (guía breve).

### Semana 3

- Ejecutar primera validación conjunta de activos prioritarios.
- Registrar decisiones y cambios de clasificación.

### Semana 4

- Publicar primer corte consolidado.
- Emitir recomendaciones de fase 2 (automatización + calidad).

## Riesgos y mitigación

- Riesgo: TRL inconsistente entre unidades.
  - Mitigación: guía única de interpretación y validación conjunta.
- Riesgo: datos incompletos en activos clave.
  - Mitigación: regla de obligatoriedad de campos mínimos antes de publicación.
- Riesgo: baja adopción operativa del módulo.
  - Mitigación: reporte corto mensual con KPIs y decisiones accionables.

## Estado

- Documento de arranque listo para sesión de trabajo con Rodrigo.
- Fecha: 2026-03-25.
