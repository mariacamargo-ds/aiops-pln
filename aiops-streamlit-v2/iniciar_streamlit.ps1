# Abre a versão em Streamlit (usa a API se ela estiver rodando; senão sobe o back-end embutido).
# Uso (PowerShell, com a venv ativa):   .\iniciar_streamlit.ps1
Set-Location $PSScriptRoot
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Criei o .env: abra-o e cole sua DEEPSEEK_API_KEY (ou use LLM_PROVIDER=ollama)." -ForegroundColor Yellow }
python -m pip install -q -r requirements-streamlit.txt
python -m streamlit run streamlit_app.py
