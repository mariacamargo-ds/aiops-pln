"""Orquestra banco, índice vetorial, ranking e RAG."""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import func, select

from . import rag, ranking
from .config import Settings
from .db import Alerta, EventoFeedback, Log, init_db, make_engine, make_session_factory
from .embeddings import make_embedder
from .ingest import ensure_ready
from .llm import DeepSeekClient
from .ranking import Event, Params
from .vectorstore import VectorStore


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Services:
    def __init__(self, settings: Settings, llm: DeepSeekClient | None = None, params: Params | None = None):
        self.s = settings
        self.params = params or Params()
        self.engine = make_engine(settings.database_url)
        self.Session = make_session_factory(self.engine)
        self.embedder = make_embedder(settings.embedder, settings.st_model)
        self.vstore = VectorStore(settings.chroma_dir, self.embedder.name)
        self.llm = llm or DeepSeekClient(settings)

    # ---------- ciclo de vida ----------
    def startup(self, force: bool = False) -> dict:
        init_db(self.engine)
        with self.Session() as s:
            return ensure_ready(s, self.vstore, self.embedder, self.s.dataset_csv, self.s.incidents_json, force)

    @contextmanager
    def session(self):
        with self.Session() as s:
            yield s

    # ---------- ranking ----------
    def _events(self, session, role: str | None = None) -> dict[str, list[Event]]:
        q = select(EventoFeedback)
        if role:
            q = q.where(EventoFeedback.papel == role)
        by: dict[str, list[Event]] = defaultdict(list)
        for e in session.scalars(q):
            by[e.alerta_id].append(Event(e.tipo, e.usuario, e.ts, e.posicao, e.dwell_s))
        return by

    def _log_lines(self, session, alerta_id: str, limit: int) -> list[str]:
        rows = session.scalars(
            select(Log).where(Log.alerta_id == alerta_id).order_by(Log.ts.desc(), Log.id.desc()).limit(limit)
        ).all()
        return [f"{l.ts:%Y-%m-%d %H:%M:%S} {l.nivel:<5} {l.servico} {l.mensagem}" for l in reversed(rows)]

    def rank_all(self, session, role: str | None = None, now: datetime | None = None) -> list[dict]:
        now = now or utcnow()
        ev = self._events(session, role)
        last = dict(
            session.execute(
                select(Log.alerta_id, func.max(Log.ts)).where(Log.alerta_id.is_not(None)).group_by(Log.alerta_id)
            ).all()
        )
        ref = session.scalar(select(func.max(Log.ts)))
        out = []
        for a in session.scalars(select(Alerta).order_by(Alerta.id)):
            sc = ranking.score(a.content_score, ev.get(a.id, []), now, self.params, a.severidade)
            minutes = int((ref - last[a.id]).total_seconds() // 60) if (ref and a.id in last) else 0
            out.append({
                "id": a.id, "service": a.servico, "severity": a.severidade, "title": a.titulo, "summary": a.resumo,
                "sla": a.sla, "grouped": a.agrupados, "minutesAgo": minutes,
                "score": round(sc.final, 4), "content_score": round(sc.content, 4),
                "engagement": round(sc.engagement, 4), "confidence": round(sc.alpha, 4),
                "events": round(sc.n_eff, 2), "floor_applied": sc.floor_applied,
                "protected": a.severidade == "critico", "model": a.modelo_id,
            })
        out.sort(key=lambda d: (-d["score"], d["id"]))
        return out

    def list_alerts(self, session, sensitivity: float | None = None, severity: str | None = None,
                    role: str | None = None, limit: int = 50, with_logs: bool = True,
                    now: datetime | None = None, explore: bool = False):
        """Lista os alertas visíveis. `explore` reserva a ÚLTIMA vaga para o alerta escondido de que o
        sistema tem menos evidência: sem isso, o que está abaixo do corte nunca recebe feedback e nunca
        poderia subir (viés de popularidade)."""
        sens = self.s.sensitivity_default if sensitivity is None else sensitivity
        ranked = self.rank_all(session, role, now)
        visible = [r for r in ranked if r["score"] >= sens or r["protected"]]
        if severity:
            visible = [r for r in visible if r["severity"] == severity]
        visible = visible[:limit]
        if explore and not severity and len(visible) < limit:
            ids = {r["id"] for r in visible}
            pool = [r for r in ranked if r["id"] not in ids]
            if pool:
                cand = min(pool, key=lambda r: (r["events"], -r["content_score"]))
                visible.append({**cand, "exploration": True})
        for i, r in enumerate(visible, 1):
            r["position"] = i
            if with_logs:
                r["log"] = "\n".join(self._log_lines(session, r["id"], 6))
        shown_ids = {r["id"] for r in visible}
        hidden = [r["id"] for r in ranked if r["id"] not in shown_ids] if not severity else []
        return {
            "alerts": visible,
            "meta": {"total": len(ranked), "shown": len(visible), "hidden": len(hidden), "sensitivity": sens,
                     "hidden_ids": hidden, "role": role, "explore": explore},
        }

    def explain(self, session, alert_id: str, role: str | None = None, now: datetime | None = None) -> dict | None:
        row = next((r for r in self.rank_all(session, role, now) if r["id"] == alert_id), None)
        if not row:
            return None
        evs = self._events(session, role).get(alert_id, [])
        p = self.params
        return {
            "id": alert_id, "score": row["score"],
            "breakdown": {"content": row["content_score"], "engagement": row["engagement"],
                          "confidence_alpha": row["confidence"], "effective_events": row["events"],
                          "floor_applied": row["floor_applied"]},
            "formula": "score = conteúdo + α·t·margem;  t = tanh(evidência líquida/escala);  α = α_max·n/(n+m);  piso para críticos",
            "events_by_type": dict(Counter(e.tipo for e in evs)),
            "params": {"half_life_h": p.half_life_h, "alpha_max": p.alpha_max, "prior_m": p.prior_m,
                       "floors": p.floors, "weights": ranking.EVENT_WEIGHTS},
        }

    def record(self, session, alert_id: str, tipo: str, usuario: str = "anon", papel: str = "analista",
               posicao: int | None = None, dwell_s: float | None = None, ts: datetime | None = None) -> bool:
        if tipo not in ranking.EVENT_WEIGHTS or session.get(Alerta, alert_id) is None:
            return False
        session.add(EventoFeedback(alerta_id=alert_id, usuario=usuario, papel=papel, tipo=tipo,
                                   posicao=posicao, dwell_s=dwell_s, ts=ts or utcnow()))
        session.commit()
        return True

    # ---------- RAG ----------
    def ask(self, session, question: str, usuario: str = "anon", papel: str = "analista", record: bool = True) -> dict:
        eng = {r["id"]: r["engagement"] for r in self.rank_all(session)}
        passages = rag.retrieve(question, self.vstore, self.embedder, self.s, self.params, eng,
                                lexical_guard=self.embedder.name.startswith("hash"))
        titles = {a.id: a.titulo for a in session.scalars(select(Alerta))}
        res = rag.answer(question, passages, self.llm, titles)
        incident = rag.dominant_incident(passages, question)
        if record and incident:
            self.record(session, incident, "ask_about", usuario, papel)
        res["incident"] = incident
        res["sources"] = [
            {"n": p.n, "id": p.id, "kind": p.kind, "service": p.service, "level": p.level, "ts": p.ts,
             "incident": p.incident, "text": p.text, "similarity": round(p.sim, 3)}
            for p in passages
        ]
        return res

    def summarize(self, text: str) -> dict:
        return rag.summarize(text, self.llm)

    # ---------- banco de dados ----------
    def db_info(self, session) -> dict:
        url = self.engine.url
        return {
            "motor": url.get_backend_name(),
            "nome": url.database if url.get_backend_name() != "sqlite" else "arquivo local",
            "tabelas": {
                "rag_alertas": session.scalar(select(func.count()).select_from(Alerta)) or 0,
                "rag_logs": session.scalar(select(func.count()).select_from(Log)) or 0,
                "rag_eventos_feedback": session.scalar(select(func.count()).select_from(EventoFeedback)) or 0,
            },
        }

    def list_logs(self, session, service=None, severity=None, incident=None, q=None, level=None,
                  limit: int = 50, offset: int = 0) -> dict:
        stmt = select(Log)
        if service: stmt = stmt.where(Log.servico == service)
        if severity: stmt = stmt.where(Log.severidade == severity)
        if incident: stmt = stmt.where(Log.alerta_id == incident)
        if level: stmt = stmt.where(Log.nivel == level.upper())
        if q: stmt = stmt.where(Log.mensagem.ilike(f"%{q}%"))
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = session.scalars(stmt.order_by(Log.ts.desc(), Log.id.desc()).limit(limit).offset(offset)).all()
        return {"total": total, "limit": limit, "offset": offset, "items": [
            {"id": l.id, "ts": l.ts.isoformat(sep=" "), "service": l.servico, "level": l.nivel,
             "severity": l.severidade, "message": l.mensagem, "incident": l.alerta_id, "relevant": l.relevante}
            for l in rows]}

    # ---------- métricas ----------
    def metrics(self, session) -> dict:
        ranked = self.rank_all(session)
        n_logs = session.scalar(select(func.count()).select_from(Log)) or 0
        n_rel = session.scalar(select(func.count()).select_from(Log).where(Log.relevante.is_(True))) or 0
        by_type = dict(session.execute(select(EventoFeedback.tipo, func.count()).group_by(EventoFeedback.tipo)).all())
        shown = [r for r in ranked if r["score"] >= self.s.sensitivity_default or r["protected"]]
        return {
            "logs_indexados": n_logs, "logs_relevantes": n_rel,
            "ruido_pct": round(100 * (1 - n_rel / n_logs), 1) if n_logs else 0.0,
            "alertas": len(ranked), "alertas_visiveis_na_sensibilidade_padrao": len(shown),
            "eventos_de_feedback": sum(by_type.values()), "eventos_por_tipo": by_type,
            "vetores_no_indice": self.vstore.count(), "embeddings": self.embedder.name,
            "llm": {"habilitado": self.llm.enabled, "modelo": self.s.llm_model if self.llm.enabled else None,
                    "provedor": self.s.llm_provider, "local": self.s.llm_is_local},
            "banco": self.db_info(session),
            "top5": [{"id": r["id"], "service": r["service"], "score": r["score"]} for r in ranked[:5]],
        }
