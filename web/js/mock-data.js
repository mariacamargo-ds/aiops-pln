/* Dados SIMULADOS (mock) — substituídos futuramente pela API FastAPI.
   Mantidos em .js (e não .json) para a página abrir por duplo clique, sem servidor. */
(function () {
  const alerts = [
    { id:'a1', service:'payments-api',        severity:'critico', score:0.97, grouped:47, minutesAgo:4,   sla:'15 min',
      title:'Timeouts em cascata no gateway de pagamentos',
      summary:'47 alertas de timeout e erro 502 foram agrupados em um único incidente. Provável causa: esgotamento do pool de conexões com o banco após o último deploy.',
      log:'2026-10-13 13:52:07 ERROR payments-api Timeout after 30000ms waiting for connection from pool\n2026-10-13 13:52:08 ERROR payments-api HTTP 502 upstream=db-primary\n2026-10-13 13:52:08 WARN  payments-api pool exhausted active=50 idle=0 waiting=212' },
    { id:'a2', service:'checkout-service',    severity:'critico', score:0.93, grouped:63, minutesAgo:9,   sla:'15 min',
      title:'Falha em finalização de compra (HTTP 500)',
      summary:'63 ocorrências de erro 500 na finalização de compra, correlacionadas ao incidente de payments-api. Tratar os dois como um único incidente.',
      log:'2026-10-13 13:47:31 ERROR checkout-service POST /checkout 500 dependency=payments-api\n2026-10-13 13:47:32 ERROR checkout-service retry 3/3 failed' },
    { id:'a3', service:'orders-worker',       severity:'alto',    score:0.84, grouped:9,  minutesAgo:21,  sla:'1 h',
      title:'Fila de pedidos acumulando',
      summary:'A fila cresceu de 120 para 4.800 mensagens em 20 minutos. Consumidores estão lentos, possivelmente por dependência de payments-api.',
      log:'2026-10-13 13:35:10 WARN orders-worker queue_depth=4800 consumers=4 lag=19m' },
    { id:'a4', service:'auth-service',        severity:'alto',    score:0.81, grouped:12, minutesAgo:33,  sla:'1 h',
      title:'Aumento de falhas de login',
      summary:'12 alertas de falha de autenticação. Taxa de erro subiu de 0,8% para 6,3%. Verificar expiração de credenciais do provedor de identidade.',
      log:'2026-10-13 13:23:44 WARN auth-service login_failed rate=6.3% idp=timeout' },
    { id:'a5', service:'cache-redis',         severity:'medio',   score:0.72, grouped:5,  minutesAgo:58,  sla:'4 h',
      title:'Uso de memória acima de 85%',
      summary:'O cache está próximo do limite de memória e começou a remover chaves (evictions). Sem impacto visível ao usuário até o momento.',
      log:'2026-10-13 12:58:02 WARN cache-redis used_memory=87% evicted_keys=1320' },
    { id:'a6', service:'log-collector',       severity:'medio',   score:0.66, grouped:3,  minutesAgo:95,  sla:'4 h',
      title:'Atraso na coleta de logs',
      summary:'O coletor de logs apresenta atraso de 6 minutos. Pode atrasar a detecção de novos incidentes.',
      log:'2026-10-13 12:21:15 WARN log-collector backlog=6m' },
    { id:'a7', service:'notification-service',severity:'baixo',   score:0.58, grouped:2,  minutesAgo:140, sla:'24 h',
      title:'Reenvio de notificações por e-mail',
      summary:'Dois lotes de e-mail foram reenviados após falha temporária do provedor. Já normalizado.',
      log:'2026-10-13 11:36:50 INFO notification-service retry batch=2 status=ok' },
    { id:'a8', service:'cert-manager',        severity:'baixo',   score:0.55, grouped:1,  minutesAgo:210, sla:'24 h',
      title:'Certificado expira em 12 dias',
      summary:'Um certificado TLS interno vence em 12 dias. Renovação deve ser agendada.',
      log:'2026-10-13 10:26:00 INFO cert-manager cert=internal-api expires_in=12d' }
  ];
  const noise = [
    { id:'n1', service:'api-gateway',    score:0.31, minutesAgo:6,   title:'Health check respondeu em 210 ms (limite 200 ms)' },
    { id:'n2', service:'cache-redis',    score:0.24, minutesAgo:12,  title:'Reconexão automática bem-sucedida' },
    { id:'n3', service:'web-frontend',   score:0.19, minutesAgo:17,  title:'Aviso de depreciação de biblioteca' },
    { id:'n4', service:'orders-worker',  score:0.15, minutesAgo:26,  title:'Mensagem reprocessada com sucesso' },
    { id:'n5', service:'log-collector',  score:0.12, minutesAgo:40,  title:'Rotação de arquivo de log concluída' },
    { id:'n6', service:'auth-service',   score:0.09, minutesAgo:44,  title:'Token renovado (rotina)' }
  ];

  /* ---- Mais alertas e logs (simulados) ---- */
  const D13 = '2026-10-13 ';
  const more = [
    { id:'a9',  service:'api-gateway',     severity:'critico', score:0.91, grouped:38, minutesAgo:6,   sla:'15 min',
      title:'Taxa de erro 5xx acima de 20% no gateway',
      summary:'38 alertas de erro 5xx agrupados. O gateway está devolvendo falhas por indisponibilidade de serviços internos, em linha com o incidente de payments-api.',
      log:[D13+'13:50:12 ERROR api-gateway upstream=payments-api status=502 count=412',D13+'13:50:14 ERROR api-gateway upstream=checkout-service status=500 count=287',D13+'13:50:20 WARN  api-gateway error_rate=21.4% threshold=5%',D13+'13:50:31 WARN  api-gateway circuit_breaker=OPEN upstream=payments-api',D13+'13:50:45 INFO  api-gateway autoscale requested replicas=6->10'] },
    { id:'a10', service:'db-primary',      severity:'critico', score:0.89, grouped:21, minutesAgo:11,  sla:'15 min',
      title:'Conexões do banco principal no limite',
      summary:'O banco principal atingiu 98% do limite de conexões. É a provável origem do esgotamento do pool em payments-api.',
      log:[D13+'13:45:03 WARN  db-primary connections=490/500 (98%)',D13+'13:45:09 ERROR db-primary FATAL: sorry, too many clients already',D13+'13:45:18 WARN  db-primary slow_query duration=8421ms table=transactions',D13+'13:45:40 ERROR db-primary replication_lag=14s replica=db-replica-2',D13+'13:46:02 WARN  db-primary lock_wait=3 blocked_sessions=57'] },
    { id:'a11', service:'inventory-service',severity:'alto',   score:0.80, grouped:7,  minutesAgo:27,  sla:'1 h',
      title:'Divergência de estoque após atualização em lote',
      summary:'Sete alertas indicam diferença entre o estoque reservado e o disponível depois da carga em lote das 13h20. Pode gerar vendas de itens indisponíveis.',
      log:[D13+'13:20:41 INFO  inventory-service batch_update started items=18400',D13+'13:29:12 WARN  inventory-service reserved_mismatch sku=48213 expected=12 actual=19',D13+'13:29:12 WARN  inventory-service reserved_mismatch sku=77102 expected=3 actual=9',D13+'13:29:55 ERROR inventory-service batch_update partial_failure failed=213 retry=scheduled'] },
    { id:'a12', service:'search-service',  severity:'alto',    score:0.78, grouped:11, minutesAgo:36,  sla:'1 h',
      title:'Latência de busca acima do normal',
      summary:'O p95 da busca subiu de 180 ms para 1.900 ms. O índice está sendo reconstruído e disputa CPU com as consultas.',
      log:[D13+'13:20:10 INFO  search-service reindex started shard=3/6',D13+'13:21:44 WARN  search-service p95_latency=1240ms threshold=400ms',D13+'13:25:03 WARN  search-service p95_latency=1900ms cpu=94%',D13+'13:25:30 WARN  search-service query_queue=318 timeouts=14'] },
    { id:'a13', service:'billing-worker',  severity:'alto',    score:0.76, grouped:6,  minutesAgo:44,  sla:'1 h',
      title:'Cobranças recorrentes com falha de comunicação',
      summary:'Seis lotes de cobrança recorrente falharam por timeout no provedor de pagamento. As tentativas seguintes estão agendadas.',
      log:[D13+'13:12:08 ERROR billing-worker charge_failed batch=B-2210 reason=gateway_timeout',D13+'13:12:09 WARN  billing-worker retry scheduled in=15m attempt=2/5',D13+'13:12:40 ERROR billing-worker charge_failed batch=B-2211 reason=gateway_timeout',D13+'13:13:02 INFO  billing-worker failed_batches=6 total_value_pending=R$ 48.230,00'] },
    { id:'a14', service:'k8s-node-07',     severity:'medio',   score:0.70, grouped:4,  minutesAgo:62,  sla:'4 h',
      title:'Disco do nó com 82% de uso',
      summary:'O nó 07 do cluster está com pouco espaço em disco, principalmente por logs antigos de contêiner. Ainda sem impacto nos serviços.',
      log:[D13+'12:54:11 WARN  k8s-node-07 disk_usage=82% mount=/var/lib/docker',D13+'12:54:11 INFO  k8s-node-07 largest_dir=/var/log/containers size=61GB',D13+'12:54:30 WARN  k8s-node-07 image_gc threshold=85% approaching'] },
    { id:'a15', service:'scheduler',       severity:'medio',   score:0.68, grouped:3,  minutesAgo:78,  sla:'4 h',
      title:'Tarefas agendadas executando com atraso',
      summary:'Três rotinas do agendador começaram com mais de 5 minutos de atraso. Possível sobrecarga do nó que executa o scheduler.',
      log:[D13+'12:38:00 WARN  scheduler job=daily-report start_delay=312s',D13+'12:40:02 WARN  scheduler job=reconcile-ledger start_delay=355s',D13+'12:45:00 INFO  scheduler queue=17 workers=4'] },
    { id:'a16', service:'web-frontend',    severity:'medio',   score:0.64, grouped:8,  minutesAgo:101, sla:'4 h',
      title:'Aumento de erros de JavaScript no navegador',
      summary:'Foram registrados 8 alertas de erro de JavaScript após a publicação da versão 3.14. Afeta a página de carrinho em parte dos navegadores.',
      log:[D13+'12:15:20 ERROR web-frontend TypeError: Cannot read properties of undefined (reading \'items\') page=/cart',D13+'12:15:44 ERROR web-frontend TypeError: Cannot read properties of undefined (reading \'items\') page=/cart',D13+'12:16:03 WARN  web-frontend js_error_rate=2.9% release=3.14.0'] },
    { id:'a17', service:'backup-job',      severity:'baixo',   score:0.60, grouped:1,  minutesAgo:150, sla:'24 h',
      title:'Backup noturno concluído com atraso',
      summary:'O backup noturno terminou 40 minutos depois do previsto. Concluído com sucesso e sem perda de dados.',
      log:[D13+'03:00:00 INFO  backup-job started target=db-primary',D13+'04:10:22 WARN  backup-job duration=70m expected=30m',D13+'04:10:25 INFO  backup-job completed size=212GB checksum=ok'] },
    { id:'a18', service:'cdn-edge',        severity:'baixo',   score:0.57, grouped:2,  minutesAgo:180, sla:'24 h',
      title:'Taxa de acerto do cache da CDN abaixo da meta',
      summary:'A taxa de acerto do cache caiu para 71% (meta de 85%) após a publicação de novas imagens. Tende a normalizar sozinha.',
      log:[D13+'10:56:00 INFO  cdn-edge cache_hit_ratio=71% target=85%',D13+'10:56:00 INFO  cdn-edge purge issued paths=1420',D13+'10:58:30 INFO  cdn-edge cache_hit_ratio=74%'] },
    { id:'a19', service:'metrics-agent',   severity:'baixo',   score:0.54, grouped:2,  minutesAgo:240, sla:'24 h',
      title:'Agente de métricas reiniciado',
      summary:'O agente de métricas foi reiniciado duas vezes no mesmo nó. Sem falta de dados na janela observada.',
      log:[D13+'09:56:10 WARN  metrics-agent restart count=2 reason=oom_killed node=k8s-node-03',D13+'09:56:14 INFO  metrics-agent resumed scrape_interval=15s'] },
    { id:'a20', service:'sso-provider',    severity:'medio',   score:0.62, grouped:3,  minutesAgo:120, sla:'4 h',
      title:'Lentidão no provedor de identidade',
      summary:'O provedor de identidade respondeu em média 2,4 s. Relacionado ao aumento de falhas de login em auth-service.',
      log:[D13+'11:56:12 WARN  sso-provider response_time=2410ms threshold=800ms',D13+'11:57:03 WARN  sso-provider token_endpoint timeouts=9',D13+'11:58:40 INFO  sso-provider upstream=ldap latency=1980ms'] }
  ];
  const addLog = {
    a1:[ '2026-10-13 13:52:10 WARN  payments-api retry 2/3 upstream=db-primary', '2026-10-13 13:52:14 ERROR payments-api transaction_failed order=88213 reason=timeout', '2026-10-13 13:52:30 ERROR payments-api transaction_failed order=88219 reason=timeout' ],
    a2:[ '2026-10-13 13:47:40 ERROR checkout-service POST /checkout 500 order=88117', '2026-10-13 13:48:02 WARN  checkout-service error_rate=18.2%' ],
    a3:[ '2026-10-13 13:36:00 WARN  orders-worker queue_depth=5120 consumers=4 lag=21m', '2026-10-13 13:36:40 ERROR orders-worker handler_timeout order=88050 after=15000ms' ],
    a4:[ '2026-10-13 13:24:01 WARN  auth-service login_failed rate=6.9% idp=timeout', '2026-10-13 13:24:50 ERROR auth-service token_refresh_failed user=u-48213' ],
    a5:[ '2026-10-13 12:58:30 WARN  cache-redis evicted_keys=2210 used_memory=88%', '2026-10-13 12:59:10 INFO  cache-redis hit_ratio=79% (anterior 91%)' ]
  };
  alerts.forEach(a => { if (addLog[a.id]) a.log = a.log + '\n' + addLog[a.id].join('\n'); });
  more.forEach(a => { a.log = a.log.join('\n'); });
  alerts.push(...more);
  alerts.sort((x, y) => y.score - x.score);
  const moreNoise = [
    ['api-gateway','Certificado de cliente renovado automaticamente',0.08,52],['web-frontend','Aviso: imagem sem atributo alt',0.07,58],
    ['scheduler','Execução de rotina concluída sem alterações',0.11,63],['cache-redis','Chave expirada removida (TTL)',0.06,66],
    ['orders-worker','Mensagem duplicada ignorada',0.14,70],['auth-service','Sessão encerrada por inatividade (rotina)',0.10,75],
    ['db-primary','Checkpoint concluído em 0,4 s',0.05,81],['log-collector','Arquivo rotacionado com sucesso',0.09,88],
    ['search-service','Cache de consulta aquecido',0.13,92],['k8s-node-03','Pod reagendado (rotina de balanceamento)',0.17,97],
    ['cdn-edge','Purge de cache finalizado',0.12,104],['billing-worker','Fatura gerada em modo de teste',0.04,110],
    ['notification-service','Template de e-mail recarregado',0.08,118],['api-gateway','Health check respondeu em 205 ms (limite 200 ms)',0.28,125],
    ['inventory-service','Sincronização incremental concluída',0.10,133],['web-frontend','Aviso de depreciação de biblioteca',0.19,140],
    ['metrics-agent','Coleta de métricas concluída',0.03,148],['cert-manager','Verificação diária de certificados concluída',0.06,155],
    ['backup-job','Snapshot incremental criado',0.07,162],['payments-api','Reconexão automática bem-sucedida',0.22,170]
  ].map((n,i)=>({ id:'n'+(7+i), service:n[0], title:n[1], score:n[2], minutesAgo:n[3] }));
  noise.push(...moreNoise);
  const sevLabel = { critico:'Crítico', alto:'Alto', medio:'Médio', baixo:'Baixo' };
  const confusion = { tp:412, fp:51, fn:33, tn:1504 };
  const received = 1248, relevant = alerts.length + 67;
  const qa = [
    { q:'O que causou a falha no checkout hoje?',
      a:'Os logs indicam esgotamento do pool de conexões de payments-api após o deploy das 13h40. Isso gerou timeouts em cascata e erros HTTP 500 em checkout-service.',
      sources:['payments-api · 13:52','checkout-service · 13:47','deploy-log · 13:40'] },
    { q:'Quais serviços estão com incidentes críticos?',
      a:'Dois serviços estão críticos: payments-api (47 alertas agrupados) e checkout-service (63 alertas agrupados). Ambos parecem fazer parte do mesmo incidente.',
      sources:['payments-api · 13:52','checkout-service · 13:47'] },
    { q:'Houve problemas de autenticação nesta semana?',
      a:'Sim. O auth-service registrou aumento de falhas de login hoje (de 0,8% para 6,3%), associado a timeout do provedor de identidade. Nos demais dias da semana não há registros relevantes.',
      sources:['auth-service · 13:23'] },
    { q:'Por que o banco de dados está lento?',
      a:'O db-primary atingiu 98% do limite de conexões (490/500) e registrou consultas lentas na tabela transactions. Isso explica o esgotamento do pool em payments-api.',
      sources:['db-primary · 13:45','payments-api · 13:52'] },
    { q:'Existe algum risco com o estoque?',
      a:'Sim. Após a carga em lote das 13h20, o inventory-service apontou divergência entre estoque reservado e disponível em alguns SKUs, com 213 itens em falha parcial agendados para nova tentativa.',
      sources:['inventory-service · 13:29'] },
    { q:'O que mudou no frontend depois do último deploy?',
      a:'Após a versão 3.14.0, o web-frontend passou a registrar erros de JavaScript na página de carrinho (taxa de 2,9%). Vale conferir o acesso à propriedade items.',
      sources:['web-frontend · 12:15','web-frontend · 12:16'] }
  ];
  window.AIOPS_DATA = {
    alerts, noise, sevLabel, confusion, qa,
    kpis: { received, relevant, noisePct: Math.round((1 - relevant / received) * 100), mttr: 24, open: alerts.length },
    director: {
      noise: { sistema:95, equipe:88, real:93 },
      mttr:  { sistema:18, equipe:35, real:24 },
      severity7d: { critico:6, alto:14, medio:23, baixo:41 }
    },
    people: [
      { name:'Equipe Plataforma',  role:'payments-api, checkout-service', link:'#' },
      { name:'Equipe Identidade',  role:'auth-service',                   link:'#' },
      { name:'Equipe Dados',       role:'orders-worker, cache-redis',     link:'#' }
    ],
    history: [
      { date:'06/10', text:'Classificador v0.3 treinado — F1 0,81' },
      { date:'09/10', text:'Parser de logs (Drain) integrado' },
      { date:'12/10', text:'Classificador v0.4 treinado — F1 0,91' }
    ]
  };
  window.AIOPS_UTIL = {
    metrics(c){ const p=c.tp/(c.tp+c.fp), r=c.tp/(c.tp+c.fn), a=(c.tp+c.tn)/(c.tp+c.tn+c.fp+c.fn), f=2*p*r/(p+r); return {p,r,a,f}; },
    pct(x){ return (x*100).toFixed(1).replace('.',',')+'%'; },
    ago(m){ return m<60 ? 'há '+m+' min' : 'há '+Math.floor(m/60)+' h'+(m%60?' '+(m%60)+' min':''); },
    esc(s){ return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); },
    store: {
      get(k,d){ try{ const v=localStorage.getItem(k); return v==null?d:JSON.parse(v);}catch(e){return d;} },
      set(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }
    },
    /* Sumarizador SIMULADO: regras simples. Na versão real será um modelo de PLN no back-end. */
    summarize(text){
      const t = text.trim();
      const svcs = [...new Set((t.match(/\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b/g) || []))].slice(0,4);
      const nums = (t.match(/\b\d+(?:[.,]\d+)?\s?(?:ms|%|min|h)\b/g) || []).slice(0,3).map(s=>s.trim());
      let sev='baixo', cause='Evento informativo, sem indício de falha.', action='Nenhuma ação imediata necessária.';
      const L = t.toLowerCase();
      if (/(timeout|exhausted|502|500|fatal|panic|outofmemory|crash)/.test(L)){ sev='critico'; cause='Indícios de indisponibilidade ou esgotamento de recursos (timeouts/erros 5xx).'; action='Acionar o time responsável e verificar o último deploy e os recursos do serviço.'; }
      else if (/(error|failed|queue|lag|retry)/.test(L)){ sev='alto'; cause='Falhas recorrentes ou degradação de desempenho.'; action='Investigar dependências do serviço e acompanhar por 15 minutos.'; }
      else if (/(warn|memory|backlog|slow|evict)/.test(L)){ sev='medio'; cause='Alerta de capacidade ou atraso, ainda sem impacto direto.'; action='Agendar verificação de capacidade.'; }
      return { sev, svcs, nums, cause, action };
    }
  };
})();
