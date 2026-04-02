# Runbook de Publicación Pública — Observatorio 3 en 1

Guía para publicar el portal abierto del observatorio con dos superficies diferenciadas:

- `https://observatorio.cchen.cl` → dashboard público
- `https://repo.cchen.cl` → DSpace público
- `https://datos.cchen.cl` → CKAN público
- `https://obs-int.cchen.cl` → dashboard interno completo

## 1. Baseline técnico

El despliegue público usa:

- `docker-compose.observatorio.yml`
- `docker-compose.observatorio.public.yml`
- `.env.public.example`
- `deploy/nginx/templates/observatorio-public-portal.conf.template`

La rama fuente de verdad para este bloque es:

- `feat/observatorio-3en1-public-portal`

Y el baseline técnico congelado es:

- `observatorio-3en1-public-beta-ready-2026-03-29`

Antes de tocar una VM pública, el repo debe quedar en verde con:

```bash
bash Scripts/check_public_beta_release.sh
```

Estado maestro y siguiente paso:

- `Docs/operations/estado_beta_publica_3en1.md`
- `Docs/operations/runbook_oracle_piloto_publico_3en1.md`

## 2. Supuestos de infraestructura

- VM pública con Docker Compose
- TLS institucional para cuatro hosts:
  - `observatorio.cchen.cl`
  - `obs-int.cchen.cl`
  - `repo.cchen.cl`
  - `datos.cchen.cl`
- `Basic Auth` sólo para `obs-int.cchen.cl`
- DSpace y CKAN accesibles públicamente

Decisión sugerida para el primer piloto:

- usar `x86` si Oracle todavía ofrece `trial credits`
- usar `VM.Standard.A1.Flex` sólo si el piloto debe ser `Always Free` desde el día 1

## 3. Archivos no versionados en la VM

- `.env.public`
- `Dashboard/.streamlit/secrets.public.toml`
- `Dashboard/.streamlit/secrets.toml`
- `/srv/observatorio/nginx/.htpasswd`
- certificados TLS en `/srv/observatorio/tls`

Si se usan certificados `Let's Encrypt`, sincronizarlos al layout esperado con:

```bash
OBSERVATORIO_ENV_FILE=.env.public \
bash Scripts/sync_observatorio_letsencrypt_certs.sh
```

## 4. Preparación

```bash
OBSERVATORIO_ENV_FILE=.env.public \
OBSERVATORIO_BASIC_AUTH_PASSWORD='CAMBIAR-CLAVE' \
bash Scripts/bootstrap_observatorio_vm.sh

cp .env.public.example .env.public
```

Completar:

- `OBSERVATORIO_PUBLIC_DASHBOARD_HOST`
- `OBSERVATORIO_INTERNAL_DASHBOARD_HOST`
- `OBSERVATORIO_DSPACE_HOST`
- `OBSERVATORIO_CKAN_HOST`
- `OBSERVATORIO_PUBLIC_SECRETS_FILE`
- `OBSERVATORIO_INTERNAL_SECRETS_FILE`
- rutas TLS y logs

Crear y mantener separados:

- `Dashboard/.streamlit/secrets.public.toml` para el dashboard público, sin `service_role_key`
- `Dashboard/.streamlit/secrets.toml` para la superficie interna, con `internal_auth` y credenciales ampliadas si aplican

## 5. Despliegue

```bash
bash Scripts/deploy_observatorio_public.sh
```

## 6. Validación

```bash
export OBSERVATORIO_INTERNAL_BASIC_AUTH_CREDENTIALS='observatorio:CAMBIAR-CLAVE'
bash Scripts/check_observatorio_published_ports.sh
bash Scripts/wait_and_check_observatorio_public_portal.sh
```

Debe responder:

- `https://observatorio.cchen.cl/_stcore/health`
- `https://repo.cchen.cl`
- `https://repo.cchen.cl/server/api`
- `https://datos.cchen.cl`
- `https://datos.cchen.cl/api/3/action/status_show`
- `https://obs-int.cchen.cl/_stcore/health` con Basic Auth

## 7. Reglas de producto

- El portal público sólo debe exponer secciones marcadas como públicas o mixtas.
- El dashboard interno mantiene `internal_auth`.
- El asistente público responde sólo con corpus abierto y activos con `public_url`.
- El asistente interno mantiene el contexto extendido del observatorio.

## 8. Checklist editorial previa al lanzamiento

1. Verificar que los activos publicados no enlacen a `localhost`.
2. Confirmar que cada activo del portal tenga `public_url` y `vinculo_cruzado`.
3. Revisar que no aparezcan secciones internas en `observatorio.cchen.cl`.
4. Confirmar al menos un documento DSpace y un dataset CKAN accesibles desde la portada.

## 9. Promoción

Promover desde staging a producción pública sólo cuando:

- staging público esté en verde,
- backup y restore estén probados,
- el catálogo 3 en 1 tenga URLs públicas correctas,
- DGIn y el equipo editorial validen la navegación pública.
