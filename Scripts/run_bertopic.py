#!/usr/bin/env python3
"""
BERTopic — Análisis de temas de investigación CCHEN
Uso: python3 Scripts/run_bertopic.py
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent.parent / "Data" / "Publications"
VIZ  = Path(__file__).parent.parent / "Notebooks" / "analysis"
VIZ.mkdir(parents=True, exist_ok=True)

# ── Cargar abstracts consolidados ─────────────────────────────────────────────
df = pd.read_csv(BASE / "cchen_abstracts_merged.csv", low_memory=False)
df_abs = df[df["abstract_best"].notna() & (df["abstract_best"].str.len() > 60)].copy()
print(f"Papers con abstract: {len(df_abs)}")

# Documento = título + abstract
df_abs["doc"] = df_abs["title"].fillna("") + ". " + df_abs["abstract_best"].fillna("")
docs = df_abs["doc"].tolist()

# ── BERTopic ──────────────────────────────────────────────────────────────────
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer

print("Cargando modelo de embeddings (paraphrase-multilingual-MiniLM-L12-v2)...")
embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

umap_model = UMAP(n_neighbors=10, n_components=5, min_dist=0.0,
                  metric="cosine", random_state=42)

hdbscan_model = HDBSCAN(min_cluster_size=5, min_samples=3,
                         metric="euclidean", cluster_selection_method="eom",
                         prediction_data=True)

vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)

topic_model = BERTopic(
    embedding_model=embed_model,
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer,
    top_n_words=10,
    verbose=True,
)

print(f"\nAjustando BERTopic sobre {len(docs)} documentos...")
topics, probs = topic_model.fit_transform(docs)

n_topics = len(set(topics)) - 1
print(f"\n✓ Temas encontrados: {n_topics} (+ outliers)")

# ── Guardar resultados ────────────────────────────────────────────────────────
df_abs_out = df_abs[["openalex_id","title","year","abstract_best"]].copy()
df_abs_out["topic_id"]   = topics
df_abs_out["topic_prob"] = [float(p) if hasattr(p, '__float__') else 0.0 for p in probs]
df_abs_out.to_csv(BASE / "cchen_bertopic_topics.csv", index=False)
print(f"Guardado: cchen_bertopic_topics.csv")

topic_info = topic_model.get_topic_info()
topic_info.to_csv(BASE / "cchen_bertopic_topic_info.csv", index=False)
print(f"Guardado: cchen_bertopic_topic_info.csv")

# ── Visualizaciones HTML ──────────────────────────────────────────────────────
try:
    fig = topic_model.visualize_topics()
    fig.write_html(str(VIZ / "bertopic_mapa_temas.html"))
    print("Guardado: bertopic_mapa_temas.html")
except Exception as e:
    print(f"  visualize_topics error: {e}")

try:
    fig2 = topic_model.visualize_barchart(top_n_topics=min(16, n_topics))
    fig2.write_html(str(VIZ / "bertopic_palabras_clave.html"))
    print("Guardado: bertopic_palabras_clave.html")
except Exception as e:
    print(f"  visualize_barchart error: {e}")

try:
    years = df_abs["year"].fillna(0).astype(int).tolist()
    tot = topic_model.topics_over_time(docs, years, nr_bins=8)
    fig3 = topic_model.visualize_topics_over_time(tot, top_n_topics=min(10, n_topics))
    fig3.write_html(str(VIZ / "bertopic_temas_por_anio.html"))
    print("Guardado: bertopic_temas_por_anio.html")
except Exception as e:
    print(f"  topics_over_time error: {e}")

# ── Resumen en consola ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"TOP {min(20, n_topics)} TEMAS DE INVESTIGACIÓN CCHEN")
print("=" * 70)
print(f"{'#':>4}  {'Papers':>6}  Palabras clave")
print("-" * 70)
for _, row in topic_info[topic_info["Topic"] != -1].head(20).iterrows():
    words = [w for w, _ in topic_model.get_topic(row["Topic"])[:6]]
    print(f"{row['Topic']:>4}  {int(row['Count']):>6}  {', '.join(words)}")

n_out = sum(1 for t in topics if t == -1)
print(f"\nOutliers (sin tema): {n_out} ({100*n_out/len(topics):.1f}%)")
print("=" * 70)
