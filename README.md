# Sistema Área de Trabalho

Sistema final em Flask com:

- Login administrativo fixo:
  - usuário: mayconramos2026
  - senha: 26511076mj
- Cadastro público de lideranças
- Aprovação obrigatória pelo administrador
- Área da liderança com apenas:
  - Pessoas espontâneas
  - Trabalho
  - Listas dos próprios cadastros
- Painel administrativo com:
  - Todas as lideranças
  - Aprovações pendentes
  - Todos os cadastros espontâneos
  - Todos os cadastros de trabalho
  - Filtros por liderança, município e busca
  - Exportação CSV

## Rodar localmente

pip install -r requirements.txt
python app.py

Acesse:
http://127.0.0.1:5000

## Colocar online

Hospede em Render, Railway ou VPS.

Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app

Importante: para uso real com muitos cadastros, use PostgreSQL. Esta versão usa SQLite para facilitar o primeiro teste.


## Atualização anti-duplicidade

O sistema bloqueia cadastros repetidos.

### Pessoas espontâneas
Bloqueia quando já existe:
- mesmo telefone; ou
- mesmo nome + município.

### Trabalho
Bloqueia quando já existe:
- mesmo número do título; ou
- mesmo telefone; ou
- mesmo nome + município.

Quando bloquear, o sistema informa que a pessoa já consta vinculada a outra liderança.


## Foto da liderança

No cadastro inicial, a liderança pode anexar ou tirar uma foto de rosto.
A foto aparece:

- no perfil da própria liderança;
- na lista de lideranças do painel administrativo.

Arquivos aceitos:
- JPG
- JPEG
- PNG
- WEBP


## Correção Render

Esta versão tem migração automática do banco.
Se o Render já tinha criado um banco antigo sem foto_path ou sem colunas de duplicidade,
o sistema adiciona as colunas automaticamente sem apagar dados.
