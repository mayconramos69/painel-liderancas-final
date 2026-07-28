# Central de Gestão

Aplicação Flask com PostgreSQL para Render.

## Render
Build Command: `pip install -r requirements.txt`
Start Command: `gunicorn --workers 2 --timeout 120 app:app`

Variáveis obrigatórias:
- `DATABASE_URL`
- `SECRET_KEY`

A rota `/health` pode ser usada no Health Check do Render.
