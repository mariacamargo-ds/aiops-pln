/* Componentes compartilhados entre o painel web e o plug-in */
(function () {
  const D = window.AIOPS_DATA, U = window.AIOPS_UTIL, e = U.esc;

  function badge(sev){ return `<span class="badge sev-${sev}">${D.sevLabel[sev]}</span>`; }

  function alertCard(a, opts = {}) {
    const fb = U.store.get('fb-' + a.id, null);
    const compact = opts.compact;
    return `<li class="alert sev-b-${a.severity}" data-id="${a.id}" data-pos="${a.position || ''}">
      <div class="alert-top">
        ${badge(a.severity)}
        <span class="svc">${e(a.service)}</span>
        <span class="time">${U.ago(a.minutesAgo)}</span>
      </div>
      <strong>${e(a.title)}</strong>
      <p class="summary">${e(a.summary)}</p>
      <div class="alert-meta">
        <span class="score" title="Relevância = conteúdo + interação dos usuários">relevância ${a.score.toFixed(2).replace('.',',')}
          <span class="bar"><i style="width:${a.score*100}%"></i></span></span>
        <span>${a.grouped} alertas agrupados</span>
        ${a.events !== undefined ? `<span title="Interações dos usuários (com decaimento)">👥 ${String(a.events).replace('.',',')} interações</span>` : ''}
        ${a.exploration ? '<span class="chip" title="Vaga de exploração: alerta com pouca evidência, para o sistema aprender">🔎 em avaliação</span>' : ''}
        ${a.floor_applied ? '<span class="chip" title="Alertas críticos nunca são escondidos">🛡 crítico protegido</span>' : ''}
        ${compact ? '' : `<span>SLA: ${e(a.sla)}</span>`}
      </div>
      <div class="alert-actions">
        <button class="btn small" data-act="log" data-id="${a.id}">Ver logs brutos</button>
        <button class="btn small" data-act="fb" data-v="up" data-id="${a.id}" aria-pressed="${fb==='up'}" aria-label="Alerta útil">👍 Útil</button>
        <button class="btn small" data-act="fb" data-v="down" data-id="${a.id}" aria-pressed="${fb==='down'}" aria-label="Alerta irrelevante">👎 Irrelevante</button>
      </div>
    </li>`;
  }

  function noiseCard(n){
    return `<li class="alert noise"><div class="alert-top">
      <span class="badge" style="background:#4b4789">Ruído</span>
      <span class="svc">${e(n.service)}</span><span class="time">${U.ago(n.minutesAgo)}</span></div>
      <span class="summary">${e(n.title)} · relevância ${n.score.toFixed(2).replace('.',',')}</span></li>`;
  }

  function toast(msg){
    const t = document.createElement('div'); t.className='toast'; t.setAttribute('role','status'); t.textContent = msg;
    document.body.appendChild(t); setTimeout(()=>t.remove(), 2200);
  }

  function logDialog(a){
    let d = document.getElementById('logdlg');
    if (!d){ d = document.createElement('dialog'); d.id='logdlg'; document.body.appendChild(d); }
    d.innerHTML = `<div class="dlg-head"><h3>Logs brutos · ${e(a.service)}</h3>
      <button class="btn small" id="logclose" aria-label="Fechar">Fechar ✕</button></div>
      <div class="dlg-body"><p class="sub" style="color:var(--faint)">${live() ? 'Últimas linhas gravadas no banco de dados para este incidente.' : 'Trecho de log simulado, do tipo que o sistema analisa.'}</p>
      <pre class="log">${e(a.log)}</pre></div>`;
    d.showModal();
    d.querySelector('#logclose').onclick = () => d.close();
    d.onclick = ev => { if (ev.target === d) d.close(); };
  }

  /* delegação de cliques (ver logs / feedback) */
  const registry = {};
  function setAlerts(list){ list.forEach(a => { registry[a.id] = a; }); }
  const API = () => window.AIOPS_API;
  const live = () => API() && API().online;
  function send(a, ev, pos){
    if (!live()) return;
    API().feedback(a.id, ev, pos).then(r => {
      if (r && r.alert) toast('Registrado · nova relevância ' + r.alert.score.toFixed(2).replace('.', ','));
      document.dispatchEvent(new CustomEvent('aiops:feedback', { detail: r }));
    }).catch(() => toast('Não consegui falar com a API; feedback guardado só neste navegador.'));
  }

  function bindAlertActions(root){
    root.addEventListener('click', ev => {
      const b = ev.target.closest('button[data-act]'); if (!b) return;
      const a = registry[b.dataset.id] || D.alerts.find(x => x.id === b.dataset.id); if (!a) return;
      const pos = +(b.closest('li') || {}).dataset?.pos || null;
      if (b.dataset.act === 'log'){ send(a, 'view_logs', pos); return logDialog(a); }
      if (b.dataset.act === 'fb'){
        const cur = U.store.get('fb-' + a.id, null);
        const next = cur === b.dataset.v ? null : b.dataset.v;
        U.store.set('fb-' + a.id, next);
        root.querySelectorAll(`button[data-act="fb"][data-id="${a.id}"]`).forEach(x => x.setAttribute('aria-pressed', String(x.dataset.v === next)));
        if (next){
          if (live()) send(a, next === 'up' ? 'thumbs_up' : 'thumbs_down', pos);
          else toast('Obrigado! Seu feedback ajuda a melhorar o classificador.');
        }
      }
    });
  }

  function summaryResult(text, api){
    const r = api ? { sev: api.severidade, svcs: api.servicos || [], cause: api.causa_provavel, action: api.acao_sugerida, nums: api.numeros || [] } : U.summarize(text);
    const tag = api ? (api.mode === 'llm' ? (api.provider === 'ollama' ? 'Local · ' : 'DeepSeek · ') + e(api.model) : 'regras locais') : 'simulado';
    return `<div class="result" aria-live="polite">
      <h3>Resumo AIOps <span class="sim-tag">${tag}</span></h3>
      <div>${badge(r.sev)} ${r.svcs.map(s=>`<span class="chip">${e(s)}</span>`).join(' ')}</div>
      <ul><li><b>Provável causa:</b> ${e(r.cause)}</li>
      <li><b>Ação sugerida:</b> ${e(r.action)}</li>
      ${r.nums.length ? `<li><b>Valores detectados:</b> ${r.nums.map(e).join(', ')}</li>` : ''}</ul>
      <small style="color:var(--faint)">${api ? 'Gerado pelo back-end (PLN).' : 'Modo simulado: ligue a API para usar o modelo de linguagem.'}</small></div>`;
  }
  async function summaryAuto(text){
    if (live()) { try { return summaryResult(text, await API().summarize(text)); } catch (err) { /* cai no simulado */ } }
    return summaryResult(text);
  }


  /* Busca simulada no dataset de 1.000 logs (na versão final: RAG com embeddings + ChromaDB) */
  const STOP = 'erro erros problema problemas falha falhas qual quais como porque pelo pela para esse essa isso existe houve tive teve fala hoje mais sobre meus nossa nosso estao esta foram'.split(' ');
  const SYN = { banco:'db-primary', dados:'db-primary', pagamento:'payments-api', pagamentos:'payments-api', estoque:'inventory-service', busca:'search-service', login:'auth-service', autenticacao:'auth-service', fila:'orders-worker', pedidos:'orders-worker', cobranca:'billing-worker', cobrancas:'billing-worker', disco:'k8s-node-07', certificado:'cert-manager', notificacao:'notification-service', email:'notification-service', frontend:'web-frontend', navegador:'web-frontend', gateway:'api-gateway', agendador:'scheduler', memoria:'cache-redis', conexoes:'connections', lento:'latency', lentidao:'latency', atraso:'delay' };
  const norm = x => x.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
  function searchLogs(q){
    const L = window.AIOPS_LOGS; if (!L) return null;
    const words = norm(q).split(/[^a-z0-9-]+/).filter(w => w.length > 3 && STOP.indexOf(w) < 0).map(w => SYN[w] || w);
    if (!words.length) return null;
    const hits = [];
    L.forEach(r => {
      if (r[7] !== 1 && !/ruido|rotina/.test(norm(q))) return;
      const text = norm(r[2] + ' ' + r[3] + ' ' + r[5] + ' ' + r[6]);
      const sc = words.filter(w => text.indexOf(w) >= 0).length;
      if (sc) hits.push({ r, sc });
    });
    if (!hits.length) return null;
    const best = Math.max.apply(null, hits.map(h => h.sc));
    const top = hits.filter(h => h.sc === best).map(h => h.r);
    const svc = {}, inc = {};
    top.forEach(r => { svc[r[2]] = (svc[r[2]]||0)+1; if (r[6]) inc[r[6]] = (inc[r[6]]||0)+1; });
    const topSvc = Object.keys(svc).sort((a,b)=>svc[b]-svc[a]).slice(0,3);
    const topInc = Object.keys(inc).sort((a,b)=>inc[b]-inc[a])[0];
    const last = top[top.length-1];
    const errs = top.filter(r => r[3]==='ERROR').length;
    const sevs = [...new Set(top.map(r => r[4]))].join(', ');
    return {
      a:'Encontrei '+top.length+' registro'+(top.length>1?'s':'')+' relacionado'+(top.length>1?'s':'')+' entre os '+L.length+' logs analisados, principalmente em '+topSvc.join(', ')+(topInc?' ('+topInc+')':'')+'. Severidade: '+sevs+'; '+errs+' deles são erros. Registro mais recente ('+last[1].slice(11,16)+'): “'+last[5]+'”.',
      sources: top.slice(-3).reverse().map(r => r[2]+' · '+r[1].slice(11,16))
    };
  }

  function askAnswer(q){
    const t = q.toLowerCase();
    let hit = D.qa.find(x => x.q.toLowerCase() === t);
    if (!hit){
      const words = t.split(/\W+/).filter(w => w.length > 3);
      let best = null, bs = 0;
      D.qa.forEach(x => { const s = words.filter(w => x.q.toLowerCase().includes(w)).length; if (s > bs){ bs = s; best = x; } });
      if (bs >= 2) hit = best;
    }
    return hit || searchLogs(q) || { a:'Não encontrei logs que respondam a essa pergunta nos dados de exemplo. Tente uma das perguntas sugeridas.', sources:[] };
  }

  function chatMsg(kind, html){ return `<div class="msg ${kind}">${html}</div>`; }
  const provLabel = r => (r.provider === 'ollama' ? '🏠 modelo local' : '☁ DeepSeek') + ' · ' + e(r.model);
  function apiBotHtml(r){
    const src = r.sources || [];
    const badge = r.mode === 'llm' ? `${r.provider === 'ollama' ? 'Local' : 'DeepSeek'} · ${e(r.model)}` : r.mode === 'extrativo' ? 'resposta extrativa' : 'sem contexto';
    const list = src.length ? `<details class="src-det"><summary>${src.length} fonte(s) recuperadas do ChromaDB</summary><ol class="src-list">${src.map(p =>
      `<li><span class="chip">${e(p.service)}${p.ts ? ' · ' + e(p.ts.slice(11, 16)) : ''}${p.incident ? ' · ' + e(p.incident) : ''}</span> <small>${e(p.text.slice(0, 160))}</small></li>`).join('')}</ol></details>` : '';
    return `${e(r.answer)}<div class="src"><span class="chip" title="Modo de geração">🤖 ${badge}</span>${r.incident ? `<span class="chip">📎 ${e(r.incident)}</span>` : ''}</div>${list}${r.aviso ? `<small style="color:var(--faint)">⚠ ${e(r.aviso)}</small>` : ''}`;
  }
  function botHtml(r){ return `${e(r.a)}${r.sources.length?`<div class="src">${r.sources.map(s=>`<span class="chip">📎 ${e(s)}</span>`).join('')}</div>`:''}`; }

  /* liga um chat a elementos: {box, input, form, sugg} */
  function bindChat(o){
    const send = q => {
      if (!q.trim()) return;
      o.box.insertAdjacentHTML('beforeend', chatMsg('user', e(q)));
      const id = 't' + Date.now();
      o.box.insertAdjacentHTML('beforeend', `<div class="msg bot typing" id="${id}"><span></span><span></span><span></span></div>`);
      o.box.scrollTop = o.box.scrollHeight;
      const done = html => { const el = document.getElementById(id); if (el){ el.classList.remove('typing'); el.innerHTML = html; } o.box.scrollTop = o.box.scrollHeight; };
      if (live()) API().ask(q).then(r => { done(apiBotHtml(r)); document.dispatchEvent(new CustomEvent('aiops:feedback')); })
        .catch(() => done(botHtml(askAnswer(q)) + '<small style="color:var(--faint)">⚠ API indisponível: resposta simulada.</small>'));
      else setTimeout(() => done(botHtml(askAnswer(q))), 700);
    };
    o.form.addEventListener('submit', ev => { ev.preventDefault(); send(o.input.value); o.input.value=''; });
    if (o.sugg) o.sugg.addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) send(b.textContent); });
  }

  window.AIOPS_UI = { badge, alertCard, noiseCard, toast, bindAlertActions, setAlerts, summaryResult, summaryAuto, bindChat, chatMsg };
})();
