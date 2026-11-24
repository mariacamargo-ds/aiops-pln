"""Camada fina sobre o ChromaDB (índice vetorial persistente, distância de cosseno)."""
from __future__ import annotations

from pathlib import Path

import shutil

import shutil

import chromadb
from chromadb.config import Settings as ChromaSettings

COLLECTION = "aiops_logs"


class VectorStore:
    def __init__(self, path: str, embedder_name: str):
        self.path = Path(path)
        self.embedder_name = embedder_name
        self.recovered = False  # True quando o índice em disco estava ilegível e foi recriado
        self._connect()
        try:
            self.col = self._open()
            self.col.count()  # força a leitura do índice HNSW em disco
        except Exception:
            # índice corrompido (ex.: servidor encerrado no meio da escrita, pasta sincronizada pelo OneDrive):
            # ele é só um cache derivado do banco, então apagamos e deixamos o startup reconstruir
            self.recovered = True
            self._wipe()
            self._connect()
            self.col = self._open()

    @property
    def healed(self) -> bool:
        return self.recovered

    def _connect(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.path), settings=ChromaSettings(anonymized_telemetry=False))

    def _wipe(self) -> None:
        try:
            from chromadb.api.shared_system_client import SharedSystemClient

            SharedSystemClient.clear_system_cache()
        except Exception:
            pass
        self.client = None
        shutil.rmtree(self.path, ignore_errors=True)

    def _meta(self) -> dict:
        return {"hnsw:space": "cosine", "embedder": self.embedder_name}

    def _open(self):
        col = self.client.get_or_create_collection(COLLECTION, metadata=self._meta())
        if (col.metadata or {}).get("embedder") != self.embedder_name:
            # trocou o modelo de embeddings: os vetores antigos não servem mais
            self.client.delete_collection(COLLECTION)
            col = self.client.get_or_create_collection(COLLECTION, metadata=self._meta())
        return col

    def count(self) -> int:
        return self.col.count()

    def reset(self) -> None:
        self.client.delete_collection(COLLECTION)
        self.col = self.client.get_or_create_collection(COLLECTION, metadata=self._meta())

    def add(self, ids, docs, metas, embs, batch: int = 500) -> None:
        for i in range(0, len(ids), batch):
            self.col.add(
                ids=ids[i : i + batch], documents=docs[i : i + batch],
                metadatas=metas[i : i + batch], embeddings=embs[i : i + batch],
            )

    def query(self, emb, k: int) -> list[dict]:
        n = min(k, max(self.count(), 1))
        r = self.col.query(query_embeddings=[emb], n_results=n, include=["documents", "metadatas", "distances"])
        out = []
        for id_, doc, meta, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0]):
            out.append({"id": id_, "doc": doc, "meta": meta, "sim": 1.0 - float(dist)})
        return out

    def get(self, id_: str) -> dict | None:
        r = self.col.get(ids=[id_], include=["documents", "metadatas"])
        if not r["ids"]:
            return None
        return {"id": r["ids"][0], "doc": r["documents"][0], "meta": r["metadatas"][0]}
