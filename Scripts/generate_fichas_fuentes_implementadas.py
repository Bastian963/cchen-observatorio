#!/usr/bin/env python3
"""Generate one-page source fact sheets for each implemented CCHEN source."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "Scripts" / "generate_fernanda_implemented_source_briefs.py"
OUTPUT_DIR = ROOT / "Docs" / "reports" / "fuentes_implementadas_observatorio" / "fichas_por_fuente"
LEGACY_OUTPUT_DIR = ROOT / "Docs" / "reports" / "fuentes_implementadas_observatorio" / "briefs_por_fuente"
INDEX_MD = OUTPUT_DIR / "indice_fichas_por_fuente.md"
LINKS_CSV = OUTPUT_DIR / "links_fichas_para_excel.csv"
LOGO_MIN = ROOT / "Docs" / "licitacion" / "assets" / "ministerio_energia_color.png"
LOGO_CCHEN = ROOT / "Docs" / "licitacion" / "assets" / "cchen360_logo_color.png"


def _load_base_module():
    spec = importlib.util.spec_from_file_location("implemented_source_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base_module()


SOURCE_DESCRIPTION_OVERRIDES = {
    "arxiv": "Repositorio abierto de preprints académicos. Sirve para detectar producción temprana antes de su publicación formal.",
    "crossref": "Infraestructura internacional de DOI académicos. Entrega metadatos bibliográficos, referencias, revistas, financiadores y enlaces por DOI.",
    "datacite_outputs": "Registro internacional de DOI para conjuntos de datos, programas y otros resultados de investigación distintos del artículo tradicional.",
    "europmc_works": "Repositorio y buscador biomédico europeo. Complementa PubMed con literatura, identificadores y enlaces a texto completo.",
    "inspire_works": "Base especializada en física de altas energías y áreas afines. Es útil para producción CCHEN en física, plasma y temas nucleares.",
    "openaire_outputs": "Infraestructura europea de ciencia abierta. Integra publicaciones, conjuntos de datos, proyectos, repositorios y relaciones entre resultados.",
    "orcid": "Registro global de identificadores persistentes de investigadores. Permite vincular personas, afiliaciones y obras declaradas.",
    "pubmed_works": "Base bibliográfica biomédica de NCBI. Aporta literatura en salud, medicina nuclear, radiofarmacia y ciencias de la vida.",
    "semantic_scholar": "Grafo académico con metadatos enriquecidos, autores, citas y relaciones semánticas entre publicaciones.",
    "unpaywall_oa": "Servicio abierto que informa si un DOI tiene versión de acceso abierto y dónde puede encontrarse.",
    "zenodo_outputs": "Repositorio generalista de CERN/OpenAIRE para conjuntos de datos, presentaciones, programas, afiches y otros resultados de investigación.",
    "patentsview_uspto": "Interfaz de consulta de patentes USPTO. Permite buscar propiedad industrial, inventores y solicitantes cuando existe credencial de acceso.",
    "radiofarmacia_cchen_seeded": "Paquete temático construido con semillas de radiofarmacia, compuestos, radionúclidos y literatura técnica abierta.",
    "clinvar": "Base biomédica de variantes clínicas. En esta etapa aparece solo como evidencia derivada de flujos de vida y salud.",
    "openalex": "Grafo académico abierto que conecta publicaciones, autores, instituciones, conceptos, citas, fuentes y financiadores.",
    "datos_gob_cl": "Portal chileno de datos abiertos. Aporta contexto institucional y registros públicos vinculables a CCHEN.",
    "genbank": "Base de secuencias genéticas de NCBI. En esta etapa queda como referencia derivada, no como extracción directa.",
    "gene_expression_omnibus_geo": "Repositorio de datos de expresión génica. Se documenta como evidencia derivada para flujos biomédicos.",
    "nih": "Ecosistema de información biomédica de NIH. En esta etapa se usa como referencia derivada, no como conexión directa propia.",
    "sequence_read_archive": "Repositorio de lecturas genómicas crudas. Queda documentado como fuente derivada para posibles líneas biomédicas.",
    "iaea_inis_monitor": "INIS/IAEA concentra literatura e información nuclear especializada. Sirve para vigilancia técnica nuclear.",
    "news_monitor": "Monitor local de noticias y señales públicas CCHEN/nuclear. Debe tratarse como vigilancia de prensa, no como dato financiero.",
}


def _tex(value: object) -> str:
    return base._latex_escape(value)


def _rel(path: Path) -> str:
    return os.path.relpath(path, OUTPUT_DIR)


def _path_item(path: str) -> str:
    text = base._text(path)
    text = text.replace("{", "").replace("}", "")
    return rf"\item \path{{{text}}}"


def _output_paths(row: dict[str, str]) -> list[str]:
    outputs = base._json_list(row.get("output_targets", ""))
    if outputs:
        return outputs[:4]
    key = row.get("source_key", "")
    if key in {"crossref", "openalex", "semantic_scholar", "pubmed_works", "europmc_works", "inspire_works", "arxiv"}:
        return ["Data/Publications/"]
    if key in {"datacite_outputs", "openaire_outputs", "zenodo_outputs"}:
        return ["Data/ResearchOutputs/"]
    if key in {"orcid"}:
        return ["Data/Researchers/"]
    if key in {"patentsview_uspto"}:
        return ["Data/Patents/"]
    if key in {"iaea_inis_monitor", "news_monitor"}:
        return ["Data/Vigilancia/"]
    return ["Data/Gobernanza/"]


def _short_text(value: str, max_len: int = 360) -> str:
    text = base._text(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip(" .,;") + "."


def _decision_label(code: str) -> str:
    return {
        "mantener": "Mantener",
        "mantener_con_observacion": "Mantener con nota",
        "bloqueada_por_token": "Bloqueada por credencial",
        "revisar_match": "Revisar correspondencia",
    }.get(code, code or "Revisar")


def _decision_color(code: str) -> str:
    return {
        "mantener": "okgreen",
        "mantener_con_observacion": "warnamber",
        "bloqueada_por_token": "badred",
        "revisar_match": "warnamber",
    }.get(code, "cchenpurple")


def _clean_for_public(text: str) -> str:
    clean = base._text(text)
    clean = clean.replace("Fernanda", "el equipo de curaduria")
    clean = clean.replace("consultora", "equipo de implementacion")
    clean = clean.replace("Consultora", "Equipo de implementacion")
    replacements = {
        "implementada_runtime": "implementada en registro operativo",
        "metadata-only": "solo metadatos",
        "CCHEN-only": "relacionada con CCHEN",
        "cchen-only": "relacionada con CCHEN",
        "filtro relacionada con CCHEN": "filtro de relación con CCHEN",
        "filtro relacionado con CCHEN": "filtro de relación con CCHEN",
        "outputs multiples": "varios archivos",
        "outputs múltiples": "varios archivos",
        "otros outputs": "otros resultados",
        "outputs": "resultados",
        "Outputs": "Resultados",
        "output": "resultado",
        "Output": "Resultado",
        "runtime": "registro operativo",
        "Runtime": "Registro operativo",
        "API key": "credencial",
        "API Key": "credencial",
        "PATENTSVIEW_API_KEY": "credencial PatentsView",
        "directa/API": "directa con interfaz",
        "Directa/API": "Directa con interfaz",
        "datasets": "conjuntos de datos",
        "Datasets": "Conjuntos de datos",
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean


def _public_code(source_key: str) -> str:
    code = base._text(source_key)
    replacements = {
        "datacite_outputs": "datacite",
        "europmc_works": "europe_pmc",
        "inspire_works": "inspire",
        "openaire_outputs": "openaire",
        "pubmed_works": "pubmed",
        "unpaywall_oa": "unpaywall",
        "zenodo_outputs": "zenodo",
        "radiofarmacia_cchen_seeded": "radiofarmacia_cchen",
        "gene_expression_omnibus_geo": "geo",
        "sequence_read_archive": "sra",
        "iaea_inis_monitor": "iaea_inis",
        "news_monitor": "noticias_cchen",
    }
    return replacements.get(code, code)


def _safe_decision(ctx: dict[str, str]) -> str:
    code = ctx["decision_code"]
    if code == "bloqueada_por_token":
        return "Mantener registrada como brecha operativa. Activar cuando exista credencial gratuita y separar claramente de INAPI local."
    if code == "revisar_match":
        return "Mantener solo como vigilancia de noticias si se confirma la correspondencia operativa; no usar como fuente financiera."
    if code == "mantener_con_observacion":
        return "Mantener como evidencia derivada o semilla. No presentarla como extractor directo hasta implementar conexion propia."
    return "Mantener como fuente implementada del observatorio y exigir refresco segun la frecuencia declarada."


def _field(ctx: dict[str, str], key: str, max_len: int = 360) -> str:
    return _tex(_short_text(_clean_for_public(ctx.get(key, "")), max_len=max_len))


def _source_description(row: dict[str, str], ctx: dict[str, str]) -> str:
    key = row.get("source_key", "")
    if key in SOURCE_DESCRIPTION_OVERRIDES:
        return SOURCE_DESCRIPTION_OVERRIDES[key]
    description = row.get("description") or row.get("especialidad") or ctx.get("data_offer", "")
    if description:
        return f"Fuente de informacion para {description.lower()}."
    return "Fuente de informacion registrada para complementar la extracción de datos relacionados con CCHEN del observatorio."


def _stats_text(row: dict[str, str], ctx: dict[str, str]) -> str:
    outputs = base._json_list(row.get("output_targets", ""))
    count = ctx["record_count_label"]
    quality = row.get("quality_score") or "sin score"
    status = row.get("last_run_status") or "sin estado"
    updated = row.get("last_updated") or row.get("updated_at") or "sin fecha"
    artifact_count = len(outputs) if outputs else len(_output_paths(row))
    text = (
        f"Registros obtenidos/evidencia: {count}. "
        f"Archivos locales generados o registrados: {artifact_count}. "
        f"Calidad registrada: {quality}. "
        f"Última actualización: {updated}. "
        f"Estado de corrida: {status}."
    )
    if ";" in base._text(row.get("record_count", "")):
        text += " Los valores múltiples corresponden a artefactos distintos; no deben sumarse como una sola tabla."
    return text


def _write_source_tex(row: dict[str, str], ctx: dict[str, str], tex_path: Path) -> None:
    outputs_tex = "\n".join(_path_item(path) for path in _output_paths(row))
    source_name = _tex(ctx["source_name"])
    source_key = _tex(_public_code(ctx["source_key"]))
    category = _tex(ctx["categoria"])
    records = _tex(_clean_for_public(ctx["record_count_label"]))
    frequency = _tex(_clean_for_public(ctx["frequency"]))
    status = _field(ctx, "operational_status", 170)
    tier = _tex(_clean_for_public(ctx["implementation_tier_label"]))
    decision_label = _tex(_decision_label(ctx["decision_code"]))
    decision_color = _decision_color(ctx["decision_code"])
    site_url = _tex(ctx["site_url"] or "sin URL registrada")
    api_url = _tex(ctx["api_url"] or "sin interfaz registrada")
    source_description = _tex(_short_text(_clean_for_public(_source_description(row, ctx)), 330))
    stats = _tex(_short_text(_clean_for_public(_stats_text(row, ctx)), 460))

    text = rf"""% !TeX program = pdflatex
\documentclass[9pt,a4paper]{{extarticle}}
\usepackage[spanish,es-nodecimaldot,es-noshorthands]{{babel}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage{{lmodern}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\usepackage[a4paper,left=0.92cm,right=0.92cm,top=0.7cm,bottom=0.76cm,headheight=9pt]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{tikz}}
\usetikzlibrary{{positioning,arrows.meta}}
\usepackage{{tcolorbox}}
\tcbuselibrary{{skins}}
\usepackage{{booktabs}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{enumitem}}
\usepackage{{fancyhdr}}
\usepackage{{hyperref}}
\usepackage{{url}}
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
  pdftitle={{Ficha de fuente de información - {source_name}}},
  pdfauthor={{CCHEN 360}}}}
\urlstyle{{same}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot[L]{{\scriptsize\color{{mutedgray}}Observatorio CCHEN 360 -- ficha de fuente de información}}
\fancyfoot[R]{{\scriptsize\color{{mutedgray}}\thepage}}
\renewcommand{{\headrulewidth}}{{0pt}}
\renewcommand{{\footrulewidth}}{{0.25pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{1.2pt}}
\hyphenpenalty=10000
\exhyphenpenalty=10000
\setlist[itemize]{{leftmargin=*,topsep=1pt,itemsep=0.2pt,parsep=0pt}}
\renewcommand{{\arraystretch}}{{1.04}}
\newcolumntype{{Y}}{{>{{\raggedright\arraybackslash}}X}}
\newcommand{{\sectiontitle}}[1]{{\vspace{{3pt}}{{\normalsize\bfseries\color{{cchenpurple}}#1}}\par\vspace{{1pt}}}}
\newtcolorbox{{keybox}}{{enhanced,colback=cchenpurple!5,colframe=cchenpurple,boxrule=0.5pt,arc=2pt,left=4pt,right=4pt,top=3pt,bottom=3pt}}
\newtcolorbox{{metricbox}}[2]{{enhanced,colback=#1!7,colframe=#1,boxrule=0.8pt,arc=2pt,left=5pt,right=5pt,top=4pt,bottom=4pt}}
\newtcolorbox{{calloutbox}}[1]{{enhanced,colback=lightgray,colframe=linegray,boxrule=0.4pt,arc=2pt,left=4pt,right=4pt,top=3pt,bottom=3pt,title={{#1}},fonttitle=\bfseries\footnotesize\color{{cchenpurple}},attach title to upper={{\par\vspace{{0.5pt}}}}}}
\newcommand{{\dotpattern}}{{\begin{{tikzpicture}}[remember picture,overlay]\foreach \x in {{0.2,0.55,...,11.2}} {{\foreach \y in {{-0.1,0.22,0.54,0.86}} {{\fill[cchenpurple!55] (\x,\y) circle (0.55pt); \fill[cchenlime!85] ({{\x+0.16}},{{\y+0.13}}) circle (0.48pt);}}}}\end{{tikzpicture}}}}

\begin{{document}}
\thispagestyle{{fancy}}

\begin{{minipage}}[t]{{0.34\textwidth}}
  \includegraphics[height=0.9cm]{{{_tex(_rel(LOGO_MIN))}}}
\end{{minipage}}
\begin{{minipage}}[t]{{0.36\textwidth}}
  \vspace{{0.08cm}}\dotpattern
\end{{minipage}}
\begin{{minipage}}[t]{{0.28\textwidth}}
  \raggedleft\includegraphics[height=0.9cm]{{{_tex(_rel(LOGO_CCHEN))}}}
\end{{minipage}}

\vspace{{0.11cm}}
{{\color{{cchenpurple}}\rule{{\textwidth}}{{1.5pt}}}}
\vspace{{0.05cm}}

\begin{{center}}
{{\fontsize{{16}}{{17.5}}\selectfont\bfseries\color{{cchenpurple}}{source_name}}}\\[-1pt]
{{\fontsize{{9.1}}{{10.4}}\selectfont\color{{textgray}}Ficha de fuente de información para datos relacionados con CCHEN}}\\[-1pt]
{{\fontsize{{7.8}}{{9}}\selectfont\color{{mutedgray}}Código: \texttt{{{source_key}}} \quad | \quad Categoría: {category}}}
\end{{center}}
\vspace{{0.01cm}}

\begin{{keybox}}
\textbf{{\color{{cchenpurple}}Mensaje operativo.}} Esta fuente se documenta solo para registros relacionados con CCHEN. No se descarga ni se usa el universo completo: el filtro opera por DOI, autor, afiliación, ROR/ORCID, alias institucional, resultados conocidos o semillas temáticas justificadas.
\end{{keybox}}

\vspace{{0.04cm}}
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{okgreen}}{{Datos obtenidos}}
{{\large\bfseries Datos obtenidos}}\par
{{\Large\bfseries {records}}}\par
{{\normalsize conteo registrado}}
\end{{metricbox}}
\end{{minipage}}\hfill
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{cchenpurple}}{{Frecuencia}}
{{\large\bfseries Frecuencia}}\par
{{\large\bfseries {frequency}}}\par
{{\normalsize refresco sugerido}}
\end{{metricbox}}
\end{{minipage}}\hfill
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{warnamber}}{{Tipo}}
{{\large\bfseries Tipo}}\par
{{\normalsize\bfseries {tier}}}\par
{{\normalsize implementación}}
\end{{metricbox}}
\end{{minipage}}\hfill
\begin{{minipage}}{{0.24\textwidth}}
\begin{{metricbox}}{{{decision_color}}}{{Decisión}}
{{\large\bfseries Decisión}}\par
{{\normalsize\bfseries {decision_label}}}\par
{{\normalsize criterio operativo}}
\end{{metricbox}}
\end{{minipage}}

\vspace{{0.04cm}}
\begin{{minipage}}[t]{{0.48\textwidth}}\raggedright
\sectiontitle{{1. Descripción de la fuente}}
{source_description}

\sectiontitle{{2. Qué datos se descargaron}}
\begin{{calloutbox}}{{Tipología de datos}}
{_field(ctx, "data_typology", 260)}
\end{{calloutbox}}
\textbf{{Datos descargados para CCHEN.}} {_field(ctx, "downloaded_data", 330)}

\sectiontitle{{3. Cómo se filtra}}
{_field(ctx, "filter", 420)}

\sectiontitle{{4. Dónde quedó guardado}}
\begin{{itemize}}
{outputs_tex}
\end{{itemize}}

\sectiontitle{{5. Estadística de descarga}}
{stats}

\end{{minipage}}\hfill
\begin{{minipage}}[t]{{0.48\textwidth}}\raggedright
\sectiontitle{{6. Para qué sirve en el observatorio}}
\begin{{itemize}}
  \item \textbf{{Uso principal:}} {_field(ctx, "observatory_use", 330)}
  \item \textbf{{Potencial:}} {_field(ctx, "potential", 330)}
\end{{itemize}}

\sectiontitle{{7. Estado operativo}}
\begin{{calloutbox}}{{Estado}}
{status}
\end{{calloutbox}}
{_field(ctx, "state", 260)}

\sectiontitle{{8. Debilidades y riesgos}}
{_field(ctx, "weakness", 420)}

\sectiontitle{{9. Decisión}}
{_tex(_safe_decision(ctx))}

\end{{minipage}}

\vspace{{0.06cm}}
\begin{{tcolorbox}}[enhanced,colback=white,colframe=cchenpurple!55,boxrule=0.45pt,arc=2pt,left=6pt,right=6pt,top=5pt,bottom=5pt]
{{\bfseries\color{{cchenpurple}}Método replicable:}} tomar la fuente, filtrar solo datos relacionados con CCHEN, guardar el archivo local, revisar calidad y usar la evidencia para indicadores del observatorio.
\end{{tcolorbox}}

\vspace{{0.02cm}}
{{\scriptsize\color{{mutedgray}}Sitio: {site_url} \quad | \quad Interfaz de datos: {api_url}}}

\end{{document}}
"""
    tex_path.write_text(text, encoding="utf-8")


def _compile(tex_path: Path) -> Path:
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=tex_path.parent,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    for suffix in [".aux", ".log", ".out"]:
        path = tex_path.with_suffix(suffix)
        if path.exists():
            path.unlink()
    return tex_path.with_suffix(".pdf")


def _pdf_pages(pdf_path: Path) -> int:
    proc = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return 0


def _pdf_has_forbidden_text(pdf_path: Path) -> bool:
    proc = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    lowered = proc.stdout.lower()
    return "fernanda" in lowered or "consultora" in lowered


def _write_index(contexts: list[dict[str, str]]) -> None:
    lines = [
        "# Fichas individuales de fuentes implementadas",
        "",
        "Una hoja por fuente. Cada PDF resume descripcion de la fuente, datos descargados, estadistica obtenida, filtro de relación con CCHEN, archivos locales, utilidad, frecuencia, estado y decision operativa.",
        "",
        "| Fuente | Tipo | Frecuencia | Decision | PDF |",
        "| --- | --- | --- | --- | --- |",
    ]
    for ctx in contexts:
        pdf_name = f"ficha_fuente_{ctx['source_key']}.pdf"
        lines.append(
            f"| {ctx['source_name']} | {_clean_for_public(ctx['implementation_tier_label'])} | {_clean_for_public(ctx['frequency'])} | "
            f"{_decision_label(ctx['decision_code'])} | [{pdf_name}]({pdf_name}) |"
        )
    INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_links_csv(contexts: list[dict[str, str]]) -> None:
    with LINKS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_key", "source_name", "ficha_pdf", "nombre_link_sugerido"],
        )
        writer.writeheader()
        for ctx in contexts:
            pdf_path = OUTPUT_DIR / f"ficha_fuente_{ctx['source_key']}.pdf"
            writer.writerow(
                {
                    "source_key": ctx["source_key"],
                    "source_name": ctx["source_name"],
                    "ficha_pdf": str(pdf_path),
                    "nombre_link_sugerido": f"Ficha fuente - {ctx['source_name']}",
                }
            )


def _clean_old_outputs() -> None:
    patterns = [
        "policy_brief_*.pdf",
        "policy_brief_*.tex",
        "ficha_fuente_*.pdf",
        "ficha_fuente_*.tex",
        "indice_briefs_por_fuente.md",
        "indice_fichas_por_fuente.md",
        "links_fichas_para_excel.csv",
    ]
    for directory in [OUTPUT_DIR, LEGACY_OUTPUT_DIR]:
        if not directory.exists():
            continue
        for pattern in patterns:
            for path in directory.glob(pattern):
                if path.is_file():
                    path.unlink()


def _mirror_legacy_outputs() -> None:
    """Keep old links working while the canonical folder is fichas_por_fuente."""
    LEGACY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT_DIR.iterdir():
        if path.is_file() and path.suffix in {".pdf", ".tex", ".md", ".csv"}:
            shutil.copy2(path, LEGACY_OUTPUT_DIR / path.name)


def main() -> int:
    catalog_rows = base._read_csv(base.DEFAULT_CATALOG)
    runtime_rows = base._read_csv(base.DEFAULT_RUNTIME)
    sources = base.enrich_with_runtime(
        base.implemented_sources(catalog_rows),
        base.runtime_by_key(runtime_rows),
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _clean_old_outputs()

    contexts: list[dict[str, str]] = []
    errors: list[str] = []
    for row in sources:
        ctx = base.brief_context(row, OUTPUT_DIR)
        contexts.append(ctx)
        tex_path = OUTPUT_DIR / f"ficha_fuente_{ctx['source_key']}.tex"
        _write_source_tex(row, ctx, tex_path)
        pdf_path = _compile(tex_path)
        pages = _pdf_pages(pdf_path)
        if pages != 1:
            errors.append(f"{pdf_path.name}: {pages} paginas")
        if _pdf_has_forbidden_text(pdf_path):
            errors.append(f"{pdf_path.name}: contiene referencia prohibida")

    _write_index(contexts)
    _write_links_csv(contexts)
    _mirror_legacy_outputs()
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(f"[OK] fichas individuales generadas: {len(contexts)}")
    print(f"[OK] carpeta -> {OUTPUT_DIR.relative_to(ROOT)}")
    print(f"[OK] indice -> {INDEX_MD.relative_to(ROOT)}")
    print(f"[OK] links Excel -> {LINKS_CSV.relative_to(ROOT)}")
    print(f"[OK] copia compatibilidad -> {LEGACY_OUTPUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
