# Metodologia - Tabla maestra de outputs CCHEN en repositorios

Fecha: 2026-05-19

## Objetivo

Unificar Zenodo, DOAJ, HAL y CORE en una tabla maestra auditable. La tabla conserva descartes y baja prioridad para trazabilidad, pero separa claramente que puede alimentar el tablero.

## Insumos

- `Data/ResearchOutputs/cchen_zenodo_metadata.csv`
- `Data/Gobernanza/curaduria_zenodo_cchen.csv`
- `Data/Gobernanza/revision_fuentes_fernanda_api_cchen.csv`

## Salidas

- `Data/Gobernanza/outputs_repositorios_cchen_master.csv`: tabla completa con auditoria.
- `Data/Gobernanza/outputs_repositorios_cchen_publicables.csv`: registros para tablero o vigilancia.
- `Data/Gobernanza/outputs_repositorios_cchen_summary.csv`: conteos de control.
- `Docs/reports/metodologia_outputs_repositorios_cchen.md`: metodologia replicable.

## Reglas de uso

- `publish_scope=tablero_principal`: puede alimentar vistas principales del observatorio.
- `publish_scope=vigilancia`: se conserva para seguimiento y benchmark.
- `publish_scope=auditoria_no_tablero_principal`: no se publica sin validacion experta.
- `publish_scope=no_publicar`: descarte trazable.
- `preferred_record=True`: fila preferida cuando hay DOI/URL repetido entre repositorios.

## Resultados

- Registros totales: 66.
- Registros publicables/vigilancia: 48.

### Por fuente

| Grupo | Registros |
| --- | ---: |
| core | 16 |
| doaj | 25 |
| hal | 11 |
| zenodo | 14 |

### Por decision

| Grupo | Registros |
| --- | ---: |
| descartar_ruido | 10 |
| mantener_baja_prioridad | 7 |
| mantener_indirecto | 1 |
| publicar_recurrente | 48 |

### Por alcance

| Grupo | Registros |
| --- | ---: |
| auditoria_no_tablero_principal | 8 |
| no_publicar | 10 |
| tablero_principal | 48 |

### Preferidos vs duplicados

| Grupo | Registros |
| --- | ---: |
| False | 2 |
| True | 64 |

## Procedimiento replicable

1. Refrescar `zenodo_outputs` y `fernanda_free_api_candidates` con el runner canonico.
2. Ejecutar `python Scripts/run_source_refresh.py --source-key repositorios_cchen_outputs_master --force`.
3. Consumir `outputs_repositorios_cchen_publicables.csv` para tablero/vigilancia.
4. Mantener `outputs_repositorios_cchen_master.csv` como evidencia completa para auditoria y consultora.
