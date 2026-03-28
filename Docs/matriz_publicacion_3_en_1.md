# Matriz de Publicación — Plataforma Institucional 3 en 1

Esta matriz define la regla editorial y operativa del observatorio para evitar duplicidades entre el dashboard, DSpace y CKAN.

## Regla principal

- `DSpace` conserva documentos y publicaciones institucionales.
- `CKAN` conserva datasets, series y recursos descargables.
- `Dashboard` conserva indicadores derivados, análisis y narrativa ejecutiva.

El dashboard puede enlazar y resumir activos, pero no debe transformarse en el repositorio primario de documentos ni de datasets publicados.

## Matriz de decisión

| Tipo de activo | Superficie canónica | Qué se publica ahí | Qué debe enlazarse |
| --- | --- | --- | --- |
| Paper, informe, policy brief, memoria técnica, documento institucional final | `DSpace` | Objeto documental completo, metadatos, autores, unidad responsable, identificador estable | Vista analítica o dataset relacionado si existe |
| Dataset curado, tabla descargable, serie temporal, recurso reutilizable | `CKAN` | Recurso descargable, vista previa, licencia, esquema, metadatos y recursos asociados | Publicación o tablero relacionado si existe |
| KPI, visualización, benchmarking, tablero ejecutivo, análisis comparado | `Dashboard` | Lectura analítica, filtros, gráficos, narrativa y contexto de gestión | Publicación en DSpace o dataset en CKAN que actúe como fuente |
| Resumen ejecutivo basado en evidencia | `Dashboard` + vínculo a fuente | Insight de gestión o contexto | Fuente documental en DSpace y/o dataset en CKAN |
| Anexo metodológico o reporte exportable final | `DSpace` | Documento final versionado | Vista o datasets que lo sustentan |

## Metadatos mínimos comunes

Todos los activos relevantes deben compartir un set mínimo de campos:

| Campo | Uso esperado |
| --- | --- |
| `area_unidad` | Centro, unidad o área responsable |
| `tema` | Tema institucional o línea I+D |
| `anio` | Año principal del activo |
| `responsables` | Autoría, responsable técnico o unidad responsable |
| `palabras_clave` | Descubrimiento y búsqueda |
| `visibilidad` | Interno, mixto o público |
| `identificador` | DOI, handle, slug o id estable |
| `vinculo_cruzado` | URL del recurso relacionado en otra superficie |

## Reglas de vínculo cruzado

- Un dataset importante publicado en `CKAN` debe enlazar la publicación, informe o contexto documental en `DSpace` cuando exista.
- Una publicación o informe en `DSpace` debe enlazar el dataset o recurso descargable en `CKAN` cuando exista.
- Una vista del `dashboard` debe enlazar al menos una fuente primaria en `DSpace` o `CKAN` cuando el análisis se base en activos institucionales publicados.
- El asistente y la búsqueda semántica pueden indexar las tres superficies, pero siempre deben señalar la fuente de verdad original.

## Lote mínimo sugerido

- `DSpace`: informes institucionales emblemáticos, policy briefs, papers relevantes y documentos finales del observatorio.
- `CKAN`: datasets curados desde `Data/`, series exportables y recursos descargables con metadata limpia.
- `Dashboard`: paneles que expliquen y conecten esos activos con indicadores y contexto institucional.
