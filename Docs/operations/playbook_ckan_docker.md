# Playbook: Orquestación Dashboard + CKAN con Docker Compose

## Objetivo
Levantar el dashboard institucional y un portal CKAN en la misma red de contenedores, facilitando pruebas, integración y despliegue reproducible.

---

## 1. Estructura de servicios
- **dashboard**: Streamlit, expone puerto 8501, accede a Data/ y Database/ como volúmenes.
- **ckan**: CKAN 2.10, expone puerto 5000, almacenamiento persistente en volumen.
- **db**: PostgreSQL 13, persistencia en volumen, usuario/clave por defecto para pruebas.

## 2. Comandos básicos

```bash
git submodule update --init --recursive
```

- Inicializa `ckan-src`, requerido para los builds locales del overlay CKAN.

```bash
docker compose up -d --build
```
- Levanta todos los servicios en modo background.

```bash
docker compose logs -f dashboard
```
- Muestra logs en tiempo real del dashboard.

```bash
docker compose logs -f ckan
```
- Muestra logs en tiempo real de CKAN.

```bash
docker compose ps
```
- Estado de los contenedores y healthchecks.

```bash
docker compose down
```
- Detiene y elimina los contenedores (los volúmenes persisten).

---

## 3. Healthchecks y troubleshooting
- **dashboard**: healthcheck en `/_stcore/health` (Streamlit).
- **ckan**: healthcheck en `/api/3/action/status_show`.
- **db**: healthcheck con `pg_isready`.

Si un servicio falla:
- Revisar logs con `docker compose logs -f <servicio>`.
- Verificar puertos libres (8501, 5000).
- Revisar variables de entorno y volúmenes.

---

## 4. Registro de errores y soluciones
| 2026-03-28  | ckan       | Build local depende de archivos operativos fuera del upstream limpio | El repositorio principal necesitaba customizaciones de Docker sin vendorear todo CKAN | Mantener `ckan-src` como submódulo limpio y mover el overlay operativo a `ckan/` |
| YYYY-MM-DD  | ckan       | Error: pull access denied for keitaroinc/ckan, repository does not exist or may require 'docker login' | Imagen retirada de Docker Hub, comunidad migró a build local | Usar build: context: https://github.com/ckan/ckan.git#ckan-2.10.4 y dockerfile oficial |
| YYYY-MM-DD  | ckan       | Error: pull access denied for ckan/ckan, repository does not exist or may require 'docker login' | Imagen obsoleta/no disponible en Docker Hub | Usar keitaroinc/ckan:2.10 en docker-compose.yml |

| Fecha       | Servicio   | Error/Evento                  | Diagnóstico           | Solución/Aprendizaje         |
|-------------|------------|-------------------------------|-----------------------|------------------------------|
| YYYY-MM-DD  | dashboard  | Ejemplo: puerto ocupado       | Puerto 8501 en uso    | Liberar puerto, reiniciar    |
| YYYY-MM-DD  | ckan       | Ejemplo: DB connection error  | DB no inicializada    | Esperar healthcheck de db    |

---

## 5. Buenas prácticas
- Mantener `ckan-src` inicializado como submódulo limpio antes de cualquier `docker compose build`.
- Versionar en el repo principal sólo el overlay operativo (`ckan/Dockerfile`, bootstrap, Solr y SQL init) y no el árbol completo de CKAN.
- Usar variables de entorno para credenciales en producción.
- Versionar siempre `docker-compose.yml` y este playbook.
- Documentar cada cambio relevante y error encontrado.
- Mantener los volúmenes para persistencia de datos.

---

## 6. Referencias
- [CKAN Docker Docs](https://github.com/ckan/ckan/wiki/Docker)
- [Streamlit Deployment](https://docs.streamlit.io/deploy)
- [Docker Compose Docs](https://docs.docker.com/compose/)
