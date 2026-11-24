"""Score de CONTEÚDO de um incidente (a parte que não depende dos usuários).

É uma heurística transparente (`heuristica-v1`). O ponto de extensão é `content_score`:
quando o classificador treinado (F1 0,91 na Sprint 02) estiver pronto, basta trocá-lo aqui.
"""
from __future__ import annotations

import math
from datetime import datetime

SEV_WEIGHT = {"critico": 0.95, "alto": 0.80, "medio": 0.62, "baixo": 0.45}


def content_score(severity: str, levels: list[str], last_ts: datetime | None, ref_now: datetime) -> float:
    n = max(len(levels), 1)
    err = sum(1 for x in levels if x == "ERROR") / n
    warn = sum(1 for x in levels if x == "WARN") / n
    volume = min(1.0, math.log1p(n) / math.log1p(60))
    minutes = max((ref_now - last_ts).total_seconds() / 60.0, 0.0) if last_ts else 240.0
    recency = math.exp(-minutes / 240.0)
    s = 0.60 * SEV_WEIGHT.get(severity, 0.5) + 0.15 * err + 0.05 * warn + 0.10 * volume + 0.10 * recency
    return round(min(max(s, 0.05), 0.99), 4)
