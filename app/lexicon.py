"""Normalização de texto e vocabulário do domínio (PT-BR ↔ nomes técnicos dos serviços)."""
from __future__ import annotations

import re
import unicodedata

TOKEN = re.compile(r"[a-z0-9]+")

STOP = set(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para com e ou que se foi "
    "esta estao esse essa isso ha houve algum alguma qual quais como porque pelo pela ao aos "
    "hoje mais sobre meu meus minha nosso nossa ser sao tem teve".split()
)

KNOWN_SERVICES = [
    "payments-api", "checkout-service", "api-gateway", "db-primary", "orders-worker", "auth-service",
    "inventory-service", "search-service", "billing-worker", "cache-redis", "k8s-node-07", "scheduler",
    "log-collector", "web-frontend", "sso-provider", "notification-service", "backup-job", "cdn-edge",
    "cert-manager", "metrics-agent",
]

# termo em PT (sem acento) -> serviço
SERVICE_ALIASES = {
    "banco": "db-primary", "bd": "db-primary", "database": "db-primary", "postgres": "db-primary",
    "pagamento": "payments-api", "pagamentos": "payments-api", "payments": "payments-api",
    "checkout": "checkout-service", "compra": "checkout-service", "compras": "checkout-service",
    "estoque": "inventory-service", "inventario": "inventory-service",
    "busca": "search-service", "pesquisa": "search-service",
    "login": "auth-service", "autenticacao": "auth-service", "auth": "auth-service",
    "fila": "orders-worker", "pedidos": "orders-worker", "pedido": "orders-worker",
    "cobranca": "billing-worker", "cobrancas": "billing-worker", "fatura": "billing-worker",
    "disco": "k8s-node-07", "cluster": "k8s-node-07", "kubernetes": "k8s-node-07",
    "certificado": "cert-manager", "certificados": "cert-manager", "tls": "cert-manager",
    "notificacao": "notification-service", "notificacoes": "notification-service", "email": "notification-service",
    "frontend": "web-frontend", "navegador": "web-frontend", "javascript": "web-frontend",
    "gateway": "api-gateway", "agendador": "scheduler", "tarefas": "scheduler",
    "memoria": "cache-redis", "cache": "cache-redis", "redis": "cache-redis",
    "cdn": "cdn-edge", "backup": "backup-job",
    "metricas": "metrics-agent", "coletor": "log-collector", "coleta": "log-collector",
    "sso": "sso-provider", "identidade": "sso-provider",
}

# conceitos em PT -> termos que aparecem nas mensagens de log
CONCEPTS = {
    "lento": "slow latency duration", "lenta": "slow latency duration", "lentidao": "slow latency duration",
    "queda": "timeout 502 500 error", "indisponivel": "timeout 502 500 error", "fora": "timeout error",
    "falha": "failed error", "falhas": "failed error", "erro": "error failed", "erros": "error failed",
    "conexoes": "connections pool", "conexao": "connection pool",
    "atraso": "delay lag backlog start_delay", "atrasos": "delay lag backlog start_delay",
    "memoria": "memory used_memory evicted", "travado": "timeout lock", "travou": "timeout lock",
    "divergencia": "mismatch", "reinicio": "restart", "reiniciado": "restart",
}


def norm(s: str) -> str:
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()


def tokens(s: str) -> list[str]:
    return TOKEN.findall(norm(s))


def mentioned_services(q: str) -> set[str]:
    n = norm(q)
    found = {SERVICE_ALIASES[t] for t in TOKEN.findall(n) if t in SERVICE_ALIASES}
    found |= {s for s in KNOWN_SERVICES if s in n}
    return found


def expand_query(q: str) -> str:
    extra: list[str] = []
    for t in TOKEN.findall(norm(q)):
        if t in SERVICE_ALIASES:
            extra.append(SERVICE_ALIASES[t])
        if t in CONCEPTS:
            extra.append(CONCEPTS[t])
    extra.extend(mentioned_services(q))
    return q + " " + " ".join(extra)
