{% extends "base.html" %}
{% block content %}
<header class="topbar modern-topbar">
  <div class="topbar-brand"><span class="mini-logo">CG</span><div><small>PAINEL DE LIDERANÇAS</small><strong>Central administrativa</strong></div></div>
  <div class="top-actions"><div class="user-chip"><span class="user-avatar">{{ (session.get('nome') or 'A')[0] }}</span><div><small>Administrador</small><b>{{ session.get('nome') }}</b></div></div><a class="btn logout-btn" href="{{ url_for('sair') }}">Sair</a></div>
</header>
<main class="container admin-shell">
  <section class="hero-admin modern-hero">
    <div><span class="eyebrow">VISÃO GERAL</span><h1>Bom trabalho, {{ session.get('nome') }}.</h1><p>Acompanhe os cadastros, previsões e atividades de todas as lideranças.</p></div>
    <div class="hero-side"><span>PREVISÃO TOTAL</span><strong>{{ total_votos_previstos }}</strong><small>votos informados</small></div>
  </section>

  <div class="metrics metrics-six dashboard-metrics">
    <div class="metric"><span class="metric-icon">L</span><small>Lideranças</small><strong>{{ total_liderancas }}</strong><em>Total de acessos</em></div>
    <div class="metric warning"><span class="metric-icon">!</span><small>Pendentes</small><strong>{{ total_pendentes }}</strong><em>Aguardando análise</em></div>
    <div class="metric"><span class="metric-icon">E</span><small>Espontâneos</small><strong>{{ total_esp }}</strong><em>Apoios cadastrados</em></div>
    <div class="metric"><span class="metric-icon">T</span><small>Trabalho</small><strong>{{ total_trab }}</strong><em>Cadastros realizados</em></div>
    <div class="metric"><span class="metric-icon">R</span><small>Líderes de rua</small><strong>{{ total_lideres_rua }}</strong><em>Atuação territorial</em></div>
    <div class="metric accent"><span class="metric-icon">BU</span><small>Boca de Urna</small><strong>{{ total_trabalho_bu }}</strong><em>Organização por urna</em></div>
  </div>

  <nav class="section-nav">
    <a href="#liderancas">Lideranças</a><a href="#titulos">Títulos</a><a href="#espontaneos">Espontâneos</a><a href="#trabalho">Trabalho</a><a href="#relatorios">Relatórios</a>
  </nav>

  <section class="card filter-card">
    <div class="section-heading"><div><span class="eyebrow">PESQUISA</span><h2>Filtros gerais</h2></div></div>
    <form method="get" action="{{ url_for('admin') }}" class="grid3">
      <div><label>Busca geral</label><input name="busca" value="{{ busca }}" placeholder="Nome, telefone, colégio ou liderança"></div>
      <div><label>Município</label><input name="municipio" value="{{ municipio }}" placeholder="Ex: Saquarema"></div>
      <div><label>Liderança</label><select name="lideranca_id"><option value="">Todas</option>{% for l in liderancas %}<option value="{{ l.id }}" {% if lideranca_id|string == l.id|string %}selected{% endif %}>{{ l.nome }}</option>{% endfor %}</select></div>
      <div class="full"><button class="btn" type="submit">Filtrar informações</button> <a class="btn ghost" href="{{ url_for('admin') }}">Limpar</a></div>
    </form>
  </section>

  <section class="card" id="liderancas">
    <div class="section-heading"><div><span class="eyebrow">ACESSOS</span><h2>Lideranças</h2></div><span class="section-count">{{ total_liderancas }} cadastradas</span></div>
    <div class="table-wrap no-shadow"><table><thead><tr><th>Nome</th><th>Município</th><th>Telefone</th><th>Status</th><th>Espontâneos</th><th>Trabalho</th><th>Permissão</th><th>Ações</th></tr></thead><tbody>
    {% for l in liderancas %}<tr><td><b>{{ l.nome }}</b></td><td>{{ l.municipio }}</td><td>{{ l.telefone }}</td><td><span class="status {{ l.status }}">{{ l.status }}</span></td><td>{{ l.total_espontaneos }}</td><td>{{ l.total_trabalho }}</td><td>{% if l.pode_trabalho|int == 1 %}<span class="permitido">Liberado</span>{% else %}<span class="negado">Bloqueado</span>{% endif %}</td><td class="actions"><a class="linkbtn" href="{{ url_for('admin', lideranca_id=l.id) }}">Ver</a>{% if l.status != 'ativo' %}<a class="linkbtn green" href="{{ url_for('aprovar', user_id=l.id) }}">Aprovar</a>{% endif %}{% if l.pode_trabalho|int == 1 %}<a class="linkbtn orange" href="{{ url_for('permissao_trabalho', user_id=l.id, acao='bloquear') }}">Bloquear trabalho</a>{% else %}<a class="linkbtn green" href="{{ url_for('permissao_trabalho', user_id=l.id, acao='liberar') }}">Liberar trabalho</a>{% endif %}<a class="linkbtn red" href="{{ url_for('bloquear', user_id=l.id) }}">Bloquear</a><a class="linkbtn dark" onclick="return confirm('Apagar esta liderança e todos os cadastros vinculados?')" href="{{ url_for('apagar_lideranca', user_id=l.id) }}">Apagar</a></td></tr>{% else %}<tr><td colspan="8">Nenhuma liderança cadastrada.</td></tr>{% endfor %}
    </tbody></table></div>
  </section>
<section class="card ranking-card"><div class="section-heading"><div><span class="eyebrow">DESEMPENHO</span><h2>Ranking de produtividade</h2></div></div><div class="table-wrap no-shadow"><table><thead><tr><th>#</th><th>Liderança</th><th>Município</th><th>Espontâneos</th><th>Trabalho</th><th>Total</th></tr></thead><tbody>{% for r in ranking %}<tr><td>{{ loop.index }}</td><td><b>{{ r.nome }}</b></td><td>{{ r.municipio }}</td><td>{{ r.total_espontaneos }}</td><td>{{ r.total_trabalho }}</td><td><b>{{ r.total_geral }}</b></td></tr>{% else %}<tr><td colspan="6">Sem dados para ranking.</td></tr>{% endfor %}</tbody></table></div></section>

  
<section class="card title-audit" id="titulos">
  <div class="section-heading"><div><span class="eyebrow">CONFERÊNCIA</span><h2>Validação dos títulos</h2><p class="muted">Veja rapidamente quais números estão corretos e quais precisam ser revisados.</p></div></div>
  <div class="title-summary">
    <a class="title-stat valid" href="{{ url_for('admin', titulo_status='validos') }}#titulos"><small>Válidos</small><strong>{{ total_titulos_validos }}</strong></a>
    <a class="title-stat invalid" href="{{ url_for('admin', titulo_status='invalidos') }}#titulos"><small>Inválidos</small><strong>{{ total_titulos_invalidos }}</strong></a>
    <a class="title-stat neutral" href="{{ url_for('admin', titulo_status='nao_informados') }}#titulos"><small>Não informados</small><strong>{{ total_titulos_nao_informados }}</strong></a>
  </div>
  <div class="title-toolbar">
    <div class="segmented-filter">
      <a class="{% if titulo_status == 'todos' %}active{% endif %}" href="{{ url_for('admin', titulo_status='todos') }}#titulos">Todos</a>
      <a class="{% if titulo_status == 'validos' %}active{% endif %}" href="{{ url_for('admin', titulo_status='validos') }}#titulos">Válidos</a>
      <a class="{% if titulo_status == 'invalidos' %}active{% endif %}" href="{{ url_for('admin', titulo_status='invalidos') }}#titulos">Inválidos</a>
      <a class="{% if titulo_status == 'nao_informados' %}active{% endif %}" href="{{ url_for('admin', titulo_status='nao_informados') }}#titulos">Sem título</a>
    </div>
    <div class="export-actions"><a class="btn ghost" href="{{ url_for('exportar_word', tipo='titulos_validos') }}">Word válidos</a><a class="btn ghost" href="{{ url_for('exportar_word', tipo='titulos_invalidos') }}">Word inválidos</a></div>
  </div>
  <div class="table-wrap no-shadow compact-table"><table><thead><tr><th><input type="checkbox" class="selecionar-titulos" title="Selecionar todos"></th><th>Pessoa</th><th>Liderança</th><th>Número</th><th>Origem</th><th>Cidade</th><th>Zona</th><th>Seção</th><th>Status</th></tr></thead><tbody>
  {% for t in titulos_lista %}<tr><td><input type="checkbox" class="titulo-check" value="{{ t.id }}"></td><td><b>{{ t.nome }}</b></td><td>{{ t.lideranca_nome }}</td><td>{{ t.numero_titulo or 'Não informado' }}</td><td>{{ t.titulo_uf or 'Não identificada' }}</td><td>{{ t.municipio }}</td><td>{{ t.zona }}</td><td>{{ t.secao }}</td><td>{% if t.titulo_valido == 1 %}<span class="titulo-selo valido">Válido</span>{% elif t.titulo_valido == 0 %}<span class="titulo-selo invalido">Inválido</span>{% else %}<span class="titulo-selo vazio">Não informado</span>{% endif %}</td></tr>{% else %}<tr><td colspan="9">Nenhum título nesta seleção.</td></tr>{% endfor %}
  </tbody></table></div>
</section>

<section class="card" id="espontaneos"><div class="section-heading"><div><span class="eyebrow">CONTATOS</span><h2>Cadastros espontâneos</h2></div><div class="export-actions"><a class="btn ghost" href="{{ url_for('exportar', tipo='espontaneos') }}">CSV</a><a class="btn yellow" href="{{ url_for('exportar_word', tipo='espontaneos') }}">Word editável</a></div></div><div class="table-wrap no-shadow"><table><thead><tr><th class="select-col"><input type="checkbox" class="selecionar-todos" title="Selecionar todos"></th><th>Liderança</th><th>Nome completo</th><th>Município</th><th>Telefone</th><th>WhatsApp</th><th>Endereço completo</th><th>Ação</th></tr></thead><tbody>{% for e in espontaneos %}<tr>{% set numero = e.telefone|whatsapp_numero %}<td class="select-col">{% if numero %}<input type="checkbox" class="contato-check" data-numero="{{ numero }}" data-nome="{{ e.nome_completo|e }}">{% endif %}</td><td>{{ e.lideranca_nome }}</td><td><b>{{ e.nome_completo }}</b></td><td>{{ e.municipio }}</td><td>{{ e.telefone }}</td><td>{% if numero %}<a class="whatsapp-btn" href="https://wa.me/{{ numero }}" target="_blank" rel="noopener" title="Abrir conversa no WhatsApp" aria-label="Abrir WhatsApp de {{ e.nome_completo }}"><span>✆</span></a>{% else %}<span class="whatsapp-off">Sem número</span>{% endif %}</td><td>{{ e.endereco_completo }}</td><td class="actions"><a class="linkbtn" href="{{ url_for('editar_espontaneo', item_id=e.id) }}">Editar</a>{% if e.edit_liberado|int == 1 %}<a class="linkbtn orange" href="{{ url_for('permissao_edicao', tipo='espontaneo', item_id=e.id, acao='bloquear') }}">Bloquear edição</a>{% else %}<a class="linkbtn green" href="{{ url_for('permissao_edicao', tipo='espontaneo', item_id=e.id, acao='liberar') }}">Liberar edição</a>{% endif %}</td></tr>{% else %}<tr><td colspan="8">Nenhum cadastro encontrado.</td></tr>{% endfor %}</tbody></table></div></section>

  <section class="card" id="trabalho"><div class="section-heading"><div><span class="eyebrow">CONTATOS</span><h2>Cadastros de trabalho</h2></div><div class="export-actions"><a class="btn ghost" href="{{ url_for('exportar', tipo='trabalho') }}">CSV</a><a class="btn yellow" href="{{ url_for('exportar_word', tipo='trabalho') }}">Word editável</a></div></div><div class="table-wrap no-shadow"><table><thead><tr><th class="select-col"><input type="checkbox" class="selecionar-todos" title="Selecionar todos"></th><th>Foto</th><th>Liderança</th><th>Nome</th><th>Tipo</th><th>Previsão de votos</th><th>Município</th><th>Colégio</th><th>Endereço</th><th>Telefone</th><th>WhatsApp</th><th>Zona</th><th>Seção</th><th>Título</th><th>Validação</th><th>Ação</th></tr></thead><tbody>{% for t in trabalhos %}<tr>{% set numero = t.telefone|whatsapp_numero %}<td class="select-col">{% if numero %}<input type="checkbox" class="contato-check" data-numero="{{ numero }}" data-nome="{{ t.nome|e }}">{% endif %}</td><td>{% if t.foto %}<img class="foto-pessoa" src="{{ url_for('foto_trabalho', item_id=t.id) }}" alt="Foto de {{ t.nome }}">{% else %}<div class="foto-pessoa foto-vazia">{{ t.nome[:1]|upper }}</div>{% endif %}</td><td>{{ t.lideranca_nome }}</td><td><b>{{ t.nome }}</b></td><td><span class="tipo-trabalho">{% if t.tipo_trabalho == 'Trabalho de BU' or not t.tipo_trabalho %}Boca de Urna{% else %}{{ t.tipo_trabalho }}{% endif %}</span></td><td><b>{{ t.votos_previstos or 0 }}</b></td><td>{{ t.municipio }}</td><td>{{ t.colegio }}</td><td>{{ t.endereco }}</td><td>{{ t.telefone }}</td><td>{% if numero %}<a class="whatsapp-btn" href="https://wa.me/{{ numero }}" target="_blank" rel="noopener" title="Abrir conversa no WhatsApp" aria-label="Abrir WhatsApp de {{ t.nome }}"><span>✆</span></a>{% else %}<span class="whatsapp-off">Sem número</span>{% endif %}</td><td>{{ t.zona }}</td><td>{{ t.secao }}</td><td>{{ t.numero_titulo }}</td>{% set info = t.numero_titulo|titulo_info %}<td><span class="titulo-selo {% if info.valido %}valido{% elif info.valido is sameas false %}invalido{% else %}vazio{% endif %}">{% if info.valido %}Válido{% elif info.valido is sameas false %}Inválido{% else %}Não informado{% endif %}</span><small class="titulo-origem">{{ info.uf }}</small></td><td class="actions"><a class="linkbtn" href="{{ url_for('editar_trabalho', item_id=t.id) }}">Editar</a>{% if t.edit_liberado|int == 1 %}<a class="linkbtn orange" href="{{ url_for('permissao_edicao', tipo='trabalho', item_id=t.id, acao='bloquear') }}">Bloquear edição</a>{% else %}<a class="linkbtn green" href="{{ url_for('permissao_edicao', tipo='trabalho', item_id=t.id, acao='liberar') }}">Liberar edição</a>{% endif %}</td></tr>{% else %}<tr><td colspan="16">Nenhum cadastro encontrado.</td></tr>{% endfor %}</tbody></table></div></section>

  <section class="report-panel" id="relatorios"><div><span class="eyebrow">RELATÓRIOS</span><h2>Exportações rápidas</h2><p>Baixe cada lista separadamente, pronta para imprimir ou encaminhar.</p></div><div class="report-buttons"><a href="{{ url_for('exportar_word', tipo='espontaneos') }}">Word Espontâneos</a><a href="{{ url_for('exportar_word', tipo='trabalho') }}">Word Trabalho</a></div></section>
</main>


<div id="barra-selecionados" class="barra-selecionados hidden">
  <div>
    <strong id="contador-selecionados">0 contatos selecionados</strong>
    <span>Abra o WhatsApp dos contatos escolhidos, um por vez.</span>
  </div>
  <div class="barra-acoes">
    <button type="button" class="btn green" id="encaminhar-selecionados">Encaminhar selecionados</button>
    <button type="button" class="btn dark" id="limpar-selecao">Limpar</button>
  </div>
</div>

<div id="modal-envio" class="modal-envio hidden" role="dialog" aria-modal="true">
  <div class="modal-envio-card">
    <button type="button" class="modal-fechar" id="fechar-modal" aria-label="Fechar">×</button>
    <span class="eyebrow">WHATSAPP</span>
    <h2>Contatos selecionados</h2>
    <p id="fila-texto">Prepare a fila para começar.</p>
    <div class="progresso-envio"><div id="barra-progresso"></div></div>
    <div class="disparo-actions">
      <button type="button" class="btn green" id="abrir-proximo">Abrir primeiro contato</button>
      <button type="button" class="btn dark" id="encerrar-fila">Encerrar</button>
    </div>
    <p class="muted pequeno">A conversa será aberta sem mensagem pronta. Você escreve e envia diretamente pelo WhatsApp.</p>
  </div>
</div>

<script>
(function(){
  const checks = () => Array.from(document.querySelectorAll('.contato-check'));
  const barra = document.getElementById('barra-selecionados');
  const contador = document.getElementById('contador-selecionados');
  const modal = document.getElementById('modal-envio');
  const filaTexto = document.getElementById('fila-texto');
  const abrirProximo = document.getElementById('abrir-proximo');
  const progresso = document.getElementById('barra-progresso');

  let fila = [];
  let indice = 0;

  function selecionados(){
    return checks().filter(item => item.checked);
  }

  function atualizarSelecao(){
    const total = selecionados().length;
    contador.textContent = total + (total === 1 ? ' contato selecionado' : ' contatos selecionados');
    barra.classList.toggle('hidden', total === 0);
  }

  document.querySelectorAll('.selecionar-todos').forEach(master => {
    master.addEventListener('change', function(){
      const tabela = master.closest('table');
      tabela.querySelectorAll('.contato-check').forEach(item => item.checked = master.checked);
      atualizarSelecao();
    });
  });

  document.addEventListener('change', function(event){
    if(event.target.classList.contains('contato-check')){
      atualizarSelecao();
    }
  });

  function atualizarFila(){
    const total = fila.length;
    const concluidos = Math.min(indice, total);
    progresso.style.width = (total ? (concluidos / total) * 100 : 0) + '%';

    if(!total){
      filaTexto.textContent = 'Nenhum contato selecionado.';
      abrirProximo.disabled = true;
      return;
    }

    if(indice >= total){
      filaTexto.textContent = 'Todos os ' + total + ' contatos foram abertos.';
      abrirProximo.textContent = 'Fila concluída';
      abrirProximo.disabled = true;
      progresso.style.width = '100%';
      return;
    }

    const contato = fila[indice];
    filaTexto.textContent = 'Próximo: ' + contato.nome + ' — contato ' + (indice + 1) + ' de ' + total;
    abrirProximo.textContent = indice === 0 ? 'Abrir primeiro contato' : 'Abrir próximo contato';
    abrirProximo.disabled = false;
  }

  document.getElementById('encaminhar-selecionados').addEventListener('click', function(){
    fila = selecionados().map(item => ({
      numero: item.dataset.numero,
      nome: item.dataset.nome || 'Contato'
    }));
    indice = 0;

    if(!fila.length){
      alert('Selecione pelo menos um contato.');
      return;
    }

    modal.classList.remove('hidden');
    atualizarFila();
  });

  abrirProximo.addEventListener('click', function(){
    if(indice >= fila.length) return;

    const contato = fila[indice];
    window.open('https://wa.me/' + contato.numero, '_blank', 'noopener');
    indice += 1;
    atualizarFila();
  });

  function fecharModal(){
    modal.classList.add('hidden');
  }

  document.getElementById('fechar-modal').addEventListener('click', fecharModal);
  document.getElementById('encerrar-fila').addEventListener('click', fecharModal);

  modal.addEventListener('click', function(event){
    if(event.target === modal) fecharModal();
  });

  document.getElementById('limpar-selecao').addEventListener('click', function(){
    checks().forEach(item => item.checked = false);
    document.querySelectorAll('.selecionar-todos').forEach(item => item.checked = false);
    fila = [];
    indice = 0;
    fecharModal();
    atualizarSelecao();
  });

  atualizarSelecao();
})();
</script>
<script>
(function(){
 const master=document.querySelector('.selecionar-titulos');
 if(master){master.addEventListener('change',()=>document.querySelectorAll('.titulo-check').forEach(c=>c.checked=master.checked));}
})();
</script>
{% endblock %}
