# Paquete pre-adjudicacion - Extraccion y catalogo de fuentes

Fecha de generacion: 2026-05-19
Matriz origen: `/media/bastin/Nuevo vol/Mumito/Descarga/Fuentes de información.xlsx`

## Artefactos generados

- `Data/Gobernanza/fuentes_informacion_fernanda_raw.csv`
- `Data/Gobernanza/catalogo_fuentes_pre_adjudicacion.csv`
- `Data/Gobernanza/priorizacion_fuentes_api_pre_adjudicacion.csv`
- `Data/Gobernanza/brechas_fuentes_pre_adjudicacion.csv`
- `Docs/reports/comentarios_excel_fernanda_fuentes_2026-05-19.md`
- `Docs/reports/calidad_pre_adjudicacion_fuentes_2026-05-19.csv`
- `Docs/reports/preflight_source_refresh_dry_run_2026-05-19.txt`

## Resumen ejecutivo

- Regla de extraccion: CCHEN-only. Se priorizan filtros por afiliacion, alias institucional, DOI, ORCID, ROR, autores conocidos o activos institucionales.
- Matriz cruda: 238 fuentes.
- Acceso: 168 abiertas, 21 freemium, 45 de pago, 4 restringidas.
- API marcada en planilla: 56 filas; catalogo API deduplicado: 54 fuentes.
- Runtime existente preservado: 42 fuentes registradas.
- Catalogo reconciliado final: 256 fuentes normalizadas.
- Brechas registradas: 18 (baja: 12, media: 6).

## Preflight

| Dependencia | Estado |
| --- | --- |
| dotenv | OK |
| openpyxl | OK |
| pandas | OK |
| supabase | OK |

- Dry-run `run_source_refresh.py --all-due --dry-run`: OK.
- Calidad de datos: ADVERTENCIA: 5, OK: 26.

## Estado de implementacion

- Por estado: api_revisar_relevancia: 13, diferida_acceso_pago_token: 72, implementada_runtime: 39, manual_sin_api: 116, registrada_diferida: 4, segunda_ola_candidata: 12.
- Por prioridad: 1_primera_ola: 14, 2_segunda_ola: 13, 3_revision: 13, diferida: 72, manual_no_api: 125, runtime_base: 19.

## Primera ola API

| Fuente | Estado | Runtime | Frecuencia | Filtro CCHEN | Brecha/accion |
| --- | --- | --- | --- | --- | --- |
| Altmetric | implementada_runtime | altmetric | trimestral | Runtime existente preservado; se asume filtro CCHEN propio de la fuente. | Fuente existente en runtime no listada en la matriz; se preserva para no perder cobertura operativa. |
| Crossref | implementada_runtime | crossref | trimestral | DOI CCHEN conocido; no se consulta universo completo. | Sin brecha critica de implementacion; validar frescura y calidad. |
| DataCite | implementada_runtime | datacite_outputs | semestral | ORCID/ROR/DOI CCHEN y metadatos de outputs institucionales. | Sin brecha critica de implementacion; validar frescura y calidad. |
| Europe PMC | implementada_runtime | europmc_works | semestral | Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos. | Sin brecha critica de implementacion; validar frescura y calidad. |
| INSPIRE | implementada_runtime | inspire_works | semestral | Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos. | Sin brecha critica de implementacion; validar frescura y calidad. |
| ORCID | implementada_runtime | orcid | semestral | Afiliacion/nombre investigador CCHEN y ORCID conocido. | Sin brecha critica de implementacion; validar frescura y calidad. |
| OpenAIRE | implementada_runtime | openaire_outputs | semestral | ORCID/ROR/DOI CCHEN y metadatos de outputs institucionales. | Sin brecha critica de implementacion; validar frescura y calidad. |
| PubMed | implementada_runtime | pubmed_works | semestral | Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos. | Sin brecha critica de implementacion; validar frescura y calidad. |
| Semantic Scholar | implementada_runtime | semantic_scholar | trimestral | Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos. | Sin brecha critica de implementacion; validar frescura y calidad. |
| Unpaywall | implementada_runtime | unpaywall_oa | semestral | DOI CCHEN conocido; no se consulta universo completo. | Sin brecha critica de implementacion; validar frescura y calidad. |
| Zenodo | implementada_runtime | zenodo_outputs | semestral | Aliases institucionales CCHEN visibles en afiliacion o metadatos; metadata-only, sin descarga de archivos. | Sin brecha critica de implementacion; validar frescura y calidad. |
| arXiv | implementada_runtime | arxiv_monitor; arxiv_works | semanal; semestral | Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos. | Sin brecha critica de implementacion; validar frescura y calidad. |
| PatentsView | implementada_runtime | patentsview_uspto | semestral | Aliases de solicitante/inventor CCHEN; requiere PATENTSVIEW_API_KEY. | Registrada con runner, pero ultima corrida fallo; validar credencial PATENTSVIEW_API_KEY. |
| USPTO | implementada_runtime | patentsview_uspto | semestral | Aliases de solicitante/inventor CCHEN; requiere PATENTSVIEW_API_KEY. | Registrada con runner, pero ultima corrida fallo; validar credencial PATENTSVIEW_API_KEY. |

## Segunda ola API

| Fuente | Categoria | API | Accion |
| --- | --- | --- | --- |
| PubChem | Bio/Farma | https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=The-URL-Path | Sin brecha critica de implementacion; validar frescura y calidad. |
| STRING DB | Bio/Farma | https://string-db.org/help/api/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| UniProt | Bio/Farma | https://www.uniprot.org/help/programmatic_access | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| BASE | Científica | https://api.base-search.net/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| CORE | Científica | https://core.ac.uk/services/api | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| DOAJ | Científica | https://doaj.org/api/v4/docs | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| Figshare | Científica | https://docs.figshare.com/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| HAL | Científica | https://api.archives-ouvertes.fr/docs | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| bioRxiv | Científica | https://api.biorxiv.org/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| medRxiv | Científica | https://api.medrxiv.org/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| EPO (OPS) | Patentes | https://developers.epo.org/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| Espacenet | Patentes | https://developers.epo.org/ | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |
| WIPO Patentscope | Patentes | https://b2b.wipo.int/catalog/api/fe3d0eba-28e8-30ee-8fbe-045c4e0a6b29 | Candidata de segunda ola; requiere validacion de relevancia CCHEN y diseno de extractor. |

## Fuentes runtime vencidas

| source_key | Fuente | last_updated | next_due | dias_atraso | blocking |
| --- | --- | --- | --- | --- | --- |
| patentsview_uspto | PatentsView / USPTO |  |  | sin fecha | False |

## Brechas priorizadas

| Severidad | source_key | Tipo | Descripcion | Accion |
| --- | --- | --- | --- | --- |
| media | patentsview_uspto | frescura_vencida | Fuente vencida al 2026-05-19 (sin fecha dias de atraso). | Ejecutar refresh focalizado, validar outputs y actualizar runtime. |
| media | Data/Publications/cchen_crossref_enriched.csv | calidad_advertencia | Baja completeness en 'crossref_funders': 26% (umbral: 30%) | Documentar causa, aceptar explicitamente o corregir antes del traspaso. |
| media | Data/Publications/cchen_openalex_grants.csv | calidad_advertencia | Archivo CSV vacío | Documentar causa, aceptar explicitamente o corregir antes del traspaso. |
| media | Publications/* | calidad_advertencia | 1 work_ids huérfanos en authorships | Documentar causa, aceptar explicitamente o corregir antes del traspaso. |
| media | Publications/* | calidad_advertencia | 1 work_ids huérfanos en concepts | Documentar causa, aceptar explicitamente o corregir antes del traspaso. |
| media | Data/Gobernanza/entity_links.csv | calidad_advertencia | 3 enlaces con target_id sin registro canónico (ej: ['puc mg', 'universidad veracruzana', 'universidad san francisco de quito']) | Documentar causa, aceptar explicitamente o corregir antes del traspaso. |

## Criterio de traspaso a consultora

- El equipo interno mantiene la extraccion, limpieza cientifica y validacion experta.
- La consultora debe integrar, desplegar, automatizar, asegurar y monitorear los pipelines priorizados.
- Las fuentes de pago, restringidas o con token comercial quedan documentadas y no bloquean la adjudicacion.
- Ninguna fuente nueva debe activarse si no puede limitarse a CCHEN o a semillas institucionales verificadas.
