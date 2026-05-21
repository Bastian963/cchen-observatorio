# Paquete Consultora: Fuentes, Evidencia Y Streamlit Cloud CCHEN

Fecha: 2026-05-21

## Resumen Ejecutivo

Este paquete deja ordenada una primera capa publicable para auditoria tecnica, continuidad con la consultora y despliegue en Streamlit Cloud. El foco no es agregar mas APIs por volumen, sino dejar trazables las fuentes ya trabajadas y conectarlas con una capa de evidencia usable por el dashboard interno.

Entregables incluidos:

- catalogo de fuentes y priorizacion pre-adjudicacion;
- curaduria de APIs abiertas sugeridas en la matriz de trabajo;
- outputs de repositorios abiertos asociados a CCHEN;
- revision tematica de radiofarmacia;
- indice de evidencia publicable para Streamlit Cloud;
- scripts reproducibles de extraccion, curaduria, evaluacion y busqueda semantica.

## Inventario Versionado

| Capa | Archivo principal | Registros | Uso |
|---|---:|---:|---|
| Catalogo de fuentes | `Data/Gobernanza/catalogo_fuentes_pre_adjudicacion.csv` | 256 | Inventario maestro de fuentes, APIs, frecuencia, token, comandos y brechas. |
| Priorizacion | `Data/Gobernanza/priorizacion_fuentes_api_pre_adjudicacion.csv` | 54 | Fuentes recomendadas para primera ola de mantencion. |
| APIs abiertas Fernanda | `Data/Gobernanza/fuentes_fernanda_api_cchen_records.csv` | 52 | Resultados DOAJ, HAL, CORE y Figshare filtrados por CCHEN. |
| Outputs repositorios | `Data/Gobernanza/outputs_repositorios_cchen_master.csv` | 66 | Outputs integrados desde Zenodo, DOAJ, HAL y CORE. |
| Radiofarmacia revisada | `Data/Gobernanza/radiofarmacia_cchen_literature_reviewed.csv` | 251 | Senales tematicas para revision experta en radiofarmacia/medicina nuclear. |
| Compuestos radiofarmacia | `Data/Gobernanza/radiofarmacia_cchen_compounds_curated.csv` | 11 | Semillas tecnicas PubChem para priorizacion tematica. |
| Evidencia publicable | `Data/Gobernanza/evidence_index_publicable.csv` | 5.072 | Base liviana usada por Streamlit Cloud cuando no existen embeddings locales. |

## Fuentes Implementadas Y Uso Operativo

Las fuentes quedan registradas en `Scripts/source_refresh_registry.py`. Cada entrada documenta `source_key`, URL, frecuencia recomendada, SLA de frescura, token requerido, comando de actualizacion, outputs y brecha.

Familias cubiertas:

- publicaciones: OpenAlex, CrossRef, PubMed, Europe PMC, Semantic Scholar, INSPIRE, arXiv;
- outputs y repositorios: OpenAIRE, DataCite, Zenodo, DOAJ, HAL, CORE;
- propiedad intelectual: INAPI local y PatentsView/USPTO con `PATENTSVIEW_API_KEY`;
- proyectos y oportunidades: ANID, matching institucional, convocatorias;
- datos institucionales: DIAN, convenios, acuerdos, capital humano;
- radiofarmacia: semillas tematicas, literatura Europe PMC/PubMed y compuestos PubChem.

## Streamlit Cloud

Configuracion esperada:

- repo: `Bastian963/cchen-observatorio`;
- rama estable: `main`;
- entrypoint: `Dashboard/app.py`;
- runtime: `runtime.txt` con Python 3.11;
- dependencias: `requirements.txt` raiz.

Secrets minimos:

```toml
GROQ_API_KEY = "gsk_..."

[supabase]
url = "https://xxxx.supabase.co"
anon_key = "eyJ..."
data_source = "auto"

[internal_auth]
enabled = true
```

La busqueda de evidencia funciona en tres niveles:

1. embeddings locales en `Data/Semantic/` si existen;
2. indice publicable `Data/Gobernanza/evidence_index_publicable.csv` con embeddings en memoria si `sentence-transformers` esta disponible;
3. fallback lexical con reranking si no hay backend semantico disponible.

## Criterios De Cuidado

- El LLM no decide transferencia tecnologica ni propiedad intelectual.
- Las respuestas deben citar fuente, tipo de evidencia, relacion con CCHEN, uso posible, brecha y nivel de confianza.
- Las patentes requieren validacion legal y vigencia antes de uso formal.
- Radiofarmacia queda como evidencia tematica para revision experta, no como declaracion de capacidad operacional.
- Los artefactos pesados `Data/Semantic/*.npy` y `.joblib` no se versionan en GitHub.

## Validacion Recomendada

```bash
python -m py_compile Scripts/build_evidence_index.py Scripts/evidence_search.py Scripts/evaluate_evidence_search.py Dashboard/sections/asistente_id.py Dashboard/sections/transferencia_portafolio.py
python Scripts/check_evidence_index.py
python Scripts/evaluate_evidence_search.py --top-k 8
python Scripts/run_source_refresh.py --source-key semantic_evidence_index --dry-run
python Scripts/check_dashboard_smoke.py
python Scripts/check_dashboard_e2e.py
```

Consultas funcionales minimas:

- radiofarmacia con potencial de transferencia;
- capacidades CCHEN en medicina nuclear;
- outputs o datasets asociados a CCHEN;
- patentes y propiedad intelectual CCHEN;
- convenios o colaboraciones institucionales nucleares;
- convocatorias y oportunidades para investigacion CCHEN.
