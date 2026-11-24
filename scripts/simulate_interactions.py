"""Simula usuários interagindo com a lista de alertas e mede se o ranking aprende.

Sem usuários reais, validamos o mecanismo com personas que têm uma "relevância verdadeira" (oculta)
por incidente. A cada rodada, cada usuário vê a lista (com viés de posição), abre/avalia alguns alertas e
o sistema reordena. Métrica: NDCG@5 contra a relevância verdadeira.

    python scripts/simulate_interactions.py                # em memória (rápido)
    python scripts/simulate_interactions.py --url http://127.0.0.1:8000   # contra a API no ar
"""
from __future__ import annotations

import argparse
import math
import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# relevância "verdadeira" (0-3) segundo a equipe fictícia; o sistema NÃO conhece isto
TRUTH = {
    "INC-001": 3, "INC-002": 3, "INC-004": 3, "INC-003": 0,   # INC-003 é crítico, mas a equipe o ignora
    "INC-005": 2, "INC-006": 2, "INC-007": 3, "INC-008": 1, "INC-009": 3,
    "INC-010": 1, "INC-011": 1, "INC-012": 0, "INC-013": 1, "INC-014": 2, "INC-015": 1,
    "INC-016": 0, "INC-017": 0, "INC-018": 2, "INC-019": 0, "INC-020": 1,   # INC-018 (baixo) interessa à equipe
}


def ndcg_at(ids: list[str], k: int = 5) -> float:
    dcg = sum((2 ** TRUTH[i] - 1) / math.log2(r + 2) for r, i in enumerate(ids[:k]))
    ideal = sorted(TRUTH.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(r + 2) for r, g in enumerate(ideal))
    return dcg / idcg


class Local:
    def __init__(self):
        from fastapi.testclient import TestClient

        from app.config import Settings
        from app.main import create_app

        d = tempfile.mkdtemp()
        self._cm = TestClient(create_app(Settings(database_url=f"sqlite:///{d}/sim.db", chroma_dir=f"{d}/chroma")))
        self.c = self._cm.__enter__()

    def get(self, path, **params):
        return self.c.get(path, params=params).json()

    def post(self, path, body):
        return self.c.post(path, json=body)


class Remote:
    def __init__(self, url):
        import httpx

        self.c = httpx.Client(base_url=url, timeout=30)

    def get(self, path, **params):
        return self.c.get(path, params=params).json()

    def post(self, path, body):
        return self.c.post(path, json=body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--users", type=int, default=12)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--explore", default="true", choices=["true", "false"], help="vaga de exploração na lista")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    api = Remote(a.url) if a.url else Local()
    base = datetime.now(timezone.utc).replace(tzinfo=None)

    def lista(sens=0.0, explore="false"):
        return api.get("/alerts", sensitivity=sens, with_logs="false", explore=explore)["alerts"]

    def estado(rotulo):
        ids = [x["id"] for x in lista()]
        vis = {x["id"] for x in lista(0.5, 'false')}
        crit = {k for k, v in {x["id"]: x["severity"] for x in lista()}.items() if v == "critico"}
        print(f"{rotulo:<22} NDCG@5={ndcg_at(ids):.3f}  top5={ids[:5]}  críticos visíveis={len(crit & vis)}/{len(crit)}"
              f"  INC-018 posição={ids.index('INC-018') + 1}  INC-003 posição={ids.index('INC-003') + 1}")

    estado("antes (só conteúdo)")
    for rodada in range(1, a.rounds + 1):
        ts = base - timedelta(hours=(a.rounds - rodada) * 3)
        for u in range(a.users):
            user = f"user{u}"
            ver = lista(0.5, explore=a.explore)   # o que o usuário vê de verdade (com o corte de sensibilidade)
            for pos, al in enumerate(ver, 1):
                g = TRUTH[al["id"]]
                p_exam = 1 / math.log2(pos + 1.5)           # viés de posição: quem está no topo é mais visto
                if rnd.random() > p_exam:
                    continue
                ev = lambda tipo, **k: api.post("/feedback", {"alert_id": al["id"], "event": tipo, "user_id": user,
                                                              "position": pos, "ts": ts.isoformat(), **k})
                if rnd.random() < 0.15 * (1 + g):
                    ev("view_logs")
                if g >= 2 and rnd.random() < 0.35:
                    ev("thumbs_up")
                if g == 0 and rnd.random() < 0.40:
                    ev("thumbs_down")
                if g == 0 and rnd.random() < 0.25:
                    ev("dismiss")
                if g == 3 and rnd.random() < 0.2:
                    ev("ack")
        if rodada in (1, 2, 4, a.rounds):
            estado(f"após rodada {rodada}")

    print("\nExplicação de INC-003 (crítico, ignorado pela equipe):")
    ex = api.get("/alerts/INC-003/explain")
    print("  ", ex["breakdown"], ex["events_by_type"])
    print("\nMétricas:", {k: v for k, v in api.get("/metrics").items() if k in ("eventos_de_feedback", "eventos_por_tipo")})


if __name__ == "__main__":
    main()
