# Runbook Oracle — Piloto Público Observatorio 3 en 1

Guía para ejecutar el primer ensayo público del Observatorio 3 en 1 en una VM Ubuntu pública de Oracle Cloud.

## 1. Baseline y decisión de arquitectura

Baseline recomendado:

- rama: `feat/observatorio-3en1-public-portal`
- tag: `observatorio-3en1-public-beta-ready-2026-03-29`

Ruta sugerida para el primer boot:

- preferir `x86` si todavía existen `trial credits`
- usar `VM.Standard.A1.Flex` sólo si el objetivo es `Always Free` estricto

Motivo:

- el stack usa imágenes externas y no se ha revalidado formalmente todo el 3 en 1 sobre `ARM`
- un primer ensayo `x86` reduce riesgo operacional antes de optimizar costo

Consulta el estado maestro antes de tocar Oracle:

- `Docs/operations/estado_beta_publica_3en1.md`

## 2. Preparación previa

Antes de entrar a Oracle:

```bash
bash Scripts/check_public_beta_release.sh
```

Y asegúrate de tener:

- acceso a Oracle Cloud
- DNS gestionable para `cchen.cl`
- llave SSH local
- correo válido para `Let's Encrypt`

## 3. Red objetivo

Dominios del piloto:

- `observatorio.cchen.cl`
- `repo.cchen.cl`
- `datos.cchen.cl`
- `obs-int.cchen.cl`

Puertos públicos:

- `80/tcp`
- `443/tcp`

Puertos que no deben quedar expuestos:

- `8501`
- `8080`
- `5001`
- `8983`
- `8984`
- `5432`
- `6379`

## 4. Provisionamiento Oracle

### 4.1 Compartment y VCN

Crear:

- un `Compartment` dedicado al piloto
- una `VCN with Internet Connectivity`
- una subnet pública

Reglas mínimas:

- `22/tcp` sólo desde la IP pública del operador
- `80/tcp` abierto
- `443/tcp` abierto

### 4.2 VM

Parámetros recomendados:

- OS: `Ubuntu 24.04 LTS`
- boot volume: `150-200 GB`
- IP pública asignada

Opciones de shape:

- preferida si hay créditos: una VM `x86` pequeña o mediana
- alternativa `Always Free`: `VM.Standard.A1.Flex`

## 5. Bootstrap base de la VM

Conéctate por SSH e instala dependencias:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git snapd

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

## 6. Clonado del repo

```bash
sudo mkdir -p /opt
sudo chown -R "$USER":"$USER" /opt
cd /opt

git clone --recurse-submodules https://github.com/Bastian963/cchen-observatorio.git
cd cchen-observatorio
git checkout observatorio-3en1-public-beta-ready-2026-03-29
git submodule update --init --recursive
```

## 7. Preparación de entorno y secretos

Bootstrap del layout operativo:

```bash
OBSERVATORIO_ENV_FILE=.env.public \
OBSERVATORIO_BASIC_AUTH_PASSWORD='CAMBIAR-POR-CLAVE-SEGURA' \
bash Scripts/bootstrap_observatorio_vm.sh
```

Completar:

- `.env.public`
- `Dashboard/.streamlit/secrets.public.toml`
- `Dashboard/.streamlit/secrets.toml`

Archivos no versionados esperados:

- `/srv/observatorio/tls`
- `/srv/observatorio/nginx/.htpasswd`
- `/srv/observatorio/logs/nginx`
- `/srv/observatorio/backups`

## 8. DNS y certificados

Configura registros `A` para:

- `observatorio.cchen.cl`
- `repo.cchen.cl`
- `datos.cchen.cl`
- `obs-int.cchen.cl`

Instala Certbot:

```bash
sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot
```

Emite certificados:

```bash
export LETSENCRYPT_EMAIL='correo@ejemplo.cl'

for host in observatorio.cchen.cl repo.cchen.cl datos.cchen.cl obs-int.cchen.cl; do
  sudo certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email "$LETSENCRYPT_EMAIL" \
    -d "$host"
done
```

Luego sincroniza al layout que espera Nginx:

```bash
OBSERVATORIO_ENV_FILE=.env.public \
bash Scripts/sync_observatorio_letsencrypt_certs.sh
```

## 9. Despliegue

```bash
bash Scripts/deploy_observatorio_public.sh
```

## 10. Validación operativa

```bash
export OBSERVATORIO_INTERNAL_BASIC_AUTH_CREDENTIALS='observatorio:CAMBIAR-POR-CLAVE-SEGURA'

ENV_FILE=.env.public bash Scripts/check_observatorio_published_ports.sh
bash Scripts/wait_and_check_observatorio_public_portal.sh
```

Validación manual:

- `https://observatorio.cchen.cl` sin `Basic Auth`
- `https://repo.cchen.cl` visible
- `https://datos.cchen.cl` visible
- `https://obs-int.cchen.cl` con `Basic Auth` y luego `internal_auth`
- sin enlaces `localhost`
- el asistente público sólo cita fuentes abiertas

## 11. Restart y backup drill

```bash
COMPOSE_ACTION=restart bash Scripts/deploy_observatorio_public.sh
bash Scripts/wait_and_check_observatorio_public_portal.sh

OBSERVATORIO_ENV_FILE=.env.public bash Scripts/backup_observatorio_prod.sh
OBSERVATORIO_ENV_FILE=.env.public bash Scripts/check_observatorio_backup_artifacts.sh
```

## 12. Registro de resultado

Después del ensayo, actualizar:

- `Docs/operations/estado_beta_publica_3en1.md`

Registrar:

- fecha
- shape usada (`x86` o `A1`)
- tag o commit desplegado
- checks ejecutados
- incidentes
- decisión `go / ajustar`
