import httpx

from app.config import Settings
from app.llm import DeepSeekClient
from app.main import create_app
from fastapi.testclient import TestClient
from tests.conftest import make_settings


def test_health_e_indexacao(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["vetores"] == 1020 and h["llm"] is False


def test_alertas_ordenados_e_com_logs(client):
    r = client.get("/alerts").json()
    scores = [a["score"] for a in r["alerts"]]
    assert scores == sorted(scores, reverse=True)
    assert r["meta"]["total"] == 20 and r["alerts"][0]["position"] == 1
    assert "\n" in r["alerts"][0]["log"]


def test_sensibilidade_esconde_ruido_mas_nunca_critico(client):
    r = client.get("/alerts", params={"sensitivity": 0.99, "explore": False}).json()
    assert r["alerts"] and all(a["severity"] == "critico" for a in r["alerts"])
    assert r["meta"]["hidden"] == 16


def test_exploracao_reserva_a_ultima_vaga_para_quem_tem_menos_evidencia(client):
    r = client.get("/alerts", params={"sensitivity": 0.99}).json()
    assert r["alerts"][-1].get("exploration") is True and r["alerts"][-1]["severity"] != "critico"
    assert r["meta"]["shown"] == 5 and r["meta"]["hidden"] == 15


def test_feedback_muda_o_score_e_e_explicavel(client):
    antes = next(a for a in client.get("/alerts", params={"sensitivity": 0}).json()["alerts"] if a["id"] == "INC-018")
    for i in range(10):
        r = client.post("/feedback", json={"alert_id": "INC-018", "event": "thumbs_up", "user_id": f"u{i}"})
        assert r.status_code == 201
    depois = next(a for a in client.get("/alerts", params={"sensitivity": 0}).json()["alerts"] if a["id"] == "INC-018")
    assert depois["score"] > antes["score"] and depois["content_score"] == antes["content_score"]
    ex = client.get("/alerts/INC-018/explain").json()
    assert ex["events_by_type"] == {"thumbs_up": 10} and ex["breakdown"]["confidence_alpha"] > 0


def test_feedback_negativo_nao_esconde_critico(client):
    for i in range(30):
        client.post("/feedback", json={"alert_id": "INC-003", "event": "dismiss", "user_id": f"u{i}"})
    ids = [a["id"] for a in client.get("/alerts").json()["alerts"]]
    assert "INC-003" in ids


def test_feedback_valida_entrada(client):
    assert client.post("/feedback", json={"alert_id": "XXX", "event": "thumbs_up"}).status_code == 404
    assert client.post("/feedback", json={"alert_id": "INC-001", "event": "curtir"}).status_code == 422
    assert client.get("/alerts/XXX/explain").status_code == 404
    assert client.get("/alerts", params={"sensitivity": 2}).status_code == 422


def test_ask_retorna_fontes_e_registra_interacao(client):
    r = client.post("/ask", json={"question": "Por que o banco de dados está lento?", "user_id": "maria"}).json()
    assert r["mode"] == "extrativo" and r["incident"] == "INC-004"
    assert r["sources"] and {s["service"] for s in r["sources"]} & {"db-primary"}
    assert client.get("/alerts/INC-004/explain").json()["events_by_type"] == {"ask_about": 1}


def test_ask_sem_contexto_nao_inventa(client):
    r = client.post("/ask", json={"question": "xyzzy qwerty"}).json()
    assert r["mode"] == "sem_contexto" and r["sources"] == []


def test_ask_nao_traz_ruido_a_menos_que_peca(client):
    r = client.post("/ask", json={"question": "Houve problema na busca?", "record_interaction": False}).json()
    assert all(s["kind"] == "incident" or "Cache de consulta" not in s["text"] for s in r["sources"])


def test_summarize_por_regras(client):
    r = client.post("/summarize", json={"text": "ERROR payments-api Timeout after 30000ms; HTTP 502"}).json()
    assert r["severidade"] == "critico" and "payments-api" in r["servicos"] and r["mode"] == "regras"


def test_metrics(client):
    m = client.get("/metrics").json()
    assert m["logs_indexados"] == 1000 and m["alertas"] == 20 and m["ruido_pct"] == 15.0


# ---------------- DeepSeek (simulado com httpx.MockTransport) ----------------

def _app_with_llm(tmp_path, handler):
    s = make_settings(tmp_path, deepseek_api_key="sk-teste-123", deepseek_model="deepseek-teste")
    llm = DeepSeekClient(s, transport=httpx.MockTransport(handler))
    return create_app(s, llm=llm)


def test_ask_usa_deepseek_com_contexto_numerado(tmp_path):
    visto = {}

    def handler(req: httpx.Request):
        visto["auth"] = req.headers["authorization"]
        visto["body"] = req.read().decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": "O pool do banco esgotou [1]."}}]})

    with TestClient(_app_with_llm(tmp_path, handler)) as c:
        r = c.post("/ask", json={"question": "Por que o banco está lento?"}).json()
    assert r["mode"] == "llm" and r["model"] == "deepseek-teste" and "[1]" in r["answer"]
    assert visto["auth"] == "Bearer sk-teste-123" and "db-primary" in visto["body"] and "deepseek-teste" in visto["body"]


def test_falha_do_deepseek_cai_no_extrativo_sem_vazar_a_chave(tmp_path):
    with TestClient(_app_with_llm(tmp_path, lambda req: httpx.Response(500, text="boom sk-teste-123"))) as c:
        r = c.post("/ask", json={"question": "Por que o banco está lento?"}).json()
        s = c.post("/summarize", json={"text": "ERROR x-y timeout"}).json()
    assert r["mode"] == "extrativo" and "sk-teste" not in r["aviso"] and "HTTP 500" in r["aviso"]
    assert s["mode"] == "regras" and "sk-teste" not in str(s)


def test_resumo_com_deepseek(tmp_path):
    payload = '{"severidade":"alto","servicos":["orders-worker"],"causa_provavel":"fila lenta","acao_sugerida":"escalar consumidores"}'
    h = lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "```json\n" + payload + "\n```"}}]})
    with TestClient(_app_with_llm(tmp_path, h)) as c:
        s = c.post("/summarize", json={"text": "WARN orders-worker queue_depth=4800 lag=19m"}).json()
    assert s["mode"] == "llm" and s["severidade"] == "alto" and s["acao_sugerida"] == "escalar consumidores"


def test_ask_prioriza_o_incidente_do_servico_citado(client):
    r = client.post("/ask", json={"question": "O que causou a falha no payments-api?"}).json()
    assert r["incident"] == "INC-001"
    assert any(x["kind"] == "incident" and x["incident"] == "INC-001" for x in r["sources"])
    assert "INC-001" in r["answer"]


def test_indice_vetorial_se_recupera_quando_falha_ao_carregar(tmp_path, monkeypatch):
    from app import vectorstore as vs

    original, chamadas = vs.VectorStore._open, {"n": 0}

    def quebra_na_primeira(self):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("Error loading hnsw index")
        return original(self)

    monkeypatch.setattr(vs.VectorStore, "_open", quebra_na_primeira)
    v = vs.VectorStore(str(tmp_path / "c"), "x")
    assert v.healed and v.count() == 0
    v.add(["a"], ["doc"], [{"k": 1}], [[0.1] * 8])
    assert v.count() == 1


def test_logs_endpoint_filters(client):
    r = client.get("/logs", params={"service": "payments-api", "limit": 5}).json()
    assert r["total"] > 0 and len(r["items"]) <= 5
    assert all(i["service"] == "payments-api" for i in r["items"])
    r2 = client.get("/logs", params={"q": "timeout", "limit": 3}).json()
    assert all("timeout" in i["message"].lower() for i in r2["items"])


def test_metrics_has_database_block(client):
    b = client.get("/metrics").json()["banco"]
    assert b["motor"] and b["tabelas"]["rag_logs"] > 0


def test_modelo_local_ollama_sem_chave_e_sem_think(tmp_path):
    visto = {}

    def handler(req: httpx.Request):
        visto["url"] = str(req.url)
        visto["auth"] = req.headers.get("authorization")
        visto["body"] = req.read().decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": "<think>hmm</think>O pool esgotou [1]."}}]})

    s = make_settings(tmp_path, llm_provider="ollama", ollama_model="gemma3:4b", deepseek_api_key="")
    app = create_app(s, llm=DeepSeekClient(s, transport=httpx.MockTransport(handler)))
    with TestClient(app) as c:
        h = c.get("/health").json()
        r = c.post("/ask", json={"question": "Por que o banco está lento?"}).json()
    assert h["llm"] is True and h["llm_provedor"] == "ollama"
    assert r["mode"] == "llm" and r["provider"] == "ollama" and r["model"] == "gemma3:4b"
    assert r["answer"] == "O pool esgotou [1]." and visto["auth"] is None
    assert visto["url"] == "http://localhost:11434/v1/chat/completions" and "gemma3:4b" in visto["body"]


def test_ollama_desligado_cai_no_extrativo(tmp_path):
    def boom(req):
        raise httpx.ConnectError("recusado")

    s = make_settings(tmp_path, llm_provider="ollama")
    with TestClient(create_app(s, llm=DeepSeekClient(s, transport=httpx.MockTransport(boom)))) as c:
        r = c.post("/ask", json={"question": "Por que o banco está lento?"}).json()
    assert r["mode"] == "extrativo" and "Ollama" in r["aviso"]


def test_troca_de_provedor_em_execucao_e_status_do_ollama(tmp_path):
    def handler(req: httpx.Request):
        if req.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok local [1]"}}]})

    s = make_settings(tmp_path, llm_provider="deepseek", deepseek_api_key="")
    with TestClient(create_app(s, llm=DeepSeekClient(s, transport=httpx.MockTransport(handler)))) as c:
        assert c.get("/llm").json()["enabled"] is False
        r = c.post("/llm", json={"provider": "ollama", "model": "qwen2.5:3b"}).json()
        assert r["provider"] == "ollama" and r["enabled"] and r["local"]["online"] and r["local"]["installed"]
        a = c.post("/ask", json={"question": "Por que o banco está lento?"}).json()
        assert a["mode"] == "llm" and a["provider"] == "ollama" and a["model"] == "qwen2.5:3b"
        c.post("/llm", json={"provider": "off"})
        assert c.post("/ask", json={"question": "Por que o banco está lento?"}).json()["mode"] == "extrativo"
        assert c.post("/llm", json={"provider": "ollama", "model": "x; rm -rf"}).status_code == 422
