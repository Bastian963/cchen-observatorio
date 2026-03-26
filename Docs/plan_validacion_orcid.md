# Validación y actualización de afiliación institucional vía ORCID

## Resumen del proceso

El observatorio CCHEN implementa un flujo automatizado para validar y actualizar la afiliación institucional de sus investigadores utilizando datos de ORCID y padrón interno. Este proceso combina extracción automática, cruce de datos y revisión manual para asegurar la máxima calidad y confiabilidad.

## Fuentes de datos principales

- **cchen_researchers_orcid.csv**: Listado de investigadores con ORCID, empleadores y métricas asociadas.
- **Padrones institucionales**: Archivos internos con la planta formal y grupos de investigación.
- **Scripts relevantes**:
  - `Scripts/build_planta_orcid_exports.py`: Cruza padrón y ORCID, genera reportes de estado y brechas.
  - `_tmp_audit_orcid.py`: Auditoría de empleadores, duplicados y casos dudosos.

## Flujo automatizado

1. **Extracción de ORCID iDs**
   - Se parte de los datos en `cchen_researchers_orcid.csv` y, si es necesario, se extraen ORCID adicionales desde OpenAlex u otras fuentes.

2. **Cruce con padrón institucional**
   - El script `build_planta_orcid_exports.py` compara los nombres y grupos del padrón con los perfiles ORCID.
   - Se valida si el empleador más reciente en ORCID corresponde a CCHEN (palabras clave configurables).

3. **Generación de reportes**
   - Se generan archivos CSV con el estado de cada investigador:
     - `cchen_planta_estado_orcid_actual.csv`: Estado de validación automática.
     - `cchen_planta_orcid_brechas_actual.csv`: Casos que requieren revisión manual.

4. **Auditoría y revisión manual**
   - El script `_tmp_audit_orcid.py` ayuda a identificar:
     - Investigadores sin empleador en ORCID.
     - Empleadores externos a CCHEN.
     - Posibles duplicados por apellido.
     - Perfiles con works_count = 0.
   - **Siempre se requiere una revisión humana** para:
     - Casos de nombres ambiguos o duplicados.
     - Empleadores no reconocidos como CCHEN.
     - Perfiles nuevos o con información incompleta.

## Recomendaciones

- Ejecutar periódicamente los scripts de auditoría y exportación.
- Documentar las decisiones tomadas en la revisión manual para trazabilidad.
- Actualizar las palabras clave de empleador según evolucione la denominación institucional.
- Mantener sincronizados los padrones internos y los datos ORCID.

## Referencias de scripts y tests

- `Scripts/build_planta_orcid_exports.py`: Flujo principal de validación y exportación.
- `Scripts/_tmp_audit_orcid.py`: Auditoría y control de calidad.
- `Tests/test_build_planta_orcid_exports.py`: Test funcional que documenta el flujo esperado y los archivos de salida.

---

**Nota:** La validación automática es robusta, pero la revisión humana es indispensable para asegurar la calidad y evitar falsos positivos/negativos en la afiliación institucional.
