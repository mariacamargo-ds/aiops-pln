"""AIOps em Streamlit — a mesma aplicação (API + RAG + banco), com o MESMO design do front-end HTML.

Rodar (dentro de aiops-backend, com a venv ativa):   streamlit run streamlit_app.py

Como ele fala com o back-end:
  1) se a API estiver no ar (padrão http://localhost:8000), usa a API por HTTP;
  2) se não estiver, sobe o MESMO back-end dentro do processo do Streamlit (um comando só).
Para apontar para outra API:  set AIOPS_API=http://host:porta
"""
from __future__ import annotations

import html
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
import streamlit as st

from streamlit_style import CSS, LOGO

API_URL = os.getenv("AIOPS_API", "http://localhost:8000").rstrip("/")
USER, ROLE = "maria", "analista"
SEV = {"critico": "Crítico", "alto": "Alto", "medio": "Médio", "baixo": "Baixo"}
SUGESTOES = ["O que causou a falha no checkout hoje?", "O que aconteceu no payments-api?",
             "Houve problemas de autenticação nesta semana?", "Por que o banco de dados está lento?",
             "Quais serviços estão com incidentes críticos?", "O que mudou no frontend depois do último deploy?"]
PEOPLE = [("Equipe Plataforma", "payments-api, checkout-service"), ("Equipe Identidade", "auth-service"), ("Equipe Dados", "orders-worker, cache-redis")]
TIMELINE = [("13:40", "Deploy de payments-api"), ("13:47", "Erros 500 em checkout-service"), ("13:52", "Pool de conexões esgotado"), ("13:56", "Incidente aberto pelo AIOps")]
CONFUSION = dict(tp=412, fp=51, fn=33, tn=1504)
HISTORY = [("06/10", "Classificador v0.3 treinado — F1 0,81"), ("09/10", "Parser de logs (Drain) integrado"), ("12/10", "Classificador v0.4 treinado — F1 0,91")]
DIRECTOR = {"noise": dict(sistema=95, equipe=88, real=93), "mttr": dict(sistema=18, equipe=35, real=24), "severity7d": dict(critico=6, alto=14, medio=23, baixo=41)}
PAGES = [("gerente", "📋", "Gerente"), ("perguntar", "💬", "Perguntar"), ("dados", "🗄", "Dados e sistema"),
         ("config", "⚙️", "Configuração"), ("direcao", "📊", "Direção"), ("resumir", "📝", "Resumir logs")]

st.set_page_config(page_title="AIOps · Painel", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x))


def br(n: float, d: int = 2) -> str:
    return f"{n:.{d}f}".replace(".", ",")


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def H(markup: str):
    st.html(markup)


# ---------------------------------------------------------------- cliente do back-end
@st.cache_resource(show_spinner="Conectando ao back-end…")
def get_client():
    """Devolve (cliente, modo). Os dois clientes têm a mesma interface (.request/.json())."""
    try:
        c = httpx.Client(base_url=API_URL, timeout=150)
        if c.get("/health", timeout=2).json().get("status") == "ok":
            return c, "http"
    except Exception:  # noqa: BLE001
        pass
    from fastapi.testclient import TestClient
    from app.main import create_app

    tc = TestClient(create_app(), base_url="http://aiops.local")
    tc.__enter__()  # roda o startup: cria tabelas, carrega os logs e o índice vetorial
    return tc, "embutido"


client, MODE = get_client()


def api(method: str, path: str, **kw):
    try:
        r = client.request(method, path, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Falha ao chamar {path}: {exc}")
        return None


def provedor(r: dict) -> str:
    return ("🖥️ modelo local" if r.get("provider") == "ollama" else "☁ DeepSeek") + f" · {r.get('model')}"


# ---------------------------------------------------------------- blocos de HTML (iguais ao front-end original)
def head(eyebrow: str, title: str, desc: str):
    H(f"<header class='page-head'><div><div class='eyebrow'>{esc(eyebrow)}</div><h1>{esc(title)}</h1><p>{esc(desc)}</p></div>"
      f"<span class='live-tag'>ao vivo · API + banco</span></header>")


def kpi(label: str, value: str, hint: str, hl: bool = False) -> str:
    return (f"<div class='card kpi {'hl' if hl else ''}'><div class='label'>{esc(label)}</div>"
            f"<div class='value {'grad-text' if hl else ''}'>{esc(value)}</div><div class='hint'>{esc(hint)}</div></div>")


def kpi_row(items: list[str], cols: int = 4):
    H(f"<div class='grid g4' style='grid-template-columns:repeat({cols},1fr)'>{''.join(items)}</div>")


def badge(sev: str) -> str:
    return f"<span class='badge sev-{sev}'>{SEV[sev]}</span>"


def card_html(title: str, sub: str, body: str) -> str:
    return f"<div class='card'><h2>{esc(title)}</h2><p class='sub'>{sub}</p>{body}</div>"


def alert_top(a: dict) -> str:
    return (f"<div class='alert alert-body'><div class='alert-top'>{badge(a['severity'])}<span class='svc'>{esc(a['service'])}</span>"
            f"<span class='time'>há {a['minutesAgo']} min</span></div><strong class='alert-title'>{esc(a['title'])}</strong>"
            f"<p class='summary'>{esc(a['summary'])}</p><div class='alert-meta'>"
            f"<span class='score' title='Relevância = conteúdo + interação dos usuários'>relevância {br(a['score'])}"
            f"<span class='bar'><i style='width:{a['score'] * 100:.0f}%'></i></span></span><span>{a['grouped']} alertas agrupados</span>"
            f"<span title='Interações dos usuários (com decaimento)'>👥 {br(a['events'], 1)} interações</span>"
            + ("<span class='chip' title='Vaga de exploração: alerta com pouca evidência, para o sistema aprender'>🔎 em avaliação</span>" if a.get("exploration") else "")
            + ("<span class='chip' title='Alertas críticos nunca são escondidos'>🛡 crítico protegido</span>" if a.get("floor_applied") else "")
            + f"<span>SLA: {esc(a['sla'])}</span></div></div>")


def grouped_bars(title: str, unit: str, d: dict, mx: int, note: str) -> str:
    cols = [("sistema", "Estimativa do sistema", "#A992F5"), ("equipe", "Estimativa da equipe", "#F6B93B"), ("real", "Resultado real", "#34D6C3")]
    W, Ht, pad, bw, gap = 520, 230, 40, 90, 44
    x = pad + 34
    s = f"<svg viewBox='0 0 {W} {Ht}' role='img' aria-label='{esc(title)}'>"
    for f in (0, .5, 1):
        y = Ht - 30 - f * (Ht - 60)
        s += (f"<line x1='{pad}' x2='{W - 10}' y1='{y}' y2='{y}' stroke='rgba(255,255,255,.14)'/>"
              f"<text x='{pad - 6}' y='{y + 4}' fill='#A9A4E2' font-size='11' text-anchor='end'>{round(f * mx)}</text>")
    for k, label, col in cols:
        v = d[k]
        h = v / mx * (Ht - 60)
        y = Ht - 30 - h
        s += (f"<rect x='{x}' y='{y}' width='{bw}' height='{h}' rx='6' fill='{col}'/>"
              f"<text x='{x + bw / 2}' y='{y - 6}' fill='#F4F2FF' font-size='13' font-weight='700' text-anchor='middle' font-family='JetBrains Mono,monospace'>{v}{unit}</text>"
              f"<text x='{x + bw / 2}' y='{Ht - 12}' fill='#CFCBF7' font-size='11' text-anchor='middle'>{label.split(' ')[-1]}</text>")
        x += bw + gap
    legend = "".join(f"<span><i class='dot' style='background:{c[2]}'></i>{c[1]}</span>" for c in cols)
    return f"<div class='card chart-wrap'><h2>{esc(title)}</h2><p class='sub'>{esc(note)}</p>{s}</svg><div class='legend'>{legend}</div></div>"


# ---------------------------------------------------------------- estado e ações
ss = st.session_state
ss.setdefault("fb", {})
ss.setdefault("chat", [])
ss.setdefault("awaiting", False)
ss.setdefault("log_page", 0)


def send_feedback(alert_id: str, event: str, position: int | None):
    r = api("POST", "/feedback", json={"alert_id": alert_id, "event": event, "user_id": USER, "role": ROLE, "position": position})
    if r:
        ss["toast"] = f"Registrado · nova relevância {br(r['alert']['score'])}"


def cb_vote(alert_id: str, vote: str, position: int | None):
    cur = ss["fb"].get(alert_id)
    if cur == vote:  # clicar de novo desmarca (como no front-end HTML)
        ss["fb"].pop(alert_id, None)
        return
    ss["fb"][alert_id] = vote
    send_feedback(alert_id, "thumbs_up" if vote == "up" else "thumbs_down", position)


def cb_logs(alert_id: str, position: int | None):
    ss["open_log"] = alert_id
    send_feedback(alert_id, "view_logs", position)


@st.dialog("Logs brutos", width="large")
def logs_dialog(a: dict):
    H(f"<p class='sub' style='margin:0 0 10px'>{esc(a['service'])} · últimas linhas gravadas no banco de dados para este incidente.</p><pre class='log'>{esc(a.get('log', ''))}</pre>")


# ---------------------------------------------------------------- navegação
with st.sidebar:
    H(f"<div class='brand'>{LOGO}<span><b>AIOps</b><small>ruídos → informações pertinentes</small></span></div>")
    labels = {k: f"{ico}  {name}" for k, ico, name in PAGES}
    page = st.radio("Navegação", [k for k, _, _ in PAGES], format_func=labels.get, label_visibility="collapsed", key="nav")
    dot = "<i class='status-dot on'></i>API conectada" if MODE == "http" else "<i class='status-dot on'></i>Back-end embutido"
    H(f"<div class='side-foot'><span>Projeto 03 · OUTTECH · PLN<br>Fatec Cotia</span><span class='mono' style='font-size:12px'>{dot}</span></div>")

if t := ss.pop("toast", None):
    st.toast(t)


# ---------------------------------------------------------------- Gerente
def page_gerente():
    head("Painel do gerente", "Alertas que realmente importam",
         "O sistema filtra o ruído e ordena os incidentes pelo conteúdo dos logs e pela interação dos usuários.")
    m = api("GET", "/metrics")
    if m:
        kpi_row([kpi("Logs no banco", thousands(m["logs_indexados"]), f"tabela rag_logs · {m['banco']['motor']}"),
                 kpi("Logs relevantes", thousands(m["logs_relevantes"]), "após classificação"),
                 kpi("Ruído filtrado", f"{br(m['ruido_pct'], 1)}%", "redução de alertas", True),
                 kpi("Interações dos usuários", str(m["eventos_de_feedback"]), "alimentam o ranking")])
    H("<div style='height:16px'></div>")
    left, right = st.columns([1.6, 1], gap="medium")
    with right:
        rows = "".join(f"<tr><td><b>{esc(n)}</b><br><small style='color:var(--faint)'>{esc(r)}</small></td><td style='text-align:right'><a href='#'>Contato</a></td></tr>" for n, r in PEOPLE)
        H(card_html("Equipes e responsáveis", "Quem acionar em cada serviço.", f"<table class='t'><tbody>{rows}</tbody></table>"))
        tl = "".join(f"<li><time>{t}</time>{esc(x)}</li>" for t, x in TIMELINE)
        H(card_html("Linha do tempo", "Eventos do incidente principal.", f"<ol class='timeline'>{tl}</ol>"))
    with left:
        with st.container(key="card_main"):
            H("<h2>Incidentes priorizados</h2><p class='sub'>A relevância aprende com 👍, 👎, “Ver logs” e perguntas no chat. Críticos nunca somem.</p>")
            f1, f2, f3 = st.columns([1.4, 1, 1.3], vertical_alignment="bottom")
            sens = f1.slider("Sensibilidade", 0.0, 1.0, 0.5, 0.05)
            sev = f2.selectbox("Severidade", ["", "critico", "alto", "medio", "baixo"], format_func=lambda x: SEV.get(x, "Todas"))
            below = f3.checkbox("Mostrar abaixo do corte")
            params = {"sensitivity": sens, "role": ROLE}
            if sev:
                params["severity"] = sev
            data = api("GET", "/alerts", params=params)
            if not data:
                return
            if not data["alerts"]:
                H("<div class='empty'>Nenhum alerta nesta sensibilidade. Reduza a sensibilidade para ver mais itens.</div>")
            for a in data["alerts"]:
                with st.container(key=f"alert_{a['severity']}_{a['id']}"):
                    H(alert_top(a))
                    c = st.columns([1.5, 1, 1.45, 2.4])
                    pos = a["position"]
                    c[0].button("Ver logs brutos", key=f"log_{a['id']}", on_click=cb_logs, args=(a["id"], pos))
                    cur = ss["fb"].get(a["id"])
                    c[1].button("👍 Útil", key=f"up_{'on' if cur == 'up' else 'off'}_{a['id']}", on_click=cb_vote, args=(a["id"], "up", pos))
                    c[2].button("👎 Irrelevante", key=f"down_{'on' if cur == 'down' else 'off'}_{a['id']}", on_click=cb_vote, args=(a["id"], "down", pos))
            meta = data["meta"]
            H(f"<p class='sub' style='margin-top:10px'>{meta['shown']} de {meta['total']} incidentes visíveis · {meta['hidden']} abaixo do corte (críticos sempre aparecem).</p>")
            if below and meta["hidden_ids"]:
                allr = api("GET", "/alerts", params={"sensitivity": 0, "explore": False, "with_logs": False, "role": ROLE}) or {"alerts": []}
                H("".join(f"<div class='noise-row'><span class='badge' style='background:#4b4789'>Abaixo do corte</span> &nbsp;<b class='mono'>{esc(a['service'])}</b> · {esc(a['title'])} · relevância {br(a['score'])}</div>"
                          for a in allr["alerts"] if a["id"] in meta["hidden_ids"]))
    if aid := ss.pop("open_log", None):
        full = api("GET", "/alerts", params={"sensitivity": 0, "role": ROLE}) or {"alerts": []}
        a = next((x for x in full["alerts"] if x["id"] == aid), None)
        if a:
            logs_dialog(a)


# ---------------------------------------------------------------- Perguntar
def cb_ask(q: str | None = None):
    q = (q or ss.get("q_in", "")).strip()
    if q and not ss["awaiting"]:
        ss["chat"].append({"role": "user", "text": q})
        ss["awaiting"] = True


def page_perguntar():
    head("Perguntar aos logs", "Pergunte em linguagem natural",
         "RAG de verdade: a pergunta vira um vetor, o ChromaDB recupera os trechos mais parecidos e o modelo responde citando as fontes.")
    left, right = st.columns([1.6, 1], gap="medium")
    with right:
        with st.container(key="card_sugg"):
            H("<h2>Perguntas sugeridas</h2><p class='sub'>Clique para testar.</p>")
            with st.container(key="sugg"):
                for i, q in enumerate(SUGESTOES):
                    st.button(q, key=f"sg{i}", on_click=cb_ask, args=(q,))
            H("<p class='sub' style='margin-top:12px'>Se não houver logs relevantes, o sistema avisa em vez de inventar uma resposta. Cada pergunta também conta como interesse no incidente citado.</p>")
    with left:
        with st.container(key="card_chat"):
            with st.container(key="msg_bot_hello"):
                st.markdown("Olá! Pergunte sobre incidentes, serviços ou erros. Exemplo: “O que causou a falha no checkout hoje?”")
            for i, msg in enumerate(ss["chat"]):
                if msg["role"] == "user":
                    with st.container(key=f"msg_user_{i}"):
                        st.markdown(esc(msg["text"]))
                else:
                    with st.container(key=f"msg_bot_{i}"):
                        st.markdown(msg["text"])
                        if msg.get("chips"):
                            H(f"<div class='src'>{msg['chips']}</div>")
                        if msg.get("sources"):
                            with st.expander(f"{len(msg['sources'])} fonte(s) recuperadas do ChromaDB"):
                                for p in msg["sources"]:
                                    when = f" · {p['ts'][11:16]}" if p.get("ts") else ""
                                    inc = f" · {p['incident']}" if p.get("incident") else ""
                                    H(f"<div style='margin-bottom:8px'><span class='chip'>[{p['n']}] {esc(p['service'])}{when}{inc}</span>"
                                      f"<div class='mono' style='font-size:11px;color:var(--faint);margin-top:3px'>{esc(p['text'][:200])}</div></div>")
                        if msg.get("aviso"):
                            H(f"<small style='color:var(--faint)'>⚠ {esc(msg['aviso'])}</small>")
            if ss["awaiting"]:
                with st.container(key="msg_bot_typing"):
                    H("<div class='typing'><span></span><span></span><span></span></div>")
            with st.form("ask", clear_on_submit=True, border=False):
                c = st.columns([6, 1], vertical_alignment="bottom")
                c[0].text_input("Sua pergunta", key="q_in", placeholder="Digite sua pergunta…", label_visibility="collapsed")
                c[1].form_submit_button("Enviar", type="primary", on_click=cb_ask, width="stretch")
    if ss["awaiting"]:
        q = ss["chat"][-1]["text"]
        r = api("POST", "/ask", json={"question": q, "user_id": USER, "role": ROLE})
        if r:
            modo = provedor(r) if r["mode"] == "llm" else ("resposta extrativa (sem IA)" if r["mode"] == "extrativo" else "sem contexto")
            chips = f"<span class='chip' title='Modo de geração'>🤖 {esc(modo)}</span>" + (f"<span class='chip'>📎 {esc(r['incident'])}</span>" if r.get("incident") else "")
            ss["chat"].append({"role": "bot", "text": r["answer"], "chips": chips, "sources": r.get("sources"), "aviso": r.get("aviso")})
        ss["awaiting"] = False
        st.rerun()


# ---------------------------------------------------------------- Dados e sistema
def page_dados():
    head("Dados e sistema", "Do dado bruto à resposta", "Tudo o que a demo usa: banco relacional, índice vetorial, API e modelo de linguagem.")
    m = api("GET", "/metrics")
    if not m:
        return
    b, llm = m["banco"], m["llm"]
    llm_txt = (("🖥️ local · " if llm.get("local") else "☁ DeepSeek · ") + str(llm["modelo"])) if llm["habilitado"] else "sem IA (resposta extrativa)"
    H(card_html("Arquitetura em execução", "Cada caixa abaixo está respondendo agora.",
                f"<div class='arch'><span class='node ok'>🖥 Front-end (Streamlit)</span>→<span class='node ok'>⚙ API FastAPI ({MODE})</span>→"
                f"<span class='node ok'>🗄 {esc(b['motor'])} · {thousands(b['tabelas']['rag_logs'])} logs</span><span>+</span>"
                f"<span class='node ok'> ChromaDB · {thousands(m['vetores_no_indice'])} vetores ({esc(m['embeddings'])})</span>→"
                f"<span class='node {'ok' if llm['habilitado'] else ''}'>🤖 {esc(llm_txt)}</span></div>"))
    H("<div style='height:16px'></div>")
    ev = ' · '.join(f'{k}: {v}' for k, v in m['eventos_por_tipo'].items()) or 'ainda sem interações'
    kpi_row([kpi("Incidentes (rag_alertas)", str(b["tabelas"]["rag_alertas"]), "agrupam os logs"),
             kpi("Logs (rag_logs)", thousands(b["tabelas"]["rag_logs"]), f"{thousands(m['logs_relevantes'])} relevantes"),
             kpi("Interações (rag_eventos_feedback)", str(b["tabelas"]["rag_eventos_feedback"]), ev),
             kpi("Vetores no ChromaDB", thousands(m["vetores_no_indice"]), "busca por similaridade", True)])
    H("<div style='height:16px'></div>")
    services = sorted({a["service"] for a in (api("GET", "/alerts", params={"sensitivity": 0, "explore": False, "with_logs": False}) or {"alerts": []})["alerts"]})
    with st.container(key="card_logs"):
        H("<h2>Logs no banco de dados</h2><p class='sub'>Consulta direta à tabela <span class='mono'>rag_logs</span> pela rota <span class='mono'>GET /logs</span>.</p>")
        f = st.columns(4)
        q = f[0].text_input("Busca", placeholder="ex.: timeout")
        svc = f[1].selectbox("Serviço", ["Todos"] + services)
        sev = f[2].selectbox("Severidade", ["Todas", "critico", "alto", "medio", "baixo", "ruido"])
        lvl = f[3].selectbox("Nível", ["Todos", "ERROR", "WARN", "INFO"])
        size = 12
        sig = (q, svc, sev, lvl)
        if ss.get("log_sig") != sig:
            ss["log_sig"], ss["log_page"] = sig, 0
        params = {"limit": size, "offset": ss["log_page"] * size}
        for k_, v in (("q", q), ("service", svc if svc != "Todos" else ""), ("severity", sev if sev != "Todas" else ""), ("level", lvl if lvl != "Todos" else "")):
            if v:
                params[k_] = v
        r = api("GET", "/logs", params=params)
        if r:
            rows = "".join(f"<tr><td>{esc(x['ts'][5:16])}</td><td>{esc(x['service'])}</td><td class='lvl-{x['level']}'>{x['level']}</td><td>{esc(x['incident'] or '—')}</td><td>{esc(x['message'])}</td></tr>" for x in r["items"])
            H("<div style='overflow:auto'><table class='t logtable'><thead><tr><th>Horário</th><th>Serviço</th><th>Nível</th><th>Incidente</th><th>Mensagem</th></tr></thead>"
              f"<tbody>{rows or '<tr><td colspan=5>Nenhum log com esses filtros.</td></tr>'}</tbody></table></div>")
            off = params["offset"]
            p = st.columns([5, 1.2, 1.2], vertical_alignment="center")
            p[0].markdown(f"<div style='text-align:right;color:var(--faint);font-size:12.5px'>{min(off + 1, r['total']) if r['total'] else 0}–{min(off + size, r['total'])} de {thousands(r['total'])}</div>", unsafe_allow_html=True)
            if p[1].button("‹ Anterior", disabled=ss["log_page"] == 0, key="prev"):
                ss["log_page"] -= 1
                st.rerun()
            if p[2].button("Próxima ›", disabled=off + size >= r["total"], key="next"):
                ss["log_page"] += 1
                st.rerun()
    rows = "".join(f"<tr><td class='mono'>{esc(t['id'])}</td><td>{esc(t['service'])}</td><td class='mono'>{br(t['score'])}</td></tr>" for t in m["top5"])
    H(card_html("Top 5 incidentes agora", "Ordem calculada pelo conteúdo + interação dos usuários.",
                f"<table class='t'><thead><tr><th>Incidente</th><th>Serviço</th><th>Relevância</th></tr></thead><tbody>{rows}</tbody></table>"))


# ---------------------------------------------------------------- Configuração
def cb_provider(p: str):
    api("POST", "/llm", json={"provider": p})
    ss["toast"] = "Modelo alterado"


def page_config():
    head("Configuração e performance", "Desempenho do classificador", "Métricas do modelo, matriz de confusão e parâmetros do sistema.")
    c = CONFUSION
    tot = sum(c.values())
    acc, p_, r_ = (c["tp"] + c["tn"]) / tot, c["tp"] / (c["tp"] + c["fp"]), c["tp"] / (c["tp"] + c["fn"])
    f1 = 2 * p_ * r_ / (p_ + r_)
    kpi_row([kpi("Acurácia", f"{br(acc * 100, 1)}%", "acertos totais"), kpi("Precisão", f"{br(p_ * 100, 1)}%", "alertas marcados que eram relevantes"),
             kpi("Recall", f"{br(r_ * 100, 1)}%", "relevantes que foram encontrados"), kpi("F1-score", br(f1), "equilíbrio precisão/recall", True)])
    H("<div style='height:16px'></div>")
    a, b = st.columns(2, gap="medium")
    with a:
        H(card_html("Matriz de confusão", f"Conjunto de teste simulado ({tot} alertas).",
                    f"<div class='cm'><span></span><div class='h'>previsto relevante</div><div class='h'>previsto ruído</div>"
                    f"<div class='h'>real relevante</div><div class='ok'><b>{c['tp']}</b>verdadeiro positivo</div><div class='bad'><b>{c['fn']}</b>falso negativo</div>"
                    f"<div class='h'>real ruído</div><div class='bad'><b>{c['fp']}</b>falso positivo</div><div class='ok'><b>{c['tn']}</b>verdadeiro negativo</div></div>"
                    "<p class='sub' style='margin-top:12px'>Falso negativo é o erro mais grave: um alerta relevante tratado como ruído.</p>"))
    with b:
        with st.container(key="card_params"):
            H("<h2>Parâmetros do sistema</h2><p class='sub'>Salvos nesta sessão.</p>")
            p1, p2 = st.columns(2)
            p1.slider("Sensibilidade padrão", 0.0, 1.0, 0.5, 0.05, key="cfg_sens")
            p2.selectbox("Janela de agrupamento", ["5 minutos", "15 minutos", "1 hora"], index=1, key="cfg_win")
            st.checkbox("Agrupar alertas repetidos", value=True, key="cfg_grp")
            st.checkbox("Resumo diário por e-mail", value=True, key="cfg_mail")
            if st.button("Salvar configurações", type="primary", key="cfg_save"):
                st.toast("Configurações salvas.")
    st_ = api("GET", "/llm")
    if st_:
        with st.container(key="card_llm"):
            H("<h2>Modelo de linguagem</h2><p class='sub'>Escolha quem escreve as respostas. O modelo local é gratuito e roda no seu computador; a nuvem gasta tokens.</p>")
            loc, nuv = st_["local"], st_["cloud"]
            opts = [("ollama", "🖥️ **Local (gratuito)**", f"Ollama · {loc['model']}"),
                    ("deepseek", "☁ **Nuvem (DeepSeek)**", f"{nuv['model']} · paga por token" if nuv["configured"] else "chave não configurada"),
                    ("off", "**Sem IA**", "resposta extrativa, custo zero")]
            cols = st.columns(3)
            for col, (key, title, desc) in zip(cols, opts):
                col.button(f"{title}  \n{desc}", key=f"opt_{'on' if st_['provider'] == key else 'off'}_{key}", on_click=cb_provider, args=(key,), width="stretch")
            warn = ("⚠ Ollama não encontrado. Instale em ollama.com e deixe-o aberto." if not loc["online"]
                    else f"⚠ Modelo ainda não baixado. No PowerShell: <span class='mono'>ollama pull {esc(loc['model'])}</span>" if not loc["installed"]
                    else f"✔ {esc(loc['model'])} pronto")
            baixados = f"<br>Baixados: {esc(', '.join(loc['models']))}" if loc["models"] else ""
            H(f"<p class='sub' style='margin-top:12px'>Modelo local: {warn}{baixados}</p>")
            w = st.columns([1.2, 3])
            if w[0].button("🔥 Aquecer / testar modelo", disabled=st_["provider"] == "off", key="warm"):
                with st.spinner("Testando… (o 1º uso de um modelo local pode levar um minuto)"):
                    res = api("POST", "/llm/warmup")
                if res:
                    w[1].markdown(f"<span class='mono' style='font-size:12px'>{'✔ respondeu em ' + str(res['segundos']) + ' s' if res['ok'] else '✖ ' + esc(res['erro'])}</span>", unsafe_allow_html=True)
    hist = "".join(f"<li><time>{d}</time>{esc(t)}</li>" for d, t in HISTORY)
    H(card_html("Histórico de treinamento", "Versões do modelo (simulado).", f"<ol class='timeline'>{hist}</ol>"))


# ---------------------------------------------------------------- Direção
def page_direcao():
    head("Painel da direção", "Estimado × real", "Compara a previsão do sistema, a estimativa da equipe e o resultado real, para decidir com base em dados.")
    d = DIRECTOR
    H(f"<div class='grid g2'>{grouped_bars('Redução de ruído', '%', d['noise'], 100, 'Quanto maior, melhor.')}"
      f"{grouped_bars('Tempo médio de resolução (MTTR)', ' min', d['mttr'], 40, 'Quanto menor, melhor.')}</div><div style='height:16px'></div>")
    sv = d["severity7d"]
    tot, mx = sum(sv.values()), max(sv.values())
    colr = {"critico": "magenta", "alto": "amber", "medio": "lilac", "baixo": "teal"}
    rows = "".join(f"<tr><td>{badge(k)}</td><td class='mono'>{v}</td><td><div class='bar' style='width:100%;height:10px'><i style='width:{v / mx * 100:.0f}%;background:var(--{colr[k]})'></i></div></td></tr>" for k, v in sv.items())
    H(card_html("Incidentes por severidade (7 dias)", f"Total: {tot} incidentes.",
                f"<table class='t'><thead><tr><th>Severidade</th><th>Quantidade</th><th style='width:50%'>Proporção</th></tr></thead><tbody>{rows}</tbody></table>"))
    H("<div style='height:16px'></div>" + card_html("Leitura rápida", "",
      "<p style='color:var(--muted)'>O resultado real de redução de ruído (93%) ficou próximo da estimativa do sistema (95%) e acima da estimativa da equipe (88%). "
      "O MTTR real (24 min) ficou entre a previsão do sistema (18 min) e a da equipe (35 min).</p>"))


# ---------------------------------------------------------------- Resumir
def page_resumir():
    head("Plug-in · Resumir logs", "Resumo em linguagem natural", "Cole um trecho de log e receba severidade, causa provável e ação sugerida.")
    with st.container(key="card_sum"):
        if st.button("Exemplo do banco de dados", key="sum_ex"):
            al = (api("GET", "/alerts", params={"sensitivity": 0, "limit": 1}) or {"alerts": []})["alerts"]
            ss["texto_log"] = al[0]["log"] if al else ""
        text = st.text_area("Trecho de log", key="texto_log", height=170, placeholder="Cole aqui um trecho de log…")
        go = st.button("Resumir", type="primary", disabled=len(text.strip()) < 3, key="sum_go")
        if go:
            with st.spinner("Resumindo…"):
                r = api("POST", "/summarize", json={"text": text})
            if r:
                tag = provedor(r) if r["mode"] == "llm" else "regras locais"
                nums = f"<li><b>Valores detectados:</b> {esc(', '.join(r['numeros']))}</li>" if r.get("numeros") else ""
                chips = " ".join(f"<span class='chip'>{esc(s)}</span>" for s in r["servicos"])
                H(f"<div class='result'><h3>Resumo AIOps <span class='live-tag'>{esc(tag)}</span></h3><div>{badge(r['severidade'])} {chips}</div>"
                  f"<ul><li><b>Provável causa:</b> {esc(r['causa_provavel'])}</li><li><b>Ação sugerida:</b> {esc(r['acao_sugerida'])}</li>{nums}</ul>"
                  + (f"<small style='color:var(--faint)'>⚠ {esc(r['aviso'])}</small>" if r.get("aviso") else "") + "</div>")


{"gerente": page_gerente, "perguntar": page_perguntar, "dados": page_dados,
 "config": page_config, "direcao": page_direcao, "resumir": page_resumir}[page]()
