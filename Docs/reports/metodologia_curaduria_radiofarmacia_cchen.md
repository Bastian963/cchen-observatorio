# Metodologia replicable - Curaduria Radiofarmacia CCHEN

Fecha: 2026-05-19

## Objetivo

Separar datos utiles de ruido en la extraccion semilla de radiofarmacia CCHEN. La metodologia evita descargar Bio/Farma completo y usa semillas controladas mas reglas trazables de curaduria.

## Insumos

- `Data/Gobernanza/radiofarmacia_cchen_seeds.csv`: lista de semillas aprobadas.
- `Data/Gobernanza/radiofarmacia_cchen_pubchem_compounds.csv`: fichas PubChem por compuesto/radionuclido semilla.
- `Data/Gobernanza/radiofarmacia_cchen_literature.csv`: literatura desde Europe PMC y PubMed.

## Salidas

- `Data/Gobernanza/radiofarmacia_cchen_literature_curated.csv`
- `Data/Gobernanza/radiofarmacia_cchen_compounds_curated.csv`
- `Data/Gobernanza/radiofarmacia_cchen_curation_summary.csv`

## Reglas de clasificacion

1. `cchen_directo`: el registro menciona CCHEN, Comision Chilena de Energia Nuclear o Chilean Nuclear Energy Commission.
2. `chile_latam_util`: no menciona CCHEN, pero contiene Chile/Chilean/Latin America u otro termino regional latinoamericano.
3. `vigilancia_global_util`: no tiene foco geografico, pero trata produccion/ciclotron/control de calidad/dosimetria/radiofarmacos/teranosticos priorizados.
4. `ruido_probable`: paper clinico generico sin vinculo CCHEN/Chile/LatAm ni senal tecnica prioritaria.
5. `revisar_manual`: registro ambiguo que no debe promoverse automaticamente.

## Tipos de informacion

- `ficha_compuesto_radionuclido`: PubChem para compuestos definidos por semilla.
- `produccion_ciclotron_control_calidad`: produccion, sintesis, GMP, rendimiento radioquimico, control de calidad.
- `dosimetria_seguridad_radiologica`: dosimetria, biodistribucion, proteccion radiologica, exposicion ocupacional.
- `radiofarmaco_teranostico_compuesto`: DOTATATE, Lu-177, Ga-68, Tc-99m, I-131, radiotracers, theranostics.
- `paper_clinico_pet_spect`: uso clinico PET/SPECT/FDG sin otra senal tecnica.

## Decisiones

- `mantener_recurrente`: ingresa al flujo regular del observatorio.
- `mantener_vigilancia`: se conserva con cupo limitado para tendencias o benchmark.
- `revisar_manual`: requiere validacion experta antes de publicarse.
- `descartar_ruido`: excluir del tablero principal; conservar solo como auditoria.

## Resultados literatura

### Por relacion CCHEN

| Grupo | Registros |
| --- | ---: |
| chile_latam_util | 31 |
| revisar_manual | 90 |
| ruido_probable | 17 |
| vigilancia_global_util | 113 |

### Por decision

| Grupo | Registros |
| --- | ---: |
| descartar_ruido | 17 |
| mantener_recurrente | 31 |
| mantener_vigilancia | 113 |
| revisar_manual | 90 |

### Por tipo de informacion

| Grupo | Registros |
| --- | ---: |
| dosimetria_seguridad_radiologica | 34 |
| otro_revisar | 75 |
| paper_clinico_pet_spect | 38 |
| produccion_ciclotron_control_calidad | 29 |
| radiofarmaco_teranostico_compuesto | 75 |

### Por semilla

| Grupo | Registros |
| --- | ---: |
| ciclotron_f18 | 39 |
| control_calidad_radiofarmacos | 31 |
| dosimetria_medicina_nuclear | 26 |
| f18_fdg | 39 |
| ga68_dotatate | 21 |
| i131 | 40 |
| lu177_dotatate | 16 |
| tc99m_sestamibi | 39 |

## Resultados compuestos

- Compuestos/radionuclidos curados: 11.
- Todos se clasifican como `mantener_recurrente` porque nacen de la lista semilla aprobada.

## Procedimiento operativo para la consultora

1. Ejecutar `python Scripts/fetch_radiofarmacia_cchen_seeded.py --max-literature-per-seed 20`.
2. Ejecutar `python Scripts/curate_radiofarmacia_cchen.py`.
3. Ejecutar `python Scripts/review_radiofarmacia_cchen.py` para cerrar la capa operativa de revision.
4. Publicar solo `publish_scope=tablero_principal`; usar `publish_scope=vigilancia` para tendencias y benchmark.
5. No ampliar semillas ni fuentes sin registrar justificacion, filtro, fecha, conteo y evidencia de ruido.
6. Si una semilla produce demasiado `descartar_ruido`, ajustar `scope_terms` en `radiofarmacia_cchen_seeds.csv` antes de la siguiente corrida.

## Control de cambios

Toda modificacion de reglas o semillas debe quedar versionada y documentada en este archivo o en el runbook operativo.
