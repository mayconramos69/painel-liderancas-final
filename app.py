{% extends "base.html" %}
{% block content %}
<section class="login-v2">
  <div class="login-v2-orb orb-a"></div><div class="login-v2-orb orb-b"></div>
  <main class="login-v2-shell">
    <section class="login-v2-brand">
      <div class="login-v2-logo"><span>CG</span><div><b>Central de Gestão</b><small>Organização e acompanhamento</small></div></div>
      <div class="login-v2-copy">
        <span class="login-v2-tag">AMBIENTE ORGANIZADO</span>
        <h1>Tudo organizado em um só lugar.</h1>
        <p>Um ambiente simples, seguro e moderno para acompanhar cadastros, informações e atividades com clareza.</p>
      </div>
      <div class="login-v2-stats">
        <div><b>01</b><span>Acesso protegido</span></div>
        <div><b>02</b><span>Informações organizadas</span></div>
        <div><b>03</b><span>Acompanhamento completo</span></div>
      </div>
    </section>
    <section class="login-v2-panel">
      <div class="login-v2-panel-head"><span>ACESSO SEGURO</span><h2>Bem-vindo</h2><p>Entre no painel ou solicite seu cadastro.</p></div>
      <div class="login-v2-tabs"><button type="button" class="active" data-tab="login">Entrar</button><button type="button" data-tab="cadastro">Criar acesso</button></div>
      <form id="login" class="login-v2-form active" method="post" action="{{ url_for('login') }}">
        <label>Usuário<input type="text" name="usuario" required autocomplete="username" placeholder="Seu usuário"></label>
        <label>Senha<input type="password" name="senha" required autocomplete="current-password" placeholder="Sua senha"></label>
        <button class="login-v2-submit" type="submit">Acessar painel <span>→</span></button>
        <small class="login-v2-safe">Ambiente exclusivo para pessoas autorizadas.</small>
      </form>
      <form id="cadastro" class="login-v2-form" method="post" action="{{ url_for('cadastro') }}">
        <div class="login-v2-grid">
          <label class="wide">Nome completo<input type="text" name="nome" required></label>
          <label>WhatsApp<input type="text" name="telefone" inputmode="numeric"></label>
          <label>E-mail<input type="email" name="email"></label>
          <label>Município<input type="text" name="municipio"></label>
          <label>Bairro<input type="text" name="bairro"></label>
          <label>Zona ou região<input type="text" name="zona_regiao"></label>
          <label>Usuário<input type="text" name="usuario" required></label>
          <label class="wide">Senha<input type="password" name="senha" required autocomplete="new-password"></label>
        </div>
        <button class="login-v2-submit" type="submit">Enviar solicitação <span>→</span></button>
        <small class="login-v2-safe">O acesso será liberado pelo administrador.</small>
      </form>
    </section>
  </main>
</section>
<script>
document.querySelectorAll('.login-v2-tabs button').forEach(btn=>btn.addEventListener('click',()=>{
 document.querySelectorAll('.login-v2-tabs button').forEach(x=>x.classList.remove('active'));
 document.querySelectorAll('.login-v2-form').forEach(x=>x.classList.remove('active'));
 btn.classList.add('active'); document.getElementById(btn.dataset.tab).classList.add('active');
}));
</script>
{% endblock %}
