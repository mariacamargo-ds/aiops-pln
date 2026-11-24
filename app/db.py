"""Modelos SQLAlchemy. Funciona com PostgreSQL (produção/demo) e SQLite (testes).

As tabelas levam o prefixo `rag_` para não colidir com as tabelas da Sprint 01
caso o back-end seja apontado para o mesmo banco `aiops`.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Alerta(Base):
    """Um incidente (grupo de logs relacionados) — é o 'alerta' mostrado ao usuário."""

    __tablename__ = "rag_alertas"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # INC-001
    servico: Mapped[str] = mapped_column(String(64), index=True)
    severidade: Mapped[str] = mapped_column(String(16))  # critico|alto|medio|baixo
    titulo: Mapped[str] = mapped_column(String(200))
    resumo: Mapped[str] = mapped_column(Text)
    sla: Mapped[str] = mapped_column(String(16), default="")
    content_score: Mapped[float] = mapped_column(Float, default=0.0)
    modelo_id: Mapped[str] = mapped_column(String(40), default="heuristica-v1")
    agrupados: Mapped[int] = mapped_column(Integer, default=0)
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Log(Base):
    __tablename__ = "rag_logs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # L0001
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    servico: Mapped[str] = mapped_column(String(64), index=True)
    nivel: Mapped[str] = mapped_column(String(8))
    severidade: Mapped[str] = mapped_column(String(16))  # inclui "ruido"
    mensagem: Mapped[str] = mapped_column(Text)
    alerta_id: Mapped[str | None] = mapped_column(ForeignKey("rag_alertas.id"), nullable=True, index=True)
    relevante: Mapped[bool] = mapped_column(Boolean, default=True)
    template_id: Mapped[str] = mapped_column(String(16), default="")
    embedding_id: Mapped[str] = mapped_column(String(32), default="")  # id do documento no ChromaDB


class EventoFeedback(Base):
    """Cada interação de um usuário com um alerta (explícita ou implícita)."""

    __tablename__ = "rag_eventos_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alerta_id: Mapped[str] = mapped_column(ForeignKey("rag_alertas.id"), index=True)
    usuario: Mapped[str] = mapped_column(String(64), default="anon")
    papel: Mapped[str] = mapped_column(String(32), default="analista")
    tipo: Mapped[str] = mapped_column(String(24))
    posicao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dwell_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)


Index("ix_evento_alerta_ts", EventoFeedback.alerta_id, EventoFeedback.ts)


def make_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(url, pool_pre_ping=True, future=True)


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
