# Flujo de trabajo — Planta provisional y estado ORCID

## Objetivo

Dejar una fuente operativa simple para representar la planta académica/investigadora vigente de forma **provisional**, separada de la cobertura ORCID, de manera que el panel y los procesos de QA no dependan de asumir que el CSV ORCID representa toda la planta actual.

## Archivos involucrados

- Fuente base provisional: `Data/Researchers/cchen_padron_academicos_provisional_2026-02-18.csv`
- Auditoría ORCID detallada: `Data/Researchers/cchen_padron_orcid_auditoria_2026-03-24.csv`
- Exportable operativo versionado: `Data/Researchers/cchen_planta_provisional_estado_orcid_2026-03-24.csv`
- Exportable operativo estable usado por el panel: `Data/Researchers/cchen_planta_estado_orcid_actual.csv`
- Exportable de brechas versionado: `Data/Researchers/cchen_planta_orcid_brechas_2026-03-24.csv`
- Exportable de brechas estable: `Data/Researchers/cchen_planta_orcid_brechas_actual.csv`
- Resumen de auditoría: `Docs/reports/auditoria_orcid_padron_provisional_2026-03-24.md`

## Qué contiene el exportable operativo

El archivo `cchen_planta_provisional_estado_orcid_2026-03-24.csv` agrega dos campos clave para operación:

- `estado_orcid`
- `estado_revision_manual`

### Valores de `estado_orcid`

- `orcid_confirmado_cchen`: match ORCID válido, nombre consistente y employer CCHEN verificable.
- `orcid_match_aproximado_cchen`: ORCID válido y employer CCHEN verificable, pero con diferencia nominal menor (por ejemplo, apellido materno ausente o nombre extendido).
- `orcid_valido_sin_employer_cchen`: ORCID válido y nombre razonable, pero sin employer CCHEN verificable en el perfil.
- `sin_orcid_csv`: persona del padrón sin match en el CSV ORCID actual.

### Valores iniciales de `estado_revision_manual`

- `confirmado`: caso suficientemente consistente para uso operativo.
- `revisar_nombre_grupo`: revisar match aproximado de nombre o adscripción antes de consolidar.
- `revisar_employer_en_orcid`: el ORCID parece correcto, pero el perfil no declara employer CCHEN.
- `pendiente_busqueda_orcid`: no existe match en el CSV ORCID actual y requiere búsqueda o carga posterior.

## Criterio actual del panel

En `Panel de Indicadores`, el KPI principal de planta usa el archivo estable `cchen_planta_estado_orcid_actual.csv` cuando existe.

- KPI mostrado: `Planta provisional`
- Subtítulo: `padron provisional vigente · X con ORCID`

Si el exportable no estuviera disponible, el panel hace fallback al conteo conservador basado solo en employer CCHEN verificado en ORCID.

Además, el panel incluye un bloque QA plegable con:

- filtro por estado de revisión (`pendientes`, `sin ORCID`, `revisar employer`, `revisar nombre/grupo`, `confirmados`, `todos`)
- tabla de revisión operativa
- descarga de la vista filtrada
- descarga directa de brechas

La sección `Formación de Capacidades` incluye una vista QA equivalente con el mismo esquema de filtro y descargas.

## Estado al 2026-03-24

- Padrón provisional total: 31 personas
- Con match ORCID: 12
- Sin match ORCID: 19
- ORCID válidos: 12 de 12 matches
- Employer CCHEN verificable: 7 de 12 matches

Distribución del exportable operativo:

- `sin_orcid_csv` + `pendiente_busqueda_orcid`: 19
- `orcid_match_aproximado_cchen` + `revisar_nombre_grupo`: 4
- `orcid_valido_sin_employer_cchen` + `revisar_employer_en_orcid`: 5
- `orcid_confirmado_cchen` + `confirmado`: 3

## Regeneración automática (script)

Se agregó el script reproducible:

- `Scripts/build_planta_orcid_exports.py`

Comando recomendado:

- `python Scripts/build_planta_orcid_exports.py --stamp YYYY-MM-DD`

El script toma:

- `Data/Researchers/cchen_padron_academicos_provisional_2026-02-18.csv` (o el padrón que se indique por parámetro)
- `Data/Researchers/cchen_researchers_orcid.csv`

Y genera automáticamente:

- `Data/Researchers/cchen_planta_estado_orcid_actual.csv`
- `Data/Researchers/cchen_planta_estado_orcid_YYYY-MM-DD.csv`
- `Data/Researchers/cchen_planta_orcid_brechas_actual.csv`
- `Data/Researchers/cchen_planta_orcid_brechas_YYYY-MM-DD.csv`

## Uso recomendado

- Para panel: usar `cchen_planta_estado_orcid_actual.csv` como fuente estable de planta vigente provisional.
- Para QA: revisar primero los casos `revisar_nombre_grupo` y `revisar_employer_en_orcid`.
- Para seguimiento de brechas: usar `cchen_planta_orcid_brechas_actual.csv` como listado operativo pendiente.

## Reemplazo futuro con planta formal

Cuando exista el padrón formal de académicos/investigadores vigentes, el flujo no requiere cambios en el panel si se mantiene el mismo esquema de columnas.

Pasos:

- Generar una nueva versión fechada del exportable con el mismo esquema.
- Sobrescribir `Data/Researchers/cchen_planta_estado_orcid_actual.csv` con la versión vigente.
- Regenerar `Data/Researchers/cchen_planta_orcid_brechas_actual.csv` con los pendientes de revisión.

Mientras el archivo estable conserve el mismo nombre y columnas, el panel seguirá funcionando sin cambios de código.
