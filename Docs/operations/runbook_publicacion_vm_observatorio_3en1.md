# Runbook de Publicación en VM — Observatorio 3 en 1

Guía para publicar el observatorio como piloto interno controlado en una VM Linux con Docker Compose, subdominios separados, TLS y login interno.

## 1. Supuestos de infraestructura

- VM: `Ubuntu 24.04 LTS`
- Docker Engine + Compose plugin instalados
- DNS institucional apuntando a la VM:
  - `obs-int.cchen.cl`
  - `repo-int.cchen.cl`
  - `datos-int.cchen.cl`
- Certificados TLS entregados por TI
- Acceso de red restringido por firewall, allowlist o VPN

## 2. Directorios operativos fuera del repo

```bash
OBSERVATORIO_BASIC_AUTH_PASSWORD='CAMBIAR-CLAVE' \
bash Scripts/bootstrap_observatorio_vm.sh
```

Archivos esperados:

- `/srv/observatorio/tls/obs-int.cchen.cl.crt`
- `/srv/observatorio/tls/obs-int.cchen.cl.key`
- `/srv/observatorio/tls/repo-int.cchen.cl.crt`
- `/srv/observatorio/tls/repo-int.cchen.cl.key`
- `/srv/observatorio/tls/datos-int.cchen.cl.crt`
- `/srv/observatorio/tls/datos-int.cchen.cl.key`
- `/srv/observatorio/nginx/.htpasswd`

## 3. Basic Auth del reverse proxy

Ejemplo para crear el archivo de credenciales sin instalar utilidades extra en la VM:

```bash
docker run --rm --entrypoint htpasswd httpd:2 -Bbn observatorio 'cambiar-por-clave-segura' \
  > /srv/observatorio/nginx/.htpasswd
chmod 600 /srv/observatorio/nginx/.htpasswd
```

## 4. Archivo de entorno productivo

```bash
cp .env.prod.example .env.prod
```

Revisa y ajusta si TI define otros nombres de dominio o rutas distintas. Variables críticas:

- `OBSERVATORIO_DASHBOARD_HOST`
- `OBSERVATORIO_DSPACE_HOST`
- `OBSERVATORIO_CKAN_HOST`
- `OBSERVATORIO_TLS_DIR`
- `OBSERVATORIO_BASIC_AUTH_FILE`
- `OBSERVATORIO_NGINX_LOG_DIR`
- `OBSERVATORIO_BACKUP_DIR`

## 5. Secretos del dashboard y credenciales de operadores

No se suben al repo. Deben existir en la VM:

- `Dashboard/.streamlit/secrets.toml`
- `.env.prod`
- credenciales Basic Auth del proxy
- credenciales admin DSpace
- credenciales admin CKAN

El dashboard mantiene `internal_auth` como segunda capa de control. El proxy bloquea primero por Basic Auth.

## 6. Despliegue

```bash
bash Scripts/deploy_observatorio_prod.sh
```

## 6.b Validación local previa sin VM institucional

Si quieres probar el overlay productivo en un notebook o workstation antes de pasar a la VM, genera un sandbox local con `*.localhost`, TLS autofirmado y Basic Auth temporal:

```bash
bash Scripts/prepare_local_public_demo.sh
docker compose --env-file deploy/local-prod-demo/runtime/.env.prod.localhost \
  -f docker-compose.observatorio.yml \
  -f docker-compose.observatorio.prod.yml \
  up -d --build

ENV_FILE=deploy/local-prod-demo/runtime/.env.prod.localhost \
  bash Scripts/wait_and_check_observatorio_public_url.sh
```

Ese flujo publica localmente por defecto en:

- `https://obs-int.localhost:8443`
- `https://repo-int.localhost:8443`
- `https://datos-int.localhost:8443`

## 7. Validación operativa por dominio

Si todavía estás usando certificados de staging, puedes permitir TLS no estricto con `OBSERVATORIO_TLS_INSECURE=true`.

```bash
export OBSERVATORIO_BASIC_AUTH_CREDENTIALS='observatorio:cambiar-por-clave-segura'
bash Scripts/check_observatorio_published_ports.sh
bash Scripts/wait_and_check_observatorio_public_url.sh
```

Endpoints esperados:

- `https://obs-int.cchen.cl/_stcore/health`
- `https://repo-int.cchen.cl`
- `https://repo-int.cchen.cl/server/api`
- `https://datos-int.cchen.cl`
- `https://datos-int.cchen.cl/api/3/action/status_show`

## 8. Regla de exposición

Sólo deben quedar accesibles desde la red autorizada:

- `80`
- `443`

No deben quedar publicados:

- `8501`
- `8080`
- `5001`
- `8983`
- `8984`
- `5432`
- `6379`

## 9. Reinicio controlado

```bash
COMPOSE_ACTION=restart bash Scripts/deploy_observatorio_prod.sh
```

## 10. Cierre de Streamlit Cloud

Una vez validada la VM:

- dejar de usar Streamlit Cloud como vía principal
- mantenerlo sólo como contingencia si realmente sigue siendo necesario
- dirigir a DGIn y revisores internos a los subdominios institucionales
