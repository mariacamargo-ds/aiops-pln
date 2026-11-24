/* Cliente da API do AIOps. Se a API estiver fora do ar, o front-end volta sozinho ao modo simulado. */
(function () {
  const qs = new URLSearchParams(location.search);
  let base = qs.get('api');
  if (base === null) {
    try { base = localStorage.getItem('aiops-api'); } catch (e) { base = null; }
  }
  if (base === null) base = location.protocol.startsWith('http') && location.pathname.indexOf('/app') === 0 ? '' : 'http://localhost:8000';
  base = base.replace(/\/$/, '');

  const A = { base, online: false, health: null, user: 'maria', role: 'analista' };

  async function req(path, opt = {}, timeout = 45000) {
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), timeout);
    try {
      const r = await fetch(base + path, Object.assign({ signal: ctl.signal }, opt,
        opt.body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(opt.body) } : {}));
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.json();
    } finally { clearTimeout(t); }
  }
  const get = (p, t) => req(p, {}, t), post = (p, body, t) => req(p, { method: 'POST', body }, t);

  A.ready = (async () => {
    try { A.health = await get('/health', 2500); A.online = A.health.status === 'ok'; } catch (e) { A.online = false; }
    document.dispatchEvent(new CustomEvent('aiops:api', { detail: A.online }));
    return A.online;
  })();

  A.alerts = (sens, extra = {}) => get('/alerts?' + new URLSearchParams(Object.assign({ role: A.role, sensitivity: sens }, extra)));
  A.feedback = (alert_id, event, position, dwell_s) =>
    post('/feedback', { alert_id, event, user_id: A.user, role: A.role, position: position || null, dwell_s: dwell_s || null });
  A.ask = question => post('/ask', { question, user_id: A.user, role: A.role }, 150000);
  A.summarize = text => post('/summarize', { text }, 150000);
  A.llm = () => get('/llm');
  A.setLlm = (provider, model) => post('/llm', model ? { provider, model } : { provider });
  A.warmup = () => post('/llm/warmup', {}, 150000);
  A.logs = params => get('/logs?' + new URLSearchParams(params));
  A.metrics = () => get('/metrics');
  A.explain = id => get('/alerts/' + id + '/explain?role=' + A.role);

  window.AIOPS_API = A;
})();
