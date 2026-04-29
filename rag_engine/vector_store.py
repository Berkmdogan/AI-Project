"""
FAISS tabanlı vektör deposu.

Olay metinlerini ve metadata'larını saklar; semantik arama yapar.
"""
import json
import threading
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from loguru import logger

from config import settings
from rag_engine.embedder import get_embedder


class VectorStore:
    """Thread-safe FAISS vektör deposu."""

    def __init__(self):
        self._lock = threading.Lock()
        self._embedder = get_embedder()
        self._dim = self._embedder.dim

        self._index_path = Path(settings.faiss_index_path)
        self._meta_path = Path(settings.events_metadata_path)
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

        self._metadata: list[dict[str, Any]] = []
        self._index: faiss.Index = faiss.IndexFlatIP(self._dim)  # Inner Product (cosine ~ L2-normalized)

        self._load()
        logger.info(f"VectorStore hazır – {len(self._metadata)} kayıt yüklendi")

    # ── Ekleme ──────────────────────────────────────────────────────────────

    def add_event(self, event_text: str, metadata: dict[str, Any]) -> int:
        """Olayı vektör deposuna ekler. Yeni vectorun indeksini döndürür."""
        vec = self._embedder.embed(event_text)
        with self._lock:
            self._index.add(vec.reshape(1, -1))
            entry = {"text": event_text, **metadata}
            self._metadata.append(entry)
            idx = len(self._metadata) - 1
        self._save()
        return idx

    def add_events_batch(
        self, event_texts: list[str], metadatas: list[dict[str, Any]]
    ) -> list[int]:
        vecs = self._embedder.embed_batch(event_texts)
        with self._lock:
            self._index.add(vecs)
            start = len(self._metadata)
            for text, meta in zip(event_texts, metadatas):
                self._metadata.append({"text": text, **meta})
        self._save()
        return list(range(start, start + len(event_texts)))

    # ── Arama ───────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Sorguya en yakın olayları döndürür.
        Her sonuç: {"text", "score", **original_metadata}
        """
        top_k = top_k or settings.top_k_results
        min_score = min_score if min_score is not None else settings.min_similarity_score

        if self._index.ntotal == 0:
            return []

        query_vec = self._embedder.embed(query).reshape(1, -1)
        k = min(top_k, self._index.ntotal)

        with self._lock:
            scores, indices = self._index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or float(score) < min_score:
                continue
            entry = dict(self._metadata[idx])
            entry["score"] = float(score)
            results.append(entry)
        return results

    # ── İstatistik ──────────────────────────────────────────────────────────

    @property
    def total_events(self) -> int:
        return self._index.ntotal

    def get_all_events(self) -> list[dict[str, Any]]:
        return list(self._metadata)

    # ── Kalıcılık ───────────────────────────────────────────────────────────

    def _save(self):
        with self._lock:
            faiss.write_index(self._index, str(self._index_path))
            with open(self._meta_path, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    def _load(self):
        if self._index_path.exists() and self._meta_path.exists():
            try:
                self._index = faiss.read_index(str(self._index_path))
                with open(self._meta_path, encoding="utf-8") as f:
                    self._metadata = json.load(f)
                logger.info(f"Mevcut index yüklendi: {self._meta_path}")
            except Exception as exc:
                logger.warning(f"Index yüklenemedi, sıfırlanıyor: {exc}")
                self._index = faiss.IndexFlatIP(self._dim)
                self._metadata = []

    def reset(self):
        with self._lock:
            self._index = faiss.IndexFlatIP(self._dim)
            self._metadata = []
        if self._index_path.exists():
            self._index_path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()
        logger.warning("VectorStore sıfırlandı")
