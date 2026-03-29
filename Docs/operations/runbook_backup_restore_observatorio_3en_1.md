# Runbook de Backup y Restore — Observatorio 3 en 1

## 1. Respaldo mínimo obligatorio

El script versionado para la VM es:

```bash
bash Scripts/backup_observatorio_prod.sh
bash Scripts/check_observatorio_backup_artifacts.sh
```

Por defecto toma `.env.prod` como entorno y escribe en `OBSERVATORIO_BACKUP_DIR`, normalmente:

- `/srv/observatorio/backups/YYYYmmdd_HHMMSS/`

Artefactos generados:

- `dspace.sql`
- `ckan.sql`
- `ckan_datastore.sql`
- `dspace_assetstore.tgz`
- `ckan_storage.tgz`

`check_observatorio_backup_artifacts.sh` valida que el último respaldo exista, no esté vacío y que ambos `.tgz` sean legibles.

## 2. Restore mínimo

### Bases de datos

```bash
cat /srv/observatorio/backups/<timestamp>/dspace.sql | docker compose --env-file .env.prod \
  -f docker-compose.observatorio.yml \
  -f docker-compose.observatorio.prod.yml \
  exec -T dspace-db psql -U dspace -d dspace

cat /srv/observatorio/backups/<timestamp>/ckan.sql | docker compose --env-file .env.prod \
  -f docker-compose.observatorio.yml \
  -f docker-compose.observatorio.prod.yml \
  exec -T ckan-db psql -U ckan -d ckan

cat /srv/observatorio/backups/<timestamp>/ckan_datastore.sql | docker compose --env-file .env.prod \
  -f docker-compose.observatorio.yml \
  -f docker-compose.observatorio.prod.yml \
  exec -T ckan-db psql -U ckan -d datastore
```

### Storages

```bash
cat /srv/observatorio/backups/<timestamp>/dspace_assetstore.tgz | docker compose --env-file .env.prod \
  -f docker-compose.observatorio.yml \
  -f docker-compose.observatorio.prod.yml \
  exec -T dspace-backend tar -C /dspace -xzf -

cat /srv/observatorio/backups/<timestamp>/ckan_storage.tgz | docker compose --env-file .env.prod \
  -f docker-compose.observatorio.yml \
  -f docker-compose.observatorio.prod.yml \
  exec -T ckan tar -C /var/lib -xzf -
```

## 3. Validación posterior a restore

```bash
bash Scripts/wait_and_check_observatorio_public_url.sh
```

Y verificar manualmente:

- acceso a `obs-int`
- acceso a `repo-int`
- acceso a `datos-int`
- login de operadores
- al menos un item DSpace y un dataset CKAN visibles

## 4. Frecuencia recomendada

- `pg_dump` diario de `dspace-db`
- `pg_dump` diario de `ckan-db` y `datastore`
- snapshot diario de `dspace_assetstore`
- snapshot diario de `ckan_storage`

Si la VM entra en piloto sostenido, mover este respaldo a cron o systemd timer.
