# Tests — CCHEN Observatory

## Ejecutar todos los tests
```bash
cd /path/to/CCHEN
pip install pytest
pytest        # usa pytest.ini en la raíz del repo
```

O con ruta explícita:
```bash
pytest Tests/ -v
```

## Ejecutar tests individuales
```bash
pytest Tests/test_data_loader.py -v
pytest Tests/test_sections_smoke.py -v
pytest Tests/test_scripts_syntax.py -v
pytest Tests/test_eval_pure_functions.py -v
pytest Tests/test_assistant_eval_batch_cli.py -v
```

## Chequeos operativos (no pytest)

Validación de contratos de datos en exportables del observatorio:

```bash
/Users/bastianayalainostroza/Dropbox/CCHEN/.venv/bin/python Scripts/check_export_data_contracts.py
```

## Tests disponibles

| Archivo | Tests | Qué cubre |
|---|---|---|
| `test_data_loader.py` | 33 | Cada loader retorna DataFrame con columnas mínimas esperadas |
| `test_sections_smoke.py` | 22 | Sintaxis + import + callable `render()` de las 10 secciones + smoke con mocks para `asistente_id.render()` |
| `test_scripts_syntax.py` | 34 | Sintaxis AST de todos los scripts en `Scripts/` |
| `test_eval_pure_functions.py` | 30 | Unit tests de funciones puras del pipeline de evaluación |
| `test_assistant_eval_batch_cli.py` | 1 | Regresión de CLI: alias `--mode` en `assistant_eval_batch.py` |

**Total: 120 tests, ~3s** (sin red, sin datos reales, sin GPU)

## Funciones cubiertas por `test_eval_pure_functions.py`

| Función | Módulo | Tests |
|---|---|---|
| `_normalize_kw` | `Scripts/assistant_eval_batch.py` | 6 (acentos, mayúsculas, vacío) |
| `_keyword_hits` | `Scripts/assistant_eval_batch.py` | 10 (unicode, multi-keyword, None) |
| `_count_citation_tags` | `Scripts/assistant_eval_structured_responses.py` | 7 (regex fuente, case-insensitive) |
| `_delta_str` | `Scripts/compare_eval_runs.py` | 7 (NaN, None, enteros, floats) |

## Brechas conocidas (Opción 2 — trabajo futuro)

- `render()` de `asistente_id.py` ahora tiene un smoke test con mocks (flujo base sin red + stream vacío + fuentes RAG visibles)
- Falta cobertura de casos límite adicionales del asistente (`st.stop`, error en `_build_assistant_system_prompt`, fallas de `generate_pdf_report`)
- Los tests de `test_data_loader.py` leen datos reales de `Data/` — no hay datos sintéticos
- Sin markers `@pytest.mark.slow` / `@pytest.mark.integration`
- Sin umbral mínimo de cobertura (`pytest-cov` no instalado)
