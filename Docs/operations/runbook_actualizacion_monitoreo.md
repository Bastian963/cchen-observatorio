# Flujo de actualización y monitoreo de datos institucionales

## 1. Automatización y ejecución periódica

- El workflow `.github/workflows/actualizacion_datos.yml` ejecuta semanalmente los scripts principales de descarga y actualización de outputs institucionales (Zenodo, Europe PMC, OpenAIRE, etc.).
- Cada corrida queda registrada en la pestaña **Actions** del repositorio GitHub, con logs completos y estado (éxito/fallo).
- Si hay cambios en los datos, el workflow hace commit y push automático, dejando trazabilidad en el historial de Git.

## 2. Registro de logs y resultados

- Los logs de cada ejecución incluyen:
  - Fecha y hora de inicio/fin
  - Scripts ejecutados y su salida
  - Errores o warnings detectados
  - Resumen de archivos modificados o nuevos
- El historial de commits permite auditar qué datos cambiaron, cuándo y por qué script.
- Se recomienda revisar periódicamente la pestaña **Actions** y el historial de commits para detectar anomalías o tendencias.

## 3. Monitoreo y alertas

- Por ahora, la notificación por email ante fallos está pendiente de implementar.
- Si una corrida falla, el estado queda en rojo en **Actions** y puede revisarse el log detallado.
- Se recomienda agregar notificaciones automáticas (email, Slack, etc.) en el futuro para incidentes críticos.

## 4. Buenas prácticas

- Mantener los scripts y el workflow actualizados según evolucionen los datos y necesidades institucionales.
- Documentar cualquier cambio relevante en este runbook y en el README.
- Si se agregan nuevos scripts o fuentes, incluirlos en el workflow y en esta documentación.

## 5. Ejemplo de trazabilidad

- **Actions**: https://github.com/Bastian963/cchen-observatorio/actions
- **Historial de commits**: https://github.com/Bastian963/cchen-observatorio/commits/main
- **Archivos de datos**: Data/ (versionados y auditables)

---

**Última actualización:** 2026-03-25
