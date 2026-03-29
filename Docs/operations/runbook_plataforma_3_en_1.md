# Runbook Operativo — Plataforma 3 en 1

Runbook corto para operar el observatorio como plataforma institucional con dashboard, DSpace y CKAN.

## 0. Clonado del repositorio

```bash
git clone --recurse-submodules https://github.com/Bastian963/cchen-observatorio.git
cd cchen-observatorio
git submodule update --init --recursive
```

`ckan-src` debe quedar inicializado antes de construir `ckan` o `ckan-solr`.

## 1. Arranque limpio

```bash
docker compose -f docker-compose.observatorio.yml down -v
docker compose -f docker-compose.observatorio.yml up --build
```

Usa `down -v` sólo cuando necesites rehacer bootstrap y volúmenes desde cero.

## 2. Arranque normal

```bash
docker compose -f docker-compose.observatorio.yml up -d
```

## 3. Chequeo post-arranque automatizado

```bash
bash Scripts/wait_and_check_observatorio_stack.sh
```

Este wrapper espera hasta que el stack responda end-to-end y luego ejecuta el smoke oficial.

Variables utiles:

- `TIMEOUT_SECONDS=900` para ampliar o acotar la espera total.
- `INTERVAL_SECONDS=10` para ajustar la frecuencia de reintentos.
- `SHOW_COMPOSE_PS=true` para imprimir `docker compose ps` en cada reintento.

Si en esta maquina el `dashboard` se ejecuta como respaldo local en vez de contenedor, primero levanta:

```bash
HOST=127.0.0.1 PORT=8501 bash Scripts/run_dashboard_prod_local.sh
```

## 4. Verificación rápida

```bash
bash Scripts/check_observatorio_stack.sh
```

Chequea:

- Dashboard Streamlit
- DSpace UI y REST
- CKAN UI y Action API
- Solr DSpace y Solr CKAN

## 5. Catalogo maestro y validación editorial

```bash
python3 Scripts/validate_asset_catalog.py
```

El catalogo canónico del ciclo vive en:

- `Data/Gobernanza/catalogo_activos_3_en_1.csv`

Ese CSV es la fuente de verdad para activos publicados o enlazados desde el dashboard.

## 6. Publicación CKAN desde catalogo

Primero genera un token CKAN para el sysadmin local:

```bash
docker exec ckan ckan -c /srv/app/ckan.ini user token add -q ckan_admin dgin-pilot-catalog
```

Luego publica la ola CKAN:

```bash
CKAN_API_KEY="<token>" python3 Scripts/publish_to_ckan.py
```

El script actualiza `public_url` y `publication_status` en el catalogo cuando la publicación termina bien.

## 7. Carga manual DSpace ola 1

La primera iteracion DSpace sigue curada manualmente. Usa:

- `Docs/operations/checklist_carga_dspace_ola_1.md`

Despues de cada carga manual, escribe `public_url` e `identificador` de vuelta en el catalogo.

## 8. URLs canónicas locales

- Dashboard: `http://localhost:8501`
- DSpace UI: `http://localhost:4000`
- DSpace REST: `http://localhost:8080/server/api`
- CKAN UI: `http://localhost:5001`
- CKAN Action API: `http://localhost:5001/api/3/action/status_show`

## 8.b Publicación interna por URL

La publicación interna controlada en VM se monta con un overlay adicional y no reemplaza este runbook local:

```bash
OBSERVATORIO_BASIC_AUTH_PASSWORD='CAMBIAR-CLAVE' \
bash Scripts/bootstrap_observatorio_vm.sh

bash Scripts/deploy_observatorio_prod.sh
```

Documentación específica:

- `Docs/operations/checklist_despliegue_vm_staging_3en1.md`
- `Docs/operations/runbook_publicacion_vm_observatorio_3en1.md`
- `Docs/operations/runbook_backup_restore_observatorio_3en_1.md`
- `Docs/operations/acceso_interno_observatorio_3en1.md`

Smoke por dominios publicados:

```bash
bash Scripts/check_observatorio_published_ports.sh
bash Scripts/wait_and_check_observatorio_public_url.sh
```

## 9. Bootstrap administrativo

### DSpace

```bash
docker compose -f docker-compose.observatorio.yml --profile ops run --rm dspace-cli \
  create-administrator -e admin@localhost -f Admin -l Local -p Admin.1234 -c en
```

### CKAN

CKAN crea sysadmin al arrancar usando estas variables:

- `CKAN_SYSADMIN_NAME`
- `CKAN_SYSADMIN_EMAIL`
- `CKAN_SYSADMIN_PASSWORD`

## 10. Reinicios parciales

```bash
docker compose -f docker-compose.observatorio.yml restart dashboard
docker compose -f docker-compose.observatorio.yml restart dspace-backend dspace-frontend
docker compose -f docker-compose.observatorio.yml restart ckan
```

## 11. Reconstrucciones frecuentes

```bash
git submodule update --init --recursive
docker compose -f docker-compose.observatorio.yml up -d --build dashboard
docker compose -f docker-compose.observatorio.yml up -d --build ckan ckan-solr
docker compose -f docker-compose.observatorio.yml up -d --build dspace-frontend
```

## 12. Restauración básica de operación

1. Verifica `docker compose -f docker-compose.observatorio.yml ps`.
2. Ejecuta `bash Scripts/wait_and_check_observatorio_stack.sh`.
3. Si falla DSpace, revisa `docker logs dspace-backend` y confirma que no reaparezca `Schema-validation: missing table [bitstream]`.
4. Si falla CKAN, revisa `docker logs ckan` y confirma que no aparezca `CKAN schema not found`.
5. Si falla el dashboard, revisa `docker logs cchen-dashboard` y luego `curl http://localhost:8501/_stcore/health`.

## 13. Regla editorial operativa

- Documento final o publicación: `DSpace`
- Dataset descargable o serie reusable: `CKAN`
- Indicador, análisis o narrativa: `Dashboard`

La matriz completa está en `Docs/matriz_publicacion_3_en_1.md`.
