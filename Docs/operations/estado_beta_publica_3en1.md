# Estado Maestro — Beta Pública Observatorio 3 en 1

Documento único de estado para el bloque de beta pública. Resume baseline, contratos visibles, riesgos, checklist Oracle y decisión `go / no-go`.

## 1. Baseline vigente

- Repositorio: `Bastian963/cchen-observatorio`
- Rama técnica de referencia: `feat/observatorio-3en1-public-portal`
- Tag congelado para el bloque: `observatorio-3en1-public-beta-ready-2026-03-29`
- Commit de referencia del baseline: `da1673b99cdf3fc7575654c82d78cd2322bca207`
- Rama visible objetivo para GitHub: `main`

Documentos de soporte:

- `Docs/operations/runbook_publicacion_portal_publico_3en1.md`
- `Docs/operations/runbook_publicacion_vm_observatorio_3en1.md`
- `Docs/operations/runbook_backup_restore_observatorio_3en_1.md`
- `Docs/operations/runbook_oracle_piloto_publico_3en1.md`
- `Docs/operations/playbook_operaciones.md`
- `Docs/matriz_visibilidad_publico_interno_3en1.md`

## 2. Contrato público del producto

Superficies objetivo:

- `https://observatorio.cchen.cl` -> dashboard público
- `https://repo.cchen.cl` -> DSpace público
- `https://datos.cchen.cl` -> CKAN público
- `https://obs-int.cchen.cl` -> dashboard interno

Regla operativa:

- `DSpace` conserva documentos y publicaciones
- `CKAN` conserva datasets y recursos descargables
- el `dashboard` explica, enlaza y relaciona, pero no reemplaza a `DSpace` ni a `CKAN`
- `obs-int` es la única superficie que debe exigir `Basic Auth` y luego `internal_auth`

## 3. Estado funcional asumido para este baseline

Este baseline se considera listo para ensayo público cuando se cumple:

- `bash Scripts/check_public_beta_release.sh` en verde
- overlay público con sólo `80/443` publicados
- documentación pública e interna separada
- runner canónico y scheduler de fuentes ya estabilizados en el bloque previo

Revalidaciones obligatorias antes del ensayo Oracle:

- `bash Scripts/check_public_beta_release.sh`
- `bash Scripts/check_observatorio_public_overlay.sh`
- `bash Scripts/check_observatorio_published_ports.sh` una vez desplegado
- `bash Scripts/wait_and_check_observatorio_public_portal.sh` una vez desplegado

## 4. Decisión de infraestructura para Oracle

Para el primer ensayo en Oracle Cloud se adopta esta regla:

- Opción preferida: VM `x86` si todavía existen `trial credits`
- Opción de costo cero estricto: `VM.Standard.A1.Flex`

Justificación:

- el stack usa imágenes externas como `dspace/dspace`
- en este bloque no se ha revalidado formalmente toda la plataforma 3 en 1 sobre `ARM`
- un primer boot `x86` reduce el riesgo de perder tiempo en compatibilidad de imágenes, plugins o binarios auxiliares

Decisión operativa:

- si Oracle ofrece `trial credits`, partir con `x86`
- si la restricción es `Always Free` sí o sí, partir con `A1` y ejecutar validación completa de servicios

## 5. Checklist Oracle piloto

- [ ] Cuenta Oracle activa y región elegida
- [ ] `Compartment` del piloto creado
- [ ] `VCN` pública creada con salida a Internet
- [ ] Reglas de red:
  - `22/tcp` sólo desde la IP del operador
  - `80/tcp` público
  - `443/tcp` público
- [ ] VM `Ubuntu 24.04` creada
- [ ] Docker Engine + Compose plugin instalados
- [ ] Repo clonado en la VM sobre el baseline correcto
- [ ] `.env.public` creado y completado
- [ ] `Dashboard/.streamlit/secrets.public.toml` creado
- [ ] `Dashboard/.streamlit/secrets.toml` creado
- [ ] `.htpasswd` creado para `obs-int`
- [ ] DNS apuntando a la IP pública de la VM
- [ ] Certificados `Let's Encrypt` emitidos para los cuatro FQDN
- [ ] `bash Scripts/sync_observatorio_letsencrypt_certs.sh` ejecutado
- [ ] `bash Scripts/deploy_observatorio_public.sh` ejecutado
- [ ] `bash Scripts/check_observatorio_published_ports.sh` en verde
- [ ] `bash Scripts/wait_and_check_observatorio_public_portal.sh` en verde
- [ ] Restart drill ejecutado
- [ ] Backup drill ejecutado

## 6. Criterio de salida del ensayo

El ensayo queda aprobado sólo si:

- `observatorio.cchen.cl` abre sin `Basic Auth`
- `repo.cchen.cl` responde público
- `datos.cchen.cl` responde público
- `obs-int.cchen.cl` exige `Basic Auth` y luego `internal_auth`
- no quedan enlaces `localhost` en el flujo público
- el asistente público responde sólo con corpus abierto
- backup y restart drill pasan al menos una vez

## 7. Riesgos abiertos

- Riesgo de compatibilidad `ARM` si el piloto parte en `Ampere A1`
- Riesgo de DNS o propagación si los FQDN no apuntan todavía a la VM
- Riesgo de certificados si `Let's Encrypt` se solicita antes de que el DNS esté estable
- Riesgo editorial si el catálogo 3 en 1 contiene activos sin `public_url`

## 8. Registro del ensayo

| Fecha | Proveedor | Shape | Baseline | Resultado | Incidentes | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Pendiente | Oracle Cloud | Pendiente | `observatorio-3en1-public-beta-ready-2026-03-29` | Pendiente | Pendiente | Pendiente |

## 9. Siguiente paso operativo

Ejecutar el piloto siguiendo:

- `Docs/operations/runbook_oracle_piloto_publico_3en1.md`

Preferencia:

- `x86` para el primer boot si hay `trial credits`
- `A1` sólo cuando se quiera validar el camino `Always Free`
