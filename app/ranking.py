"""Relevância de um alerta aprendida pela INTERAÇÃO dos usuários (sugestão do professor).

score_final = conteúdo + α · t · margem        (t = tanh(evidência líquida); margem = 1−conteúdo se t>0, senão conteúdo)

* conteúdo     : estimativa feita só pelos logs (severidade, erros, volume, recência).
* evidência     : soma ponderada dos eventos dos usuários, com
                 - decaimento exponencial no tempo (meia-vida configurável);
                 - peso maior para feedback explícito (👍/👎) do que para sinais implícitos;
                 - correção do viés de posição nos sinais implícitos (IPW com teto);
                 - retorno decrescente por usuário/tipo (um usuário insistente não domina);
                 - suavização bayesiana: com pouca evidência o engajamento fica perto de 0,5.
* α            : confiança, cresce com a quantidade (efetiva) de eventos, até `alpha_max`.
* piso         : alertas críticos nunca ficam abaixo de um piso — o feedback só os REORDENA,
                 nunca os esconde (evita o ciclo "ninguém clica → some → ninguém clica").
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

EVENT_WEIGHTS: dict[str, float] = {
    "thumbs_up": 3.0,     # explícito
    "thumbs_down": -3.0,  # explícito
    "escalate": 3.0,      # explícito: levou a incidente para cima
    "resolve": 2.0,       # trabalhou e resolveu
    "ack": 2.0,           # reconheceu (assumiu)
    "view_logs": 1.0,     # implícito: abriu os logs brutos
    "ask_about": 1.0,     # implícito: perguntou no chat sobre o assunto
    "dwell": 0.0,         # implícito: peso vem do tempo (ver event_weight)
    "dismiss": -2.0,      # dispensou
}
IMPLICIT = {"view_logs", "dwell"}  # sujeitos ao viés de posição
EVENT_TYPES = tuple(EVENT_WEIGHTS)


@dataclass
class Params:
    half_life_h: float = 24.0
    alpha_max: float = 0.6
    prior_m: float = 5.0       # "quantos eventos valem o prior"
    scale: float = 4.0         # suaviza a sigmoide
    user_cap: int = 3          # eventos do mesmo tipo por usuário com peso cheio
    cap_decay: float = 0.25    # peso dos excedentes
    ipw_clip: float = 3.0
    floors: dict[str, float] = field(default_factory=lambda: {"critico": 0.75})
    retrieval_beta: float = 0.10  # intensidade do bônus de engajamento na busca do RAG


@dataclass
class Event:
    tipo: str
    usuario: str
    ts: datetime
    posicao: int | None = None
    dwell_s: float | None = None


@dataclass
class Score:
    final: float
    content: float
    engagement: float
    alpha: float
    n_eff: float
    raw: float
    floor_applied: bool


def event_weight(e: Event, p: Params) -> float:
    if e.tipo not in EVENT_WEIGHTS:
        raise ValueError(f"evento desconhecido: {e.tipo}")
    w = min((e.dwell_s or 0.0) / 30.0, 2.0) if e.tipo == "dwell" else EVENT_WEIGHTS[e.tipo]
    if e.tipo in IMPLICIT and e.posicao and e.posicao > 1:
        # quem clica lá embaixo da lista fez mais esforço: compensa a menor exposição
        w *= min(math.log2(e.posicao + 1), p.ipw_clip)
    return w


def aggregate(events: list[Event], now: datetime, p: Params) -> tuple[float, float]:
    raw = n_eff = 0.0
    seen: Counter = Counter()
    for e in sorted(events, key=lambda x: x.ts):
        age_h = max((now - e.ts).total_seconds() / 3600.0, 0.0)
        decay = 0.5 ** (age_h / p.half_life_h)
        seen[(e.usuario, e.tipo)] += 1
        cap = 1.0 if seen[(e.usuario, e.tipo)] <= p.user_cap else p.cap_decay
        raw += event_weight(e, p) * decay * cap
        n_eff += decay * cap
    return raw, n_eff


def engagement(raw: float, n_eff: float, p: Params) -> tuple[float, float]:
    s = 1.0 / (1.0 + math.exp(-raw / p.scale))
    eng = (n_eff * s + p.prior_m * 0.5) / (n_eff + p.prior_m)
    alpha = p.alpha_max * n_eff / (n_eff + p.prior_m)
    return eng, alpha


def score(content: float, events: list[Event], now: datetime, p: Params, severity: str | None = None) -> Score:
    raw, n_eff = aggregate(events, now, p)
    eng, alpha = engagement(raw, n_eff, p)
    # O sinal move o score a partir do conteúdo, na direção da evidência, usando a "margem" restante
    # (até 1 se for positivo, até 0 se for negativo). Assim 👍 nunca reduz e 👎 nunca aumenta o score.
    t = math.tanh(raw / p.scale)
    room = (1.0 - content) if t > 0 else content
    final = content + alpha * t * room
    floor = p.floors.get(severity or "")
    applied = floor is not None and final < floor
    if applied:
        final = floor
    return Score(final=final, content=content, engagement=eng, alpha=alpha, n_eff=n_eff, raw=raw, floor_applied=applied)


def retrieval_boost(eng: float, p: Params) -> float:
    """Bônus (−β…+β) somado à similaridade dos trechos de um incidente na busca do RAG."""
    return (eng - 0.5) * 2.0 * p.retrieval_beta
