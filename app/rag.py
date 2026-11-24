"""RAG: recuperar trechos de log → (opcional) reordenar com o engajamento → gerar a resposta citando fontes."""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass

from .llm import DeepSeekClient, LLMError
from .lexicon import STOP, expand_query, mentioned_services, tokens
from .ranking import Params, retrieval_boost

SYSTEM_QA = (
    "Você é o assistente do AIOps, que ajuda equipes de operação a entender incidentes. "
    "Responda em português do Brasil, de forma objetiva (no máximo 5 frases), usando APENAS os trechos de "
    "contexto numerados. Cite as fontes no formato [n]. Se o contexto não for suficiente para responder, "
    "diga que não encontrou logs que respondam à pergunta. Não invente serviços, horários nem números."
)
SYSTEM_SUM = (
    "Você resume trechos de log para analistas. Responda SOMENTE um JSON com as chaves: "
    '"severidade" (critico|alto|medio|baixo), "servicos" (lista), "causa_provavel" (string curta) e '
    '"acao_sugerida" (string curta), em português do Brasil, com base apenas no texto fornecido.'
)


@dataclass
class Passage:
    n: int
    id: str
    kind: str
    service: str
    level: str
    ts: str
    incident: str
    text: str
    sim: float
    score: float


def retrieve(question: str, vstore, embedder, s, params: Params, engagement_by_inc: dict[str, float],
             lexical_guard: bool = True) -> list[Passage]:
    hits = vstore.query(embedder.embed_query(question), s.top_k * 4)  # pool largo: depois deduplica por template
    if not hits or max(h["sim"] for h in hits) < s.min_similarity:
        return []
    wanted = mentioned_services(question)
    qtok = {t for t in tokens(expand_query(question)) if t not in STOP}
    wants_noise = bool(re.search(r"ruido|rotina|rotineir", question.lower()))
    ranked = []
    for h in hits:
        m = h["meta"]
        if m["kind"] == "log" and not m["relevant"] and not wants_noise:
            continue  # ruído só entra no contexto se a pessoa perguntar por ele
        # com embeddings por hashing, colisões geram similaridade espúria: exige 1 termo em comum
        if lexical_guard and h["sim"] < 0.35 and not (qtok & set(tokens(h["doc"]))):
            continue
        sc = h["sim"]
        if m["service"] in wanted:
            sc += 0.15  # a pessoa citou o serviço
        if m["incident"] in engagement_by_inc:
            sc += retrieval_boost(engagement_by_inc[m["incident"]], params)  # feedback dos usuários
        if m["kind"] == "log" and not m["relevant"]:
            sc -= 0.10  # ruído rotulado (só chega aqui se a pessoa perguntou por ele)
        ranked.append((sc, h))
    if not ranked:
        return []
    ranked.sort(key=lambda x: -x[0])

    out: list[Passage] = []
    per_template: Counter = Counter()
    for sc, h in ranked:
        m = h["meta"]
        if m["kind"] == "log":
            if per_template[m["template"]] >= 2:  # evita 10 linhas quase idênticas
                continue
            per_template[m["template"]] += 1
        out.append(Passage(0, h["id"], m["kind"], m["service"], m["level"], m["ts"], m["incident"],
                           h["doc"], h["sim"], sc))
        if len(out) >= s.context_passages:
            break
    dom = dominant_incident(out, question)
    if dom and not any(p.kind == "incident" and p.incident == dom for p in out):
        got = vstore.get("inc:" + dom)  # o resumo do incidente principal sempre entra no contexto
        if got:
            m = got["meta"]
            out.append(Passage(0, got["id"], "incident", m["service"], "", "", dom, got["doc"], 0.0, 0.0))
    out.sort(key=lambda p: (p.kind != "incident", p.ts))  # resumo do incidente primeiro, depois cronológico
    for i, p in enumerate(out, 1):
        p.n = i
    return out


def dominant_incident(passages: list[Passage], question: str) -> str | None:
    """Incidente mais ligado à pergunta; trechos do serviço citado pela pessoa valem mais."""
    wanted = mentioned_services(question)
    sc: Counter = Counter()
    for p in passages:
        if p.incident:
            sc[p.incident] += 1 + (2 if p.service in wanted else 0)
    return sc.most_common(1)[0][0] if sc else None


def _fmt(p: Passage) -> str:
    when = p.ts[11:16] if p.ts else "resumo"
    lvl = f" · {p.level}" if p.level else ""
    inc = f" · {p.incident}" if p.incident else ""
    return f"[{p.n}] ({when} · {p.service}{lvl}{inc}) {p.text}"


def build_context(passages: list[Passage]) -> str:
    return "\n".join(_fmt(p) for p in passages)


def extractive_answer(passages: list[Passage], titles: dict[str, str], dom: str | None = None) -> str:
    logs = [p for p in passages if p.kind == "log"]
    incs = [p for p in passages if p.kind == "incident"]
    svc = Counter(p.service for p in passages).most_common(3)
    svc_txt = ", ".join(s for s, _ in svc)
    parts = [f"Encontrei {len(passages)} trecho(s) relacionado(s), principalmente em {svc_txt}."]
    if dom:
        parts.append(f"O incidente mais ligado é {dom}: {titles.get(dom, '')}".strip().rstrip(":") + ".")
    inc_p = next((p for p in incs if p.incident == dom), incs[0] if incs else None)
    if inc_p:
        parts.append(f"Resumo: {inc_p.text.split('. ', 1)[-1]} [{inc_p.n}]")
    if logs:
        last = max((p for p in logs if not dom or p.incident == dom), key=lambda p: p.ts, default=max(logs, key=lambda p: p.ts))
        parts.append(f"Registro mais recente ({last.ts[11:16]}): “{last.text.split(' ', 2)[-1]}” [{last.n}].")
    return " ".join(parts)


def answer(question: str, passages: list[Passage], llm: DeepSeekClient, titles: dict[str, str]) -> dict:
    if not passages:
        return {"answer": "Não encontrei logs que respondam a essa pergunta nos dados indexados.",
                "mode": "sem_contexto", "model": None}
    dom = dominant_incident(passages, question)
    if llm.enabled:
        try:
            text = llm.chat([
                {"role": "system", "content": SYSTEM_QA},
                {"role": "user", "content": f"Pergunta: {question}\n\nContexto:\n{build_context(passages)}"},
            ])
            return {"answer": text, "mode": "llm", "model": llm.s.llm_model, "provider": llm.s.llm_provider}
        except LLMError as exc:
            return {"answer": extractive_answer(passages, titles, dom), "mode": "extrativo",
                    "model": None, "aviso": str(exc)}
    return {"answer": extractive_answer(passages, titles, dom), "mode": "extrativo", "model": None}


# ---------------- resumo de logs colados pelo usuário (plug-in) ----------------

def rule_summary(text: str) -> dict:
    t = text.strip()
    low = t.lower()
    svcs = list(dict.fromkeys(re.findall(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b", t)))[:4]
    nums = [m.strip() for m in re.findall(r"\b\d+(?:[.,]\d+)?\s?(?:ms|%|min|h)\b", t)][:3]
    sev, cause, action = "baixo", "Evento informativo, sem indício de falha.", "Nenhuma ação imediata necessária."
    if re.search(r"timeout|exhausted|502|500|fatal|panic|outofmemory|crash|too many clients", low):
        sev, cause = "critico", "Indícios de indisponibilidade ou esgotamento de recursos (timeouts/erros 5xx)."
        action = "Acionar o time responsável e verificar o último deploy e os recursos do serviço."
    elif re.search(r"error|failed|queue|lag|retry", low):
        sev, cause = "alto", "Falhas recorrentes ou degradação de desempenho."
        action = "Investigar dependências do serviço e acompanhar por 15 minutos."
    elif re.search(r"warn|memory|backlog|slow|evict", low):
        sev, cause = "medio", "Alerta de capacidade ou atraso, ainda sem impacto direto."
        action = "Agendar verificação de capacidade."
    return {"severidade": sev, "servicos": svcs, "numeros": nums, "causa_provavel": cause, "acao_sugerida": action}


def summarize(text: str, llm: DeepSeekClient) -> dict:
    base = rule_summary(text)
    if not llm.enabled:
        return {**base, "mode": "regras", "model": None}
    try:
        raw = llm.chat([{"role": "system", "content": SYSTEM_SUM}, {"role": "user", "content": text[:6000]}],
                       max_tokens=400)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {}
        sev = data.get("severidade", base["severidade"])
        if sev not in ("critico", "alto", "medio", "baixo"):
            sev = base["severidade"]
        return {"severidade": sev, "servicos": data.get("servicos") or base["servicos"], "numeros": base["numeros"],
                "causa_provavel": data.get("causa_provavel") or base["causa_provavel"],
                "acao_sugerida": data.get("acao_sugerida") or base["acao_sugerida"],
                "mode": "llm", "model": llm.s.llm_model, "provider": llm.s.llm_provider}
    except (LLMError, ValueError):
        return {**base, "mode": "regras", "model": None, "aviso": "LLM indisponível; usei as regras locais"}
