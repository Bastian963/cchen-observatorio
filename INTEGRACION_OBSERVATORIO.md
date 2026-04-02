# Integración Observatorio 3 en 1: Dashboard + DSpace + CKAN

`docker-compose.observatorio.yml` es la orquestación canónica del stack institucional local. El compose raíz `docker-compose.yml` queda como flujo legado e histórico.

## 1. Qué deja operativo este stack

- `Dashboard Streamlit` como capa analítica y de contexto.
- `DSpace` como repositorio institucional de publicaciones y documentos.
- `CKAN` como portal de datos abiertos y recursos descargables.
- `DSpace` precrea `pgcrypto`, desactiva la validación temprana de Hibernate y ejecuta `database migrate` antes del arranque REST.
- `CKAN` inicializa `ckan`, `datastore`, permisos y sysadmin local por defecto.
- `Solr DSpace` y `Solr CKAN` quedan con healthchecks reales.

## 2. Arranque limpio recomendado

```bash
docker compose -f docker-compose.observatorio.yml down -v
docker compose -f docker-compose.observatorio.yml up --build
```

Para un arranque normal:

```bash
docker compose -f docker-compose.observatorio.yml up -d
```

## 3. Accesos locales

- Dashboard: http://localhost:8501
- DSpace frontend: http://localhost:4000
- DSpace backend: http://localhost:8080/server
- CKAN: http://localhost:5001
- Solr DSpace: http://localhost:8983
- Solr CKAN: http://localhost:8984

## 4. Verificación mínima de salud

```bash
bash Scripts/check_observatorio_stack.sh
```

Para automatizar la verificación justo después del arranque:

```bash
bash Scripts/wait_and_check_observatorio_stack.sh
```

Este wrapper reintenta el smoke hasta que el stack quede operativo o se cumpla el timeout.

Chequeos esperados:

- Dashboard responde en `/_stcore/health`
- DSpace UI y REST responden sin error
- CKAN UI y `status_show` responden sin error
- ambos Solr responden correctamente

Chequeos de base de datos útiles:

```bash
docker exec dspace-db psql -U dspace -d dspace -c "SELECT extname FROM pg_extension ORDER BY extname;"
docker exec ckan-db psql -U ckan -d postgres -c "SELECT datname FROM pg_database ORDER BY datname;"
```

Expectativas:

- `dspace-db` debe listar `pgcrypto`
- la BD DSpace no debe quedar vacía tras `database migrate`
- PostgreSQL de CKAN debe listar `ckan` y `datastore`
- no debe reaparecer `Schema-validation: missing table [bitstream]`
- no debe reaparecer `CKAN schema not found`

## 5. Bootstrap administrativo

DSpace no crea admin automáticamente. Usa el servicio CLI:

```bash
docker compose -f docker-compose.observatorio.yml --profile ops run --rm dspace-cli \
  create-administrator -e admin@localhost -f Admin -l Local -p Admin.1234 -c en
```

CKAN crea sysadmin al arrancar usando:

- `CKAN_SYSADMIN_NAME`
- `CKAN_SYSADMIN_EMAIL`
- `CKAN_SYSADMIN_PASSWORD`

Defaults locales actuales:

- usuario: `ckan_admin`
- email: `admin@localhost`
- password: `Admin.1234`

## 6. Regla editorial del observatorio

- Documento institucional, paper o informe final: `DSpace`
- Dataset, serie o recurso descargable: `CKAN`
- Indicador, análisis o narrativa ejecutiva: `Dashboard`

La matriz completa está en `Docs/matriz_publicacion_3_en_1.md`.

## 7. Catalogo maestro y primera ola de contenido

La capa canónica de activos institucionales vive en:

- `Data/Gobernanza/catalogo_activos_3_en_1.csv`

Uso operativo:

- `python3 Scripts/validate_asset_catalog.py`
- `CKAN_API_KEY="<token>" python3 Scripts/publish_to_ckan.py`
- `Docs/operations/checklist_carga_dspace_ola_1.md` para la ola documental en DSpace

Primera ola curada:

- 4 documentos para DSpace
- 5 datasets para CKAN

El dashboard ya consume este catalogo para mostrar activos publicados y colas editoriales.

## 8. Runbook diario

El flujo operativo corto quedó documentado en:

- `Docs/operations/runbook_plataforma_3_en_1.md`

Incluye:

- arranque limpio
- verificación rápida
- bootstrap admin
- reinicios parciales
- reconstrucción por servicio
- diagnóstico básico

## 9. Alcance

- Este flujo está pensado para Docker local en esta máquina.
- No incluye hardening productivo, TLS ni exposición pública definitiva.
- El objetivo inmediato es operación reproducible y coherencia entre las tres superficies de producto.

## 10. Publicación interna por URL

La publicación por dominio institucional se hace con un overlay adicional:

```bash
OBSERVATORIO_BASIC_AUTH_PASSWORD='CAMBIAR-CLAVE' \
bash Scripts/bootstrap_observatorio_vm.sh

bash Scripts/deploy_observatorio_prod.sh
```

Piezas relevantes:

- `docker-compose.observatorio.prod.yml`
- `deploy/nginx/templates/observatorio-public.conf.template`
- `Scripts/bootstrap_observatorio_vm.sh`
- `Scripts/deploy_observatorio_prod.sh`
- `Scripts/check_observatorio_prod_overlay.sh`
- `Scripts/check_observatorio_published_ports.sh`
- `Scripts/check_observatorio_public_url.sh`
- `Scripts/wait_and_check_observatorio_public_url.sh`
- `Scripts/backup_observatorio_prod.sh`
- `Scripts/check_observatorio_backup_artifacts.sh`
- `Scripts/prepare_local_public_demo.sh`

Runbooks:

- `Docs/operations/checklist_despliegue_vm_staging_3en1.md`
- `Docs/operations/runbook_publicacion_vm_observatorio_3en1.md`
- `Docs/operations/runbook_backup_restore_observatorio_3en_1.md`
- `Docs/operations/acceso_interno_observatorio_3en1.md`
