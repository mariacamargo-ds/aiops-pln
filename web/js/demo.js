/* Página de demonstração: simula o comportamento do plug-in sobre uma página qualquer */
(function () {
  const fc = document.getElementById('fc');
  const hs = [18,22,20,25,19,24,30,28,35,60,92,88,70];
  fc.innerHTML = hs.map(h => `<i class="${h>55?'hot':''}" style="height:${h}%"></i>`).join('');

  const frame = document.querySelector('iframe');
  let btn = null;
  const clear = () => { if (btn){ btn.remove(); btn = null; } };

  document.addEventListener('mouseup', ev => {
    if (ev.target.closest('.float-btn')) return;
    setTimeout(() => {
      const sel = window.getSelection(), text = sel ? sel.toString().trim() : '';
      clear();
      if (text.length < 8) return;
      const r = sel.getRangeAt(0).getBoundingClientRect();
      btn = document.createElement('button');
      btn.className = 'float-btn'; btn.textContent = 'Resumir com AIOps';
      btn.style.left = Math.max(8, r.left + window.scrollX) + 'px';
      btn.style.top = (r.bottom + window.scrollY + 8) + 'px';
      btn.addEventListener('click', () => {
        frame.contentWindow.postMessage({ type:'aiops:summarize', text }, '*');
        clear();
      });
      document.body.appendChild(btn);
    }, 0);
  });
  document.addEventListener('mousedown', ev => { if (!ev.target.closest('.float-btn')) clear(); });
})();
