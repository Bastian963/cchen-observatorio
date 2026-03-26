# Formulario semanal MVP — versión lista para Google Forms y Microsoft Forms

## Objetivo

Dejar un formulario simple y amigable para completar semana a semana, sin bloquear el envío cuando falte información.

## Regla general de uso

- Mantener el tiempo de llenado en 5 a 8 minutos.
- Permitir completar con información parcial.
- Incluir siempre la opción "Sin información por ahora" en campos clave de priorización o contexto.
- No exigir links ni evidencia para poder enviar.

## Texto de encabezado sugerido (copiar y pegar)

"Este formulario está pensado para completarse semanalmente en pocos minutos. Si algún dato no está disponible, puedes marcar 'Sin información por ahora' y enviar igual."

## Campos obligatorios mínimos

- Semana de reporte
- Unidad
- Responsable que reporta
- Correo de contacto
- Tipo de ingreso
- Título breve
- Descripción breve

---

## Plantilla exacta para Google Forms

### Sección 1 — Identificación

1. Semana de reporte
- Tipo: Fecha (o respuesta corta con formato YYYY-W##)
- Obligatorio: Sí
- Ayuda: "Ejemplo: 2026-W13"

2. Unidad
- Tipo: Lista desplegable
- Obligatorio: Sí
- Opciones:
  - DGIn
  - Vigilancia
  - Transferencia
  - Gobernanza
  - Otra

3. Responsable que reporta
- Tipo: Respuesta corta
- Obligatorio: Sí

4. Correo de contacto
- Tipo: Respuesta corta
- Validación: Texto de correo electrónico
- Obligatorio: Sí

5. Rol o cargo
- Tipo: Respuesta corta
- Obligatorio: No

### Sección 2 — Tipo y descripción

6. Tipo de ingreso
- Tipo: Opción múltiple
- Obligatorio: Sí
- Opciones:
  - Solicitud nueva
  - Seguimiento de solicitud previa
  - Idea de mejora
  - Información para compartir

7. Título breve
- Tipo: Respuesta corta
- Obligatorio: Sí
- Ayuda: "Ejemplo: Indicador semanal de oportunidades priorizadas"

8. Descripción breve
- Tipo: Párrafo
- Obligatorio: Sí
- Ayuda: "Describe la necesidad, idea o información en lenguaje simple"

9. ¿Qué decisión o proceso apoya?
- Tipo: Párrafo
- Obligatorio: No
- Ayuda: "Si no aplica, escribe: No aplica por ahora"

10. Resultado esperado
- Tipo: Párrafo
- Obligatorio: No
- Ayuda: "Ejemplo: reporte, alerta, indicador, mejora de datos"

### Sección 3 — Prioridad y contexto

11. Nivel de urgencia
- Tipo: Opción múltiple
- Obligatorio: Sí
- Opciones:
  - Alta
  - Media
  - Baja
  - Sin información por ahora

12. Impacto esperado
- Tipo: Opción múltiple
- Obligatorio: Sí
- Opciones:
  - Alto
  - Medio
  - Bajo
  - Sin información por ahora

13. Fecha objetivo
- Tipo: Fecha
- Obligatorio: No

14. ¿Hay archivo, evidencia o fuente disponible?
- Tipo: Opción múltiple
- Obligatorio: Sí
- Opciones:
  - Sí
  - Parcial
  - No
  - No tengo información por ahora

### Sección 4 — Links y evidencia

15. Link principal de referencia
- Tipo: Respuesta corta
- Validación: URL
- Obligatorio: No
- Ayuda: "Debe comenzar con http:// o https://"

16. Links adicionales (uno por línea)
- Tipo: Párrafo
- Obligatorio: No
- Ayuda: "Si no hay, escribe: Sin links adicionales"

17. Ruta de archivo o carpeta (Drive, SharePoint u otro)
- Tipo: Respuesta corta
- Obligatorio: No

18. Persona de contacto para ampliar información
- Tipo: Respuesta corta
- Obligatorio: No

19. Ideas o antecedentes adicionales
- Tipo: Párrafo
- Obligatorio: No
- Ayuda: "Si no hay, escribe: Sin antecedentes adicionales"

### Sección 5 — Cierre

20. Estado sugerido
- Tipo: Opción múltiple
- Obligatorio: Sí
- Opciones:
  - Recibida
  - En revisión
  - En backlog
  - En piloto
  - Cerrada
  - Sin definir por ahora

21. Confirmo que esta solicitud puede ser evaluada y priorizada por el Observatorio
- Tipo: Casilla de verificación (una sola)
- Obligatorio: Sí

22. Botón Enviar
- Resultado esperado: mensaje de confirmación y, si la plataforma lo permite, número de caso.

Texto sugerido de confirmación:
"Gracias. Tu envío fue recibido por el Observatorio. Si necesitamos más antecedentes, te contactaremos al correo informado."

---

## Plantilla exacta para Microsoft Forms

Usar los mismos textos de preguntas anteriores con estos tipos equivalentes:

- Respuesta corta -> Texto
- Párrafo -> Texto largo
- Opción múltiple -> Elección
- Lista desplegable -> Elección con menú desplegable
- Fecha -> Fecha

### Configuraciones recomendadas en Microsoft Forms

1. Activar "Obligatorio" solo en los campos mínimos definidos.
2. En Correo de contacto, usar restricción de formato correo.
3. En Link principal, usar validación de URL cuando esté disponible.
4. En preguntas largas, incluir texto guía con "Si no aplica, escribe: Sin información por ahora".
5. Activar mensaje de agradecimiento al enviar.

Texto sugerido de agradecimiento:
"Tu información fue enviada correctamente. Esta entrada se revisará en la próxima sesión semanal del Observatorio."

---

## Lógica condicional recomendada (opcional, fase 2)

1. Si en "¿Hay archivo, evidencia o fuente disponible?" responde "Sí" o "Parcial", mostrar bloque de links.
2. Si responde "No" o "No tengo información por ahora", ocultar bloque de links.
3. Si el tipo de ingreso es "Seguimiento de solicitud previa", mostrar campo adicional "ID de caso previo".

Campo adicional para fase 2:

- ID de caso previo
  - Tipo: Respuesta corta
  - Obligatorio: Sí solo cuando el tipo sea "Seguimiento de solicitud previa"

---

## Checklist de implementación rápida

1. Crear formulario con esta estructura.
2. Probar una respuesta con datos completos.
3. Probar una respuesta con "Sin información por ahora".
4. Verificar que ambos casos se puedan enviar sin bloqueo.
5. Validar que el equipo Observatorio pueda revisar semanalmente las entradas.

## Estado

- Documento operativo listo para implementación en Google Forms o Microsoft Forms.
- Diseñado para uso semanal con información completa o parcial.