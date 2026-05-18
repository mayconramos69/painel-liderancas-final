import os
import sqlite3
import csv
import io
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque_essa_chave_em_producao")
DB_NAME = os.environ.get("DB_NAME", "sistema.db")

ADMIN_USER = "mayconramos2026"
ADMIN_PASS = "26511076mj"


def normalizar(texto):
    """Padroniza textos para comparação e evita duplicidade por diferença de maiúsculas/espaços."""
    return " ".join((texto or "").strip().lower().split())



        extensoes_permitidas = {"jpg", "jpeg", "png", "webp"}
        nome_original = secure_filename(arquivo.filename or "")
        extensao = nome_original.rsplit(".", 1)[-1].lower() if "." in nome_original else ""

        if extensao not in extensoes_permitidas:
            return ""

        pasta_upload = os.path.join(app.root_path, "static", "uploads")
        os.makedirs(pasta_upload, exist_ok=True)

        usuario_limpo = normalizar(usuario).replace(" ", "_") or "lideranca"
        nome_final = f"{usuario_limpo}_{int(datetime.now().timestamp())}.{extensao}"
        caminho = os.path.join(pasta_upload, nome_final)

        arquivo.save(caminho)

        return f"uploads/{nome_final}"

    except Exception as erro:
        print("ERRO AO SALVAR FOTO:", erro)
        return ""


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn



def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS espontaneos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lideranca_id INTEGER NOT NULL,
        nome_completo TEXT NOT NULL,
        municipio TEXT NOT NULL,
        telefone TEXT,
        endereco_completo TEXT,
        nome_normalizado TEXT,
        telefone_normalizado TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(lideranca_id) REFERENCES usuarios(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trabalho (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lideranca_id INTEGER NOT NULL,
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
        created_at TEXT NOT NULL,
        FOREIGN KEY(lideranca_id) REFERENCES usuarios(id)
    )
    """)

    # Migração automática:
    # Se o banco já foi criado por uma versão antiga, adiciona colunas novas sem apagar dados.
    def ensure_column(table, column, column_type="TEXT"):
        cols = [row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

        ensure_column("espontaneos", "nome_normalizado")
    ensure_column("espontaneos", "telefone_normalizado")
    ensure_column("trabalho", "nome_normalizado")
    ensure_column("trabalho", "telefone_normalizado")
    ensure_column("trabalho", "titulo_normalizado")

    # Preenche campos normalizados antigos, caso existam cadastros de versões anteriores.
    antigos_e = cur.execute("SELECT id, nome_completo, telefone FROM espontaneos WHERE nome_normalizado IS NULL OR telefone_normalizado IS NULL").fetchall()
    for r in antigos_e:
        cur.execute("UPDATE espontaneos SET nome_normalizado=?, telefone_normalizado=? WHERE id=?",
                    (normalizar(r["nome_completo"]), normalizar(r["telefone"]), r["id"]))

    antigos_t = cur.execute("SELECT id, nome, telefone, numero_titulo FROM trabalho WHERE nome_normalizado IS NULL OR telefone_normalizado IS NULL OR titulo_normalizado IS NULL").fetchall()
    for r in antigos_t:
        cur.execute("UPDATE trabalho SET nome_normalizado=?, telefone_normalizado=?, titulo_normalizado=? WHERE id=?",
                    (normalizar(r["nome"]), normalizar(r["telefone"]), normalizar(r["numero_titulo"]), r["id"]))

    admin = cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (ADMIN_USER,)).fetchone()
    if not admin:
        cur.execute("""
            INSERT INTO usuarios
            (nome, usuario, senha_hash, telefone, email, municipio, bairro, zona_regiao, perfil, status, created_at)
            VALUES (?, ?, ?, '', '', '', '', '', 'admin', 'ativo', ?)
        """, ("Administrador", ADMIN_USER, generate_password_hash(ADMIN_PASS), datetime.now().isoformat()))

    conn.commit()
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
            flash("Acesso restrito.")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def lideranca_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("perfil") != "lideranca":
            flash("Acesso restrito.")
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
    zona_regiao = request.form.get("zona_regiao", "").strip(), usuario)

    if not nome or not usuario or not senha:
        flash("Preencha nome, usuário e senha.")
        return redirect(url_for("index"))

    conn = db()
    try:
        conn.execute("""
            INSERT INTO usuarios
            (nome, usuario, senha_hash, telefone, email, municipio, bairro, zona_regiao, perfil, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'lideranca', 'pendente', ?)
        """, (nome, usuario, generate_password_hash(senha), telefone, email, municipio, bairro, zona_regiao, datetime.now().isoformat()))
        conn.commit()
        flash("Cadastro enviado. Aguarde aprovação do administrador.")
    except sqlite3.IntegrityError:
        flash("Esse usuário já existe. Escolha outro.")
    finally:
        conn.close()

    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    usuario = request.form.get("usuario", "").strip().lower()
    senha = request.form.get("senha", "").strip()

    conn = db()
    user = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
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

    if user["perfil"] == "admin":
        return redirect(url_for("admin"))
    return redirect(url_for("lideranca"))


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
    user = conn.execute("SELECT * FROM usuarios WHERE id=?", (lid,)).fetchone()
    espontaneos = conn.execute("SELECT * FROM espontaneos WHERE lideranca_id=? ORDER BY id DESC", (lid,)).fetchall()
    trabalhos = conn.execute("SELECT * FROM trabalho WHERE lideranca_id=? ORDER BY id DESC", (lid,)).fetchall()
    conn.close()
    return render_template("lideranca.html", user=user, espontaneos=espontaneos, trabalhos=trabalhos)



@app.route("/espontaneo/novo", methods=["POST"])
@login_required
@lideranca_required
def novo_espontaneo():
    nome = request.form.get("nome_completo", "").strip()
    municipio = request.form.get("municipio", "").strip()
    telefone = request.form.get("telefone", "").strip()
    endereco = request.form.get("endereco_completo", "").strip()

    nome_norm = normalizar(nome)
    tel_norm = normalizar(telefone)

    conn = db()

    existente = conn.execute("""
        SELECT e.id, e.nome_completo, u.nome AS lideranca_nome
        FROM espontaneos e
        JOIN usuarios u ON u.id = e.lideranca_id
        WHERE
            (e.telefone_normalizado != '' AND e.telefone_normalizado = ?)
            OR
            (e.nome_normalizado = ? AND LOWER(TRIM(e.municipio)) = LOWER(TRIM(?)))
        LIMIT 1
    """, (tel_norm, nome_norm, municipio)).fetchone()

    if existente:
        conn.close()
        flash(f"Cadastro bloqueado: essa pessoa já consta no sistema vinculada à liderança {existente['lideranca_nome']}.")
        return redirect(url_for("lideranca"))

    conn.execute("""
        INSERT INTO espontaneos
        (lideranca_id, nome_completo, municipio, telefone, endereco_completo, nome_normalizado, telefone_normalizado, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        nome,
        municipio,
        telefone,
        endereco,
        nome_norm,
        tel_norm,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    flash("Cadastro espontâneo salvo.")
    return redirect(url_for("lideranca"))



@app.route("/trabalho/novo", methods=["POST"])
@login_required
@lideranca_required
def novo_trabalho():
    nome = request.form.get("nome", "").strip()
    municipio = request.form.get("municipio", "").strip()
    colegio = request.form.get("colegio", "").strip()
    endereco = request.form.get("endereco", "").strip()
    telefone = request.form.get("telefone", "").strip()
    zona = request.form.get("zona", "").strip()
    secao = request.form.get("secao", "").strip()
    numero_titulo = request.form.get("numero_titulo", "").strip()

    nome_norm = normalizar(nome)
    tel_norm = normalizar(telefone)
    titulo_norm = normalizar(numero_titulo)

    conn = db()

    existente = conn.execute("""
        SELECT t.id, t.nome, u.nome AS lideranca_nome
        FROM trabalho t
        JOIN usuarios u ON u.id = t.lideranca_id
        WHERE
            (t.titulo_normalizado != '' AND t.titulo_normalizado = ?)
            OR
            (t.telefone_normalizado != '' AND t.telefone_normalizado = ?)
            OR
            (t.nome_normalizado = ? AND LOWER(TRIM(t.municipio)) = LOWER(TRIM(?)))
        LIMIT 1
    """, (titulo_norm, tel_norm, nome_norm, municipio)).fetchone()

    if existente:
        conn.close()
        flash(f"Cadastro bloqueado: essa pessoa já consta no sistema vinculada à liderança {existente['lideranca_nome']}.")
        return redirect(url_for("lideranca"))

    conn.execute("""
        INSERT INTO trabalho
        (lideranca_id, nome, municipio, colegio, endereco, telefone, zona, secao, numero_titulo,
         nome_normalizado, telefone_normalizado, titulo_normalizado, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        nome,
        municipio,
        colegio,
        endereco,
        telefone,
        zona,
        secao,
        numero_titulo,
        nome_norm,
        tel_norm,
        titulo_norm,
        datetime.now().isoformat()
    ))
    conn.commit()
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

    liderancas = conn.execute("""
        SELECT u.*,
            (SELECT COUNT(*) FROM espontaneos e WHERE e.lideranca_id = u.id) AS total_espontaneos,
            (SELECT COUNT(*) FROM trabalho t WHERE t.lideranca_id = u.id) AS total_trabalho
        FROM usuarios u
        WHERE u.perfil='lideranca'
        ORDER BY u.status DESC, u.nome ASC
    """).fetchall()

    total_liderancas = conn.execute("SELECT COUNT(*) c FROM usuarios WHERE perfil='lideranca'").fetchone()["c"]
    total_pendentes = conn.execute("SELECT COUNT(*) c FROM usuarios WHERE perfil='lideranca' AND status='pendente'").fetchone()["c"]
    total_esp = conn.execute("SELECT COUNT(*) c FROM espontaneos").fetchone()["c"]
    total_trab = conn.execute("SELECT COUNT(*) c FROM trabalho").fetchone()["c"]

    where_e = []
    params_e = []
    where_t = []
    params_t = []

    if busca:
        where_e.append("(e.nome_completo LIKE ? OR e.telefone LIKE ? OR u.nome LIKE ?)")
        params_e += [f"%{busca}%", f"%{busca}%", f"%{busca}%"]
        where_t.append("(t.nome LIKE ? OR t.telefone LIKE ? OR t.colegio LIKE ? OR u.nome LIKE ?)")
        params_t += [f"%{busca}%", f"%{busca}%", f"%{busca}%", f"%{busca}%"]

    if municipio:
        where_e.append("e.municipio LIKE ?")
        params_e.append(f"%{municipio}%")
        where_t.append("t.municipio LIKE ?")
        params_t.append(f"%{municipio}%")

    if lideranca_id:
        where_e.append("e.lideranca_id = ?")
        params_e.append(lideranca_id)
        where_t.append("t.lideranca_id = ?")
        params_t.append(lideranca_id)

    sql_e = """
        SELECT e.*, u.nome AS lideranca_nome
        FROM espontaneos e
        JOIN usuarios u ON u.id = e.lideranca_id
    """
    if where_e:
        sql_e += " WHERE " + " AND ".join(where_e)
    sql_e += " ORDER BY e.id DESC"

    sql_t = """
        SELECT t.*, u.nome AS lideranca_nome
        FROM trabalho t
        JOIN usuarios u ON u.id = t.lideranca_id
    """
    if where_t:
        sql_t += " WHERE " + " AND ".join(where_t)
    sql_t += " ORDER BY t.id DESC"

    espontaneos = conn.execute(sql_e, params_e).fetchall()
    trabalhos = conn.execute(sql_t, params_t).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        liderancas=liderancas,
        espontaneos=espontaneos,
        trabalhos=trabalhos,
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
    conn.execute("UPDATE usuarios SET status='ativo' WHERE id=? AND perfil='lideranca'", (user_id,))
    conn.commit()
    conn.close()
    flash("Liderança aprovada.")
    return redirect(url_for("admin"))


@app.route("/admin/bloquear/<int:user_id>")
@login_required
@admin_required
def bloquear(user_id):
    conn = db()
    conn.execute("UPDATE usuarios SET status='bloqueado' WHERE id=? AND perfil='lideranca'", (user_id,))
    conn.commit()
    conn.close()
    flash("Liderança bloqueada.")
    return redirect(url_for("admin"))


@app.route("/admin/exportar/<tipo>")
@login_required
@admin_required
def exportar(tipo):
    conn = db()
    output = io.StringIO()
    writer = csv.writer(output)

    if tipo == "espontaneos":
        writer.writerow(["Lideranca", "Nome completo", "Municipio", "Telefone", "Endereco completo", "Data"])
        rows = conn.execute("""
            SELECT e.*, u.nome AS lideranca_nome
            FROM espontaneos e JOIN usuarios u ON u.id=e.lideranca_id
            ORDER BY e.id DESC
        """).fetchall()
        for r in rows:
            writer.writerow([r["lideranca_nome"], r["nome_completo"], r["municipio"], r["telefone"], r["endereco_completo"], r["created_at"]])
        filename = "espontaneos.csv"
    else:
        writer.writerow(["Lideranca", "Nome", "Municipio", "Colegio", "Endereco", "Telefone", "Zona", "Secao", "Numero titulo", "Data"])
        rows = conn.execute("""
            SELECT t.*, u.nome AS lideranca_nome
            FROM trabalho t JOIN usuarios u ON u.id=t.lideranca_id
            ORDER BY t.id DESC
        """).fetchall()
        for r in rows:
            writer.writerow([r["lideranca_nome"], r["nome"], r["municipio"], r["colegio"], r["endereco"], r["telefone"], r["zona"], r["secao"], r["numero_titulo"], r["created_at"]])
        filename = "trabalho.csv"

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
