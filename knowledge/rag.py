# -*- coding: utf-8 -*-
"""本地向量 RAG：从原 local_vector_rag_analyzer 精简拷贝后改为医学分割域。"""
from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from knowledge.medseg_kb import iter_documents

try:
    import faiss

    FAISS_OK = True
except ImportError:
    FAISS_OK = False


class SimpleEmbeddings:
    """简单本地词哈希嵌入（ponytail: 够用的本地向量，换 sentence-transformers 若召回不够）。"""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_embedding(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._text_to_embedding(text)

    def _text_to_embedding(self, text: str) -> List[float]:
        words = text.lower().split()
        embedding = np.zeros(self.dimension, dtype=np.float32)
        for word in words:
            hash_val = hash(word) % self.dimension
            embedding[hash_val] += 1.0
        norm = float(np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()


class MedSegRAG:
    def __init__(self):
        self.embeddings = SimpleEmbeddings()
        self.docs = iter_documents()
        self.texts = [d["text"] for d in self.docs]
        vectors = np.array(self.embeddings.embed_documents(self.texts), dtype=np.float32)
        self._vectors = vectors
        self._index = None
        if FAISS_OK and len(vectors):
            dim = vectors.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            # 已归一化，内积=余弦
            self._index.add(vectors)

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        if not self.texts:
            return []
        q = np.array([self.embeddings.embed_query(query)], dtype=np.float32)
        if self._index is not None:
            scores, idxs = self._index.search(q, min(top_k, len(self.texts)))
            return [self.texts[i] for i in idxs[0] if i >= 0]
        # 无 faiss：暴力余弦
        sims = (self._vectors @ q[0])
        order = np.argsort(-sims)[:top_k]
        return [self.texts[i] for i in order]

    def build_context(self, query: str, top_k: int = 3) -> str:
        chunks = self.retrieve(query, top_k=top_k)
        if not chunks:
            return ""
        return "\n\n---\n\n".join(chunks)
