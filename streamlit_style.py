"""CSS do app Streamlit: porta fiel do front-end HTML (css/styles.css) + ajustes dos componentes do Streamlit."""

_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128' width='40' height='40'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='0'>"
        "<stop offset='0' stop-color='#A8EBE3'/><stop offset='1' stop-color='#8F7FE0'/></linearGradient></defs><rect width='128' height='128' rx='28' fill='#120C63'/>"
        "<polyline points='14,64 22,40 30,88 38,34 46,92 54,48 62,76 70,62' fill='none' stroke='#8F7FE0' stroke-width='6' stroke-linecap='round' stroke-linejoin='round' opacity='.75'/>"
        "<line x1='70' y1='62' x2='104' y2='62' stroke='url(#g)' stroke-width='7' stroke-linecap='round'/><circle cx='108' cy='62' r='9' fill='#34D6C3'/></svg>")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Montserrat:wght@400;500;600;700&display=swap');
:root{
  --bg-0:#030218; --bg-1:#0B0747; --surf:rgba(255,255,255,.045); --surf-2:rgba(255,255,255,.09); --line:rgba(255,255,255,.14);
  --text:#F4F2FF; --muted:#CFCBF7; --faint:#A9A4E2; --teal:#34D6C3; --lilac:#A992F5; --magenta:#F2589B; --amber:#F6B93B; --mint:#5FE3A1;
  --grad:linear-gradient(90deg,#A8EBE3,#8F7FE0);
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:'Montserrat',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif; --r:14px;
}
/* --- esconde o "chrome" do Streamlit --- */
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarHeader"], [data-testid="collapsedControl"]{display:none !important}
html, body, .stApp, [data-testid="stAppViewContainer"]{background:var(--bg-0) !important; color:var(--text); font-family:var(--sans); font-size:15px}
h1,h2,h3,h4,code,.mono{font-family:var(--mono) !important}
[data-testid="stMainBlockContainer"]{padding:30px 36px 60px !important; max-width:1280px !important}
a{color:var(--teal)}
.grad-text{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}

/* --- barra lateral --- */
section[data-testid="stSidebar"]{width:260px !important; min-width:260px !important; background:rgba(3,2,26,.72) !important; border-right:1px solid var(--line)}
section[data-testid="stSidebar"] > div{width:260px !important}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:24px 0 18px !important;width:100% !important;box-sizing:border-box;margin:0 !important}
.brand{display:flex;gap:10px;align-items:center;margin-bottom:22px}
.brand b{font-family:var(--mono);font-size:18px;letter-spacing:.5px;display:block;color:var(--text)}
.brand small{color:var(--faint);font-size:11px;display:block;line-height:1.2}
.st-key-nav,.st-key-nav [data-testid="stRadio"],.st-key-nav [data-testid="stRadioGroup"]{width:100% !important}
.st-key-nav [data-testid="stRadioGroup"]{gap:4px !important;flex-direction:column !important}
.st-key-nav [data-testid="stRadioGroup"] > div{width:100%}
.st-key-nav [data-testid="stRadioOption"]{display:flex !important;width:100%;padding:10px 14px !important;border-radius:12px;border:1px solid transparent;cursor:pointer;margin:0 !important;transition:background .15s, box-shadow .15s}
.st-key-nav [data-testid="stRadioOption"] > div > div:first-child{display:none !important}
.st-key-nav [data-testid="stRadioOption"] p{font-size:14px !important;font-weight:600 !important;color:var(--muted) !important;margin:0 !important;white-space:pre}
.st-key-nav [data-testid="stRadioOption"]:hover{background:var(--surf)}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"]{background:var(--surf-2);border-color:var(--line);box-shadow:inset 3px 0 0 var(--teal)}
.st-key-nav [data-testid="stRadioOption"][data-selected="true"] p{color:var(--text) !important}
.side-foot{margin-top:34px;font-size:12px;color:var(--faint);display:flex;flex-direction:column;gap:10px;line-height:1.5}
.side-foot a{font-weight:600;text-decoration:none}
.status-dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--amber);margin-right:6px}
.status-dot.on{background:var(--teal);box-shadow:0 0 8px var(--teal)}

section[data-testid="stSidebar"] [data-testid="stVerticalBlock"], section[data-testid="stSidebar"] [data-testid="stElementContainer"]{width:100% !important}
[class*="st-key-opt_"] button > div, [class*="st-key-opt_"] button [data-testid="stMarkdownContainer"]{text-align:left !important;justify-content:flex-start !important;width:100%}

/* --- cabeçalho de página --- */
.page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:22px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:3px;text-transform:uppercase;color:var(--teal);margin-bottom:6px}
.page-head h1{font-family:var(--mono);font-size:30px;line-height:1.2;font-weight:700;margin:0;padding:0;color:var(--text)}
.page-head p{color:var(--muted);max-width:60ch;margin:6px 0 0}
.live-tag{display:inline-block;white-space:nowrap;font-family:var(--mono);font-size:10.5px;letter-spacing:1px;text-transform:uppercase;color:var(--teal);border:1px solid var(--teal);border-radius:999px;padding:2px 9px}
.sim-tag{display:inline-block;font-family:var(--mono);font-size:10.5px;letter-spacing:1px;text-transform:uppercase;color:var(--amber);border:1px solid var(--amber);border-radius:999px;padding:2px 9px}

/* --- cards --- */
.card, [class*="st-key-card"]{background:var(--surf);border:1px solid var(--line);border-radius:var(--r);padding:20px}
[class*="st-key-card"]{margin-bottom:16px}
.card h2, [class*="st-key-card"] h2{font-family:var(--mono);font-size:15px;letter-spacing:.5px;margin:0 0 4px;padding:0;font-weight:700}
.sub{color:var(--faint);font-size:12.5px;margin-bottom:14px}
.grid{display:grid;gap:16px}.g4{grid-template-columns:repeat(4,1fr)}.g2{grid-template-columns:repeat(2,1fr)}
@media (max-width:1000px){.g4{grid-template-columns:repeat(2,1fr)}.g2{grid-template-columns:1fr}}
.kpi .label{font-size:12px;color:var(--faint);text-transform:uppercase;letter-spacing:1.5px;font-family:var(--mono)}
.kpi .value{font-family:var(--mono);font-size:34px;font-weight:700;margin:6px 0 2px;line-height:1.3}
.kpi .hint{font-size:12.5px;color:var(--muted)}
.kpi.hl{border-color:var(--teal);box-shadow:0 0 0 1px rgba(52,214,195,.25) inset}

/* --- badges, alertas --- */
.badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#fff;border-radius:999px;padding:3px 10px;white-space:nowrap}
.sev-critico{background:#C2306F}.sev-alto{background:#A8700A}.sev-medio{background:#6B52C9}.sev-baixo{background:#0F8F82}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
[class*="st-key-alert_"]{background:var(--surf);border:1px solid var(--line);border-left:5px solid var(--lilac);border-radius:12px;padding:14px 16px;margin-bottom:10px}
[class*="st-key-alert_critico"]{border-left-color:var(--magenta)}[class*="st-key-alert_alto"]{border-left-color:var(--amber)}
[class*="st-key-alert_medio"]{border-left-color:var(--lilac)}[class*="st-key-alert_baixo"]{border-left-color:var(--teal)}
.alert-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.alert-top .svc{font-family:var(--mono);font-weight:700}
.alert-top .time{margin-left:auto;color:var(--faint);font-size:12px}
.alert-title{font-weight:700;display:block;margin-bottom:6px}
.alert .summary{color:var(--muted);font-size:14px;margin:0 0 8px}
.alert-meta{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--faint);align-items:center;margin-bottom:4px}
.score{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:12px;color:var(--muted)}
.bar{width:90px;height:7px;background:rgba(255,255,255,.12);border-radius:99px;overflow:hidden;display:inline-block}
.bar i{display:block;height:100%;background:var(--grad)}
.chip{font-family:var(--mono);font-size:11px;background:rgba(52,214,195,.16);border:1px solid var(--teal);border-radius:8px;padding:2px 8px;color:var(--text);display:inline-block}
.noise-row{opacity:.55;border:1px dashed var(--line);border-radius:12px;padding:12px 16px;margin-bottom:8px;font-size:14px;color:var(--muted)}
.empty{padding:26px;text-align:center;color:var(--faint);border:1px dashed var(--line);border-radius:12px}

/* --- botões do Streamlit = .btn do HTML --- */
.stButton > button, .stFormSubmitButton > button{border:1px solid var(--line) !important;background:var(--surf-2) !important;border-radius:10px !important;padding:4px 12px !important;min-height:0 !important;color:var(--text) !important;transition:background .15s, filter .15s}
.stButton > button p, .stFormSubmitButton > button p{font-size:12.5px !important;font-weight:600 !important;margin:0 !important;white-space:nowrap;line-height:1.35}
.stButton > button:hover, .stFormSubmitButton > button:hover{background:rgba(255,255,255,.18) !important;border-color:var(--line) !important;color:var(--text) !important}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"], .stFormSubmitButton > button[kind="primary"]{background:var(--grad) !important;border-color:transparent !important;color:#0A0640 !important}
.stButton > button[kind="primary"] p, .stFormSubmitButton > button p{color:inherit !important}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover{filter:brightness(1.08)}
[class*="_on_"] button{border-color:var(--teal) !important;background:rgba(52,214,195,.2) !important}
.st-key-sugg .stButton > button{text-align:left;justify-content:flex-start;padding:9px 14px !important;width:100%}
.st-key-sugg .stButton > button p{font-size:13.5px !important;text-align:left;white-space:normal !important}
[class*="st-key-opt_"] button{padding:12px 16px !important;text-align:left;justify-content:flex-start;height:auto}
[class*="st-key-opt_"] button p{font-size:13.5px !important;text-align:left;white-space:normal !important}

/* --- campos --- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], textarea{background:rgba(0,0,0,.28) !important;border-color:var(--line) !important;border-radius:10px !important;color:var(--text) !important}
[data-baseweb="input"] input, textarea{color:var(--text) !important;font-family:var(--sans) !important}
[data-testid="stWidgetLabel"] p{font-size:13px;color:var(--muted);font-weight:600}
[data-testid="stExpander"]{border:1px solid var(--line) !important;border-radius:10px !important;background:rgba(255,255,255,.03)}
[data-testid="stExpander"] summary p{font-size:12.5px;color:var(--lilac)}

/* --- chat --- */
[class*="st-key-msg_"]{max-width:78%;padding:12px 15px;border-radius:14px;border:1px solid var(--line);font-size:14px;margin-bottom:12px}
[class*="st-key-msg_user"]{margin-left:auto;background:rgba(143,127,224,.35)}
[class*="st-key-msg_bot"]{margin-right:auto;background:var(--surf)}
[class*="st-key-msg_"] p{font-size:14px;margin-bottom:.4rem}
[class*="st-key-msg_"] ul{margin:4px 0 8px 18px}
[class*="st-key-msg_"] code{font-size:12px;background:rgba(169,146,245,.18);border-radius:5px;padding:1px 5px}
.src{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.typing span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--muted);margin-right:3px;animation:b 1s infinite}
.typing span:nth-child(2){animation-delay:.15s}.typing span:nth-child(3){animation-delay:.3s}
@keyframes b{0%,80%,100%{opacity:.25}40%{opacity:1}}

/* --- tabelas, matriz, linha do tempo, resultado --- */
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}
table.t th{font-family:var(--mono);font-size:11.5px;letter-spacing:1px;text-transform:uppercase;color:var(--faint);font-weight:600}
table.logtable{font-family:var(--mono);font-size:12px}
table.logtable td{vertical-align:top;padding:6px 8px}
.lvl-ERROR{color:var(--magenta)}.lvl-WARN{color:var(--amber)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin-top:8px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.cm{display:grid;grid-template-columns:auto 1fr 1fr;gap:6px;font-size:13px;text-align:center}
.cm div{padding:14px 8px;border-radius:10px}
.cm .h{color:var(--faint);font-size:11.5px;font-family:var(--mono);display:flex;align-items:center;justify-content:center}
.cm .ok{background:rgba(52,214,195,.22);border:1px solid var(--teal)}.cm .bad{background:rgba(242,88,155,.2);border:1px solid var(--magenta)}
.cm b{display:block;font-family:var(--mono);font-size:22px}
.timeline{list-style:none;display:flex;flex-direction:column;gap:10px;padding:0;margin:0}
.timeline li{display:flex;gap:12px;font-size:13.5px;color:var(--muted)}
.timeline time{font-family:var(--mono);color:var(--teal);min-width:48px}
.arch{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-family:var(--mono);font-size:12px}
.arch span.node{border:1px solid var(--line);border-radius:10px;padding:6px 10px;background:rgba(169,146,245,.1)}
.arch span.node.ok{border-color:var(--teal)}
.result{background:var(--surf);border:1px solid var(--teal);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:10px;margin-top:12px}
.result h3{font-size:13px;color:var(--teal);letter-spacing:1px;text-transform:uppercase;margin:0}
.result ul{padding-left:18px;color:var(--muted);font-size:14px;margin:0}
.chart-wrap svg{width:100%;height:auto;display:block}

/* --- janela (logs brutos) --- */
div[data-testid="stDialog"] div[role="dialog"]{background:#0A0640 !important;border:1px solid var(--line);border-radius:16px}
pre.log{background:rgba(0,0,0,.4);border-radius:10px;padding:12px;font-family:var(--mono);font-size:12px;overflow:auto;color:#d6f7f2;max-height:260px;white-space:pre-wrap;margin:0}
[data-testid="stToast"]{background:#0F8F82 !important;color:#fff !important;border-radius:12px}
hr{border-color:var(--line) !important}
</style>
"""

import urllib.parse as _u
LOGO = "<img width='40' height='40' alt='AIOps' src=\"data:image/svg+xml;utf8," + _u.quote(_SVG) + "\">"
