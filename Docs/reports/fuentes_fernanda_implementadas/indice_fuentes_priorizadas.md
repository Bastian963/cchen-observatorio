# Indice de fuentes implementadas Fernanda/CCHEN

Fecha: 2026-05-19

Total fuentes implementadas documentadas: 22.

## Resumen

| Grupo | Fuentes |
| --- | ---: |
| Bloqueada por token | 1 |
| Implementada OK | 20 |
| Revisar match runtime | 1 |

## Tipo de implementacion

| Tipo | Fuentes |
| --- | ---: |
| Implementada directa/API | 12 |
| Implementada derivada/semilla | 6 |
| Implementada runtime/local | 2 |
| Bloqueada por token | 1 |
| Revisar match runtime | 1 |

## Decision operativa

| Decision | Fuentes |
| --- | ---: |
| `mantener` | 14 |
| `mantener_con_observacion` | 6 |
| `bloqueada_por_token` | 1 |
| `revisar_match` | 1 |

## Categorias

| Categoria | Fuentes |
| --- | ---: |
| Científica | 12 |
| Life Sciences | 4 |
| Bio/Farma | 2 |
| Patentes | 1 |
| Datos Abiertos | 1 |
| Nuclear | 1 |
| Reportes financieros | 1 |

## Fuentes

| Fuente | Tipologia de datos | Uso observatorio | Tipo | Decision | Frecuencia | Estado | Brief |
| --- | --- | --- | --- | --- | --- | --- | --- |
| arXiv | Preprints, metadatos bibliograficos y vigilancia temprana | Vigilar preprints y produccion temprana en física y areas afines CCHEN. | Implementada directa/API | `mantener` | semanal (otros outputs: semestral) | Implementada y usable con control de calidad/frescura. | [briefs/brief_arxiv.md](briefs/brief_arxiv.md) |
| Crossref | Metadatos DOI, referencias, abstracts y funding | Enriquecer DOI CCHEN con metadatos bibliograficos, referencias, abstracts y funding. | Implementada directa/API | `mantener` | trimestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_crossref.md](briefs/brief_crossref.md) |
| DataCite | Datasets, DOIs y outputs de investigacion | Identificar datasets y outputs con DOI vinculados a CCHEN, ORCID o ROR. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_datacite_outputs.md](briefs/brief_datacite_outputs.md) |
| Europe PMC | Publicaciones biomédicas y metadatos Europe PMC | Complementar publicaciones biomédicas y de radiofarmacia con metadatos Europe PMC. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_europmc_works.md](briefs/brief_europmc_works.md) |
| INSPIRE | Publicaciones/preprints de fisica e informacion académica especializada | Cubrir fisica, plasma, altas energias y areas afines donde CCHEN tiene produccion. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_inspire_works.md](briefs/brief_inspire_works.md) |
| OpenAIRE | Outputs académicos, repositorios y relaciones ORCID/DOI | Consolidar outputs academicos europeos y repositorios vinculados a ORCID/DOI CCHEN. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_openaire_outputs.md](briefs/brief_openaire_outputs.md) |
| ORCID | Perfiles de investigadores, afiliaciones e identificadores | Mantener perfiles de investigadores CCHEN, afiliaciones, identificadores y obras declaradas. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_orcid.md](briefs/brief_orcid.md) |
| PubMed | Publicaciones biomédicas, medicina nuclear y radiofarmacia | Capturar publicaciones biomédicas, medicina nuclear y radiofarmacia con señal CCHEN. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_pubmed_works.md](briefs/brief_pubmed_works.md) |
| Semantic Scholar | Metadatos académicos, autores, citas y relaciones semanticas | Complementar citas, autores y metadatos semanticos de publicaciones CCHEN. | Implementada directa/API | `mantener` | trimestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_semantic_scholar.md](briefs/brief_semantic_scholar.md) |
| Unpaywall | Estado de acceso abierto por DOI | Determinar disponibilidad open access de DOI CCHEN. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_unpaywall_oa.md](briefs/brief_unpaywall_oa.md) |
| Zenodo | Metadatos de datasets, presentaciones y archivos asociados | Inventariar metadatos de datasets, presentaciones y outputs CCHEN en Zenodo sin descargar archivos. | Implementada directa/API | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_zenodo_outputs.md](briefs/brief_zenodo_outputs.md) |
| PatentsView / USPTO | Patentes USPTO, solicitantes e inventores | Serviria para propiedad industrial internacional cuando exista API key; por ahora queda como brecha documentada. | Bloqueada por token | `bloqueada_por_token` | semestral | Registrada, pero bloqueada hasta configurar credencial/API key. | [briefs/brief_patentsview_uspto.md](briefs/brief_patentsview_uspto.md) |
| PubChem | Radiofarmacos, radionuclidos, compuestos PubChem y literatura técnica | Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original. | Implementada derivada/semilla | `mantener_con_observacion` | trimestral | Implementada como derivada/semilla; requiere nota metodologica al usarla. | [briefs/brief_radiofarmacia_cchen_seeded.md](briefs/brief_radiofarmacia_cchen_seeded.md) |
| ClinVar | Variantes clínicas relacionadas por flujos biomédicos derivados | Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original. | Implementada derivada/semilla | `mantener_con_observacion` | semestral (otros outputs: trimestral) | Implementada como derivada/semilla; requiere nota metodologica al usarla. | [briefs/brief_clinvar.md](briefs/brief_clinvar.md) |
| OpenAlex | Publicaciones, autores, conceptos, afiliaciones y citas | Base principal de publicaciones, autores, conceptos y relaciones bibliométricas CCHEN. | Implementada directa/API | `mantener` | trimestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_openalex.md](briefs/brief_openalex.md) |
| Datos.gob.cl | Convenios, acuerdos e informacion institucional publica | Datos publicos nacionales vinculados a convenios, acuerdos e informacion institucional CCHEN. | Implementada runtime/local | `mantener` | semestral | Implementada y usable con control de calidad/frescura. | [briefs/brief_datos_gob_cl.md](briefs/brief_datos_gob_cl.md) |
| GenBank | Secuencias genéticas relacionadas por flujos biomédicos derivados | Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original. | Implementada derivada/semilla | `mantener_con_observacion` | semestral (otros outputs: trimestral) | Implementada como derivada/semilla; requiere nota metodologica al usarla. | [briefs/brief_genbank.md](briefs/brief_genbank.md) |
| Gene Expression Omnibus (GEO) | Datos de expresion génica relacionados por flujos derivados | Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original. | Implementada derivada/semilla | `mantener_con_observacion` | semestral (otros outputs: trimestral) | Implementada como derivada/semilla; requiere nota metodologica al usarla. | [briefs/brief_gene_expression_omnibus_geo.md](briefs/brief_gene_expression_omnibus_geo.md) |
| NIH | Investigacion biomédica relacionada por flujos derivados | Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original. | Implementada derivada/semilla | `mantener_con_observacion` | semestral (otros outputs: trimestral) | Implementada como derivada/semilla; requiere nota metodologica al usarla. | [briefs/brief_nih.md](briefs/brief_nih.md) |
| Sequence Read Archive | Datos genómicos relacionados por flujos derivados | Sirve como evidencia temática o vigilancia exploratoria; no como indicador directo de la fuente original. | Implementada derivada/semilla | `mantener_con_observacion` | semestral (otros outputs: trimestral) | Implementada como derivada/semilla; requiere nota metodologica al usarla. | [briefs/brief_sequence_read_archive.md](briefs/brief_sequence_read_archive.md) |
| IAEA (INIS) | Registros de informacion nuclear y vigilancia técnica | Vigilancia especializada de INIS/IAEA para informacion nuclear relevante a CCHEN. | Implementada runtime/local | `mantener` | semanal | Implementada y usable con control de calidad/frescura. | [briefs/brief_iaea_inis_monitor.md](briefs/brief_iaea_inis_monitor.md) |
| Google Finance / News monitor (revisar match) | Noticias y monitoreo de prensa CCHEN/nuclear; match financiero en revision | Solo serviria para vigilancia de noticias si se reclasifica; no usar como fuente financiera sin confirmacion. | Revisar match runtime | `revisar_match` | semanal | Requiere confirmacion de correspondencia entre planilla y runtime. | [briefs/brief_news_monitor.md](briefs/brief_news_monitor.md) |
