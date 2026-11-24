# Inicia a demo completa: API + RAG + banco + front-end  ->  http://localhost:8000/app/
# Uso (PowerShell, dentro da pasta aiops-backend, com a venv ativada):   .\iniciar.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Criei o .env. Abra-o e cole sua DEEPSEEK_API_KEY (sem aspas) e, se quiser, DATABASE_URL." -ForegroundColor Yellow }
Start-Process "http://localhost:8000/app/"
python -m uvicorn app.main:app --port 8000
