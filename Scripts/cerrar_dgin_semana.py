#!/usr/bin/env python3
"""Automatiza el cierre semanal DGIn (acta + tracker KPI + comparativo).

Uso rapido (prefill):
  python Scripts/cerrar_dgin_semana.py \
    --week-ref 2026-W16 \
    --fecha 2026-04-13 \
    --acta Docs/reports/acta_dgin_semana_03_2026-04-13.md \
    --comparativo Docs/reports/resumen_comparativo_dgin_semana_02_vs_03_2026-04-13.md

Uso de cierre con KPIs:
  python Scripts/cerrar_dgin_semana.py \
    --week-ref 2026-W16 \
    --fecha 2026-04-13 \
    --acta Docs/reports/acta_dgin_semana_03_2026-04-13.md \
    --comparativo Docs/reports/resumen_comparativo_dgin_semana_02_vs_03_2026-04-13.md \
    --convocatorias 18 --activables 2 --acciones 3 --tiempo 26 --pct-estado 100
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKING = ROOT / "Docs" / "reports" / "dgin_piloto_kpi_tracking_2026-03-24.csv"

KPI_FIELDS = {
    "convocatorias_revisadas_semana": "convocatorias",
    "activables_gestionadas_semana": "activables",
    "acciones_ejecutadas_semana": "acciones",
    "tiempo_sesion_min": "tiempo",
    "pct_activables_con_estado": "pct_estado",
}


@dataclass
class DginRow:
    semana_ref: str
    fecha_sesion: str
    responsable_dgin: str
    convocatorias_revisadas_semana: str = ""
    activables_gestionadas_semana: str = ""
    acciones_ejecutadas_semana: str = ""
    tiempo_sesion_min: str = ""
    pct_activables_con_estado: str = ""
    bloqueos_principales: str = ""
    acciones_correctivas: str = ""
    observaciones: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, str]) -> "DginRow":
        return cls(**{k: row.get(k, "") for k in cls.__annotations__.keys()})

    def to_dict(self) -> dict[str, str]:
        return {k: str(getattr(self, k, "")) for k in self.__annotations__.keys()}


def _fmt_number(value: str | float | int | None, one_decimal: bool = False) -> str:
    if value is None:
        return "por completar"
    txt = str(value).strip()
    if txt == "":
        return "por completar"
    try:
        num = float(txt)
    except ValueError:
        return txt
    if one_decimal:
        return f"{num:.1f}"
    if num.is_integer():
        return str(int(num))
    return f"{num:.1f}"


def _is_complete(row: DginRow) -> bool:
    return all(getattr(row, field).strip() != "" for field in KPI_FIELDS.keys())


def _variation(prev: str, curr: str, one_decimal: bool = False) -> str:
    if not prev.strip() or not curr.strip():
        return "por calcular"
    try:
        p = float(prev)
        c = float(curr)
    except ValueError:
        return "por calcular"
    d = c - p
    if abs(d) < 1e-9:
        return "0.0" if one_decimal else "0"
    if one_decimal:
        return f"{d:+.1f}"
    if float(int(d)) == d:
        return f"{int(d):+d}"
    return f"{d:+.1f}"


def read_tracking(path: Path) -> list[DginRow]:
    if not path.exists():
        raise SystemExit(f"[ERROR] No existe tracker KPI: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [DginRow.from_dict(r) for r in reader]
    return rows


def write_tracking(path: Path, rows: list[DginRow], dry_run: bool) -> None:
    if dry_run:
        return
    if not rows:
        raise SystemExit("[ERROR] No hay filas para escribir en el tracker")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].to_dict().keys()))
        writer.writeheader()
        writer.writerows(r.to_dict() for r in rows)


def upsert_week_row(rows: list[DginRow], args: argparse.Namespace) -> tuple[DginRow, int, bool]:
    target_idx = -1
    for i, row in enumerate(rows):
        if row.semana_ref == args.week_ref:
            target_idx = i
            break

    created = False
    if target_idx < 0:
        rows.append(
            DginRow(
                semana_ref=args.week_ref,
                fecha_sesion=args.fecha,
                responsable_dgin=args.responsable,
                bloqueos_principales=args.bloqueos,
                acciones_correctivas=args.acciones_correctivas,
                observaciones=args.observaciones,
            )
        )
        target_idx = len(rows) - 1
        created = True

    row = rows[target_idx]
    row.fecha_sesion = args.fecha or row.fecha_sesion
    if args.responsable:
        row.responsable_dgin = args.responsable
    if args.bloqueos:
        row.bloqueos_principales = args.bloqueos
    if args.acciones_correctivas:
        row.acciones_correctivas = args.acciones_correctivas
    if args.observaciones:
        row.observaciones = args.observaciones

    updates = {
        "convocatorias_revisadas_semana": args.convocatorias,
        "activables_gestionadas_semana": args.activables,
        "acciones_ejecutadas_semana": args.acciones,
        "tiempo_sesion_min": args.tiempo,
        "pct_activables_con_estado": args.pct_estado,
    }
    for field, raw in updates.items():
        if raw is not None:
            setattr(row, field, str(raw))

    return row, target_idx, created


def resolve_prev_row(rows: list[DginRow], target_idx: int, prev_week_ref: str) -> DginRow:
    if prev_week_ref:
        for row in rows:
            if row.semana_ref == prev_week_ref:
                return row
        raise SystemExit(f"[ERROR] --prev-week-ref no encontrado en tracker: {prev_week_ref}")

    for idx in range(target_idx - 1, -1, -1):
        prev = rows[idx]
        if prev.semana_ref.strip():
            return prev
    raise SystemExit("[ERROR] No se pudo inferir semana previa. Usa --prev-week-ref.")


def _replace_line(text: str, pattern: str, replacement: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count == 0:
        return text
    return new_text


def _replace_semana_estado_lines(text: str, first_status: str, second_status: str) -> tuple[str, int]:
    lines = text.splitlines()
    idxs = [i for i, line in enumerate(lines) if re.match(r"^- Semana \d{2}: ", line)]
    if len(idxs) < 2:
        return text, 0
    changes = 0
    first_line_new = re.sub(r": .*?$", f": {first_status}", lines[idxs[0]])
    second_line_new = re.sub(r": .*?$", f": {second_status}", lines[idxs[1]])
    if lines[idxs[0]] != first_line_new:
        lines[idxs[0]] = first_line_new
        changes += 1
    if lines[idxs[1]] != second_line_new:
        lines[idxs[1]] = second_line_new
        changes += 1
    return "\n".join(lines) + "\n", changes


def update_acta(acta_path: Path, row: DginRow, args: argparse.Namespace, dry_run: bool) -> list[str]:
    if not acta_path.exists():
        raise SystemExit(f"[ERROR] No existe acta: {acta_path}")
    content = acta_path.read_text(encoding="utf-8")
    changes: list[str] = []

    replacements = [
        (
            r"^- `convocatorias_revisadas_semana`: .*?$",
            f"- `convocatorias_revisadas_semana`: {_fmt_number(row.convocatorias_revisadas_semana)}",
            "KPI convocatorias en acta",
        ),
        (
            r"^- `activables_gestionadas_semana`: .*?$",
            f"- `activables_gestionadas_semana`: {_fmt_number(row.activables_gestionadas_semana)}",
            "KPI activables en acta",
        ),
        (
            r"^- `acciones_ejecutadas_semana`: .*?$",
            f"- `acciones_ejecutadas_semana`: {_fmt_number(row.acciones_ejecutadas_semana)}",
            "KPI acciones en acta",
        ),
        (
            r"^- `tiempo_sesion_min`: .*?$",
            f"- `tiempo_sesion_min`: {_fmt_number(row.tiempo_sesion_min)}",
            "KPI tiempo en acta",
        ),
        (
            r"^- `%_activables_con_estado`: .*?$",
            f"- `%_activables_con_estado`: {_fmt_number(row.pct_activables_con_estado, one_decimal=True)}",
            "KPI porcentaje en acta",
        ),
    ]

    for pattern, replacement, label in replacements:
        new_content = _replace_line(content, pattern, replacement)
        if new_content != content:
            content = new_content
            changes.append(label)

    if args.tiempo is not None:
        new_content = _replace_line(
            content,
            r"^- Duración real \(min\): .*?$",
            f"- Duración real (min): {_fmt_number(row.tiempo_sesion_min)}",
        )
        if new_content != content:
            content = new_content
            changes.append("Duración en datos de sesión")

    if args.responsable:
        for replacement, pattern, label in [
            (f"- Responsable DGIn titular: {args.responsable}", r"^- Responsable DGIn titular: .*?$", "Responsable titular"),
            (f"- Responsable DGIn respaldo: {args.responsable}", r"^- Responsable DGIn respaldo: .*?$", "Responsable respaldo"),
        ]:
            new_content = _replace_line(content, pattern, replacement)
            if new_content != content:
                content = new_content
                changes.append(f"{label} en acta")

    if args.exportable:
        new_content = _replace_line(
            content,
            r"^- Exportable actualizado generado: .*?$",
            f"- Exportable actualizado generado: `{args.exportable}`",
        )
        if new_content != content:
            content = new_content
            changes.append("Evidencia exportable en acta")

    if args.proxima_revision:
        new_content = _replace_line(
            content,
            r"^- Próxima revisión agendada para: .*?$",
            f"- Próxima revisión agendada para: {args.proxima_revision}",
        )
        if new_content != content:
            content = new_content
            changes.append("Próxima revisión en acta")

    if args.resumen_oportunidades:
        new_content = _replace_line(
            content,
            r"^- Oportunidades prioritarias revisadas: .*?$",
            f"- Oportunidades prioritarias revisadas: {args.resumen_oportunidades}",
        )
        if new_content != content:
            content = new_content
            changes.append("Resumen de oportunidades en acta")

    if args.resumen_acciones:
        new_content = _replace_line(
            content,
            r"^- Acciones definidas esta semana: .*?$",
            f"- Acciones definidas esta semana: {args.resumen_acciones}",
        )
        if new_content != content:
            content = new_content
            changes.append("Resumen de acciones en acta")

    if args.resumen_riesgos:
        new_content = _replace_line(
            content,
            r"^- Riesgos o bloqueos detectados: .*?$",
            f"- Riesgos o bloqueos detectados: {args.resumen_riesgos}",
        )
        if new_content != content:
            content = new_content
            changes.append("Resumen de riesgos en acta")

    if not dry_run:
        acta_path.write_text(content, encoding="utf-8")

    return changes


def update_comparativo(
    comparativo_path: Path,
    prev_row: DginRow,
    curr_row: DginRow,
    dry_run: bool,
) -> list[str]:
    if not comparativo_path.exists():
        raise SystemExit(f"[ERROR] No existe comparativo: {comparativo_path}")

    content = comparativo_path.read_text(encoding="utf-8")
    changes: list[str] = []

    values = {
        "convocatorias_revisadas_semana": (
            _fmt_number(prev_row.convocatorias_revisadas_semana),
            _fmt_number(curr_row.convocatorias_revisadas_semana),
            _variation(prev_row.convocatorias_revisadas_semana, curr_row.convocatorias_revisadas_semana),
        ),
        "activables_gestionadas_semana": (
            _fmt_number(prev_row.activables_gestionadas_semana),
            _fmt_number(curr_row.activables_gestionadas_semana),
            _variation(prev_row.activables_gestionadas_semana, curr_row.activables_gestionadas_semana),
        ),
        "acciones_ejecutadas_semana": (
            _fmt_number(prev_row.acciones_ejecutadas_semana),
            _fmt_number(curr_row.acciones_ejecutadas_semana),
            _variation(prev_row.acciones_ejecutadas_semana, curr_row.acciones_ejecutadas_semana),
        ),
        "tiempo_sesion_min": (
            _fmt_number(prev_row.tiempo_sesion_min),
            _fmt_number(curr_row.tiempo_sesion_min),
            _variation(prev_row.tiempo_sesion_min, curr_row.tiempo_sesion_min),
        ),
        "pct_activables_con_estado": (
            _fmt_number(prev_row.pct_activables_con_estado, one_decimal=True),
            _fmt_number(curr_row.pct_activables_con_estado, one_decimal=True),
            _variation(prev_row.pct_activables_con_estado, curr_row.pct_activables_con_estado, one_decimal=True),
        ),
    }

    for kpi, (v_prev, v_curr, v_delta) in values.items():
        pattern = rf"^\|\s*{re.escape(kpi)}\s*\|.*?$"
        replacement = f"| {kpi} | {v_prev} | {v_curr} | {v_delta} |"
        new_content = _replace_line(content, pattern, replacement)
        if new_content != content:
            content = new_content
            changes.append(f"Tabla comparativo: {kpi}")

    state_prev = "cerrada con datos completos." if _is_complete(prev_row) else "prellenada; completar KPIs al cierre de sesión."
    state_curr = "cerrada con datos completos." if _is_complete(curr_row) else "prellenada; completar KPIs al cierre de sesión."

    content, n_state = _replace_semana_estado_lines(
        content,
        first_status=state_prev,
        second_status=state_curr,
    )
    if n_state > 0:
        changes.append("Estado de semanas en comparativo")

    if _is_complete(curr_row):
        t_prev = float(prev_row.tiempo_sesion_min)
        t_curr = float(curr_row.tiempo_sesion_min)
        a_prev = float(prev_row.acciones_ejecutadas_semana)
        a_curr = float(curr_row.acciones_ejecutadas_semana)
        pct_prev = float(prev_row.pct_activables_con_estado)
        pct_curr = float(curr_row.pct_activables_con_estado)

        adopcion = (
            "se sostuvo la cadencia de revisión"
            if float(curr_row.convocatorias_revisadas_semana or 0) >= float(prev_row.convocatorias_revisadas_semana or 0)
            else "se redujo la cobertura de revisión; revisar capacidad operativa"
        )
        velocidad = (
            "mejora en velocidad de sesión"
            if t_curr < t_prev
            else "sesión más lenta que la semana previa"
        )
        efectividad = (
            "aumentaron acciones ejecutadas"
            if a_curr > a_prev
            else "acciones ejecutadas estables o a la baja"
        )
        trazabilidad = (
            "trazabilidad sostenida"
            if pct_curr >= pct_prev
            else "baja en trazabilidad de activables"
        )

        trend_replacements = [
            (r"^- Adopción semanal: .*?$", f"- Adopción semanal: {adopcion}."),
            (r"^- Velocidad de sesión: .*?$", f"- Velocidad de sesión: {velocidad}."),
            (r"^- Efectividad de acciones: .*?$", f"- Efectividad de acciones: {efectividad}."),
            (r"^- Trazabilidad de activables: .*?$", f"- Trazabilidad de activables: {trazabilidad}."),
        ]
        for pattern, replacement in trend_replacements:
            tmp = _replace_line(content, pattern, replacement)
            if tmp != content:
                content = tmp
                changes.append("Lectura de tendencia en comparativo")

        content = _replace_line(
            content,
            r"^## Lectura de tendencia \(completar al cierre\)$",
            "## Lectura de tendencia",
        )

    if not dry_run:
        comparativo_path.write_text(content, encoding="utf-8")

    return changes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cierre semanal DGIn (tracker + acta + comparativo)")
    parser.add_argument("--week-ref", required=True, help="Semana en formato ISO, por ejemplo 2026-W16")
    parser.add_argument("--fecha", required=True, help="Fecha de sesión, formato YYYY-MM-DD")
    parser.add_argument("--tracking", default=str(DEFAULT_TRACKING), help="Ruta al CSV de tracking KPI")
    parser.add_argument("--acta", required=True, help="Ruta al acta semanal a actualizar")
    parser.add_argument("--comparativo", required=True, help="Ruta al comparativo semanal a actualizar")
    parser.add_argument("--prev-week-ref", default="", help="Semana previa (opcional). Si no se entrega, se infiere por orden del CSV")

    parser.add_argument("--responsable", default="", help="Responsable DGIn para la fila de tracking y acta")
    parser.add_argument("--convocatorias", type=int, default=None, help="KPI convocatorias revisadas")
    parser.add_argument("--activables", type=int, default=None, help="KPI activables gestionadas")
    parser.add_argument("--acciones", type=int, default=None, help="KPI acciones ejecutadas")
    parser.add_argument("--tiempo", type=int, default=None, help="KPI tiempo de sesión (min)")
    parser.add_argument("--pct-estado", type=float, dest="pct_estado", default=None, help="KPI % activables con estado")

    parser.add_argument("--bloqueos", default="", help="Texto breve para bloqueos principales en tracker")
    parser.add_argument("--acciones-correctivas", default="", help="Texto breve para acciones correctivas en tracker")
    parser.add_argument("--observaciones", default="", help="Observaciones de la fila semanal en tracker")

    parser.add_argument("--exportable", default="", help="Ruta del exportable generado para dejar en evidencia del acta")
    parser.add_argument("--proxima-revision", default="", help="Texto de próxima revisión, por ejemplo 2026-04-20 09:00")

    parser.add_argument("--resumen-oportunidades", default="", help="Texto para la línea de resumen de oportunidades en acta")
    parser.add_argument("--resumen-acciones", default="", help="Texto para la línea de resumen de acciones en acta")
    parser.add_argument("--resumen-riesgos", default="", help="Texto para la línea de resumen de riesgos en acta")

    parser.add_argument("--dry-run", action="store_true", help="No escribe archivos, solo muestra cambios")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    tracking_path = Path(args.tracking)
    acta_path = Path(args.acta)
    comparativo_path = Path(args.comparativo)

    rows = read_tracking(tracking_path)
    curr_row, target_idx, created = upsert_week_row(rows, args)
    prev_row = resolve_prev_row(rows, target_idx, args.prev_week_ref)

    write_tracking(tracking_path, rows, dry_run=args.dry_run)
    acta_changes = update_acta(acta_path, curr_row, args, dry_run=args.dry_run)

    comparativo_changes = update_comparativo(
        comparativo_path=comparativo_path,
        prev_row=prev_row,
        curr_row=curr_row,
        dry_run=args.dry_run,
    )

    action = "[dry-run]" if args.dry_run else "[ok]"
    print(f"{action} tracker: {'fila creada' if created else 'fila actualizada'} para {args.week_ref}")
    print(f"{action} acta: {len(acta_changes)} cambios")
    print(f"{action} comparativo: {len(comparativo_changes)} cambios")

    if args.dry_run:
        if acta_changes:
            print(f"[dry-run] detalles acta: {', '.join(acta_changes)}")
        if comparativo_changes:
            print(f"[dry-run] detalles comparativo: {', '.join(comparativo_changes)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
