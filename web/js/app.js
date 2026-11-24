/* Painel web: roteador por hash + 4 telas */
(function () {
  const D = window.AIOPS_DATA, U = window.AIOPS_UTIL, UI = window.AIOPS_UI, e = U.esc;
  const view = document.getElementById('view');
  const routes = {
    gerente:  { label:'Gerente',       ico:'📋', render: gerente },
    perguntar:{ label:'Perguntar',     ico:'💬', render: perguntar },
    dados:    { label:'Dados e sistema', ico:'🗄', render: dados },
    config:   { label:'Configuração',  ico:'⚙️', render: config },
    direcao:  { label:'Direção',       ico:'📊', render: direcao }
  };

  function nav(cur){
    const html = Object.entries(routes).map(([k,r]) =>
      `<a href="#${k}" ${k===cur?'aria-current="page"':''}><span class="ico" aria-hidden="true">${r.ico}</span>${r.label}</a>`).join('');
    document.getElementById('nav').innerHTML = html;
    document.getElementById('mnav').innerHTML = Object.entries(routes).map(([k,r]) =>
      `<a href="#${k}" ${k===cur?'aria-current="page"':''}>${r.ico} ${r.label}</a>`).join('');
  }

  function head(eyebrow, title, desc){
    return `<header class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${desc}</p></div>${tag()}</header>`;
  }
  const kpi = (l,v,h,hl) => `<div class="card kpi ${hl?'hl':''}"><div class="label">${l}</div><div class="value ${hl?'grad-text':''}">${v}</div><div class="hint">${h}</div></div>`;

  const API = window.AIOPS_API;
  const fmt = n => Number(n).toLocaleString('pt-BR');
  const tag = () => API.online ? '<span class="live-tag">ao vivo · API + banco</span>' : '<span class="sim-tag">dados simulados</span>';

  /* ---------- Gerente ---------- */
  async function gerente(){
    await API.ready;
    const live = API.online;
    let m = null; if (live) { try { m = await API.metrics(); } catch (er) { /* segue simulado */ } }
    const k = D.kpis;
    const kp = m ? [
      kpi('Logs no banco', fmt(m.logs_indexados), 'tabela rag_logs · ' + m.banco.motor),
      kpi('Logs relevantes', fmt(m.logs_relevantes), 'após classificação'),
      kpi('Ruído filtrado', String(m.ruido_pct).replace('.', ',') + '%', 'redução de alertas', true),
      kpi('Interações dos usuários', fmt(m.eventos_de_feedback), 'alimentam o ranking')] : [
      kpi('Alertas recebidos', k.received.toLocaleString('pt-BR'), 'últimas 24 h'), kpi('Alertas relevantes', k.relevant, 'após classificação'),
      kpi('Ruído filtrado', k.noisePct+'%', 'redução de alertas', true), kpi('MTTR real', k.mttr+' min', k.open+' incidentes abertos')];
    view.innerHTML = head('Painel do gerente','Alertas que realmente importam','O sistema filtra o ruído e ordena os incidentes pelo conteúdo dos logs e pela interação dos usuários.') + `
    <section class="grid g4" aria-label="Indicadores">${kp.join('')}</section>
    <section class="grid g-main" style="margin-top:16px">
      <div class="card">
        <h2>Incidentes priorizados</h2>
        <p class="sub">${live ? 'A relevância aprende com 👍, 👎, “Ver logs” e perguntas no chat. Críticos nunca somem.' : 'Ordenados por relevância. Ajuste a sensibilidade para ver o que o sistema descarta.'}</p>
        <div class="toolbar">
          <label class="slider-wrap" for="thr">Sensibilidade: <b class="mono" id="thrv">0,50</b>
            <input id="thr" type="range" min="0" max="1" step="0.05" value="0.5"></label>
          <label class="slider-wrap" for="sevf">Severidade:
            <select id="sevf" style="width:auto"><option value="">Todas</option>${Object.entries(D.sevLabel).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label>
          <label class="toggle"><input type="checkbox" id="shown"> Mostrar o que ficou abaixo do corte</label>
        </div>
        <ul class="alerts" id="alist" aria-live="polite"></ul>
        <p class="sub" id="ameta" style="margin-top:10px"></p>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px">
        <div class="card"><h2>Equipes e responsáveis</h2><p class="sub">Quem acionar em cada serviço.</p>
          <table><tbody>${D.people.map(p=>`<tr><td><b>${e(p.name)}</b><br><small style="color:var(--faint)">${e(p.role)}</small></td><td style="text-align:right"><a href="${p.link}" data-nolink>Contato</a></td></tr>`).join('')}</tbody></table></div>
        <div class="card"><h2>Linha do tempo</h2><p class="sub">Eventos do incidente principal.</p>
          <ol class="timeline">
            <li><time>13:40</time>Deploy de payments-api</li>
            <li><time>13:47</time>Erros 500 em checkout-service</li>
            <li><time>13:52</time>Pool de conexões esgotado</li>
            <li><time>13:56</time>Incidente aberto pelo AIOps</li></ol></div>
      </div>
    </section>`;
    const list = document.getElementById('alist'), thr = document.getElementById('thr'), sevf = document.getElementById('sevf'), sh = document.getElementById('shown'), meta = document.getElementById('ameta');
    let seq = 0;
    async function draw(){
      const t = +thr.value; document.getElementById('thrv').textContent = t.toFixed(2).replace('.',',');
      const my = ++seq;
      if (live) {
        try {
          const r = await API.alerts(t, sevf.value ? { severity: sevf.value } : {});
          if (my !== seq) return;
          UI.setAlerts(r.alerts);
          let html = r.alerts.map(a => UI.alertCard(a)).join('');
          if (sh.checked && r.meta.hidden_ids.length) {
            const all = await API.alerts(0, { explore: false, with_logs: false });
            html += all.alerts.filter(a => r.meta.hidden_ids.includes(a.id)).map(a => UI.noiseCard(a)).join('');
          }
          list.innerHTML = html || `<li class="empty">Nenhum alerta nesta sensibilidade. Reduza a sensibilidade para ver mais itens.</li>`;
          meta.textContent = `${r.meta.shown} de ${r.meta.total} incidentes visíveis · ${r.meta.hidden} abaixo do corte (críticos sempre aparecem).`;
          return;
        } catch (er) { API.online = false; }
      }
      const rel = D.alerts.filter(a => a.score >= t && (!sevf.value || a.severity === sevf.value));
      UI.setAlerts(D.alerts);
      let html = rel.map(a => UI.alertCard(a)).join('');
      if (sh.checked) html += D.noise.concat(D.alerts.filter(a => a.score < t)).map(n => UI.noiseCard(n)).join('');
      list.innerHTML = html || `<li class="empty">Nenhum alerta nesta sensibilidade. Reduza a sensibilidade para ver mais itens.</li>`;
    }
    let tm; [thr, sevf, sh].forEach(x => x.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(draw, 180); })); draw();
    document.addEventListener('aiops:feedback', function onfb(){ if (!document.getElementById('alist')) return document.removeEventListener('aiops:feedback', onfb); clearTimeout(tm); tm = setTimeout(draw, 300); });
    UI.bindAlertActions(list);
    view.querySelectorAll('[data-nolink]').forEach(a => a.addEventListener('click', ev => { ev.preventDefault(); UI.toast('Link de exemplo (simulado)'); }));
  }

  /* ---------- Perguntar ---------- */
  async function perguntar(){
    await API.ready;
    view.innerHTML = head('Perguntar aos logs','Pergunte em linguagem natural', API.online ? 'RAG de verdade: sua pergunta vira um vetor, o ChromaDB recupera os trechos mais parecidos e o modelo responde citando as fontes.' : 'Modo simulado sobre 1.000 logs sintéticos. Ligue a API para usar o RAG completo.') + `
    <div class="grid g-main">
      <div class="card">
        <div class="chat" id="chat" role="log" aria-live="polite">
          <div class="msg bot">Olá! Pergunte sobre incidentes, serviços ou erros. Exemplo: “O que causou a falha no checkout hoje?”</div></div>
        <form class="ask" id="askf"><label class="sr-only" for="q">Sua pergunta</label>
          <input type="text" id="q" placeholder="Digite sua pergunta…" autocomplete="off"><button class="btn primary" type="submit">Enviar</button></form>
      </div>
      <div class="card"><h2>Perguntas sugeridas</h2><p class="sub">Clique para testar.</p>
        <div class="sugg" id="sugg" style="flex-direction:column">${D.qa.map(x=>`<button class="btn" style="text-align:left">${e(x.q)}</button>`).join('')}</div>
        <p class="sub">Se não houver logs relevantes, o sistema avisa em vez de inventar uma resposta. Cada pergunta também conta como interesse no incidente citado.</p></div>
    </div>`;
    UI.bindChat({ box:document.getElementById('chat'), input:document.getElementById('q'), form:document.getElementById('askf'), sugg:document.getElementById('sugg') });
  }

  /* ---------- Dados e sistema (banco + índice vetorial) ---------- */
  async function dados(){
    await API.ready;
    if (!API.online) { view.innerHTML = head('Dados e sistema','Banco de dados e índice vetorial','') + `<div class="card"><h2>API desligada</h2><p class="sub">Esta tela lê o banco de dados de verdade. Inicie o back-end (<span class="mono">uvicorn app.main:app --port 8000</span>) e recarregue a página.</p></div>`; return; }
    const [m, h] = [await API.metrics(), API.health], b = m.banco;
    const sev = ['critico','alto','medio','baixo','ruido'];
    view.innerHTML = head('Dados e sistema','Do dado bruto à resposta','Tudo o que a demo usa: banco relacional, índice vetorial, API e modelo de linguagem.') + `
    <section class="card"><h2>Arquitetura em execução</h2><p class="sub">Cada caixa abaixo está respondendo agora.</p>
      <div class="arch"><span class="node ok">🖥 Front-end (este painel)</span>→<span class="node ok">⚙ API FastAPI</span>→<span class="node ok">🗄 ${e(b.motor)} · ${fmt(b.tabelas.rag_logs)} logs</span>
      <span>+</span><span class="node ok">🧭 ChromaDB · ${fmt(m.vetores_no_indice)} vetores (${e(m.embeddings)})</span>→<span class="node ${m.llm.habilitado?'ok':''}">🤖 ${m.llm.habilitado ? (m.llm.local ? 'Modelo local · ' : 'DeepSeek · ') + e(m.llm.modelo) : 'modelo desligado (resposta extrativa)'}</span></div></section>
    <section class="grid g4" style="margin-top:16px">
      ${kpi('Incidentes (rag_alertas)', fmt(b.tabelas.rag_alertas), 'agrupam os logs')}
      ${kpi('Logs (rag_logs)', fmt(b.tabelas.rag_logs), fmt(m.logs_relevantes) + ' relevantes')}
      ${kpi('Interações (rag_eventos_feedback)', fmt(b.tabelas.rag_eventos_feedback), Object.entries(m.eventos_por_tipo).map(([k,v])=>k+': '+v).join(' · ') || 'ainda sem interações')}
      ${kpi('Vetores no ChromaDB', fmt(m.vetores_no_indice), 'busca por similaridade', true)}
    </section>
    <section class="card" style="margin-top:16px"><h2>Logs no banco de dados</h2><p class="sub">Consulta direta à tabela <span class="mono">rag_logs</span> pela rota <span class="mono">GET /logs</span>.</p>
      <div class="filters">
        <label>Busca<input type="text" id="lq" placeholder="ex.: timeout"></label>
        <label>Serviço<select id="ls"><option value="">Todos</option></select></label>
        <label>Severidade<select id="lv"><option value="">Todas</option>${sev.map(x=>`<option>${x}</option>`).join('')}</select></label>
        <label>Nível<select id="ll"><option value="">Todos</option><option>ERROR</option><option>WARN</option><option>INFO</option></select></label>
      </div>
      <div style="overflow:auto"><table class="logtable"><thead><tr><th>Horário</th><th>Serviço</th><th>Nível</th><th>Incidente</th><th>Mensagem</th></tr></thead><tbody id="lrows"></tbody></table></div>
      <div class="pager"><span id="lcount"></span><button class="btn small" id="lprev">‹ Anterior</button><button class="btn small" id="lnext">Próxima ›</button></div></section>
    <section class="card" style="margin-top:16px"><h2>Top 5 incidentes agora</h2><p class="sub">Ordem calculada pelo conteúdo + interação dos usuários.</p>
      <table><thead><tr><th>Incidente</th><th>Serviço</th><th>Relevância</th></tr></thead><tbody>${m.top5.map(t=>`<tr><td class="mono">${e(t.id)}</td><td>${e(t.service)}</td><td class="mono">${t.score.toFixed(2).replace('.',',')}</td></tr>`).join('')}</tbody></table></section>`;
    const services = [...new Set((await API.alerts(0,{explore:false,with_logs:false})).alerts.map(a=>a.service))].sort();
    document.getElementById('ls').insertAdjacentHTML('beforeend', services.map(s=>`<option>${e(s)}</option>`).join(''));
    let off = 0; const L = 12, g = id => document.getElementById(id);
    async function load(){
      const p = { limit: L, offset: off }; [['lq','q'],['ls','service'],['lv','severity'],['ll','level']].forEach(([i,k]) => { if (g(i).value) p[k] = g(i).value; });
      const r = await API.logs(p);
      g('lrows').innerHTML = r.items.map(x => `<tr><td>${e(x.ts.slice(5,16))}</td><td>${e(x.service)}</td><td class="lvl-${x.level}">${x.level}</td><td>${e(x.incident||'—')}</td><td>${e(x.message)}</td></tr>`).join('') || '<tr><td colspan="5">Nenhum log com esses filtros.</td></tr>';
      g('lcount').textContent = `${r.total ? off+1 : 0}–${Math.min(off+L, r.total)} de ${fmt(r.total)}`;
      g('lprev').disabled = off === 0; g('lnext').disabled = off + L >= r.total;
    }
    ['lq','ls','lv','ll'].forEach(i => g(i).addEventListener('input', () => { off = 0; clearTimeout(g(i)._t); g(i)._t = setTimeout(load, 220); }));
    g('lprev').onclick = () => { off = Math.max(0, off - L); load(); }; g('lnext').onclick = () => { off += L; load(); };
    load();
  }

  /* ---------- Configuração / performance ---------- */
  async function config(){
    const m = U.metrics(D.confusion), c = D.confusion;
    const saved = U.store.get('cfg', { thr:0.5, group:true, email:true, window:'15' });
    view.innerHTML = head('Configuração e performance','Desempenho do classificador','Métricas do modelo, matriz de confusão e parâmetros do sistema.') + `
    <section class="grid g4">
      ${kpi('Acurácia', U.pct(m.a), 'acertos totais')}
      ${kpi('Precisão', U.pct(m.p), 'alertas marcados que eram relevantes')}
      ${kpi('Recall', U.pct(m.r), 'relevantes que foram encontrados')}
      ${kpi('F1-score', m.f.toFixed(2).replace('.',','), 'equilíbrio precisão/recall', true)}
    </section>
    <section class="grid g2" style="margin-top:16px">
      <div class="card"><h2>Matriz de confusão</h2><p class="sub">Conjunto de teste simulado (${c.tp+c.fp+c.fn+c.tn} alertas).</p>
        <div class="cm"><span></span><div class="h">previsto relevante</div><div class="h">previsto ruído</div>
          <div class="h">real relevante</div><div class="ok"><b>${c.tp}</b>verdadeiro positivo</div><div class="bad"><b>${c.fn}</b>falso negativo</div>
          <div class="h">real ruído</div><div class="bad"><b>${c.fp}</b>falso positivo</div><div class="ok"><b>${c.tn}</b>verdadeiro negativo</div></div>
        <p class="sub" style="margin-top:12px">Falso negativo é o erro mais grave: um alerta relevante tratado como ruído.</p></div>
      <div class="card"><h2>Parâmetros do sistema</h2><p class="sub">Salvos neste navegador.</p>
        <form id="cfgf" class="form-grid">
          <label class="f">Sensibilidade padrão<input type="range" id="c-thr" min="0" max="1" step="0.05" value="${saved.thr}"><span class="mono" id="c-thrv">${saved.thr}</span></label>
          <label class="f">Janela de agrupamento<select id="c-win"><option value="5">5 minutos</option><option value="15">15 minutos</option><option value="60">1 hora</option></select></label>
          <label class="toggle"><input type="checkbox" id="c-grp" ${saved.group?'checked':''}> Agrupar alertas repetidos</label>
          <label class="toggle"><input type="checkbox" id="c-mail" ${saved.email?'checked':''}> Resumo diário por e-mail</label>
          <div style="grid-column:1/-1"><button class="btn primary" type="submit">Salvar configurações</button></div></form></div>
    </section>
    <section class="card" style="margin-top:16px" id="llmcard"><h2>Modelo de linguagem</h2>
      <p class="sub">Escolha quem escreve as respostas. O modelo local é gratuito e roda no seu computador; a nuvem gasta tokens.</p>
      <div id="llmbody"><p class="sub">${API.online ? 'Consultando…' : 'Disponível quando a API estiver ligada.'}</p></div></section>
    <section class="card" style="margin-top:16px"><h2>Histórico de treinamento</h2><p class="sub">Versões do modelo (simulado).</p>
      <ol class="timeline">${D.history.map(h=>`<li><time>${h.date}</time>${e(h.text)}</li>`).join('')}</ol></section>`;
    document.getElementById('c-win').value = saved.window;
    const t = document.getElementById('c-thr'); t.oninput = () => document.getElementById('c-thrv').textContent = t.value;
    document.getElementById('cfgf').onsubmit = ev => { ev.preventDefault();
      U.store.set('cfg', { thr:+t.value, group:document.getElementById('c-grp').checked, email:document.getElementById('c-mail').checked, window:document.getElementById('c-win').value });
      UI.toast('Configurações salvas.'); };
    if (API.online) llmCard();
  }

  /* ---------- seletor do modelo de linguagem (local / nuvem / sem IA) ---------- */
  async function llmCard(){
    const box = document.getElementById('llmbody'); if (!box) return;
    let st; try { st = await API.llm(); } catch (er) { box.innerHTML = '<p class="sub">Não consegui consultar a API.</p>'; return; }
    const opt = (v, ico, t, d) => `<button class="btn" data-p="${v}" aria-pressed="${st.provider === v}" style="text-align:left;flex:1;min-width:190px"><b>${ico} ${t}</b><br><small style="font-weight:500">${d}</small></button>`;
    const L = st.local, warn = !L.online ? '⚠ Ollama não encontrado. Instale em ollama.com e deixe-o aberto.' : !L.installed ? `⚠ Modelo ainda não baixado. No PowerShell: <span class="mono">ollama pull ${e(L.model)}</span>` : `✔ ${e(L.model)} pronto`;
    box.innerHTML = `<div style="display:flex;gap:10px;flex-wrap:wrap">
        ${opt('ollama','🏠','Local (grátis)','Ollama · '+e(L.model))}${opt('deepseek','☁','Nuvem (DeepSeek)',st.cloud.configured ? e(st.cloud.model)+' · paga por token' : 'chave não configurada')}${opt('off','🧩','Sem IA','resposta extrativa, custo zero')}</div>
      <p class="sub" style="margin-top:12px">Modelo local: ${warn}${L.models.length ? '<br>Baixados: ' + L.models.map(e).join(', ') : ''}</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="llmwarm" ${st.provider === 'off' ? 'disabled' : ''}>🔥 Aquecer / testar modelo</button><span class="mono" id="llmres" style="align-self:center;font-size:12px"></span></div>`;
    box.querySelectorAll('button[data-p]').forEach(b => b.onclick = async () => {
      try { await API.setLlm(b.dataset.p); UI.toast('Modelo alterado: ' + b.querySelector('b').textContent.replace(/^\S+\s/, '')); llmCard(); } catch (er) { UI.toast('Falha ao trocar o modelo.'); }
    });
    document.getElementById('llmwarm').onclick = async () => {
      const out = document.getElementById('llmres'); out.textContent = 'testando… (o 1º uso de um modelo local pode levar um minuto)';
      try { const r = await API.warmup(); out.textContent = r.ok ? `✔ respondeu em ${r.segundos} s` : '✖ ' + r.erro; } catch (er) { out.textContent = '✖ sem resposta'; }
    };
  }

  /* ---------- Direção ---------- */
  function groupedBars(title, unit, d, max, note){
    const cols = [['sistema','Estimativa do sistema','#A992F5'],['equipe','Estimativa da equipe','#F6B93B'],['real','Resultado real','#34D6C3']];
    const W=520,H=230,pad=40,bw=90,gap=44;
    let x=pad+34, s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${title}: ${cols.map(c=>c[1]+' '+d[c[0]]+unit).join('; ')}">`;
    [0,.5,1].forEach(f=>{ const y=H-30-f*(H-60); s+=`<line x1="${pad}" x2="${W-10}" y1="${y}" y2="${y}" stroke="rgba(255,255,255,.14)"/><text x="${pad-6}" y="${y+4}" fill="#A9A4E2" font-size="11" text-anchor="end">${Math.round(f*max)}</text>`; });
    cols.forEach(([k,l,col])=>{ const v=d[k], h=v/max*(H-60), y=H-30-h;
      s+=`<rect x="${x}" y="${y}" width="${bw}" height="${h}" rx="6" fill="${col}"/><text x="${x+bw/2}" y="${y-6}" fill="#F4F2FF" font-size="13" font-weight="700" text-anchor="middle" font-family="JetBrains Mono,monospace">${v}${unit}</text><text x="${x+bw/2}" y="${H-12}" fill="#CFCBF7" font-size="11" text-anchor="middle">${l.split(' ').pop()}</text>`; x+=bw+gap; });
    return `<div class="card chart-wrap"><h2>${title}</h2><p class="sub">${note}</p>${s}</svg>
      <div class="legend">${cols.map(c=>`<span><i class="dot" style="background:${c[2]}"></i>${c[1]}</span>`).join('')}</div></div>`;
  }
  function direcao(){
    const sv = D.director.severity7d, tot = Object.values(sv).reduce((a,b)=>a+b,0), mx = Math.max(...Object.values(sv));
    view.innerHTML = head('Painel da direção','Estimado × real','Compara a previsão do sistema, a estimativa da equipe e o resultado real, para decidir com base em dados.') + `
    <section class="grid g2">
      ${groupedBars('Redução de ruído','%',D.director.noise,100,'Quanto maior, melhor.')}
      ${groupedBars('Tempo médio de resolução (MTTR)',' min',D.director.mttr,40,'Quanto menor, melhor.')}
    </section>
    <section class="card" style="margin-top:16px"><h2>Incidentes por severidade (7 dias)</h2><p class="sub">Total: ${tot} incidentes.</p>
      <table><thead><tr><th>Severidade</th><th>Quantidade</th><th style="width:50%">Proporção</th></tr></thead><tbody>
      ${Object.entries(sv).map(([k,v])=>`<tr><td>${UI.badge(k)}</td><td class="mono">${v}</td><td><div class="bar" style="width:100%;height:10px"><i style="width:${v/mx*100}%;background:var(--${{critico:'magenta',alto:'amber',medio:'lilac',baixo:'teal'}[k]})"></i></div></td></tr>`).join('')}</tbody></table></section>
    <section class="card" style="margin-top:16px"><h2>Leitura rápida</h2>
      <p style="color:var(--muted)">O resultado real de redução de ruído (93%) ficou próximo da estimativa do sistema (95%) e acima da estimativa da equipe (88%). O MTTR real (24 min) ficou entre a previsão do sistema (18 min) e a da equipe (35 min).</p></section>`;
  }

  async function route(){
    await API.ready;
    const k = (location.hash || '#gerente').slice(1); const r = routes[k] || routes.gerente;
    nav(routes[k] ? k : 'gerente'); r.render(); document.title = r.label + ' · AIOps'; window.scrollTo(0,0);
    document.getElementById('view').focus({preventScroll:true});
  }
  window.addEventListener('hashchange', route); route();
  API.ready.then(on => { const el = document.getElementById('apistat'); if (el) el.innerHTML = on ? '<i class="status-dot on"></i>API conectada' : '<i class="status-dot"></i>modo simulado (API desligada)'; });
})();
