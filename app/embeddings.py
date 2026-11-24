"""Embeddings plugáveis.

* `hash`  — vetorização por hashing (unigramas + bigramas, sinal aleatório). Determinística,
            sem download e sem GPU: roda em qualquer máquina e serve para testes e demo offline.
* `st`    — sentence-transformers multilíngue (semântico de verdade). Baixa o modelo na 1ª execução.
"""
from __future__ import annotations

import math
import zlib
from collections import Counter

from .lexicon import STOP, expand_query, tokens


class HashEmbedder:
    dim = 1024
    name = "hash-1024"

    def _tokens(self, text: str) -> list[str]:
        toks = [t for t in tokens(text) if t not in STOP and not (t.isdigit() and len(t) > 4)]
        return toks + [a + "_" + b for a, b in zip(toks, toks[1:])]

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok, c in Counter(self._tokens(text)).items():
            h = zlib.crc32(tok.encode())
            v[h % self.dim] += (1 if (h >> 16) & 1 else -1) * (1 + math.log(c))
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_docs(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(expand_query(text))


class STEmbedder:
    def __init__(self, model: str):
        from sentence_transformers import SentenceTransformer  # import tardio: dependência opcional

        self._m = SentenceTransformer(model)
        self.name = f"st-{model}"

    def embed_docs(self, texts: list[str]) -> list[list[float]]:
        return self._m.encode(texts, normalize_embeddings=True, batch_size=64).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._m.encode([expand_query(text)], normalize_embeddings=True)[0].tolist()


def make_embedder(kind: str, st_model: str):
    if kind == "st":
        return STEmbedder(st_model)
    return HashEmbedder()
