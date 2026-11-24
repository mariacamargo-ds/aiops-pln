import random, csv, json, datetime as dt
random.seed(2026)
BASE = dt.datetime(2026,10,13,13,56)
R=random.randint
# (incident, service, severity, minutesAgo, n_lines, [(level, template)])
INC=[
('payments-api','critico',4,60,[('ERROR','Timeout after {ms}ms waiting for connection from pool'),('ERROR','HTTP 502 upstream=db-primary'),('WARN','pool exhausted active=50 idle=0 waiting={n}'),('ERROR','transaction_failed order={o} reason=timeout'),('WARN','retry {r}/3 upstream=db-primary')]),
('checkout-service','critico',9,60,[('ERROR','POST /checkout 500 dependency=payments-api order={o}'),('ERROR','retry 3/3 failed'),('WARN','error_rate={p}%'),('ERROR','payment_confirmation_missing order={o}')]),
('api-gateway','critico',6,50,[('ERROR','upstream=payments-api status=502 count={n}'),('ERROR','upstream=checkout-service status=500 count={n}'),('WARN','error_rate={p}% threshold=5%'),('WARN','circuit_breaker=OPEN upstream=payments-api'),('INFO','autoscale requested replicas=6->10')]),
('db-primary','critico',11,50,[('WARN','connections={c}/500 (98%)'),('ERROR','FATAL: sorry, too many clients already'),('WARN','slow_query duration={ms}ms table=transactions'),('ERROR','replication_lag={r}s replica=db-replica-2'),('WARN','lock_wait=3 blocked_sessions={n}')]),
('orders-worker','alto',21,45,[('WARN','queue_depth={q} consumers=4 lag={r}m'),('ERROR','handler_timeout order={o} after=15000ms'),('WARN','consumer_slow avg_ms={ms}')]),
('auth-service','alto',33,45,[('WARN','login_failed rate={p}% idp=timeout'),('ERROR','token_refresh_failed user=u-{o}'),('WARN','idp_latency={ms}ms')]),
('inventory-service','alto',27,40,[('WARN','reserved_mismatch sku={o} expected={r} actual={n}'),('ERROR','batch_update partial_failure failed={n} retry=scheduled'),('INFO','batch_update progress items={q}')]),
('search-service','alto',36,40,[('WARN','p95_latency={ms}ms threshold=400ms'),('WARN','query_queue={n} timeouts={r}'),('INFO','reindex shard={r}/6 cpu={c}%')]),
('billing-worker','alto',44,40,[('ERROR','charge_failed batch=B-{o} reason=gateway_timeout'),('WARN','retry scheduled in=15m attempt={r}/5'),('INFO','failed_batches={r} total_value_pending=R$ {q},00')]),
('cache-redis','medio',58,35,[('WARN','used_memory={p}% evicted_keys={q}'),('INFO','hit_ratio={p}% (anterior 91%)'),('WARN','maxmemory-policy=allkeys-lru active')]),
('k8s-node-07','medio',62,30,[('WARN','disk_usage={p}% mount=/var/lib/docker'),('INFO','largest_dir=/var/log/containers size={c}GB'),('WARN','image_gc threshold=85% approaching')]),
('scheduler','medio',78,30,[('WARN','job=daily-report start_delay={ms}s'),('WARN','job=reconcile-ledger start_delay={ms}s'),('INFO','queue={n} workers=4')]),
('log-collector','medio',95,30,[('WARN','backlog={r}m'),('WARN','ingest_lag={r}m shards_delayed=2'),('INFO','flush batch={q}')]),
('web-frontend','medio',101,35,[("ERROR","TypeError: Cannot read properties of undefined (reading 'items') page=/cart"),('WARN','js_error_rate={p}% release=3.14.0'),('INFO','session_affected={n}')]),
('sso-provider','medio',120,30,[('WARN','response_time={ms}ms threshold=800ms'),('WARN','token_endpoint timeouts={r}'),('INFO','upstream=ldap latency={ms}ms')]),
('notification-service','baixo',140,28,[('INFO','retry batch={r} status=ok'),('WARN','smtp_temporary_failure provider=mail-1'),('INFO','delivered={q}')]),
('backup-job','baixo',150,25,[('INFO','started target=db-primary'),('WARN','duration={c}m expected=30m'),('INFO','completed size={c}GB checksum=ok')]),
('cdn-edge','baixo',180,25,[('INFO','cache_hit_ratio={p}% target=85%'),('INFO','purge issued paths={q}'),('INFO','cache_hit_ratio={p}% (recuperando)')]),
('cert-manager','baixo',210,25,[('INFO','cert=internal-api expires_in=12d'),('INFO','renewal_window_open cert=internal-api'),('WARN','manual_renewal_required cert=internal-api')]),
('metrics-agent','baixo',240,25,[('WARN','restart count=2 reason=oom_killed node=k8s-node-03'),('INFO','resumed scrape_interval=15s'),('INFO','targets_up={n}')]),
]
NOISE=[('api-gateway','INFO','Health check respondeu em {ms} ms (limite 200 ms)'),('cache-redis','INFO','Reconexão automática bem-sucedida'),('web-frontend','WARN','Aviso de depreciação de biblioteca'),('orders-worker','INFO','Mensagem reprocessada com sucesso'),('log-collector','INFO','Rotação de arquivo de log concluída'),('auth-service','INFO','Token renovado (rotina)'),('scheduler','INFO','Execução de rotina concluída sem alterações'),('db-primary','INFO','Checkpoint concluído em {ms} ms'),('search-service','INFO','Cache de consulta aquecido'),('cdn-edge','INFO','Purge de cache finalizado'),('inventory-service','INFO','Sincronização incremental concluída'),('metrics-agent','INFO','Coleta de métricas concluída'),('notification-service','INFO','Template de e-mail recarregado'),('cert-manager','INFO','Verificação diária de certificados concluída')]
def fill(t):
    return t.format(ms=R(210,9800),n=R(12,480),o=R(48000,99999),r=R(2,19),p=R(5,97),c=R(51,98),q=R(120,5200))
rows=[]; tid={}
def T(key):
    return tid.setdefault(key,'T%03d'%(len(tid)+1))
tot_inc=850; weights=[i[3] for i in INC]; sw=sum(weights)
counts=[round(tot_inc*w/sw) for w in weights]; counts[0]+=tot_inc-sum(counts)
for k,(svc,sev,ago,win,tpls) in enumerate(INC):
    inc='INC-%03d'%(k+1)
    start=BASE-dt.timedelta(minutes=ago)
    for _ in range(counts[k]):
        lvl,t=random.choice(tpls)
        ts=start+dt.timedelta(seconds=R(0,min(win,ago)*60))
        rows.append(dict(timestamp=ts,service=svc,level=lvl,severity=sev,message=fill(t),incident_id=inc,is_relevant=1,template_id=T(svc+t)))
for _ in range(150):
    svc,lvl,t=random.choice(NOISE)
    ts=BASE-dt.timedelta(seconds=R(0,240*60))
    rows.append(dict(timestamp=ts,service=svc,level=lvl,severity='ruido',message=fill(t),incident_id='',is_relevant=0,template_id=T(svc+t)))
rows.sort(key=lambda r:r['timestamp'])
for i,r in enumerate(rows,1):
    r['log_id']='L%04d'%i; r['timestamp']=r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
cols=['log_id','timestamp','service','level','severity','message','incident_id','is_relevant','template_id']
with open('aiops_logs_sinteticos.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
json.dump(rows,open('aiops_logs_sinteticos.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
open('../aiops-frontend/js/dataset.js','w',encoding='utf-8').write('/* Dataset SINTÉTICO de logs ('+str(len(rows))+' linhas). Gerado por gen.py */\nwindow.AIOPS_LOGS = '+json.dumps([[r[c] for c in cols] for r in rows],ensure_ascii=False,separators=(',',':'))+';\nwindow.AIOPS_LOG_COLS = '+json.dumps(cols)+';\n')
from collections import Counter
print(len(rows),Counter(r['severity'] for r in rows),len(tid),Counter(r['is_relevant'] for r in rows))
