# Checklist manual - Carga DSpace ola 1

Esta primera iteracion no automatiza DSpace. La carga es curada y luego se registra el resultado en el catalogo maestro `Data/Gobernanza/catalogo_activos_3_en_1.csv`.

## 1. Preparar la coleccion

1. Confirmar la comunidad y coleccion destino para documentos del observatorio.
2. Verificar que exista un administrador DSpace operativo.
3. Confirmar si los documentos quedaran publicos o mixtos.

## 2. Cargar los 4 documentos semilla

Documentos de primera ola:

1. `Docs/design/Memoria Metodológica - Observatorio CCHEN 360.pdf`
2. `Docs/design/Propuesta de implementación del Observatorio.pdf`
3. `Docs/reports/observatorio_cchen_documentacion.pdf`
4. `Docs/reports/dgin_piloto_observatorio_3_en_1_resumen_2026-03-28.pdf`

## 3. Metadatos minimos por item

- `title`
- `area_unidad`
- `tema`
- `anio`
- `responsables`
- `palabras_clave`
- `visibilidad`
- `identificador`
- `vinculo_cruzado`

## 4. Registrar el resultado en el catalogo

Por cada item cargado:

1. Copiar la URL publica o handle generado por DSpace.
2. Escribir ese valor en `public_url`.
3. Escribir el handle o identificador persistente en `identificador`.
4. Cambiar `publication_status` a `published`.
5. Verificar que `vinculo_cruzado` siga apuntando a una superficie valida del observatorio.

## 5. Verificacion final

1. Abrir el item desde DSpace.
2. Confirmar que el PDF descarga correctamente.
3. Confirmar que el activo aparece en la portada `Plataforma Institucional` del dashboard cuando el catalogo ya tenga `public_url`.
4. Confirmar que el asistente puede citar la URL publica cuando la consulta sea pertinente.
