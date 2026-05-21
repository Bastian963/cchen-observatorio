# Metodologia de revision operativa - Radiofarmacia CCHEN

Fecha: 2026-05-19

## Objetivo

Cerrar la capa `revisar_manual` de radiofarmacia con reglas replicables. Esta revision no reemplaza la validacion experta CCHEN, pero evita publicar ruido clinico, biomédico o de conferencias en el tablero principal.

## Insumos y salidas

- Insumo: `Data/Gobernanza/radiofarmacia_cchen_literature_curated.csv`.
- Salida revisada: `Data/Gobernanza/radiofarmacia_cchen_literature_reviewed.csv`.
- Resumen: `Data/Gobernanza/radiofarmacia_cchen_review_summary.csv`.

## Criterios

- `publicar_recurrente`: sale de la curaduria base como CCHEN/Chile/LatAm util o tema prioritario.
- `mantener_vigilancia`: registro global con senal tecnica o clinica de radiofarmacia/medicina nuclear.
- `mantener_baja_prioridad`: contexto regulatorio, clinico o regional sin senal radiofarmaceutica suficiente.
- `descartar_ruido`: conferencia generica, biomedicina no radiofarmaceutica, fisica no aplicable, registro sin titulo o metadata insuficiente.

## Resultados

### Por decision final

| Grupo | Registros |
| --- | ---: |
| descartar_ruido | 71 |
| mantener_baja_prioridad | 17 |
| mantener_vigilancia | 132 |
| publicar_recurrente | 31 |

### Por alcance de publicacion

| Grupo | Registros |
| --- | ---: |
| auditoria_no_tablero_principal | 17 |
| no_publicar | 71 |
| tablero_principal | 31 |
| vigilancia | 132 |

### Solo registros que venian como revisar_manual

| Grupo | Registros |
| --- | ---: |
| descartar_ruido | 54 |
| mantener_baja_prioridad | 17 |
| mantener_vigilancia | 19 |

## Uso operativo

Para tablero principal usar `publish_scope=tablero_principal`. Para vigilancia usar `publish_scope=vigilancia`. `auditoria_no_tablero_principal` y `no_publicar` no deben alimentar vistas públicas sin revisión experta.
