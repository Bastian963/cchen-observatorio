# Tests — CCHEN Observatory

## Ejecutar todos los tests
```bash
cd /Users/bastianayalainostroza/Dropbox/CCHEN
pip install pytest
pytest Tests/ -v
```

## Ejecutar tests individuales
```bash
pytest Tests/test_data_loader.py -v
pytest Tests/test_sections_smoke.py -v
pytest Tests/test_scripts_syntax.py -v
```

## Tests disponibles
- `test_data_loader.py` — 30+ parametrizados, verifica que cada loader retorna DataFrame
- `test_sections_smoke.py` — verifica sintaxis + import + callable de las 10 secciones
- `test_scripts_syntax.py` — verifica sintaxis de todos los scripts ETL
