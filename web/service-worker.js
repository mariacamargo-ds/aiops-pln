// Service worker do plug-in (Manifest V3)
// - Clicar no ícone da extensão abre o painel lateral.
// - Menu de clique direito "Resumir seleção com AIOps" envia o texto ao painel.

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
  chrome.contextMenus.create({
    id: 'aiops-summarize',
    title: 'Resumir seleção com AIOps',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'aiops-summarize' || !tab) return;
  // abre o painel imediatamente (precisa estar no gesto do usuário) e guarda o texto
  chrome.sidePanel.open({ tabId: tab.id });
  chrome.storage.session.set({ pendingSelection: info.selectionText || '' });
});
