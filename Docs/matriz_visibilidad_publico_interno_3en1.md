# Matriz de Visibilidad — Observatorio 3 en 1

Define qué capas del observatorio pueden exponerse en el **portal público**, cuáles permanecen en la **superficie interna** y cuáles requieren un comportamiento dual.

## 1. Regla general

- `DSpace` y `CKAN` son las superficies públicas canónicas para documentos y datasets.
- El `dashboard` se divide en dos modos:
  - `public`: acceso anónimo, sólo vistas y corpus publicables.
  - `internal`: acceso autenticado, vistas sensibles y diagnóstico completo.
- La visibilidad se decide por:
  - sensibilidad del dataset o tabla,
  - visibilidad editorial del activo,
  - riesgo de exponer datos nominativos o de operación interna.

## 2. Matriz por sección

| Sección | Visibilidad objetivo | Criterio |
| --- | --- | --- |
| Plataforma Institucional | `publica` | Portada 3 en 1, enlaces a DSpace y CKAN, activos publicados |
| Panel de Indicadores | `interna` | Mezcla capital humano y métricas ejecutivas sensibles |
| Producción Científica | `publica` | Bibliometría y outputs científicos publicables |
| Redes y Colaboración | `publica` | Colaboración institucional y científica publicable |
| Vigilancia Tecnológica | `publica` | Monitores, tendencias y señales abiertas |
| Financiamiento I+D | `publica` | ANID, IAEA TC y evidencia publicable; sin capa sensible interna |
| Convocatorias y Matching | `publica` | Matching formal curado y activos publicados |
| Transferencia y Portafolio | `publica` | Portafolio semilla y outputs observables publicables |
| Modelo y Gobernanza | `interna` | Entidades operativas, relaciones internas y trazabilidad de gobierno |
| Formación de Capacidades | `interna` | Capital humano y posibles registros nominativos |
| Asistente I+D | `mixta` | Público con corpus abierto; interno con contexto extendido |
| Grafo de Citas | `publica` | Visualización de impacto científico publicable |

## 3. Matriz por tipo de dato

| Tipo | Visibilidad objetivo | Fuente de verdad |
| --- | --- | --- |
| Publicaciones | `publico` | DSpace, OpenAlex, Crossref, OpenAIRE |
| Datasets descargables | `publico` | CKAN |
| Convenios y acuerdos institucionales publicables | `publico` | CKAN / dashboard / DSpace según caso |
| Capital humano | `interno` | Dashboard interno / Supabase sensible |
| Funding complementario no publicado | `interno` | Dashboard interno / Supabase sensible |
| Entity registry nominativo | `interno` | Dashboard interno |
| Entity links internos | `interno` | Dashboard interno |
| Activos institucionales con `public_url` | `publico` o `mixto` | Catálogo 3 en 1 |

## 4. Reglas operativas

1. Un activo sólo entra al portal público si tiene `public_url` estable.
2. El dashboard público no debe depender de `service_role_key`.
3. Si una consulta requiere capital humano o registros internos, el portal público debe decirlo explícitamente y derivar a la superficie interna autorizada.
4. Todo dataset o documento nuevo debe registrarse primero en `Data/Gobernanza/catalogo_activos_3_en_1.csv`.
5. Los enlaces citados por la portada y por el asistente deben resolverse a las URLs activas de la plataforma, no a `localhost`.
