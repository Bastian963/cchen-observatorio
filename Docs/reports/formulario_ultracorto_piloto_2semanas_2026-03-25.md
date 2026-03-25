# Formulario ultra corto (10 preguntas) + operación interna

## Objetivo

Implementar un piloto de 2 semanas con un formulario muy liviano que permita registrar necesidades, ideas o información útil sin fricción, y dejar trazabilidad interna completa con ID de caso y estado.

## Alcance del piloto

- Duración: 2 semanas.
- Frecuencia de uso: semanal.
- Tiempo de respuesta esperado por usuario: 3 a 5 minutos.
- Regla: permitir envío con información parcial.

## Texto de encabezado sugerido (copiar y pegar)

"Este formulario está pensado para completarse rápidamente semana a semana. Si no cuentas con toda la información, selecciona 'Sin información por ahora' y envía igual."

---

## Formulario ultra corto (máximo 10 preguntas)

- **Pregunta 1: Semana de reporte**

  - Tipo: fecha o texto corto (YYYY-W##)
  - Obligatorio: sí

- **Pregunta 2: Unidad**

  - Tipo: lista
  - Obligatorio: sí
  - Opciones sugeridas: DGIn, Vigilancia, Transferencia, Gobernanza, Otra

- **Pregunta 3: Nombre y correo de quien reporta**

  - Tipo: texto corto
  - Obligatorio: sí
  - Formato sugerido: "Nombre Apellido - correo institucional"

- **Pregunta 4: Tipo de ingreso**

  - Tipo: lista
  - Obligatorio: sí
  - Opciones: Solicitud nueva, Seguimiento, Idea de mejora, Información para compartir

- **Pregunta 5: Título breve**

  - Tipo: texto corto
  - Obligatorio: sí

- **Pregunta 6: Descripción breve**

  - Tipo: texto largo
  - Obligatorio: sí

- **Pregunta 7: Urgencia**

  - Tipo: lista
  - Obligatorio: sí
  - Opciones: Alta, Media, Baja, Sin información por ahora

- **Pregunta 8: Impacto esperado**

  - Tipo: lista
  - Obligatorio: sí
  - Opciones: Alto, Medio, Bajo, Sin información por ahora

- **Pregunta 9: Link o evidencia (opcional)**

  - Tipo: texto corto o URL
  - Obligatorio: no
  - Ayuda: "Puede ser link, ruta de archivo o texto 'Sin link por ahora'"

- **Pregunta 10: Ideas o antecedentes adicionales**

  - Tipo: texto largo
  - Obligatorio: no
  - Ayuda: "Si no hay, escribir: Sin antecedentes adicionales"

## Reglas de diseño para no bloquear el envío

- No exigir links ni adjuntos como condición de envío.
- Mantener solo 8 campos realmente obligatorios (1 a 8).
- Permitir valores "Sin información por ahora" en urgencia e impacto.

---

## Esquema de ID de caso

## Formato recomendado

`OBS-YYYY-NNNN`

Ejemplos:

- OBS-2026-0001
- OBS-2026-0002

## Regla de generación

1. Prefijo fijo: `OBS`.
2. Año de ingreso: `YYYY`.
3. Correlativo de 4 dígitos, incremental y único por año.
4. El ID se asigna automáticamente al recibir el formulario.

## Momento de asignación

- Al enviar el formulario se crea inmediatamente el ID.
- En el mensaje de confirmación se muestra: "Tu caso fue registrado con ID OBS-2026-00XX".

---

## Tabla de seguimiento interno (operación Observatorio)

## Nombre sugerido

`seguimiento_formulario_observatorio`

## Campos mínimos

1. `case_id` (texto, único)
2. `fecha_ingreso` (fecha-hora)
3. `semana_reporte` (texto)
4. `unidad` (texto)
5. `solicitante_nombre` (texto)
6. `solicitante_correo` (texto)
7. `tipo_ingreso` (texto)
8. `titulo` (texto)
9. `descripcion` (texto largo)
10. `urgencia` (texto)
11. `impacto` (texto)
12. `link_evidencia` (texto)
13. `antecedentes` (texto largo)
14. `estado` (texto)
15. `responsable_observatorio` (texto)
16. `fecha_revision` (fecha)
17. `decision` (texto)
18. `comentarios_internos` (texto largo)
19. `fecha_cierre` (fecha)

## Catálogo de estados recomendado

- Recibida
- En revisión
- Priorizada
- En backlog
- En piloto
- Implementada
- Cerrada
- Fuera de alcance

## Flujo operativo semanal (simple)

1. Recepción: se registra caso con `estado = Recibida`.
2. Triage semanal: se cambia a `En revisión` y se asigna responsable.
3. Decisión: `Priorizada`, `En backlog`, `En piloto` o `Fuera de alcance`.
4. Ejecución: cuando aplica, pasar a `Implementada`.
5. Cierre: registrar resultado y `fecha_cierre`.

## SLA sugerido para piloto de 2 semanas

- Confirmación de recepción: inmediata (automática).
- Primera revisión interna: dentro de 5 días hábiles.
- Decisión inicial de estado: dentro de 7 días hábiles.

---

## Checklist de puesta en marcha

1. Publicar formulario con 10 preguntas.
2. Definir responsable de triage semanal.
3. Activar generación de `case_id` en registro interno.
4. Probar 2 casos: uno completo y otro con "Sin información por ahora".
5. Validar que ambos recorran el flujo sin bloqueo.

## Estado

- Documento listo para piloto de 2 semanas.
- Diseño mínimo viable, amigable y operativo.
