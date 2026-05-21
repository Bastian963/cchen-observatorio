# Metodologia de extraccion CCHEN desde fuentes de Fernanda

Fecha de corte: 2026-05-19

## Regla principal

El observatorio no descarga bases completas externas. Cada fuente se trabaja con alcance CCHEN-only:

- Alias institucionales: `CCHEN`, `Comision Chilena de Energia Nuclear`, `Comisión Chilena de Energía Nuclear`, `Chilean Nuclear Energy Commission`.
- Identificadores conocidos: DOI, ORCID, ROR, autores CCHEN o activos institucionales ya presentes en el observatorio.
- Semillas tematicas cuando no existe filtro institucional seguro, por ejemplo radiofarmacos, radionuclidos, ciclotron, control de calidad y dosimetria.

Si una fuente no permite filtrar por CCHEN o por una semilla justificada, no se descarga masivamente. Se documenta como diferida, candidata o de pago/acceso.

## Flujo replicable

1. Construir catalogo desde la matriz de Fernanda y runtime actual.

```bash
python Scripts/build_pre_adjudicacion_fuentes.py \
  --input "/media/bastin/Nuevo vol/Mumito/Descarga/Fuentes de información.xlsx" \
  --date 2026-05-19 \
  --run-preflight \
  --run-quality
```

2. Ver fuentes vencidas.

```bash
python Scripts/run_source_refresh.py --all-due --dry-run
```

3. Ejecutar fuentes CCHEN-only conectadas en esta etapa.

```bash
python Scripts/run_source_refresh.py --source-key zenodo_outputs --force
python Scripts/run_source_refresh.py --source-key fernanda_free_api_candidates --force
python Scripts/run_source_refresh.py --source-key repositorios_cchen_outputs_master --force
python Scripts/run_source_refresh.py --source-key radiofarmacia_cchen_seeded --force
```

4. Validar calidad.

```bash
python Database/data_quality.py
```

## Fuentes conectadas o curadas en esta pasada

### Zenodo

Estado: conectada como `zenodo_outputs`.

Politica: metadata-only. No descarga archivos binarios. Solo guarda inventario de metadatos y archivos asociados.

Salidas:

- `Data/ResearchOutputs/cchen_zenodo_metadata.csv`
- `Data/ResearchOutputs/cchen_zenodo_files.csv`
- `Data/ResearchOutputs/zenodo_cchen_state.json`
- `Data/Gobernanza/curaduria_zenodo_cchen.csv`

Resultado curado:

- 14 registros metadata CCHEN escritos.
- 39 archivos asociados inventariados, sin descarga.
- 5 `mantener_recurrente`.
- 1 `mantener_indirecto`: dataset asociado a publicacion con senal CCHEN, pero registro Zenodo con creador externo.
- 8 `descartar_ruido`: 7 falsos positivos donde `CCHEN` aparecia como correo/identificador externo y 1 registro sin relacion institucional.

Decision operativa: mantener como fuente recurrente semestral, con conteo institucional solo para registros con afiliacion CCHEN directa.

### DOAJ, HAL y CORE

Estado: conectadas como prueba controlada en `fernanda_free_api_candidates`.

Politica: se consultan solo aliases CCHEN. Los resultados pasan por curaduria automatica y revision manual reproducible.

Salidas:

- `Data/Gobernanza/fuentes_fernanda_api_cchen_records.csv`
- `Data/Gobernanza/fuentes_fernanda_api_cchen_status.csv`
- `Data/Gobernanza/curaduria_fuentes_fernanda_api_cchen.csv`
- `Data/Gobernanza/revision_fuentes_fernanda_api_cchen.csv`

Resultado revisado:

- 52 registros candidatos.
- 43 `mantener_recurrente`.
- 7 `mantener_baja_prioridad`.
- 2 `descartar_ruido`.

Detalle por fuente:

- CORE: 13 recurrentes, 1 baja prioridad, 2 descartes.
- DOAJ: 22 recurrentes, 3 baja prioridad.
- HAL: 8 recurrentes, 3 baja prioridad.

Decision operativa:

- CORE: mantener como fuente secundaria semestral, util para full text y verificacion cruzada.
- DOAJ: mantener como fuente secundaria semestral, util para cobertura open access.
- HAL: mantener como fuente suplementaria semestral; revisar baja prioridad antes de publicar.

Nota de calidad: se corrigio la regla de deteccion de `SPECT` para evitar falsos positivos dentro de palabras como `spectra`, `spectrometric` o `prospecto`.

### Tabla maestra Zenodo + DOAJ + HAL + CORE

Estado: integrada como fuente derivada `repositorios_cchen_outputs_master`.

Politica: no llama APIs externas. Toma los resultados ya extraidos y curados, normaliza campos comunes y separa que entra al tablero de lo que queda como auditoria o descarte.

Salidas:

- `Data/Gobernanza/outputs_repositorios_cchen_master.csv`
- `Data/Gobernanza/outputs_repositorios_cchen_publicables.csv`
- `Data/Gobernanza/outputs_repositorios_cchen_summary.csv`
- `Docs/reports/metodologia_outputs_repositorios_cchen.md`

Resultado:

- 66 registros totales.
- 48 registros para `tablero_principal`.
- 8 registros en `auditoria_no_tablero_principal`.
- 10 registros en `no_publicar`.
- 2 filas no preferidas por duplicado; la tabla conserva la evidencia y marca `preferred_record=True` en la fila principal.

Decision operativa: este es el insumo usable para el observatorio y para la consultora cuando se hable de outputs CCHEN en repositorios abiertos.

### Radiofarmacia CCHEN

Estado: conectada como `radiofarmacia_cchen_seeded`.

Politica: no descarga Bio/Farma completo. Usa semillas controladas CCHEN y fuentes abiertas:

- PubChem para fichas de compuestos/radionuclidos.
- Europe PMC y PubMed para literatura tecnica/clinica.

Semillas actuales:

- F-18 FDG / fludeoxyglucose.
- Ga-68 DOTATATE.
- Lu-177 DOTATATE.
- Tc-99m sestamibi.
- I-131.
- Ciclotron / produccion F-18.
- Control de calidad de radiofarmacos.
- Dosimetria en medicina nuclear.

Salidas:

- `Data/Gobernanza/radiofarmacia_cchen_seeds.csv`
- `Data/Gobernanza/radiofarmacia_cchen_pubchem_compounds.csv`
- `Data/Gobernanza/radiofarmacia_cchen_literature.csv`
- `Data/Gobernanza/radiofarmacia_cchen_literature_curated.csv`
- `Data/Gobernanza/radiofarmacia_cchen_compounds_curated.csv`
- `Data/Gobernanza/radiofarmacia_cchen_curation_summary.csv`
- `Data/Gobernanza/radiofarmacia_cchen_literature_reviewed.csv`
- `Data/Gobernanza/radiofarmacia_cchen_review_summary.csv`
- `Docs/reports/metodologia_curaduria_radiofarmacia_cchen.md`
- `Docs/reports/metodologia_revision_radiofarmacia_cchen.md`

Resultado:

- 8 semillas controladas.
- 11 compuestos/radionuclidos.
- 251 registros de literatura.
- Curaduria base: 31 `mantener_recurrente`, 113 `mantener_vigilancia`, 90 `revisar_manual`, 17 `descartar_ruido`.
- Revision operativa final: 31 `publicar_recurrente`, 132 `mantener_vigilancia`, 17 `mantener_baja_prioridad`, 71 `descartar_ruido`.
- Los 90 registros manuales quedaron cerrados: 19 a vigilancia, 17 a baja prioridad y 54 a descarte.

Decision operativa: mantener como fuente trimestral. Publicar en tablero principal solo `publish_scope=tablero_principal`; usar `publish_scope=vigilancia` para tendencias y benchmark; conservar baja prioridad y descartes como auditoria.

## Fuentes evaluadas pero no promovidas aun

- Figshare: API respondio, pero no devolvio resultados CCHEN en la prueba.
- UniProt: API respondio, pero requiere semillas tematicas; no usar como universo completo.
- BASE: bloqueo por IP/User-Agent en probe.
- bioRxiv/medRxiv: API no ofrece busqueda institucional/texto libre segura sin crawlear ventanas amplias.
- PubChem/STRING genericos: solo se consultan con semillas, no por descarga completa.
- EPO/WIPO: quedan para revision de acceso y terminos.

## Fuentes diferidas por pago, token o acceso

- Scopus.
- Web of Science.
- IEEE Xplore.
- JSTOR.
- Nature Portfolio.
- Dimensions pago.
- Ahrefs.
- SEMrush.
- G2.
- Google Patents via SerpAPI.

Estas fuentes se documentan, pero no bloquean la adjudicacion ni la preparacion del paquete consultora.

## Criterios de decision

- `mantener_recurrente`: entra al flujo regular del observatorio.
- `mantener_indirecto`: se conserva como relacion contextual, pero no cuenta como output institucional hasta confirmar afiliacion.
- `mantener_baja_prioridad`: se conserva para auditoria o produccion CCHEN general, pero no alimenta tablero principal sin revision.
- `mantener_vigilancia`: se conserva con cupo limitado para tendencias, benchmark o alertas.
- `revisar_manual`: requiere validacion experta CCHEN.
- `descartar_ruido`: no se promueve; se conserva solo como evidencia de descarte.

## Estado operativo al cierre

- Zenodo, Fernanda API candidates, outputs repositorios master y radiofarmacia quedaron integradas al runner canonico.
- Los flujos ejecutan extraccion, curaduria y/o normalizacion segun corresponda.
- Calidad general: 0 criticos, 5 advertencias conocidas.
- Unica fuente vencida/bloqueada: `patentsview_uspto`, requiere `PATENTSVIEW_API_KEY`.

## Responsabilidad esperada de la consultora

La consultora debe poder replicar este proceso sin cambiar la regla de alcance:

1. Ejecutar el runner canonico.
2. Revisar artefactos CSV/JSON.
3. Mantener trazabilidad de fecha, conteo, fuente y filtro usado.
4. No ampliar semillas ni fuentes sin documentar justificacion, evidencia de ruido y decision CCHEN.
5. Automatizar monitoreo, alertas, logs y publicacion controlada.

La decision funcional sigue siendo interna: CCHEN define que semillas, temas y registros pasan de evidencia a tablero.
