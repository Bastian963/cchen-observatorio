# SLA Semanal — Observatorio Tecnológico CCHEN 360°

Registro operacional de cada corrida del workflow `arxiv_monitor.yml`.  
Actualizar cada lunes tras revisar el log con el [checklist de 10 puntos](#checklist-de-10-puntos).

---

## Tabla de registro

| Semana | Fecha run | Run ID | Duración | arXiv | News | IAEA | Convocatorias | Boletín | Migración | Nivel | Acción tomada | Responsable |
|--------|-----------|--------|----------|-------|------|------|---------------|---------|-----------|-------|---------------|-------------|
| S13-2026 | 2026-03-23 | 23462090812 | 2m5s | ✅ 33f | ✅ 65f | ⚠️ TLS | ⚠️ SKIP | ✅ boletin_2026-S13.html | ✅ 98f OK | 🟡 Alerta | IAEA y Convocatorias inaccesibles desde GitHub runners (continue-on-error activo). Sin acción requerida. | Bastián |

---

## Criterio de nivel

| Nivel | Semáforo | Condición |
|-------|----------|-----------|
| Operativo | 🟢 Verde | arXiv ≥10f + News ≥20f + migración 100% + boletín OK |
| Alerta | 🟡 Amarillo | ≥1 fuente best-effort en SKIP o arXiv/News bajos (1-9 / 1-19) |
| Incidente | 🔴 Rojo | arXiv=0 o News=0 o migración falla o run ≠ success |

---

## Umbrales por fuente

| Fuente | Operativo | Alerta | Incidente |
|--------|-----------|--------|-----------|
| arXiv | ≥10 filas | 1-9 filas | 0 filas / SKIP |
| News | ≥20 filas | 1-19 filas | 0 filas / SKIP |
| IAEA INIS | TLS ≤30% | TLS 31-70% | TLS >70% o SKIP ≥2 semanas consecutivas |
| Convocatorias | Archivo presente | SKIP 1 semana | SKIP ≥2 semanas consecutivas |
| Migración Supabase | Leídas = Migradas | Diferencia 1-10% | Diferencia >10% o falla total |
| Duración job | ≤4 min | 4-8 min | >8 min |

---

## Acción por nivel

| Nivel | Acción |
|-------|--------|
| 🟢 Verde | Solo registrar en tabla. Sin acción. |
| 🟡 Alerta | Registrar + revisar log raw. Si IAEA/Convocatorias: marcar semana consecutiva. Si arXiv/News bajos: revisar filtros del script. |
| 🔴 Incidente | Registrar + abrir issue en GitHub + notificar + corregir antes de próxima corrida. Trigger manual tras fix. |

---

## Comando rápido de revisión

```bash
RUN_ID=$(gh run list --workflow arxiv_monitor.yml --limit 1 --json databaseId -q '.[0].databaseId') \
&& echo "=== RUN ===" \
&& gh run list --workflow arxiv_monitor.yml --limit 1 --json databaseId,conclusion,createdAt,updatedAt \
   -q '.[0] | "ID: \(.databaseId) | \(.conclusion) | \(.createdAt) → \(.updatedAt)"' \
&& echo "=== LOG ===" \
&& gh run view "$RUN_ID" --log | grep -E \
  "Estado operativo|arXiv|News.*fila|IAEA|SKIP|convocatorias|Boletín guardado|filas migradas|Leídas:|TLS"
```

---

## Checklist de 10 puntos

Copiar y completar cada semana:

```
Semana: S__-2026  |  Fecha: 2026-__-__  |  Run ID: ___________

[ ] 1. Run = success
[ ] 2. Duración ≤ 4 min
[ ] 3. arXiv: OK y filas > 0
[ ] 4. News: OK y filas > 0
[ ] 5. Migración arXiv: filas migradas = filas leídas
[ ] 6. Migración News: filas migradas = filas leídas
[ ] 7. IAEA: si SKIP → ¿semana 1 o 2 consecutiva?
[ ] 8. Convocatorias: archivo curado presente?
[ ] 9. Boletín: boletin_YYYY-S__.html generado?
[10] Nivel final: 🟢/🟡/🔴 + acción tomada: ___________
```

---

## Historial IAEA/Convocatorias (seguimiento consecutivo)

| Semana | IAEA | Convocatorias | Acción |
|--------|------|---------------|--------|
| S13-2026 | ⚠️ TLS total (semana 1) | ⚠️ SKIP (semana 1) | Sin acción — semana 1, continue-on-error activo |
