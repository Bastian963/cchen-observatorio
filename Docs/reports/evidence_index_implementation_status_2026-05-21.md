# Estado de implementacion: indice de evidencia CCHEN

Fecha: 2026-05-21

## Resultado

Se implemento la primera version operativa de la capa de evidencia para la Plataforma interna para gestion de investigacion e innovacion CCHEN.

El objetivo fue conectar tres piezas que antes estaban separadas:

1. extraccion de datos CCHEN;
2. busqueda por significado mediante vectores;
3. uso del LLM como asistente de sintesis con fuentes.

## Archivos principales

| Componente | Archivo |
|---|---|
| Constructor del indice | `Scripts/build_evidence_index.py` |
| Buscador reutilizable | `Scripts/evidence_search.py` |
| Evaluacion de consultas | `Scripts/evaluate_evidence_search.py` |
| Chequeo de contrato | `Scripts/check_evidence_index.py` |
| Fichas por tema | `Scripts/generate_evidence_topic_briefs.py` |
| Vista Streamlit | `Dashboard/sections/transferencia_portafolio.py` |
| Contexto LLM | `Dashboard/sections/asistente_id.py` |
| Metodologia | `Docs/reports/metodologia_indice_evidencia_semantica_cchen.md` |

## Datos generados

| Archivo | Estado |
|---|---|
| `Data/Semantic/evidence_index.csv` | Generado |
| `Data/Semantic/evidence_embeddings.npy` | Generado |
| `Data/Semantic/evidence_embeddings_meta.csv` | Generado |
| `Data/Semantic/evidence_embedding_pipeline.joblib` | Generado |
| `Data/Semantic/evidence_index_summary.csv` | Generado |
| `Data/Semantic/evidence_index_state.json` | Generado |
| `Docs/reports/evidence_topics/` | Generado |

## Cobertura inicial

| Tipo de evidencia | Registros |
|---|---:|
| Publicacion | 2.780 |
| Dataset/output | 963 |
| Acceso abierto | 780 |
| Senal tematica | 168 |
| Convenio | 145 |
| Registro interno | 133 |
| Oportunidad | 56 |
| Proyecto | 33 |
| Compuesto | 7 |
| Patente | 7 |

Total: 5.072 registros.

## Validacion ejecutada

Comandos ejecutados:

```bash
.venv/bin/python Scripts/build_evidence_index.py --embedding-mode auto
.venv/bin/python Scripts/evaluate_evidence_search.py --top-k 8
.venv/bin/python Scripts/check_evidence_index.py
.venv/bin/python Scripts/generate_evidence_topic_briefs.py --top-k 12
.venv/bin/python Scripts/run_source_refresh.py --source-key semantic_evidence_index --dry-run
.venv/bin/python -m py_compile Scripts/build_evidence_index.py Scripts/evidence_search.py Scripts/evaluate_evidence_search.py Dashboard/sections/asistente_id.py Dashboard/sections/transferencia_portafolio.py
```

Resultado de evaluacion:

| Consulta | Estado |
|---|---|
| Radiofarmacia con potencial de transferencia | OK |
| Capacidades CCHEN en medicina nuclear | OK |
| Outputs o datasets asociados a CCHEN | OK |
| Patentes y propiedad intelectual CCHEN | OK |
| Convenios o colaboraciones institucionales nucleares | OK |
| Convocatorias y oportunidades para investigacion CCHEN | OK |

## Estado del entorno

- El entorno correcto es `.venv` dentro del repositorio CCHEN.
- `.venv` tiene Streamlit 1.57.0, scikit-learn, joblib y `sentence-transformers`.
- El indice vigente fue regenerado con `sentence-transformers` y modelo `paraphrase-multilingual-MiniLM-L12-v2`.
- La app Streamlit fue levantada correctamente en `http://127.0.0.1:8501`.
- El chequeo E2E del dashboard completo paso correctamente, incluyendo `Transferencia y Portafolio` y `Asistente I+D`.
- `pytest` no esta instalado en `.venv`; las pruebas unitarias quedan pendientes hasta instalar esa dependencia de desarrollo.
- La capa de patentes sigue limitada por INAPI local y por PatentsView pendiente de API key.

## Nota para Streamlit Cloud / GitHub

Los artefactos `Data/Semantic/*` quedan excluidos de GitHub por contener datos internos y derivados de fuentes CCHEN. Por tanto, el despliegue en Streamlit Cloud debe usar una de estas rutas antes de activar el buscador semantico en produccion:

1. subir un artefacto sanitizado y versionable del indice;
2. regenerar `Data/Semantic/*` dentro del entorno de despliegue con datos ya provisionados;
3. mover el indice a una base privada, por ejemplo Supabase/pgvector, y configurar la app para leer desde ahi.

El codigo del dashboard ya queda preparado para usar los artefactos locales cuando existan; si no existen, muestra una advertencia operativa en vez de fallar.

## Siguiente mejora recomendada

La siguiente iteracion deberia agregar exportacion PDF de las fichas por tema y, si corresponde, pasar el indice de evidencia a Supabase/pgvector para uso multiusuario.
