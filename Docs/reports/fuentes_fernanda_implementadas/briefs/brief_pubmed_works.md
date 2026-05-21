# Brief de fuente implementada: PubMed

**Source key:** `pubmed_works`  
**Categoria:** Científica  
**Madurez:** Implementada OK  
**Tipo:** Implementada directa/API  
**Decision operativa:** `mantener`

![Resumen de fuente](../assets/pubmed_works_resumen.png)

## Ficha rapida para Fernanda

- **Tipo de datos descargados:** CSV de publicaciones PubMed con señal CCHEN en DOI, autor, afiliacion o tema relevante.
- **Tipologia de datos:** Publicaciones biomédicas, medicina nuclear y radiofarmacia
- **Uso posible en el observatorio:** Capturar publicaciones biomédicas, medicina nuclear y radiofarmacia con señal CCHEN.
- **Frecuencia de descarga:** semestral
- **Estado:** Implementada y usable con control de calidad/frescura.
- **Decision operativa:** `mantener`

## Comentario para Excel

Implementada para extraccion CCHEN-only; Capturar publicaciones biomédicas, medicina nuclear y radiofarmacia con señal CCHEN; mantener frecuencia semestral.

## Que datos ofrece la fuente

Biomedicina

## Que extraemos para CCHEN

Se guardan artefactos locales trazables: Data/Publications/cchen_pubmed_works.csv, Data/Publications/pubmed_state.json.

## Como se filtra CCHEN-only

Aliases CCHEN, autores/afiliaciones o DOI ya conocidos; revisar falsos positivos.

## Potencial para el observatorio

Capturar publicaciones biomédicas, medicina nuclear y radiofarmacia con señal CCHEN.

## Debilidades y riesgos

Riesgo principal: falsos positivos si se relaja el filtro CCHEN-only o si se consume sin curaduria.

## Frecuencia recomendada

semestral

## Estado operativo

Estado catalogo: implementada_runtime. Ultima corrida: seeded_from_outputs; ultima actualizacion: 2026-05-11.

## Evidencia disponible

Conteo registrado: 20. Calidad: 1.0. Outputs: Data/Publications/cchen_pubmed_works.csv; Data/Publications/pubmed_state.json.

## Decision

Mantener como fuente implementada del observatorio y exigir evidencia de refresco segun frecuencia declarada.

## URLs

- Sitio: https://pubmed.ncbi.nlm.nih.gov
- API: https://www.ncbi.nlm.nih.gov/home/develop/api/
