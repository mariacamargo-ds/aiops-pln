/* Painel lateral do plug-in: Alertas | Perguntar | Resumir */
(function () {
  const D = window.AIOPS_DATA, U = window.AIOPS_UTIL, UI = window.AIOPS_UI, e = U.esc;
  const $ = id => document.getElementById(id);
  const tabs = ['alertas','perguntar','resumir'];

  function select(name){
    tabs.forEach(t => { $('tab-'+t).setAttribute('aria-selected', String(t===name)); $('pan-'+t).hidden = t!==name; });
  }
  tabs.forEach(t => $('tab-'+t).addEventListener('click', () => select(t)));

  const API = window.AIOPS_API;
  // Alertas
  function drawStatic(){
    $('sp-kpis').innerHTML = `<div><b>${D.kpis.relevant}</b><small>relevantes</small></div><div><b class="grad-text">${D.kpis.noisePct}%</b><small>ruído filtrado</small></div><div><b>${D.kpis.open}</b><small>abertos</small></div>`;
    UI.setAlerts(D.alerts);
    $('sp-alerts').innerHTML = D.alerts.slice(0,5).map(a => UI.alertCard(a, { compact:true })).join('');
  }
  async function drawAlerts(){
    if (API.online) {
      try {
        const [r, m] = await Promise.all([API.alerts(0.5, { limit: 5 }), API.metrics()]);
        UI.setAlerts(r.alerts);
        $('sp-kpis').innerHTML = `<div><b>${r.meta.shown}</b><small>visíveis</small></div><div><b class="grad-text">${String(m.ruido_pct).replace('.', ',')}%</b><small>ruído filtrado</small></div><div><b>${m.eventos_de_feedback}</b><small>interações</small></div>`;
        $('sp-alerts').innerHTML = r.alerts.map(a => UI.alertCard(a, { compact:true })).join('');
        return;
      } catch (err) { API.online = false; }
    }
    drawStatic();
  }
  UI.bindAlertActions($('sp-alerts'));
  API.ready.then(on => {
    const t = $('sp-tag'); if (on) { t.textContent = 'ao vivo'; t.className = 'live-tag'; }
    drawAlerts();
  });
  document.addEventListener('aiops:feedback', () => setTimeout(drawAlerts, 300));

  // Perguntar
  UI.bindChat({ box:$('sp-chat'), input:$('sp-q'), form:$('sp-askf'), sugg:$('sp-sugg') });

  // Resumir
  async function summarize(text){
    $('sp-text').value = text;
    select('resumir');
    if (!text.trim()) { $('sp-result').innerHTML = ''; return; }
    $('sp-result').innerHTML = '<p class="sub">Resumindo…</p>';
    $('sp-result').innerHTML = await UI.summaryAuto(text);
  }
  $('sp-sum').addEventListener('click', () => summarize($('sp-text').value));
  $('sp-example').addEventListener('click', () => {
    const L = (window.AIOPS_LOGS || []).filter(r => r[7] === 1), i = Math.floor(Math.random() * Math.max(1, L.length - 8));
    const pick = L.filter(r => r[6] === (L[i] || [])[6]).slice(0, 8);
    summarize(pick.length ? pick.map(r => r[1] + ' ' + r[3].padEnd(5) + ' ' + r[2] + ' ' + r[5]).join('\n') : D.alerts[0].log);
  });

  // 1) demo: mensagem vinda da página (iframe)
  window.addEventListener('message', ev => {
    if (ev.data && ev.data.type === 'aiops:summarize' && typeof ev.data.text === 'string') summarize(ev.data.text);
  });
  // 2) extensão real: texto guardado pelo service worker
  try {
    if (window.chrome && chrome.storage && chrome.storage.session) {
      const take = () => chrome.storage.session.get('pendingSelection', r => {
        if (r && r.pendingSelection){ summarize(r.pendingSelection); chrome.storage.session.remove('pendingSelection'); }
      });
      take();
      chrome.storage.onChanged.addListener((ch, area) => { if (area === 'session' && ch.pendingSelection) take(); });
    }
  } catch (err) { /* fora da extensão: ignora */ }
})();
