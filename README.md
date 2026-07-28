# Painel de Lideranças

Versão organizada com:

- edição de cada contato liberada individualmente pelo administrador;
- permissão encerrada automaticamente após a liderança salvar a alteração;
- aba de conferência de títulos válidos, inválidos e não informados;
- filtros e seleção visual dos títulos;
- exportação em Word editável e CSV;
- banco atualizado de forma aditiva, sem apagar cadastros existentes.

## Render

Build Command:

pip install -r requirements.txt

Start Command:

gunicorn --workers 2 --timeout 120 app:app
