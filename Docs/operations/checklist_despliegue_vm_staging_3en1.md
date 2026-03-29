# Checklist de Despliegue — VM Staging Observatorio 3 en 1

## Antes del despliegue

- VM `Ubuntu 24.04 LTS` disponible
- Docker Engine y Compose plugin instalados
- DNS interno resuelto para:
  - `obs-int.cchen.cl`
  - `repo-int.cchen.cl`
  - `datos-int.cchen.cl`
- acceso restringido por `VPN o red interna`
- certificados TLS entregados por TI
- credenciales de `Basic Auth` definidas
- `Dashboard/.streamlit/secrets.toml` preparado

## Bootstrap de la VM

```bash
OBSERVATORIO_BASIC_AUTH_PASSWORD='CAMBIAR-CLAVE' \
bash Scripts/bootstrap_observatorio_vm.sh
```

Verificar:
- existe `.env.prod`
- existe `/srv/observatorio/nginx/.htpasswd`
- existen directorios `tls`, `logs/nginx`, `backups`

## Despliegue staging

```bash
bash Scripts/deploy_observatorio_prod.sh
```

## Validaciones obligatorias

```bash
export OBSERVATORIO_BASIC_AUTH_CREDENTIALS='observatorio:CAMBIAR-CLAVE'
bash Scripts/check_observatorio_published_ports.sh
bash Scripts/wait_and_check_observatorio_public_url.sh
```

Validar manualmente:
- Dashboard abre detrás de `Basic Auth`
- `internal_auth` del dashboard funciona
- DSpace UI abre
- `repo-int/server/api` responde
- CKAN UI abre
- `api/3/action/status_show` responde
- el dashboard enlaza a DSpace y CKAN por URL institucional

## Prueba operativa mínima

```bash
COMPOSE_ACTION=restart bash Scripts/deploy_observatorio_prod.sh
bash Scripts/backup_observatorio_prod.sh
bash Scripts/check_observatorio_backup_artifacts.sh
```

## Criterio de salida

- sólo `80/443` publicados
- URLs internas responden
- backup válido generado
- staging lista para promover a VM piloto interna
