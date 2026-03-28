# Plan de Trabajo 2026 — Plataforma Institucional 3 en 1

**Versión:** 2.0  
**Fecha:** Marzo 2026  
**Autor:** Bastián Ayala Inostroza  
**Estado actual:** TRL 5, validación en entorno relevante

## 1. Contexto

El observatorio deja de operar como un dashboard expandido y pasa a definirse como una plataforma institucional de conocimiento con tres productos coordinados:

- `Observatorio Analítico`: inteligencia, vigilancia y apoyo a decisiones.
- `Repositorio Institucional DSpace`: publicaciones, informes y documentos institucionales.
- `Portal de Datos CKAN`: datasets, series y recursos descargables.

Regla operativa:

- `DSpace` conserva documentos.
- `CKAN` conserva datos publicables.
- `Dashboard` consume, relaciona y explica.

## 2. Objetivo 2026

Consolidar una plataforma 3 en 1 operativa, reproducible y editorialmente coherente, capaz de:

- levantar localmente con Docker sin intervención manual frágil;
- publicar activos institucionales en DSpace y CKAN;
- conectar el dashboard y el asistente con esas dos superficies sin duplicar su rol;
- y sostener una narrativa institucional única en la documentación y los accesos.

## 3. Fases de trabajo

### Fase 1 — Cierre operativo del stack

**Objetivo:** stack local 3 en 1 completamente sano.

Entregables:

- `docker-compose.observatorio.yml` como orquestación canónica.
- Dashboard, DSpace, CKAN y servicios asociados con healthchecks funcionales.
- smoke test del stack con `Scripts/check_observatorio_stack.sh`.
- runbook corto de operación diaria.

**Criterio de salida:** las URLs locales del dashboard, DSpace y CKAN responden correctamente tras `down -v` y `up --build`.

### Fase 2 — Modelo de información institucional

**Objetivo:** reglas claras de publicación y descubrimiento.

Entregables:

- matriz editorial obligatoria para decidir entre DSpace, CKAN y dashboard;
- esquema mínimo común de metadatos;
- regla de vínculo cruzado entre datasets, publicaciones y vistas analíticas.

**Criterio de salida:** todo activo nuevo tiene superficie canónica definida y campos mínimos homogéneos.

### Fase 3 — Integración funcional

**Objetivo:** hacer visible la plataforma como un sistema coordinado.

Entregables:

- portada institucional 3 en 1 dentro del dashboard;
- enlaces profundos desde el dashboard a DSpace y CKAN;
- búsqueda y asistente preparados para descubrir activos de las tres superficies;
- vista de catálogo o descubrimiento sin duplicar las funciones nativas de DSpace/CKAN.

**Criterio de salida:** un usuario puede entender desde la entrada qué se consulta, qué se publica y qué se descarga.

### Fase 4 — Contenido mínimo viable

**Objetivo:** poblar la plataforma con activos institucionales reales.

Entregables:

- lote inicial de publicaciones e informes en DSpace;
- lote inicial de datasets curados en CKAN;
- vistas analíticas del dashboard enlazadas a esos activos;
- validación editorial mínima de metadatos, URLs y consistencia.

**Criterio de salida:** al menos un conjunto representativo de publicaciones y datasets está visible y conectado con la capa analítica.

### Fase 5 — Comunicación y consolidación

**Objetivo:** unificar el relato del producto y preparar evolución institucional.

Entregables:

- `README.md`, `ARCHITECTURE.md` y documentos de operación alineados al modelo 3 en 1;
- demo principal del proyecto reformulada como plataforma, no sólo como dashboard;
- hoja de ruta separada para operación interna y publicación pública.

**Criterio de salida:** la documentación deja de contar productos distintos y pasa a describir una sola arquitectura institucional.

## 4. Prioridades inmediatas

1. Estabilizar y validar el stack local completo.
2. Formalizar la matriz editorial DSpace / CKAN / Dashboard.
3. Cargar un lote institucional mínimo en DSpace y CKAN.
4. Conectar el dashboard con enlaces y descubrimiento transversal.
5. Mantener la documentación y los playbooks sincronizados con la operación real.

## 5. Indicadores de avance

- `Operación`: stack levanta y responde en todos sus endpoints críticos.
- `Contenido`: existen activos institucionales reales publicados en DSpace y CKAN.
- `Coherencia`: la documentación y la UI explican la plataforma como un sistema 3 en 1.
- `Trazabilidad`: cada activo relevante tiene superficie canónica, metadatos mínimos y vínculo cruzado cuando corresponde.

## 6. Referencias operativas

- `INTEGRACION_OBSERVATORIO.md`
- `Docs/matriz_publicacion_3_en_1.md`
- `Docs/operations/runbook_plataforma_3_en_1.md`
