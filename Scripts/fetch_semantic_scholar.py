#!/usr/bin/env python3
"""
Descarga abstracts de Semantic Scholar para los 877 papers CCHEN.
Equivalente al notebook 10, pero ejecutable directamente.

Uso: python3 Scripts/fetch_semantic_scholar.py
"""

import pandas as pd
import requests
import time
import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "Data" / "Publications"
OUT  = BASE / "cchen_semantic_scholar.csv"

SS_API_KEY = None   # Opcional: pegar clave para mayor velocidad
BATCH_SIZE = 10
PAUSE_SECS = 4.0    # 100 req / 5min sin clave = ~3s mín. Usamos 4s por seguridad.

FIELDS = "paperId,externalIds,title,abstract,year,citationCount,isOpenAccess,fieldsOfStudy,tldr"


def query_batch(identifiers):
    url     = "https://api.semanticscholar.org/graph/v1/paper/batch"
    headers = {"x-api-key": SS_API_KEY} if SS_API_KEY else {}
    try:
        r = requests.post(url,
                          json={"ids": identifiers},
                          params={"fields": FIELDS},
                          headers=headers,
                          timeout=30)
        if r.status_code == 429:
            print("  rate-limit → esperando 60s...")
            time.sleep(60)
            r = requests.post(url, json={"ids": identifiers},
                              params={"fields": FIELDS}, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  error batch: {e}")
        return [None] * len(identifiers)


def build_id(row):
    doi = row.get("doi", "")
    if pd.notna(doi) and str(doi).startswith("10."):
        return f"DOI:{doi}"
    oa = str(row.get("openalex_id", ""))
    if "openalex.org/W" in oa:
        return f"OPENALEX:{oa.split('/')[-1]}"
    return None


def main():
    pub = pd.read_csv(BASE / "cchen_openalex_works.csv", low_memory=False)
    print(f"Papers totales: {len(pub)}")

    # Reanudar si hay progreso previo
    done_ids = set()
    if OUT.exists():
        ex = pd.read_csv(OUT)
        done_ids = set(ex["openalex_id"].dropna())
        print(f"Ya descargados: {len(done_ids)} → continuando desde ahí")

    pending = pub[~pub["openalex_id"].isin(done_ids)].to_dict("records")
    print(f"Pendientes: {len(pending)}")
    if not pending:
        print("Nada que descargar.")
        return

    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
    results = []

    for batch_i, i in enumerate(range(0, len(pending), BATCH_SIZE), start=1):
        batch = pending[i : i + BATCH_SIZE]
        ids   = [build_id(r) for r in batch]
        ids_clean = [x for x in ids if x]

        if not ids_clean:
            continue

        print(f"Batch {batch_i:3d}/{total_batches}  ({len(ids_clean)} IDs)...", end="  ")
        ss_data = query_batch(ids_clean)
        ss_by_id = {clean_id: ss for clean_id, ss in zip(ids_clean, ss_data)}

        # Alinear cada resultado con su ID original para no mezclar abstracts.
        for j, original in enumerate(batch):
            ss = ss_by_id.get(ids[j])
            if ss is None:
                ss = {}
            tldr_text = None
            if ss.get("tldr") and isinstance(ss["tldr"], dict):
                tldr_text = ss["tldr"].get("text")
            fos = ss.get("fieldsOfStudy") or []
            # fieldsOfStudy puede ser lista de strings o lista de dicts según versión API
            fos_str = ";".join(
                (f.get("category","") if isinstance(f, dict) else str(f)) for f in fos
            )
            results.append({
                "openalex_id":    original["openalex_id"],
                "doi":            original.get("doi"),
                "ss_paper_id":    ss.get("paperId"),
                "title":          original.get("title"),
                "year":           original.get("year"),
                "abstract":       ss.get("abstract"),
                "tldr":           tldr_text,
                "citation_count": ss.get("citationCount"),
                "is_oa":          ss.get("isOpenAccess"),
                "fields_of_study": fos_str,
            })

        n_abs = sum(1 for x in ss_data if x and x.get("abstract"))
        print(f"{n_abs}/{len(ids_clean)} con abstract")

        # Guardar cada 50 batches
        if batch_i % 50 == 0:
            _save(results, done_ids)
            results = []

        time.sleep(PAUSE_SECS)

    _save(results, done_ids)
    print("\nDescarga completada.")


def _save(new_rows, done_ids):
    if not new_rows:
        return
    df_new = pd.DataFrame(new_rows)
    if OUT.exists():
        df_old = pd.read_csv(OUT)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
        df_all = df_all.drop_duplicates(subset="openalex_id", keep="last")
    else:
        df_all = df_new

    df_all.to_csv(OUT, index=False)
    n_abs = df_all["abstract"].notna().sum()
    print(f"  → guardado ({len(df_all)} total, {n_abs} con abstract = {100*n_abs/len(df_all):.1f}%)")


if __name__ == "__main__":
    main()
