# Dataset sintético de logs — AIOps (PLN)

1.000 linhas **sintéticas** (geradas por `gen.py`, semente fixa) que simulam a operação de 20 serviços durante um incidente de pagamentos (13/10/2026).

| Coluna | Descrição |
|---|---|
| log_id | identificador (L0001…L1000) |
| timestamp | data e hora |
| service | serviço de origem |
| level | INFO / WARN / ERROR |
| severity | critico, alto, medio, baixo ou ruido |
| message | texto do log |
| incident_id | INC-001…INC-020 (vazio quando é ruído) |
| is_relevant | 1 = relevante, 0 = ruído |
| template_id | modelo da mensagem (como o Drain agruparia) |

Composição: 850 linhas de 20 incidentes e 150 linhas de ruído. Não há dados reais.
