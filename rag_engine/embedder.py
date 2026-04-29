"""
Sentence-Transformers tabanlı metin gömme (embedding) modülü.
Prompt caching'den yararlanmak için embed çağrıları toplu yapılır.
"""
from functools import lru_cache

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

from config import settings


class Embedder:

    def __init__(self):
        logger.info(f"Embedding modeli yükleniyor: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        self.dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding boyutu: {self.dim}")

    def embed(self, text: str) -> np.ndarray:
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.astype(np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vecs.astype(np.float32)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()
