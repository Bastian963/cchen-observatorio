# Brief de fuente implementada: DataCite

**Source key:** `datacite_outputs`  
**Categoria:** Científica  
**Madurez:** Implementada OK  
**Tipo:** Implementada directa/API  
**Decision operativa:** `mantener`

![Resumen de fuente](../assets/datacite_outputs_resumen.png)

## Ficha rapida para Fernanda

- **Tipo de datos descargados:** CSV de outputs/datasets con DOI vinculados a CCHEN, ORCID/ROR o metadatos institucionales.
- **Tipologia de datos:** Datasets, DOIs y outputs de investigacion
- **Uso posible en el observatorio:** Identificar datasets y outputs con DOI vinculados a CCHEN, ORCID o ROR.
- **Frecuencia de descarga:** semestral
- **Estado:** Implementada y usable con control de calidad/frescura.
- **Decision operativa:** `mantener`

## Comentario para Excel

Implementada para extraccion CCHEN-only; Identificar datasets y outputs con DOI vinculados a CCHEN, ORCID o ROR; mantener frecuencia semestral.

## Que datos ofrece la fuente

DOIs de datasets

## Que extraemos para CCHEN

Se guardan artefactos locales trazables: Data/ResearchOutputs/cchen_datacite_outputs.csv, Data/ResearchOutputs/datacite_state.json.

## Como se filtra CCHEN-only

ORCID/ROR/DOI CCHEN y metadatos de outputs institucionales.

## Potencial para el observatorio

Identificar datasets y outputs con DOI vinculados a CCHEN, ORCID o ROR.

## Debilidades y riesgos

Riesgo principal: falsos positivos si se relaja el filtro CCHEN-only o si se consume sin curaduria.

## Frecuencia recomendada

semestral

## Estado operativo

Estado catalogo: implementada_runtime. Ultima corrida: seeded_from_outputs; ultima actualizacion: 2026-03-22.

## Evidencia disponible

Conteo registrado: 12. Calidad: 1.0. Outputs: Data/ResearchOutputs/cchen_datacite_outputs.csv; Data/ResearchOutputs/datacite_state.json.

## Decision

Mantener como fuente implementada del observatorio y exigir evidencia de refresco segun frecuencia declarada.

## URLs

- Sitio: https://datacite.org
- API: https://support.datacite.org/docs/api
