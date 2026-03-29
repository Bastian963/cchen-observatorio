"""Tests para data_loader — CCHEN Observatory"""
import sys
import pytest
import pandas as pd
sys.path.insert(0, str(__file__.replace('/Tests/test_data_loader.py', '/Dashboard')))

from data_loader import (
    load_publications, load_publications_enriched, load_authorships,
    load_anid, load_capital_humano, load_patents,
    load_unpaywall_oa, load_funding_complementario, load_iaea_tc,
    load_orcid_researchers, load_ror_registry, load_ror_pending_review,
    load_concepts, load_datacite_outputs, load_openaire_outputs,
    load_grants_openalex, load_perfiles_institucionales,
    load_matching_institucional, load_entity_registry_personas,
    load_entity_registry_proyectos, load_entity_registry_convocatorias,
    load_entity_links, load_publications_with_concepts,
    load_convenios_nacionales, load_acuerdos_internacionales,
    load_iaea_inis, load_dian_publications, load_crossref_enriched,
    load_data_sources_runtime, load_data_source_runs,
    get_source_timestamps, get_data_backend_info,
)

# Columnas mínimas esperadas por loader
EXPECTED_COLS = {
    "publications":        ["openalex_id", "title", "year", "cited_by_count"],
    "publications_enriched": ["work_id", "quartile"],
    "authorships":         ["work_id", "author_id"],
    "anid":                ["proyecto"],
    "unpaywall_oa":        ["doi", "oa_status"],
    "orcid_researchers":   ["orcid_id"],
    "ror_registry":        ["normalized_key"],
    "convenios_nacionales": ["id"],
    "acuerdos_internacionales": ["id"],
}

@pytest.mark.parametrize("loader_name,loader_fn,min_cols", [
    ("publications",            load_publications,            ["openalex_id", "title", "year"]),
    ("publications_enriched",   load_publications_enriched,   ["work_id"]),
    ("authorships",             load_authorships,             ["work_id"]),
    ("anid",                    load_anid,                    ["proyecto"]),
    ("capital_humano",          load_capital_humano,          ["nombre"]),
    ("patents",                 load_patents,                 []),
    ("unpaywall_oa",            load_unpaywall_oa,            ["doi"]),
    ("funding_complementario",  load_funding_complementario,  ["funding_id"]),
    ("iaea_tc",                 load_iaea_tc,                 []),
    ("orcid_researchers",       load_orcid_researchers,       ["orcid_id"]),
    ("ror_registry",            load_ror_registry,            ["normalized_key"]),
    ("ror_pending_review",      load_ror_pending_review,      []),
    ("concepts",                load_concepts,                []),
    ("datacite_outputs",        load_datacite_outputs,        []),
    ("openaire_outputs",        load_openaire_outputs,        []),
    ("grants_openalex",         load_grants_openalex,         []),
    ("perfiles_institucionales",load_perfiles_institucionales,[]),
    ("matching_institucional",  load_matching_institucional,  []),
    ("entity_personas",         load_entity_registry_personas,[]),
    ("entity_proyectos",        load_entity_registry_proyectos,[]),
    ("entity_convocatorias",    load_entity_registry_convocatorias,[]),
    ("entity_links",            load_entity_links,            []),
    ("pub_with_concepts",       load_publications_with_concepts,[]),
    ("convenios_nacionales",    load_convenios_nacionales,    []),
    ("acuerdos_internacionales",load_acuerdos_internacionales,[]),
    ("iaea_inis",               load_iaea_inis,               []),
    ("dian_publications",       load_dian_publications,       []),
    ("crossref_enriched",       load_crossref_enriched,       ["doi"]),
    ("data_sources_runtime",    load_data_sources_runtime,    ["source_key", "source_name"]),
    ("data_source_runs",        load_data_source_runs,        []),
])
def test_loader_returns_dataframe(loader_name, loader_fn, min_cols):
    """Cada loader debe retornar un DataFrame (puede estar vacío)."""
    df = loader_fn()
    assert isinstance(df, pd.DataFrame), f"{loader_name} no retornó DataFrame"
    for col in min_cols:
        assert col in df.columns, f"{loader_name}: columna '{col}' faltante"

def test_publications_has_data():
    df = load_publications()
    assert len(df) > 100, "Se esperan >100 publicaciones"

def test_authorships_has_data():
    df = load_authorships()
    assert len(df) > 1000, "Se esperan >1000 autorías"

def test_ror_registry_has_data():
    df = load_ror_registry()
    assert len(df) > 100, "Se esperan >100 instituciones en ROR"

def test_timestamps_returns_dict():
    ts = get_source_timestamps()
    assert isinstance(ts, dict)
    assert len(ts) > 0

def test_backend_info_returns_dict():
    info = get_data_backend_info()
    assert isinstance(info, dict)
