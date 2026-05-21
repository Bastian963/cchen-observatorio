# Metodologia: indice maestro de evidencia semantica CCHEN

Fecha: 2026-05-21

## Objetivo

Convertir las extracciones CCHEN en una base unica de evidencia para la Plataforma interna para gestion de investigacion e innovacion. El indice no descarga universos completos: normaliza registros ya filtrados, curados o relacionados con CCHEN.

## Archivos generados

| Archivo | Uso |
|---|---|
| `Data/Semantic/evidence_index.csv` | Tabla maestra con publicaciones, outputs, proyectos, oportunidades, patentes, convenios, radiofarmacia y datos internos. |
| `Data/Semantic/evidence_embeddings.npy` | Vectores para busqueda por significado. |
| `Data/Semantic/evidence_embeddings_meta.csv` | Metadatos alineados con los vectores. |
| `Data/Semantic/evidence_embedding_pipeline.joblib` | Pipeline TF-IDF + SVD de respaldo, usado solo si no esta disponible `sentence-transformers`. |
| `Data/Semantic/evidence_index_summary.csv` | Conteos por tipo de evidencia y fuente. |
| `Data/Semantic/evidence_index_state.json` | Estado de generacion, backend de vectores y rutas de salida. |
| `Docs/reports/evidence_topics/` | Fichas Markdown por tema estrategico generadas desde el indice. |
| `Docs/reports/prompt_asistente_evidencia_cchen.md` | Prompt maestro para usar la evidencia recuperada con Groq/LLM. |

## Esquema normalizado

Campos principales:

`id`, `titulo`, `resumen`, `tipo_evidencia`, `fuente`, `url`, `fecha`, `autores`, `relacion_cchen`, `tema`, `uso_observatorio`, `brecha`, `nivel_confianza`, `identificador`, `source_path`, `texto_embedding`, `fetched_at`.

## Fuentes incorporadas en la primera version

- Publicaciones: OpenAlex, PubMed, Europe PMC, INSPIRE, arXiv, Semantic Scholar, CrossRef, Unpaywall y DIAN.
- Outputs y repositorios: DataCite, OpenAIRE, Zenodo, DOAJ/HAL/CORE/Figshare desde la tabla maestra curada.
- Radiofarmacia: literatura revisada y compuestos curados.
- Proyectos y oportunidades: ANID, convocatorias curadas y matching institucional.
- Patentes: INAPI local.
- Redes institucionales: convenios nacionales y acuerdos internacionales.
- Transferencia: evidencia semilla asociada a activos del portafolio.

## Comandos reproducibles

Construir indice y vectores:

```bash
python Scripts/build_evidence_index.py --embedding-mode auto
```

Ejecutarlo desde el runner canonico:

```bash
python Scripts/run_source_refresh.py --source-key semantic_evidence_index --force
```

Buscar evidencia:

```bash
python Scripts/evidence_search.py "radiofarmacia con potencial de transferencia" --top 10
python Scripts/evidence_search.py "capacidades CCHEN en medicina nuclear" --top 10
python Scripts/evidence_search.py "outputs o datasets asociados a CCHEN" --top 10
```

Evaluar consultas fijas de control:

```bash
python Scripts/check_evidence_index.py
python Scripts/evaluate_evidence_search.py --top-k 8
```

Generar fichas por tema:

```bash
python Scripts/generate_evidence_topic_briefs.py --top-k 12
```

## Uso de LLM

El LLM debe recibir solo evidencia recuperada desde el indice. Su rol es sintetizar y ordenar hallazgos, no decidir transferencia tecnologica ni inventar informacion.

Cada respuesta debe indicar fuente, tipo de evidencia, relacion con CCHEN, posible uso, brecha y nivel de confianza.

## Restricciones metodologicas

- No afirmar que una tecnologia esta lista para transferirse sin validacion tecnica, legal y comercial.
- Separar evidencia directa CCHEN de vigilancia tematica o registros secundarios.
- Mantener las brechas visibles.
- Registrar fuente y fecha de extraccion.
- Actualizar el indice despues de cada refresh relevante de fuentes.
- Para despliegues en Streamlit Cloud, no subir datos internos sin sanitizacion. El indice puede regenerarse en el entorno privado, cargarse como artefacto sanitizado o moverse a una base privada.

## Estado operativo inicial

La primera corrida produjo 5.072 registros normalizados:

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

El backend de vectores usado en la corrida vigente fue `sentence-transformers` con el modelo `paraphrase-multilingual-MiniLM-L12-v2`, ejecutado desde el entorno `.venv` del repositorio CCHEN. El fallback `tfidf-svd` queda disponible para entornos mínimos, pero no es el backend recomendado.
