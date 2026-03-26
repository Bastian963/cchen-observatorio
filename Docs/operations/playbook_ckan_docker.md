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
| YYYY-MM-DD  | ckan       | Error: failed to read dockerfile: open docker/Dockerfile: no such file or directory | El contexto remoto de GitHub no expone subdirectorios como contexto de build estándar | Clonar CKAN localmente y usar context: ./ckan-src en docker-compose.yml |
| YYYY-MM-DD  | ckan       | Error: pull access denied for keitaroinc/ckan, repository does not exist or may require 'docker login' | Imagen retirada de Docker Hub, comunidad migró a build local | Usar build: context: https://github.com/ckan/ckan.git#ckan-2.10.4 y dockerfile oficial |
| YYYY-MM-DD  | ckan       | Error: pull access denied for ckan/ckan, repository does not exist or may require 'docker login' | Imagen obsoleta/no disponible en Docker Hub | Usar keitaroinc/ckan:2.10 en docker-compose.yml |

| Fecha       | Servicio   | Error/Evento                  | Diagnóstico           | Solución/Aprendizaje         |
|-------------|------------|-------------------------------|-----------------------|------------------------------|
| YYYY-MM-DD  | dashboard  | Ejemplo: puerto ocupado       | Puerto 8501 en uso    | Liberar puerto, reiniciar    |
| YYYY-MM-DD  | ckan       | Ejemplo: DB connection error  | DB no inicializada    | Esperar healthcheck de db    |

---

## 5. Buenas prácticas
+ Si usas build desde un repo remoto y falla por contexto/Dockerfile, clona el repo localmente y apunta el contexto de build a la carpeta local.
- Usar siempre la imagen oficial recomendada de CKAN (keitaroinc/ckan) y revisar la documentación de la comunidad ante errores de pull.
+ Si la imagen oficial no está disponible en Docker Hub, construir CKAN desde el Dockerfile oficial del repositorio GitHub (rama ckan-2.10.x) usando build: en docker-compose.yml.
- Usar variables de entorno para credenciales en producción.
+ Usar siempre la imagen oficial recomendada de CKAN (keitaroinc/ckan) y revisar la documentación de la comunidad ante errores de pull.
- Versionar siempre `docker-compose.yml` y este playbook.
- Documentar cada cambio relevante y error encontrado.
- Mantener los volúmenes para persistencia de datos.
- Usar variables de entorno para credenciales en producción.

---

## 6. Referencias
- [CKAN Docker Docs](https://github.com/ckan/ckan/wiki/Docker)
- [Streamlit Deployment](https://docs.streamlit.io/deploy)
- [Docker Compose Docs](https://docs.docker.com/compose/)
