#!/usr/bin/env python3
"""
Generador de Boletín Semanal CCHEN
====================================
Genera un HTML listo para enviar por correo o publicar en intranet,
con las noticias y papers relevantes de la semana.

Uso:
    python3 Scripts/generar_boletin.py            # semana actual
    python3 Scripts/generar_boletin.py --weeks 2  # últimas 2 semanas
    python3 Scripts/generar_boletin.py --all       # todo el historial disponible
"""

import datetime
import argparse
import sys
import pandas as pd
from pathlib import Path

BASE     = Path(__file__).parent.parent
DATA_PUB = BASE / "Data" / "Publications"
DATA_VIG = BASE / "Data" / "Vigilancia"
OUT_DIR  = BASE / "Data" / "Boletines"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Allow importing data_loader from Dashboard folder as fallback
sys.path.insert(0, str(BASE / "Dashboard"))


# ── Carga de datos ─────────────────────────────────────────────────────────────

def load_news(weeks_back=1):
    path = DATA_VIG / "news_monitor.csv"
    if path.exists():
        df = pd.read_csv(path)
    else:
        try:
            import data_loader
            df = data_loader.load_news_monitor()
        except Exception:
            return pd.DataFrame()
    if df.empty:
        return df
    df["dt"] = pd.to_datetime(df["published"], errors="coerce", utc=True).dt.tz_localize(None)
    df = df.drop_duplicates(subset=["news_id"])
    if weeks_back > 0:
        cutoff = datetime.datetime.now() - datetime.timedelta(weeks=weeks_back)
        df = df[df["dt"] >= cutoff]
    return df.sort_values("dt", ascending=False)


def load_cchen_papers(n=5):
    oa_path = DATA_PUB / "cchen_openalex_works.csv"
    we_path = DATA_PUB / "cchen_works_enriched.csv"
    if oa_path.exists():
        df = pd.read_csv(oa_path, low_memory=False)
        if we_path.exists():
            we = pd.read_csv(we_path, low_memory=False)
            df = df.merge(
                we[["work_id", "publication_date"]].rename(columns={"work_id": "openalex_id"}),
                on="openalex_id", how="left"
            )
    else:
        try:
            import data_loader
            df = data_loader.load_publications()
        except Exception:
            return pd.DataFrame()
    if df.empty:
        return df
    # Ordenar por publication_date si existe con datos, si no por year
    if "publication_date" in df.columns and df["publication_date"].notna().any():
        df["_sort_dt"] = pd.to_datetime(df["publication_date"], errors="coerce")
        return df.sort_values("_sort_dt", ascending=False, na_position="last").drop(columns=["_sort_dt"]).head(n)
    elif "year" in df.columns:
        return df.sort_values("year", ascending=False, na_position="last").head(n)
    return df.head(n)


# ── Helpers HTML ───────────────────────────────────────────────────────────────

COLORS = {
    "blue_dark":  "#1E3A5F",
    "blue":       "#2563EB",
    "blue_light": "#EFF6FF",
    "amber":      "#D97706",
    "green":      "#16A34A",
    "red":        "#DC2626",
    "gray":       "#64748B",
    "bg":         "#F8FAFC",
    "white":      "#FFFFFF",
    "border":     "#E2E8F0",
}

TOPIC_COLORS = {
    "CIENCIA":      ("#DBEAFE", "#1D4ED8"),
    "POLÍTICA":     ("#FEF3C7", "#92400E"),
    "INSTITUCIONAL":("#D1FAE5", "#065F46"),
    "GENERAL":      ("#F1F5F9", "#475569"),
}

FLAG_COLORS = {
    "ALTA":  ("#FEE2E2", "#991B1B"),
    "MEDIA": ("#FEF3C7", "#92400E"),
    "BAJA":  ("#F1F5F9", "#475569"),
}


def badge(text, bg, color):
    return (
        f'<span style="background:{bg};color:{color};padding:2px 8px;'
        f'border-radius:12px;font-size:11px;font-weight:600;">{text}</span>'
    )


def section_header(title, icon=""):
    c = COLORS
    return f"""
    <tr><td style="padding:32px 0 8px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="border-left:4px solid {c['blue']};padding-left:12px;">
            <span style="font-size:18px;font-weight:700;color:{c['blue_dark']};">
              {icon} {title}
            </span>
          </td>
        </tr>
      </table>
    </td></tr>
    """


def news_card(row):
    c = COLORS
    topic = _safe_str(row.get("topic_flag"), "GENERAL")
    bg, col = TOPIC_COLORS.get(topic, TOPIC_COLORS["GENERAL"])
    title   = _strip_tags(_safe_str(row.get("title"), ""))
    source  = _safe_str(row.get("source_name"), "")
    snippet = _strip_tags(_safe_str(row.get("snippet"), ""))[:250]
    link    = _safe_str(row.get("link"), "")
    dt      = row.get("dt")
    date_s  = dt.strftime("%-d %b %Y") if dt is not None and pd.notna(dt) else ""

    link_html = f'<a href="{link}" style="color:{c["blue"]};font-size:12px;">Leer noticia →</a>' if link else ""

    return f"""
    <tr><td style="padding:6px 0;">
      <table width="100%" cellpadding="12" cellspacing="0"
             style="background:{c['white']};border:1px solid {c['border']};
                    border-radius:8px;border-left:4px solid {col};">
        <tr>
          <td>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>{badge(topic, bg, col)}&nbsp;
                    <span style="color:{c['gray']};font-size:12px;">{source} · {date_s}</span>
                </td>
              </tr>
              <tr><td style="padding:6px 0 4px;">
                <span style="font-size:14px;font-weight:600;color:{c['blue_dark']};
                             line-height:1.4;">{title}</span>
              </td></tr>
              {"<tr><td><span style='font-size:12px;color:" + c['gray'] + ";line-height:1.5;'>" + snippet + "</span></td></tr>" if snippet else ""}
              <tr><td style="padding-top:6px;">{link_html}</td></tr>
            </table>
          </td>
        </tr>
      </table>
    </td></tr>
    """


def _safe_str(val, default="") -> str:
    """Convierte val a str descartando None/NaN/nan."""
    if val is None:
        return default
    try:
        import pandas as _pd
        if _pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    return default if s.lower() in ("none", "nan", "") else s


def _strip_tags(text: str) -> str:
    """Elimina etiquetas HTML/XML (incluyendo MathML) del texto."""
    import re
    text = re.sub(r"<[^<>]*>?", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def paper_card(row):
    c = COLORS
    title  = _strip_tags(_safe_str(row.get("title"), "Sin título"))
    src    = _safe_str(row.get("source"), "")[:80]
    doi    = _safe_str(row.get("doi"), "")
    cites  = int(row.get("cited_by_count", 0)) if pd.notna(row.get("cited_by_count")) else 0
    dt     = row.get("pub_dt")
    _yr    = row.get("year", "")
    yr_s   = str(int(float(_yr))) if _yr and pd.notna(_yr) else ""
    date_s = dt.strftime("%-d %b %Y") if dt is not None and pd.notna(dt) else yr_s
    link   = f"https://doi.org/{doi}" if doi and doi.startswith("10.") else ""

    doi_html   = f'<a href="{link}" style="color:{c["blue"]};font-size:12px;">Ver publicación →</a>' if link else ""
    cites_html = f'<span style="font-size:11px;color:{c["gray"]};">⭐ {cites} citas</span>' if cites else ""

    return f"""
    <tr><td style="padding:6px 0;">
      <table width="100%" cellpadding="12" cellspacing="0"
             style="background:{c['white']};border:1px solid {c['border']};
                    border-radius:8px;">
        <tr><td>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td>
              <span style="color:{c['gray']};font-size:12px;">{src} · {date_s}</span>
            </td></tr>
            <tr><td style="padding:5px 0 3px;">
              <span style="font-size:14px;font-weight:600;color:{c['blue_dark']};
                           line-height:1.4;">{title}</span>
            </td></tr>
            <tr><td style="padding-top:6px;">
              {doi_html}&nbsp;&nbsp;{cites_html}
            </td></tr>
          </table>
        </td></tr>
      </table>
    </td></tr>
    """


def empty_state(msg):
    c = COLORS
    return f"""
    <tr><td style="padding:16px;text-align:center;color:{c['gray']};
                   font-size:13px;font-style:italic;">{msg}</td></tr>
    """


# ── Generación del HTML ────────────────────────────────────────────────────────

def generate_html(news_df, papers_df, weeks_back, week_label):
    c = COLORS
    now = datetime.datetime.now()

    n_news   = len(news_df)
    n_papers = len(papers_df)

    # Build news cards
    news_rows = "".join(news_card(r) for _, r in news_df.iterrows()) \
                if not news_df.empty \
                else empty_state("No se encontraron noticias de CCHEN en este período.")

    # Build CCHEN papers
    paper_rows = "".join(paper_card(r) for _, r in papers_df.iterrows()) \
                 if not papers_df.empty \
                 else empty_state("No hay publicaciones recientes registradas.")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Boletín Semanal CCHEN · {week_label}</title>
</head>
<body style="margin:0;padding:0;background:{c['bg']};font-family:Arial,Helvetica,sans-serif;">

<!-- WRAPPER -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['bg']};padding:20px 0;">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0"
       style="max-width:640px;width:100%;background:{c['white']};
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 8px rgba(0,0,0,0.08);">

  <!-- HEADER -->
  <tr>
    <td style="background:{c['blue_dark']};padding:32px 36px 28px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <div style="color:rgba(255,255,255,0.6);font-size:12px;letter-spacing:2px;
                        text-transform:uppercase;margin-bottom:6px;">
              Observatorio Tecnológico
            </div>
            <div style="color:{c['white']};font-size:26px;font-weight:700;
                        line-height:1.2;">
              Boletín Científico Semanal
            </div>
            <div style="color:rgba(255,255,255,0.75);font-size:14px;margin-top:6px;">
              Comisión Chilena de Energía Nuclear &nbsp;·&nbsp; {week_label}
            </div>
          </td>
          <td align="right" valign="top">
            <div style="color:rgba(255,255,255,0.5);font-size:11px;">
              Generado el {now.strftime("%-d %b %Y")}
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- RESUMEN EJECUTIVO -->
  <tr>
    <td style="background:{c['blue_light']};padding:16px 36px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:0 16px;">
            <div style="font-size:28px;font-weight:700;color:{c['blue_dark']};">{n_news}</div>
            <div style="font-size:12px;color:{c['gray']};">Noticias de CCHEN</div>
          </td>
          <td align="center" style="padding:0 16px;border-left:1px solid {c['border']};">
            <div style="font-size:28px;font-weight:700;color:{c['green']};">{n_papers}</div>
            <div style="font-size:12px;color:{c['gray']};">Publicaciones CCHEN</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- BODY -->
  <tr><td style="padding:8px 36px 36px;">
    <table width="100%" cellpadding="0" cellspacing="0">

      <!-- NOTICIAS CCHEN -->
      {section_header("CCHEN en la prensa", "📰")}
      {news_rows}

      <!-- PUBLICACIONES CCHEN -->
      {section_header("Publicaciones recientes de CCHEN", "📄")}
      <tr><td style="padding:0 0 8px;">
        <span style="font-size:12px;color:{c['gray']};">
          Últimas publicaciones científicas de investigadores CCHEN · Fuente: OpenAlex
        </span>
      </td></tr>
      {paper_rows}

    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:{c['blue_dark']};padding:20px 36px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <div style="color:rgba(255,255,255,0.6);font-size:11px;line-height:1.6;">
              Este boletín es generado automáticamente por el
              <strong style="color:rgba(255,255,255,0.85);">
                Observatorio Tecnológico CCHEN</strong>.<br>
              Los datos provienen de OpenAlex, arXiv y Google News.<br>
              Período cubierto: últimas {weeks_back} semana(s).
            </div>
          </td>
          <td align="right" valign="middle">
            <div style="color:rgba(255,255,255,0.4);font-size:10px;">cchen.cl</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

</table>
</td></tr>
</table>

</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generador de Boletín Semanal CCHEN")
    parser.add_argument("--weeks", type=int, default=1,
                        help="Cuántas semanas hacia atrás incluir (default: 1)")
    parser.add_argument("--all", action="store_true",
                        help="Incluir todo el historial disponible")
    parser.add_argument("--output", type=str, default=None,
                        help="Ruta de salida (default: Data/Boletines/boletin_YYYY-WNN.html)")
    args = parser.parse_args()

    weeks_back = 0 if args.all else args.weeks
    now        = datetime.datetime.now()
    year, week, _ = now.isocalendar()
    week_label = f"Semana {week} · {now.strftime('%B %Y').capitalize()}"

    print(f"Generando boletín: {week_label}")

    news_df   = load_news(weeks_back)
    papers_df = load_cchen_papers(n=5)

    print(f"  Noticias CCHEN:      {len(news_df)}")
    print(f"  Publicaciones CCHEN: {len(papers_df)}")

    html = generate_html(news_df, papers_df, weeks_back or "todas las", week_label)

    out_path = Path(args.output) if args.output else \
               OUT_DIR / f"boletin_{year}-S{week:02d}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n✓ Boletín guardado en: {out_path}")
    print(f"  Abre en tu navegador o adjunta al correo.")
    return str(out_path)


if __name__ == "__main__":
    main()
