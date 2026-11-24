# AIOps — Back-end (RAG + relevância por interação)

API em **FastAPI** que (1) responde perguntas sobre os logs com **RAG** (ChromaDB + DeepSeek) e
(2) ordena os alertas por uma **relevância aprendida com a interação dos usuários**, em vez de um limiar fixo.

```
 front-end (HTML)  ──HTTP──►  FastAPI ──► ranking.py  (score = conteúdo + engajamento, piso p/ críticos)
                                 │
                                 ├──► rag.py ──► ChromaDB (vetores)  ──► DeepSeek (resposta citando [n])
                                 └──► SQLAlchemy ──► PostgreSQL / SQLite (alertas, logs, eventos de feedback)
```

## Rodar (Windows · PowerShell)

```powershell
cd aiops-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # se bloquear: Set-ExecutionPolicy -Scope Process RemoteSigned
pip install -r requirements.txt

copy .env.example .env                 # abra o .env e preencha DEEPSEEK_API_KEY (e DEEPSEEK_MODEL)
uvicorn app.main:app --port 8000
```

Abra **http://127.0.0.1:8000/docs** — a documentação interativa permite testar tudo sem front-end.
Na 1ª subida a API carrega os 1.000 logs no banco e indexa 1.020 vetores (alguns segundos).

* **Sem chave do DeepSeek** a API funciona em modo *extrativo* (monta a resposta com os trechos recuperados).
  Com a chave, o campo `mode` da resposta passa a ser `"llm"`. Se o DeepSeek falhar, ela cai no extrativo sozinha.
* **PostgreSQL 18:** no `.env`, descomente `DATABASE_URL=postgresql+psycopg://postgres:SENHA@localhost:5432/aiops`.
  As tabelas têm prefixo `rag_` (`rag_alertas`, `rag_logs`, `rag_eventos_feedback`) e não colidem com as da Sprint 01.
* **Embeddings:** `EMBEDDER=hash` (padrão) não baixa nada. Para busca semântica de verdade:
  `pip install sentence-transformers` e `EMBEDDER=st`; a API reindexa sozinha ao detectar a troca.

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| GET | `/alerts?sensitivity=0.5&role=&severity=&explore=true` | alertas ordenados pelo score; `sensitivity` substitui o antigo limiar |
| GET | `/alerts/{id}/logs` | logs brutos do incidente |
| GET | `/alerts/{id}/explain` | **por que** o alerta tem este score (conteúdo, engajamento, α, eventos, piso) |
| POST | `/feedback` | registra uma interação (`thumbs_up`, `thumbs_down`, `view_logs`, `ack`, `resolve`, `escalate`, `dismiss`, `dwell`, `ask_about`) |
| POST | `/ask` | pergunta em linguagem natural → resposta + fontes numeradas |
| POST | `/summarize` | resume um trecho de log (plug-in) |
| GET | `/metrics` | contagens, % de ruído, eventos por tipo, top 5 |
| POST | `/admin/reindex` | recarrega o CSV e reconstrói o índice (mantém o feedback) |
| GET | `/health` | estado, modo do LLM, nº de vetores |

Exemplo (PowerShell):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ask -Method Post -ContentType 'application/json' `
  -Body '{"question":"Por que o banco de dados está lento?","user_id":"maria"}'

Invoke-RestMethod http://127.0.0.1:8000/feedback -Method Post -ContentType 'application/json' `
  -Body '{"alert_id":"INC-018","event":"thumbs_up","user_id":"maria","position":16}'
```

## Como a relevância é calculada

`score = conteúdo + α · t · margem`  (t = tanh da evidência líquida; margem = o quanto ainda cabe subir ou descer)

* **Conteúdo** (`content.py`): severidade, proporção de erros, volume e recência dos logs do incidente
  (`heuristica-v1`; é o ponto onde entra o classificador treinado).
* **Engajamento** (`ranking.py`): soma ponderada dos eventos — 👍/👎/escalar pesam ±3, resolver/reconhecer +2,
  abrir logs/perguntar +1, dispensar −2 — com:
  decaimento exponencial (meia-vida 24 h) · correção do viés de posição nos sinais implícitos ·
  retorno decrescente por usuário · suavização bayesiana (pouco dado ⇒ fica perto de 0,5).
* **α** cresce com a quantidade efetiva de eventos, até 0,6. Poucos votos movem pouco o score e muitos movem muito;
  👍 nunca reduz o score e 👎 nunca o aumenta.
* **Piso de segurança:** alertas críticos nunca ficam abaixo de 0,75 e **nunca são escondidos** — o feedback só os reordena.
* **Exploração:** a última vaga da lista vai para o alerta escondido com menos evidência, para que algo abaixo do corte
  possa ser descoberto (senão nunca receberia feedback).
* **No RAG:** o mesmo engajamento dá um bônus (±0,10) à similaridade dos trechos do incidente na busca.

Limitações assumidas: ainda não há usuários reais, então a avaliação usa **personas simuladas**
(`scripts/simulate_interactions.py`); os sinais implícitos são ruidosos (clicar ≠ achar útil); e a base é **sintética**.

## Testes e simulação

```powershell
python -m pytest -q                              # 26 testes (ranking, embeddings, API, DeepSeek simulado)
python scripts\simulate_interactions.py          # mostra o NDCG@5 subindo conforme os usuários interagem
```

## Estrutura

```
app/  main.py (rotas) · services.py · ranking.py · content.py · rag.py · llm.py
      embeddings.py · vectorstore.py · ingest.py · lexicon.py · db.py · config.py
data/ aiops_logs_sinteticos.csv · incidents.json
tests/  scripts/
```


## Demo completa (back-end + RAG + banco + front-end)

Um único comando sobe tudo e o front-end passa a ser servido pela própria API:

```powershell
cd aiops-backend
.\.venv\Scripts\Activate.ps1      # ou a sua venv (AIOps)
pip install -r requirements.txt
.\iniciar.ps1                       # abre http://localhost:8000/app/
```

- **Painel**: `/app/` (Gerente, Perguntar, Dados e sistema, Configuração, Direção) · **Plug-in**: `/app/plugin-demo.html`
- **Docs da API**: `/docs` · **Saúde**: `/health`
- **Banco**: PostgreSQL via `DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/aiops` (ou SQLite por padrão). As tabelas `rag_*` são criadas e populadas sozinhas na primeira execução.
- **RAG**: ChromaDB (índice recriado sozinho se estiver corrompido) + DeepSeek (`DEEPSEEK_API_KEY` no `.env`). Sem chave, a resposta é extrativa.
- Se a API estiver desligada, o front-end cai sozinho no modo simulado (etiqueta amarela). Para apontar o front-end para outra API: `?api=http://host:porta`.


## Modelo local (sem gastar tokens)

1. Instale o Ollama (ollama.com) e deixe-o aberto. 2. `ollama pull qwen2.5:3b` (notebook de 8 GB). 3. Na tela **Configuração → Modelo de linguagem**, escolha **Local (grátis)** e clique em "Aquecer / testar modelo".
Ou, no `.env`: `LLM_PROVIDER=ollama` (`deepseek` = nuvem, `off` = sem IA). A troca na tela vale na hora e não precisa reiniciar.
