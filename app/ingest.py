"""Carrega o dataset (CSV) + incidentes (JSON) no banco e no índice vetorial."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, func, select

from .content import content_score
from .db import Alerta, Log

FMT = "%Y-%m-%d %H:%M:%S"


def log_doc(servico: str, nivel: str, mensagem: str) -> str:
    return f"{servico} {nivel} {mensagem}"


def incident_doc(a: Alerta) -> str:
    return f"{a.servico} {a.severidade} {a.titulo}. {a.resumo}"


def load_db(session, csv_path: str, incidents_path: str) -> dict:
    """(Re)cria alertas e logs. Os eventos de feedback são preservados."""
    incs = json.load(open(incidents_path, encoding="utf-8"))
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    session.execute(delete(Log))  # os alertas são atualizados (merge): eventos de feedback ficam intactos
    session.flush()

    by_inc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["incident_id"]:
            by_inc[r["incident_id"]].append(r)
    ref_now = max(datetime.strptime(r["timestamp"], FMT) for r in rows)

    for i in incs:
        lines = by_inc.get(i["id"], [])
        ts = [datetime.strptime(r["timestamp"], FMT) for r in lines]
        session.merge(
            Alerta(
                id=i["id"], servico=i["service"], severidade=i["severity"], titulo=i["title"],
                resumo=i["summary"], sla=i.get("sla", ""),
                content_score=content_score(i["severity"], [r["level"] for r in lines], max(ts) if ts else None, ref_now),
                modelo_id="heuristica-v1", agrupados=len(lines), iniciado_em=min(ts) if ts else None,
            )
        )
    session.flush()
    for r in rows:
        session.add(
            Log(
                id=r["log_id"], ts=datetime.strptime(r["timestamp"], FMT), servico=r["service"], nivel=r["level"],
                severidade=r["severity"], mensagem=r["message"], alerta_id=r["incident_id"] or None,
                relevante=r["is_relevant"] == "1", template_id=r["template_id"], embedding_id="log:" + r["log_id"],
            )
        )
    session.commit()
    return {"alertas": len(incs), "logs": len(rows)}


def build_index(session, vstore, embedder) -> int:
    vstore.reset()
    ids, docs, metas = [], [], []
    for a in session.scalars(select(Alerta)):
        ids.append("inc:" + a.id)
        docs.append(incident_doc(a))
        metas.append({"kind": "incident", "incident": a.id, "service": a.servico, "severity": a.severidade,
                      "level": "", "ts": "", "template": "", "relevant": 1})
    for l in session.scalars(select(Log)):
        ids.append(l.embedding_id)
        docs.append(log_doc(l.servico, l.nivel, l.mensagem))
        metas.append({"kind": "log", "incident": l.alerta_id or "", "service": l.servico, "severity": l.severidade,
                      "level": l.nivel, "ts": l.ts.strftime(FMT), "template": l.template_id,
                      "relevant": 1 if l.relevante else 0, "log_id": l.id})
    embs = embedder.embed_docs(docs)
    vstore.add(ids, docs, metas, embs)
    return len(ids)


def ensure_ready(session, vstore, embedder, csv_path: str, incidents_path: str, force: bool = False) -> dict:
    out = {}
    n_alertas = session.scalar(select(func.count()).select_from(Alerta)) or 0
    if force or n_alertas == 0:
        out["db"] = load_db(session, csv_path, incidents_path)
    expected = (session.scalar(select(func.count()).select_from(Log)) or 0) + (
        session.scalar(select(func.count()).select_from(Alerta)) or 0
    )
    if force or vstore.count() != expected:
        out["index"] = build_index(session, vstore, embedder)
    return out
