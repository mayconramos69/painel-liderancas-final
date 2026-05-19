import os, csv, io
from datetime import datetime
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-temporaria")

DATABASE_URL = os.environ.get("DATABASE_URL")

ADMIN_USER = "mayconramos2026"
ADMIN_PASS = "26511076mj"


def normalizar(texto):
    return " ".join((texto or "").strip().lower().split())


def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada no Render.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        telefone TEXT,
        email TEXT,
        municipio TEXT,
        bairro TEXT,
        zona_regiao TEXT,
        perfil TEXT NOT NULL DEFAULT 'lideranca',
        status TEXT NOT NULL DEFAULT 'pendente',
        pode_trabalho INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS espontaneos (
        id SERIAL PRIMARY KEY,
        lideranca_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        nome_completo TEXT NOT NULL,
        municipio TEXT NOT NULL,
        telefone TEXT,
        endereco_completo TEXT,
        nome_normalizado TEXT,
        telefone_normalizado TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trabalho (
        id SERIAL PRIMARY KEY,
        lideranca_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        municipio TEXT NOT NULL,
        colegio TEXT,
        endereco TEXT,
        telefone TEXT,
        zona TEXT,
        secao TEXT,
        numero_titulo TEXT,
        nome_normalizado TEXT,
        telefone_normalizado TEXT,
        titulo_normalizado TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("SELECT id FROM usuarios WHERE usuario=%s", (ADMIN_USER,))
    admin = cur.fetchone()

    if not admin:
        cur.execute("""
            INSERT INTO usuarios
            (nome, usuario, senha_hash, telefone, email, municipio, bairro, zona_regiao, perfil, status, pode_trabalho, created_at)
            VALUES (%s, %s, %s, '', '', '', '', '', 'admin', 'ativo', 1, %s)
        """, ("Administrador", ADMIN_USER, generate_password_hash(ADMIN_PASS), datetime.now().isoformat()))
    else:
        cur.execute("UPDATE usuarios SET pode_trabalho=1, status='ativo', perfil='admin' WHERE usuario=%s", (ADMIN_USER,))

    conn.commit()
    cur.close()
    conn.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("perfil") != "admin":
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def lideranca_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("perfil") != "lideranca":
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    if session.get("perfil") == "admin":
        return redirect(url_for("admin"))
    if session.get("perfil") == "lideranca":
        return redirect(url_for("lideranca"))
    return render_template("index.html")


@app.route("/cadastro", methods=["POST"])
def cadastro():
    nome = request.form.get("nome", "").strip()
    usuario = request.form.get("usuario", "").strip().lower()
    senha = request.form.get("senha", "").strip()
    telefone = request.form.get("telefone", "").strip()
    email = request.form.get("email", "").strip()
    municipio = request.form.get("municipio", "").strip()
    bairro = request.form.get("bairro", "").strip()
    zona_regiao = request.form.get("zona_regiao", "").strip()

    if not nome or not usuario or not senha:
        flash("Preencha nome, usuário e senha.")
        return redirect(url_for("index"))

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO usuarios
            (nome, usuario, senha_hash, telefone, email, municipio, bairro, zona_regiao, perfil, status, pode_trabalho, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'lideranca', 'pendente', 0, %s)
        """, (nome, usuario, generate_password_hash(senha), telefone, email, municipio, bairro, zona_regiao, datetime.now().isoformat()))
        conn.commit()
        flash("Cadastro enviado. Aguarde aprovação do administrador.")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("Esse usuário já existe.")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    usuario = request.form.get("usuario", "").strip().lower()
    senha = request.form.get("senha", "").strip()

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario=%s", (usuario,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not check_password_hash(user["senha_hash"], senha):
        flash("Usuário ou senha inválidos.")
        return redirect(url_for("index"))

    if user["status"] != "ativo":
        flash("Seu acesso ainda não foi aprovado ou está bloqueado.")
        return redirect(url_for("index"))

    session["user_id"] = user["id"]
    session["nome"] = user["nome"]
    session["perfil"] = user["perfil"]

    return redirect(url_for("admin" if user["perfil"] == "admin" else "lideranca"))


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("index"))


@app.route("/lideranca")
@login_required
@lideranca_required
def lideranca():
    lid = session["user_id"]
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM usuarios WHERE id=%s", (lid,))
    user = cur.fetchone()

    cur.execute("SELECT * FROM espontaneos WHERE lideranca_id=%s ORDER BY id DESC", (lid,))
    esp = cur.fetchall()

    cur.execute("SELECT * FROM trabalho WHERE lideranca_id=%s ORDER BY id DESC", (lid,))
    trab = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("lideranca.html", user=user, espontaneos=esp, trabalhos=trab)


@app.route("/espontaneo/novo", methods=["POST"])
@login_required
@lideranca_required
def novo_espontaneo():
    nome = request.form.get("nome_completo", "").strip()
    municipio = request.form.get("municipio", "").strip()
    telefone = request.form.get("telefone", "").strip()
    endereco = request.form.get("endereco_completo", "").strip()

    nn = normalizar(nome)
    tn = normalizar(telefone)

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.nome AS lideranca_nome
        FROM espontaneos e
        JOIN usuarios u ON u.id=e.lideranca_id
        WHERE
            (e.telefone_normalizado != '' AND e.telefone_normalizado=%s)
            OR
            (e.nome_normalizado=%s AND LOWER(TRIM(e.municipio))=LOWER(TRIM(%s)))
        LIMIT 1
    """, (tn, nn, municipio))

    dup = cur.fetchone()

    if dup:
        cur.close()
        conn.close()
        flash(f"Cadastro bloqueado: já consta vinculado à liderança {dup['lideranca_nome']}.")
        return redirect(url_for("lideranca"))

    cur.execute("""
        INSERT INTO espontaneos
        (lideranca_id, nome_completo, municipio, telefone, endereco_completo, nome_normalizado, telefone_normalizado, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (session["user_id"], nome, municipio, telefone, endereco, nn, tn, datetime.now().isoformat()))

    conn.commit()
    cur.close()
    conn.close()

    flash("Cadastro espontâneo salvo.")
    return redirect(url_for("lideranca"))


@app.route("/trabalho/novo", methods=["POST"])
@login_required
@lideranca_required
def novo_trabalho():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT pode_trabalho FROM usuarios WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()

    if not user or int(user["pode_trabalho"] or 0) != 1:
        cur.close()
        conn.close()
        flash("Você ainda não tem autorização para cadastrar em Trabalho.")
        return redirect(url_for("lideranca"))

    nome = request.form.get("nome", "").strip()
    municipio = request.form.get("municipio", "").strip()
    colegio = request.form.get("colegio", "").strip()
    endereco = request.form.get("endereco", "").strip()
    telefone = request.form.get("telefone", "").strip()
    zona = request.form.get("zona", "").strip()
    secao = request.form.get("secao", "").strip()
    titulo = request.form.get("numero_titulo", "").strip()

    nn = normalizar(nome)
    tn = normalizar(telefone)
    titn = normalizar(titulo)

    cur.execute("""
        SELECT u.nome AS lideranca_nome
        FROM trabalho t
        JOIN usuarios u ON u.id=t.lideranca_id
        WHERE
            (t.titulo_normalizado != '' AND t.titulo_normalizado=%s)
            OR
            (t.telefone_normalizado != '' AND t.telefone_normalizado=%s)
            OR
            (t.nome_normalizado=%s AND LOWER(TRIM(t.municipio))=LOWER(TRIM(%s)))
        LIMIT 1
    """, (titn, tn, nn, municipio))

    dup = cur.fetchone()

    if dup:
        cur.close()
        conn.close()
        flash(f"Cadastro bloqueado: já consta vinculado à liderança {dup['lideranca_nome']}.")
        return redirect(url_for("lideranca"))

    cur.execute("""
        INSERT INTO trabalho
        (lideranca_id, nome, municipio, colegio, endereco, telefone, zona, secao, numero_titulo,
         nome_normalizado, telefone_normalizado, titulo_normalizado, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (session["user_id"], nome, municipio, colegio, endereco, telefone, zona, secao, titulo, nn, tn, titn, datetime.now().isoformat()))

    conn.commit()
    cur.close()
    conn.close()

    flash("Cadastro de trabalho salvo.")
    return redirect(url_for("lideranca"))


@app.route("/admin")
@login_required
@admin_required
def admin():
    busca = request.args.get("busca", "").strip()
    municipio = request.args.get("municipio", "").strip()
    lideranca_id = request.args.get("lideranca_id", "").strip()

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.*,
            (SELECT COUNT(*) FROM espontaneos e WHERE e.lideranca_id=u.id) AS total_espontaneos,
            (SELECT COUNT(*) FROM trabalho t WHERE t.lideranca_id=u.id) AS total_trabalho,
            ((SELECT COUNT(*) FROM espontaneos e WHERE e.lideranca_id=u.id) + (SELECT COUNT(*) FROM trabalho t WHERE t.lideranca_id=u.id)) AS total_geral
        FROM usuarios u
        WHERE u.perfil='lideranca'
        ORDER BY u.status DESC, total_geral DESC, u.nome ASC
    """)
    liderancas = cur.fetchall()

    cur.execute("""
        SELECT u.id, u.nome, u.municipio, u.status, u.pode_trabalho,
            COUNT(DISTINCT e.id) AS total_espontaneos,
            COUNT(DISTINCT t.id) AS total_trabalho,
            (COUNT(DISTINCT e.id) + COUNT(DISTINCT t.id)) AS total_geral
        FROM usuarios u
        LEFT JOIN espontaneos e ON e.lideranca_id=u.id
        LEFT JOIN trabalho t ON t.lideranca_id=u.id
        WHERE u.perfil='lideranca'
        GROUP BY u.id
        ORDER BY total_geral DESC, total_trabalho DESC, total_espontaneos DESC, u.nome ASC
        LIMIT 20
    """)
    ranking = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS c FROM usuarios WHERE perfil='lideranca'")
    total_liderancas = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM usuarios WHERE perfil='lideranca' AND status='pendente'")
    total_pendentes = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM espontaneos")
    total_esp = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM trabalho")
    total_trab = cur.fetchone()["c"]

    where_e, params_e = [], []
    where_t, params_t = [], []

    if busca:
        where_e.append("(e.nome_completo ILIKE %s OR e.telefone ILIKE %s OR u.nome ILIKE %s)")
        params_e += [f"%{busca}%", f"%{busca}%", f"%{busca}%"]

        where_t.append("(t.nome ILIKE %s OR t.telefone ILIKE %s OR t.colegio ILIKE %s OR u.nome ILIKE %s)")
        params_t += [f"%{busca}%", f"%{busca}%", f"%{busca}%", f"%{busca}%"]

    if municipio:
        where_e.append("e.municipio ILIKE %s")
        params_e.append(f"%{municipio}%")

        where_t.append("t.municipio ILIKE %s")
        params_t.append(f"%{municipio}%")

    if lideranca_id:
        where_e.append("e.lideranca_id=%s")
        params_e.append(lideranca_id)

        where_t.append("t.lideranca_id=%s")
        params_t.append(lideranca_id)

    sql_e = """
        SELECT e.*, u.nome AS lideranca_nome
        FROM espontaneos e
        JOIN usuarios u ON u.id=e.lideranca_id
    """
    if where_e:
        sql_e += " WHERE " + " AND ".join(where_e)
    sql_e += " ORDER BY e.id DESC"

    cur.execute(sql_e, params_e)
    esp = cur.fetchall()

    sql_t = """
        SELECT t.*, u.nome AS lideranca_nome
        FROM trabalho t
        JOIN usuarios u ON u.id=t.lideranca_id
    """
    if where_t:
        sql_t += " WHERE " + " AND ".join(where_t)
    sql_t += " ORDER BY t.id DESC"

    cur.execute(sql_t, params_t)
    trab = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "admin.html",
        liderancas=liderancas,
        ranking=ranking,
        espontaneos=esp,
        trabalhos=trab,
        total_liderancas=total_liderancas,
        total_pendentes=total_pendentes,
        total_esp=total_esp,
        total_trab=total_trab,
        busca=busca,
        municipio=municipio,
        lideranca_id=lideranca_id
    )


@app.route("/admin/aprovar/<int:user_id>")
@login_required
@admin_required
def aprovar(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET status='ativo' WHERE id=%s AND perfil='lideranca'", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Liderança aprovada.")
    return redirect(url_for("admin"))


@app.route("/admin/bloquear/<int:user_id>")
@login_required
@admin_required
def bloquear(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET status='bloqueado' WHERE id=%s AND perfil='lideranca'", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Liderança bloqueada.")
    return redirect(url_for("admin"))


@app.route("/admin/apagar_lideranca/<int:user_id>")
@login_required
@admin_required
def apagar_lideranca(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id=%s AND perfil='lideranca'", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Liderança apagada com todos os cadastros vinculados.")
    return redirect(url_for("admin"))


@app.route("/admin/permissao_trabalho/<int:user_id>/<acao>")
@login_required
@admin_required
def permissao_trabalho(user_id, acao):
    valor = 1 if acao == "liberar" else 0
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET pode_trabalho=%s WHERE id=%s AND perfil='lideranca'", (valor, user_id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Permissão de trabalho atualizada.")
    return redirect(url_for("admin"))


@app.route("/admin/editar_espontaneo/<int:item_id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_espontaneo(item_id):
    conn = db()
    cur = conn.cursor()

    if request.method == "POST":
        nome = request.form.get("nome_completo", "").strip()
        municipio = request.form.get("municipio", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco_completo", "").strip()

        cur.execute("""
            UPDATE espontaneos
            SET nome_completo=%s, municipio=%s, telefone=%s, endereco_completo=%s,
                nome_normalizado=%s, telefone_normalizado=%s
            WHERE id=%s
        """, (nome, municipio, telefone, endereco, normalizar(nome), normalizar(telefone), item_id))

        conn.commit()
        cur.close()
        conn.close()

        flash("Cadastro espontâneo editado.")
        return redirect(url_for("admin"))

    cur.execute("""
        SELECT e.*, u.nome AS lideranca_nome
        FROM espontaneos e
        JOIN usuarios u ON u.id=e.lideranca_id
        WHERE e.id=%s
    """, (item_id,))
    item = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("editar_espontaneo.html", item=item)


@app.route("/admin/editar_trabalho/<int:item_id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_trabalho(item_id):
    conn = db()
    cur = conn.cursor()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        municipio = request.form.get("municipio", "").strip()
        colegio = request.form.get("colegio", "").strip()
        endereco = request.form.get("endereco", "").strip()
        telefone = request.form.get("telefone", "").strip()
        zona = request.form.get("zona", "").strip()
        secao = request.form.get("secao", "").strip()
        titulo = request.form.get("numero_titulo", "").strip()

        cur.execute("""
            UPDATE trabalho
            SET nome=%s, municipio=%s, colegio=%s, endereco=%s, telefone=%s,
                zona=%s, secao=%s, numero_titulo=%s,
                nome_normalizado=%s, telefone_normalizado=%s, titulo_normalizado=%s
            WHERE id=%s
        """, (nome, municipio, colegio, endereco, telefone, zona, secao, titulo, normalizar(nome), normalizar(telefone), normalizar(titulo), item_id))

        conn.commit()
        cur.close()
        conn.close()

        flash("Cadastro de trabalho editado.")
        return redirect(url_for("admin"))

    cur.execute("""
        SELECT t.*, u.nome AS lideranca_nome
        FROM trabalho t
        JOIN usuarios u ON u.id=t.lideranca_id
        WHERE t.id=%s
    """, (item_id,))
    item = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("editar_trabalho.html", item=item)


@app.route("/admin/exportar/<tipo>")
@login_required
@admin_required
def exportar(tipo):
    conn = db()
    cur = conn.cursor()
    output = io.StringIO()
    writer = csv.writer(output)

    if tipo == "espontaneos":
        writer.writerow(["Lideranca", "Nome completo", "Municipio", "Telefone", "Endereco completo", "Data"])
        cur.execute("""
            SELECT e.*, u.nome AS lideranca_nome
            FROM espontaneos e
            JOIN usuarios u ON u.id=e.lideranca_id
            ORDER BY e.id DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            writer.writerow([r["lideranca_nome"], r["nome_completo"], r["municipio"], r["telefone"], r["endereco_completo"], r["created_at"]])
        filename = "espontaneos.csv"
    else:
        writer.writerow(["Lideranca", "Nome", "Municipio", "Colegio", "Endereco", "Telefone", "Zona", "Secao", "Numero titulo", "Data"])
        cur.execute("""
            SELECT t.*, u.nome AS lideranca_nome
            FROM trabalho t
            JOIN usuarios u ON u.id=t.lideranca_id
            ORDER BY t.id DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            writer.writerow([r["lideranca_nome"], r["nome"], r["municipio"], r["colegio"], r["endereco"], r["telefone"], r["zona"], r["secao"], r["numero_titulo"], r["created_at"]])
        filename = "trabalho.csv"

    cur.close()
    conn.close()

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
