#!/usr/bin/env python3
"""Generate a one-page policy brief for implemented CCHEN-only data sources."""

from __future__ import annotations

import csv
import os
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "Docs" / "reports" / "fuentes_implementadas_observatorio"
COMMENTS_CSV = ROOT / "Data" / "Gobernanza" / "comentarios_excel_fernanda_recomendados.csv"
ASSETS_DIR = REPORT_DIR / "assets"
OUTPUT_TEX = REPORT_DIR / "policy_brief_fuentes_implementadas_observatorio.tex"
OUTPUT_PDF = REPORT_DIR / "policy_brief_fuentes_implementadas_observatorio.pdf"
LOGO_MIN = ROOT / "Docs" / "licitacion" / "assets" / "ministerio_energia_color.png"
LOGO_CCHEN = ROOT / "Docs" / "licitacion" / "assets" / "cchen360_logo_color.png"


def _read_rows() -> list[dict[str, str]]:
    with COMMENTS_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _tex(value: object) -> str:
    text = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _rel(path: Path) -> str:
    return os.path.relpath(path, REPORT_DIR)


def _top_sources(rows: list[dict[str, str]]) -> str:
    preferred = [
        "OpenAlex",
        "Crossref",
        "Semantic Scholar",
        "OpenAIRE",
        "PubChem",
        "Unpaywall",
        "arXiv",
        "IAEA (INIS)",
        "Zenodo",
        "ORCID",
    ]
    by_name = {row["source_name"]: row for row in rows}
    out = []
    for name in preferred:
        row = by_name.get(name)
        if row:
            out.append(f"{_tex(name)} ({_tex(row['record_count'])})")
    return "; ".join(out)


def _row_for(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    for row in rows:
        if row["source_key"] == key:
            return row
    return {}


def write_tex(rows: list[dict[str, str]]) -> None:
    total = len(rows)
    tier_counts = Counter(row["tipo_implementacion"] for row in rows)
    decision_counts = Counter(row["decision_operativa"] for row in rows)
    direct = tier_counts.get("Implementada directa/API", 0)
    derived = tier_counts.get("Implementada derivada/semilla", 0)
    local = tier_counts.get("Implementada runtime/local", 0)
    blocked = decision_counts.get("bloqueada_por_token", 0)
    review = decision_counts.get("revisar_match", 0)
    maintain = decision_counts.get("mantener", 0)
    observe = decision_counts.get("mantener_con_observacion", 0)
    top_sources = _top_sources(rows)

    crossref = _row_for(rows, "crossref")
    zenodo = _row_for(rows, "zenodo_outputs")
    radio = _row_for(rows, "radiofarmacia_cchen_seeded")
    patents = _row_for(rows, "patentsview_uspto")
    news = _row_for(rows, "news_monitor")

    content = rf"""% !TeX program = pdflatex
\documentclass[9pt,a4paper]{{extarticle}}
\usepackage[spanish,es-nodecimaldot,es-noshorthands]{{babel}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage{{lmodern}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\usepackage[a4paper,left=0.92cm,right=0.92cm,top=0.72cm,bottom=0.78cm,headheight=9pt]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{tikz}}
\usetikzlibrary{{positioning,arrows.meta}}
\usepackage{{multicol}}
\usepackage{{tcolorbox}}
\tcbuselibrary{{skins}}
\usepackage{{booktabs}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{enumitem}}
\usepackage{{fancyhdr}}
\usepackage{{hyperref}}
\usepackage{{microtype}}

\definecolor{{cchenpurple}}{{HTML}}{{483888}}
\definecolor{{cchenlime}}{{HTML}}{{DDDC40}}
\definecolor{{textgray}}{{HTML}}{{333333}}
\definecolor{{mutedgray}}{{HTML}}{{6F6F6F}}
\definecolor{{lightgray}}{{HTML}}{{F3F3F5}}
\definecolor{{linegray}}{{HTML}}{{D9D9DF}}
\definecolor{{okgreen}}{{HTML}}{{2E7D32}}
\definecolor{{warnamber}}{{HTML}}{{F9A825}}
\definecolor{{badred}}{{HTML}}{{C62828}}

\hypersetup{{colorlinks=true, linkcolor=cchenpurple, urlcolor=cchenpurple,
  pdftitle={{Brief ejecutivo - fuentes implementadas para extracción CCHEN-only}},
  pdfauthor={{CCHEN 360}}}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot[L]{{\scriptsize\color{{mutedgray}}Observatorio CCHEN 360 -- extracción CCHEN-only}}
\fancyfoot[R]{{\scriptsize\color{{mutedgray}}\thepage}}
\renewcommand{{\headrulewidth}}{{0pt}}
\renewcommand{{\footrulewidth}}{{0.25pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{1.3pt}}
\setlength{{\columnsep}}{{0.42cm}}
\hyphenpenalty=10000
\exhyphenpenalty=10000
\setlist[itemize]{{leftmargin=*,topsep=1pt,itemsep=0.15pt,parsep=0pt}}
\renewcommand{{\arraystretch}}{{1.02}}
\newcolumntype{{Y}}{{>{{\raggedright\arraybackslash}}X}}
\newcommand{{\sectiontitle}}[1]{{\vspace{{1pt}}{{\normalsize\bfseries\color{{cchenpurple}}#1}}\par\vspace{{0.2pt}}{{\color{{cchenlime}}\rule{{0.25\linewidth}}{{1.1pt}}}}\vspace{{0.8pt}}}}
\newcommand{{\tightsection}}[1]{{\vspace{{2pt}}{{\normalsize\bfseries\color{{cchenpurple}}#1}}\par}}
\newtcolorbox{{keybox}}{{enhanced,colback=cchenpurple!5,colframe=cchenpurple,boxrule=0.5pt,arc=2pt,left=4pt,right=4pt,top=3pt,bottom=3pt}}
\newtcolorbox{{metricbox}}[2]{{enhanced,colback=#1!8,colframe=#1,boxrule=0.5pt,arc=2pt,left=3pt,right=3pt,top=3pt,bottom=3pt,title={{#2}},fonttitle=\bfseries\tiny\color{{textgray}},coltitle=textgray}}
\newtcolorbox{{calloutbox}}[1]{{enhanced,colback=lightgray,colframe=linegray,boxrule=0.4pt,arc=2pt,left=4pt,right=4pt,top=3pt,bottom=3pt,title={{#1}},fonttitle=\bfseries\scriptsize\color{{cchenpurple}},attach title to upper={{\par\vspace{{0.5pt}}}}}}
\newcommand{{\dotpattern}}{{\begin{{tikzpicture}}[remember picture,overlay]\foreach \x in {{0.2,0.55,...,11.2}} {{\foreach \y in {{-0.1,0.22,0.54,0.86}} {{\fill[cchenpurple!55] (\x,\y) circle (0.55pt); \fill[cchenlime!85] ({{\x+0.16}},{{\y+0.13}}) circle (0.48pt);}}}}\end{{tikzpicture}}}}

\begin{{document}}
\thispagestyle{{fancy}}

\begin{{minipage}}[t]{{0.34\textwidth}}
  \includegraphics[height=0.92cm]{{{_tex(_rel(LOGO_MIN))}}}
\end{{minipage}}
\begin{{minipage}}[t]{{0.36\textwidth}}
  \vspace{{0.08cm}}\dotpattern
\end{{minipage}}
\begin{{minipage}}[t]{{0.28\textwidth}}
  \raggedleft\includegraphics[height=0.92cm]{{{_tex(_rel(LOGO_CCHEN))}}}
\end{{minipage}}

\vspace{{0.12cm}}
{{\color{{cchenpurple}}\rule{{\textwidth}}{{1.55pt}}}}
\vspace{{0.05cm}}

\begin{{center}}
{{\fontsize{{17}}{{18.5}}\selectfont\bfseries\color{{cchenpurple}}Fuentes implementadas para extracción CCHEN-only}}\\[-1pt]
{{\fontsize{{9.2}}{{10.6}}\selectfont\color{{textgray}}Qué se descargó, dónde quedó guardado y cómo alimenta el Observatorio CCHEN 360}}\\[-1pt]
{{\fontsize{{7.8}}{{9}}\selectfont\color{{mutedgray}}Fecha de corte: 20 de mayo de 2026}}
\end{{center}}
\vspace{{0.02cm}}

\begin{{keybox}}
\textbf{{\color{{cchenpurple}}Mensaje central.}} Se documentaron \textbf{{{total} fuentes implementadas}}: \textbf{{{direct} directas/API}}, \textbf{{{derived} derivadas por semillas}}, \textbf{{{local} runtime/local}}, \textbf{{{blocked} bloqueada por credencial}} y \textbf{{{review} match a revisar}}. No se descarga el universo completo de cada fuente: se extraen registros con señal CCHEN por DOI, autor, afiliación, ROR/ORCID, alias institucional o semillas temáticas justificadas.
\end{{keybox}}

\vspace{{0.02cm}}
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{okgreen}}{{Fuentes documentadas}}
{{\LARGE\bfseries {total}}}\\[-2pt]
{{\tiny implementadas o registradas}}
\end{{metricbox}}
\end{{minipage}}\hfill
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{cchenpurple}}{{Directas/API}}
{{\LARGE\bfseries {direct}}}\\[-2pt]
{{\tiny listas para mostrar primero}}
\end{{metricbox}}
\end{{minipage}}\hfill
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{warnamber}}{{Con observación}}
{{\LARGE\bfseries {observe + review + blocked}}}\\[-2pt]
{{\tiny semillas, token o match}}
\end{{metricbox}}
\end{{minipage}}\hfill
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{badred}}{{Bloqueo crítico}}
{{\LARGE\bfseries {blocked}}}\\[-2pt]
{{\tiny PatentsView requiere API key}}
\end{{metricbox}}
\end{{minipage}}

\begin{{minipage}}[t]{{0.48\textwidth}}

\sectiontitle{{1. Qué se descargó}}

\begin{{tabularx}}{{\linewidth}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.29\linewidth}}Y@{{}}}}
\toprule
\textbf{{Tipología}} & \textbf{{Datos descargados y uso}} \\
\midrule
Publicaciones y citas & OpenAlex, CrossRef, Semantic Scholar, PubMed, Europe PMC, INSPIRE y arXiv consolidan DOI, autores, afiliaciones, conceptos, citas, abstracts y preprints CCHEN. \\
Investigadores y acceso & ORCID mantiene perfiles de investigadores; Unpaywall marca acceso abierto por DOI. \\
Datasets y outputs & DataCite, OpenAIRE y Zenodo inventarian datasets, presentaciones, archivos y outputs asociados a CCHEN. \\
Bio/Farma nuclear & PubChem/radiofarmacia descarga semillas, compuestos/radionúclidos y literatura técnica; ClinVar, GenBank, GEO, NIH y SRA quedan como evidencia derivada. \\
Patentes & INAPI queda como base local; PatentsView/USPTO está registrado como fuente API, pero bloqueado hasta contar con credencial gratuita. \\
Institucional y vigilancia & Datos.gob.cl, IAEA INIS y noticias CCHEN/nuclear agregan convenios, acuerdos, registros nucleares y señales de vigilancia. \\
\bottomrule
\end{{tabularx}}

\begin{{calloutbox}}{{Volumen de evidencia}}
Conteos principales: {_tex(top_sources)}. Los valores múltiples son artefactos distintos y no se suman como una sola tabla.
\end{{calloutbox}}

\sectiontitle{{2. Dónde quedaron guardados}}

\begin{{itemize}}
  \item \textbf{{Publicaciones:}} \texttt{{Data/Publications/}}.
  \item \textbf{{Outputs:}} \texttt{{Data/ResearchOutputs/}}.
  \item \textbf{{Gobernanza/radiofarmacia:}} \texttt{{Data/Gobernanza/}}.
  \item \textbf{{Vigilancia/patentes:}} \texttt{{Data/Vigilancia/}} y \texttt{{Data/Patents/}}.
\end{{itemize}}

\end{{minipage}}\hfill
\begin{{minipage}}[t]{{0.48\textwidth}}

\sectiontitle{{3. Estado y frecuencia de descarga}}

\begin{{tabularx}}{{\linewidth}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.31\linewidth}}Y@{{}}}}
\toprule
\textbf{{Frecuencia}} & \textbf{{Fuentes}} \\
\midrule
Semanal & arXiv monitor, IAEA INIS y noticias CCHEN/nuclear. \\
Trimestral & OpenAlex, CrossRef, Semantic Scholar y radiofarmacia/semillas. \\
Semestral & ORCID, PubMed, Europe PMC, INSPIRE, DataCite, OpenAIRE, Unpaywall, Zenodo, datos institucionales y patentes. \\
\bottomrule
\end{{tabularx}}

\sectiontitle{{4. Uso para el observatorio}}

\begin{{itemize}}
  \item \textbf{{Producción científica:}} alimentar indicadores de publicaciones, autores, colaboración, citas, temas y acceso abierto.
  \item \textbf{{Radiofarmacia y medicina nuclear:}} vigilar compuestos, radionúclidos, literatura técnica y oportunidades temáticas.
  \item \textbf{{Vigilancia institucional:}} monitorear señales nucleares, prensa CCHEN/nuclear y oportunidades de posicionamiento.
  \item \textbf{{Gobernanza de datos:}} evidenciar qué fuentes ya existen, qué producen y qué requiere monitoreo.
\end{{itemize}}

\begin{{calloutbox}}{{Observaciones críticas}}
\textbf{{PatentsView/USPTO}} requiere \texttt{{PATENTSVIEW\_API\_KEY}} y no reemplaza INAPI local. \textbf{{Google Finance / News monitor}} debe revisarse: el runtime implementado monitorea noticias CCHEN/nuclear, no datos financieros. Las fuentes Life Sciences derivadas deben presentarse como evidencia temática hasta implementar extractores directos.
\end{{calloutbox}}

\sectiontitle{{5. Entregables}}
\textbf{{CSV operativo}}, \textbf{{briefs PDF}} y \textbf{{gráficos de estado}}. Cada respaldo incluye tipología, uso, frecuencia, estado, comentario y decisión.

\end{{minipage}}

\vspace{{0.08cm}}
\begin{{tcolorbox}}[enhanced,colback=white,colframe=cchenpurple!55,boxrule=0.45pt,arc=2pt,left=5pt,right=5pt,top=4pt,bottom=4pt]
{{\bfseries\color{{cchenpurple}}Método replicable de extracción:}}\hfill
\begin{{tikzpicture}}[baseline=-0.55ex, every node/.style={{font=\scriptsize, align=center}}]
\node[draw=cchenpurple,fill=cchenpurple!8,rounded corners=2pt,inner xsep=5pt,inner ysep=3pt] (a) {{Fuente API\\o archivo local}};
\node[draw=okgreen,fill=okgreen!8,rounded corners=2pt,inner xsep=5pt,inner ysep=3pt,right=0.32cm of a] (b) {{Filtro\\CCHEN-only}};
\node[draw=cchenpurple,fill=cchenpurple!8,rounded corners=2pt,inner xsep=5pt,inner ysep=3pt,right=0.32cm of b] (c) {{CSV local\\y runtime}};
\node[draw=warnamber,fill=warnamber!10,rounded corners=2pt,inner xsep=5pt,inner ysep=3pt,right=0.32cm of c] (d) {{Calidad\\y brechas}};
\node[draw=okgreen,fill=okgreen!8,rounded corners=2pt,inner xsep=5pt,inner ysep=3pt,right=0.32cm of d] (e) {{Indicador\\Observatorio}};
\draw[-{{Latex[length=2mm]}},cchenpurple] (a) -- (b);
\draw[-{{Latex[length=2mm]}},cchenpurple] (b) -- (c);
\draw[-{{Latex[length=2mm]}},cchenpurple] (c) -- (d);
\draw[-{{Latex[length=2mm]}},cchenpurple] (d) -- (e);
\end{{tikzpicture}}
\end{{tcolorbox}}
\end{{document}}
"""
    OUTPUT_TEX.write_text(content, encoding="utf-8")


def compile_pdf() -> None:
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", OUTPUT_TEX.name],
        cwd=REPORT_DIR,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    for suffix in [".aux", ".log", ".out"]:
        path = OUTPUT_TEX.with_suffix(suffix)
        if path.exists():
            path.unlink()


def main() -> int:
    rows = _read_rows()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_tex(rows)
    compile_pdf()
    print(f"[OK] policy brief TEX -> {OUTPUT_TEX.relative_to(ROOT)}")
    print(f"[OK] policy brief PDF -> {OUTPUT_PDF.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
