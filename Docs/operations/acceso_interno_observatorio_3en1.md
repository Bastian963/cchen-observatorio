# Acceso Interno — Observatorio 3 en 1

Documento corto para revisores DGIn y equipos CCHEN durante el piloto interno controlado.

## URLs

- Dashboard: `https://obs-int.cchen.cl`
- Repositorio institucional DSpace: `https://repo-int.cchen.cl`
- Portal de datos CKAN: `https://datos-int.cchen.cl`

## Acceso

Hay dos capas de control:

1. `Basic Auth` del reverse proxy
2. `internal_auth` del dashboard para vistas y datos sensibles

DSpace y CKAN quedan visibles detrás del proxy, pero sus cuentas administrativas siguen reservadas para operadores.

## Qué revisar

- Portada institucional 3 en 1
- Enlaces entre dashboard, DSpace y CKAN
- Navegación general
- Activos institucionales publicados
- Consultas del asistente con URLs institucionales

## Qué no compartir todavía

- credenciales del proxy
- credenciales admin CKAN
- credenciales admin DSpace
- capturas o links fuera de la red autorizada sin coordinación

## Canal de retroalimentación sugerido

Cada revisión debe registrar:

- fecha
- nombre de la persona revisora
- módulo revisado
- hallazgo
- severidad
- acción sugerida

El objetivo de esta etapa es validar utilidad, navegación y operación antes de cualquier exposición más amplia.
