"""API FastAPI do AIOps.

Rodar:  uvicorn app.main:app --reload --port 8000     (docs interativas em /docs)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .llm import DeepSeekClient
from .ranking import EVENT_TYPES
from .services import Services

Severity = Literal["critico", "alto", "medio", "baixo"]
EventType = Literal[
    "thumbs_up", "thumbs_down", "escalate", "resolve",
    "ack", "view_logs", "ask_about", "dwell",
]


class FeedbackIn(BaseModel):
    alert_id: str
    event: EventType
    user_id: str = "anon"
    role: str = "analista"
    position: int | None = Field(None, ge=1, description="posição do alerta na lista quando foi interagido")
    dwell_s: float | None = Field(None, ge=0)
    ts: datetime | None = None


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    user_id: str = "anon"
    role: str = "analista"
    record_interaction: bool = True


class LLMIn(BaseModel):
    provider: Literal["ollama", "deepseek", "off"]
    model: str | None = Field(None, pattern=r"^[\w.\-:/]{1,80}$")


class SummarizeIn(BaseModel):
    text: str = Field(min_length=3, max_length=20000)


def create_app(settings: Settings | None = None, llm: DeepSeekClient | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svc = Services(cfg, llm=llm)
        app.state.startup = {**svc.startup(), **({"indice_recuperado": True} if svc.vstore.recovered else {})}
        app.state.svc = svc
        yield

    app = FastAPI(title="AIOps API", version="1.0.0",
                  description="RAG sobre logs + ranking de relevância por interação dos usuários.",
                  lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    def svc_dep() -> Services:
        return app.state.svc

    def db_dep(svc: Services = Depends(svc_dep)):
        with svc.session() as s:
            yield s

    @app.get("/health")
    def health(svc: Services = Depends(svc_dep)):
        return {"status": "ok", "llm": svc.llm.enabled, "llm_provedor": svc.s.llm_provider, "llm_modelo": svc.s.llm_model if svc.s.llm_provider != "off" else None, "embeddings": svc.embedder.name,
                "vetores": svc.vstore.count(), "startup": app.state.startup}

    @app.get("/alerts")
    def alerts(sensitivity: float | None = Query(None, ge=0, le=1), severity: Severity | None = None,
               role: str | None = None, limit: int = Query(50, ge=1, le=200), with_logs: bool = True,
               explore: bool = Query(True, description="reserva a última vaga para o alerta com menos evidência"),
               svc: Services = Depends(svc_dep), db=Depends(db_dep)):
        return svc.list_alerts(db, sensitivity, severity, role, limit, with_logs, explore=explore)

    @app.get("/alerts/{alert_id}/logs")
    def alert_logs(alert_id: str, limit: int = Query(100, ge=1, le=500), svc: Services = Depends(svc_dep),
                   db=Depends(db_dep)):
        if not any(r["id"] == alert_id for r in svc.rank_all(db)):
            raise HTTPException(404, "alerta não encontrado")
        return {"alert_id": alert_id, "lines": svc._log_lines(db, alert_id, limit)}

    @app.get("/alerts/{alert_id}/explain")
    def explain(alert_id: str, role: str | None = None, svc: Services = Depends(svc_dep), db=Depends(db_dep)):
        out = svc.explain(db, alert_id, role)
        if out is None:
            raise HTTPException(404, "alerta não encontrado")
        return out

    @app.post("/feedback", status_code=201)
    def feedback(body: FeedbackIn, svc: Services = Depends(svc_dep), db=Depends(db_dep)):
        ok = svc.record(db, body.alert_id, body.event, body.user_id, body.role, body.position, body.dwell_s, body.ts)
        if not ok:
            raise HTTPException(404, "alerta não encontrado")
        return {"recorded": True, "alert": svc.explain(db, body.alert_id)}

    @app.post("/ask")
    def ask(body: AskIn, svc: Services = Depends(svc_dep), db=Depends(db_dep)):
        return svc.ask(db, body.question, body.user_id, body.role, body.record_interaction)

    @app.post("/summarize")
    def summarize(body: SummarizeIn, svc: Services = Depends(svc_dep)):
        return svc.summarize(body.text)

    @app.get("/logs")
    def logs(service: str | None = None, severity: str | None = None, incident: str | None = None,
             level: str | None = None, q: str | None = Query(None, max_length=100),
             limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
             svc: Services = Depends(svc_dep), db=Depends(db_dep)):
        return svc.list_logs(db, service, severity, incident, q, level, limit, offset)

    def llm_info(svc: Services) -> dict:
        cfg_ = svc.s
        local = svc.llm.local_status()
        return {
            "provider": cfg_.llm_provider, "model": cfg_.llm_model if cfg_.llm_provider != "off" else None,
            "enabled": svc.llm.enabled,
            "local": {**local, "model": cfg_.ollama_model, "installed": cfg_.ollama_model in local["models"]
                      or f"{cfg_.ollama_model}:latest" in local["models"]},
            "cloud": {"configured": bool(cfg_.deepseek_api_key), "model": cfg_.deepseek_model},
        }

    @app.get("/llm")
    def llm_get(svc: Services = Depends(svc_dep)):
        return llm_info(svc)

    @app.post("/llm")
    def llm_set(body: LLMIn, svc: Services = Depends(svc_dep)):
        """Liga/desliga o modelo local (ou a nuvem) sem reiniciar o servidor."""
        if body.model and body.provider == "ollama":
            svc.s.ollama_model = body.model
        elif body.model and body.provider == "deepseek":
            svc.s.deepseek_model = body.model
        svc.s.apply_provider(body.provider)
        return llm_info(svc)

    @app.post("/llm/warmup")
    def llm_warmup(svc: Services = Depends(svc_dep)):
        """Carrega o modelo na memória (a 1ª chamada de um modelo local é a mais lenta)."""
        import time
        t0 = time.time()
        try:
            svc.llm.chat([{"role": "user", "content": "Responda apenas: ok"}], max_tokens=5)
            return {"ok": True, "segundos": round(time.time() - t0, 1)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "erro": str(exc)}

    @app.get("/metrics")
    def metrics(svc: Services = Depends(svc_dep), db=Depends(db_dep)):
        return svc.metrics(db)

    @app.post("/admin/reindex")
    def reindex(svc: Services = Depends(svc_dep)):
        return svc.startup(force=True)

    @app.middleware("http")
    async def sem_cache_no_front(request, call_next):
        resp = await call_next(request)
        if request.url.path.startswith("/app"):
            resp.headers["Cache-Control"] = "no-cache"  # o navegador sempre revalida: nada de CSS/JS velho
        return resp

    web = Path(cfg.web_dir)
    if (web / "index.html").exists():  # front-end servido pela própria API: http://localhost:8000/app/
        app.mount("/app", StaticFiles(directory=str(web), html=True), name="web")

        @app.get("/", include_in_schema=False)
        def root():
            return RedirectResponse("/app/")

    return app


app = create_app()
