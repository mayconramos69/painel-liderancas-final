import os, sqlite3, csv, io
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-temporaria")
DB_NAME = os.environ.get("DB_NAME", "sistema.db")
ADMIN_USER = "mayconramos2026"
ADMIN_PASS = "26511076mj"

def normalizar(texto):
    return " ".join((texto or "").strip().lower().split())

def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_column(cur, table, column, column_type):
    cols = [row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, usuario TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL, telefone TEXT, email TEXT, municipio TEXT, bairro TEXT, zona_regiao TEXT,
        perfil TEXT NOT NULL DEFAULT 'lideranca', status TEXT NOT NULL DEFAULT 'pendente', pode_trabalho INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS espontaneos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lideranca_id INTEGER NOT NULL, nome_completo TEXT NOT NULL,
        municipio TEXT NOT NULL, telefone TEXT, endereco_completo TEXT, nome_normalizado TEXT, telefone_normalizado TEXT,
        created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS trabalho (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lideranca_id INTEGER NOT NULL, nome TEXT NOT NULL, municipio TEXT NOT NULL,
        colegio TEXT, endereco TEXT, telefone TEXT, zona TEXT, secao TEXT, numero_titulo TEXT,
        nome_normalizado TEXT, telefone_normalizado TEXT, titulo_normalizado TEXT, created_at TEXT NOT NULL)""")
    ensure_column(cur, "usuarios", "pode_trabalho", "INTEGER NOT NULL DEFAULT 0")
    admin = cur.execute("SELECT id FROM usuarios WHERE usuario=?", (ADMIN_USER,)).fetchone()
    if not admin:
        cur.execute("""INSERT INTO usuarios
        (nome, usuario, senha_hash, telefone, email, municipio, bairro, zona_regiao, perfil, status, pode_trabalho, created_at)
        VALUES (?, ?, ?, '', '', '', '', '', 'admin', 'ativo', 1, ?)""",
        ("Administrador", ADMIN_USER, generate_password_hash(ADMIN_PASS), datetime.now().isoformat()))
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
    nome = request.form.get("nome","").strip()
    usuario = request.form.get("usuario","").strip().lower()
    senha = request.form.get("senha","").strip()
    telefone = request.form.get("telefone","").strip()
    email = request.form.get("email","").strip()
    municipio = request.form.get("municipio","").strip()
    bairro = request.form.get("bairro","").strip()
    zona_regiao = request.form.get("zona_regiao","").strip()
    if not nome or not usuario or not senha:
        flash("Preencha nome, usuário e senha.")
        return redirect(url_for("index"))
    conn = db()
    try:
        conn.execute("""INSERT INTO usuarios
        (nome, usuario, senha_hash, telefone, email, municipio, bairro, zona_regiao, perfil, status, pode_trabalho, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'lideranca', 'pendente', 0, ?)""",
        (nome, usuario, generate_password_hash(senha), telefone, email, municipio, bairro, zona_regiao, datetime.now().isoformat()))
        conn.commit()
        flash("Cadastro enviado. Aguarde aprovação do administrador.")
    except sqlite3.IntegrityError:
        flash("Esse usuário já existe.")
    finally:
        conn.close()
    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    usuario = request.form.get("usuario","").strip().lower()
    senha = request.form.get("senha","").strip()
    conn = db()
    user = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user["senha_hash"], senha):
        flash("Usuário ou senha inválidos.")
        return redirect(url_for("index"))
    if user["status"] != "ativo":
        flash("Seu acesso ainda não foi aprovado ou está bloqueado.")
        return redirect(url_for("index"))
    session["user_id"], session["nome"], session["perfil"] = user["id"], user["nome"], user["perfil"]
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
    user = conn.execute("SELECT * FROM usuarios WHERE id=?", (lid,)).fetchone()
    esp = conn.execute("SELECT * FROM espontaneos WHERE lideranca_id=? ORDER BY id DESC", (lid,)).fetchall()
    trab = conn.execute("SELECT * FROM trabalho WHERE lideranca_id=? ORDER BY id DESC", (lid,)).fetchall()
    conn.close()
    return render_template("lideranca.html", user=user, espontaneos=esp, trabalhos=trab)

@app.route("/espontaneo/novo", methods=["POST"])
@login_required
@lideranca_required
def novo_espontaneo():
    nome = request.form.get("nome_completo","").strip()
    municipio = request.form.get("municipio","").strip()
    telefone = request.form.get("telefone","").strip()
    endereco = request.form.get("endereco_completo","").strip()
    nn, tn = normalizar(nome), normalizar(telefone)
    conn = db()
    dup = conn.execute("""SELECT u.nome lideranca_nome FROM espontaneos e JOIN usuarios u ON u.id=e.lideranca_id
        WHERE (e.telefone_normalizado!='' AND e.telefone_normalizado=?) OR
        (e.nome_normalizado=? AND LOWER(TRIM(e.municipio))=LOWER(TRIM(?))) LIMIT 1""", (tn, nn, municipio)).fetchone()
    if dup:
        conn.close()
        flash(f"Cadastro bloqueado: já consta vinculado à liderança {dup['lideranca_nome']}.")
        return redirect(url_for("lideranca"))
    conn.execute("""INSERT INTO espontaneos
        (lideranca_id,nome_completo,municipio,telefone,endereco_completo,nome_normalizado,telefone_normalizado,created_at)
        VALUES (?,?,?,?,?,?,?,?)""", (session["user_id"], nome, municipio, telefone, endereco, nn, tn, datetime.now().isoformat()))
    conn.commit(); conn.close()
    flash("Cadastro espontâneo salvo.")
    return redirect(url_for("lideranca"))


@app.route("/trabalho/novo", methods=["POST"])
@login_required
@lideranca_required
def novo_trabalho():
    conn = db()
    user = conn.execute("SELECT pode_trabalho FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
    if not user or int(user["pode_trabalho"] or 0) != 1:
        conn.close()
        flash("Você ainda não tem autorização para cadastrar em Trabalho.")
        return redirect(url_for("lideranca"))

    nome = request.form.get("nome","").strip()
    municipio = request.form.get("municipio","").strip()
    colegio = request.form.get("colegio","").strip()
    endereco = request.form.get("endereco","").strip()
    telefone = request.form.get("telefone","").strip()
    zona = request.form.get("zona","").strip()
    secao = request.form.get("secao","").strip()
    titulo = request.form.get("numero_titulo","").strip()
    nn, tn, titn = normalizar(nome), normalizar(telefone), normalizar(titulo)

    dup = conn.execute("""SELECT u.nome lideranca_nome FROM trabalho t JOIN usuarios u ON u.id=t.lideranca_id
        WHERE (t.titulo_normalizado!='' AND t.titulo_normalizado=?) OR
        (t.telefone_normalizado!='' AND t.telefone_normalizado=?) OR
        (t.nome_normalizado=? AND LOWER(TRIM(t.municipio))=LOWER(TRIM(?))) LIMIT 1""", (titn, tn, nn, municipio)).fetchone()
    if dup:
        conn.close()
        flash(f"Cadastro bloqueado: já consta vinculado à liderança {dup['lideranca_nome']}.")
        return redirect(url_for("lideranca"))
    conn.execute("""INSERT INTO trabalho
        (lideranca_id,nome,municipio,colegio,endereco,telefone,zona,secao,numero_titulo,nome_normalizado,telefone_normalizado,titulo_normalizado,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (session["user_id"], nome, municipio, colegio, endereco, telefone, zona, secao, titulo, nn, tn, titn, datetime.now().isoformat()))
    conn.commit(); conn.close()
    flash("Cadastro de trabalho salvo.")
    return redirect(url_for("lideranca"))



@app.route("/admin")
@login_required
@admin_required
def admin():
    busca = request.args.get("busca","").strip()
    municipio = request.args.get("municipio","").strip()
    lideranca_id = request.args.get("lideranca_id","").strip()
    conn = db()

    liderancas = conn.execute("""SELECT u.*,
        (SELECT COUNT(*) FROM espontaneos e WHERE e.lideranca_id=u.id) total_espontaneos,
        (SELECT COUNT(*) FROM trabalho t WHERE t.lideranca_id=u.id) total_trabalho,
        ((SELECT COUNT(*) FROM espontaneos e WHERE e.lideranca_id=u.id) + (SELECT COUNT(*) FROM trabalho t WHERE t.lideranca_id=u.id)) total_geral
        FROM usuarios u WHERE u.perfil='lideranca'
        ORDER BY u.status DESC, total_geral DESC, u.nome ASC""").fetchall()

    ranking = conn.execute("""SELECT u.id, u.nome, u.municipio, u.status, u.pode_trabalho,
        COUNT(DISTINCT e.id) total_espontaneos,
        COUNT(DISTINCT t.id) total_trabalho,
        (COUNT(DISTINCT e.id) + COUNT(DISTINCT t.id)) total_geral
        FROM usuarios u
        LEFT JOIN espontaneos e ON e.lideranca_id=u.id
        LEFT JOIN trabalho t ON t.lideranca_id=u.id
        WHERE u.perfil='lideranca'
        GROUP BY u.id
        ORDER BY total_geral DESC, total_trabalho DESC, total_espontaneos DESC, u.nome ASC
        LIMIT 20""").fetchall()

    total_liderancas = conn.execute("SELECT COUNT(*) c FROM usuarios WHERE perfil='lideranca'").fetchone()["c"]
    total_pendentes = conn.execute("SELECT COUNT(*) c FROM usuarios WHERE perfil='lideranca' AND status='pendente'").fetchone()["c"]
    total_esp = conn.execute("SELECT COUNT(*) c FROM espontaneos").fetchone()["c"]
    total_trab = conn.execute("SELECT COUNT(*) c FROM trabalho").fetchone()["c"]

    we, pe, wt, pt = [], [], [], []
    if busca:
        we.append("(e.nome_completo LIKE ? OR e.telefone LIKE ? OR u.nome LIKE ?)")
        pe += [f"%{busca}%", f"%{busca}%", f"%{busca}%"]
        wt.append("(t.nome LIKE ? OR t.telefone LIKE ? OR t.colegio LIKE ? OR u.nome LIKE ?)")
        pt += [f"%{busca}%", f"%{busca}%", f"%{busca}%", f"%{busca}%"]
    if municipio:
        we.append("e.municipio LIKE ?"); pe.append(f"%{municipio}%")
        wt.append("t.municipio LIKE ?"); pt.append(f"%{municipio}%")
    if lideranca_id:
        we.append("e.lideranca_id=?"); pe.append(lideranca_id)
        wt.append("t.lideranca_id=?"); pt.append(lideranca_id)

    se = "SELECT e.*, u.nome lideranca_nome FROM espontaneos e JOIN usuarios u ON u.id=e.lideranca_id"
    st = "SELECT t.*, u.nome lideranca_nome FROM trabalho t JOIN usuarios u ON u.id=t.lideranca_id"
    if we: se += " WHERE " + " AND ".join(we)
    if wt: st += " WHERE " + " AND ".join(wt)
    esp = conn.execute(se + " ORDER BY e.id DESC", pe).fetchall()
    trab = conn.execute(st + " ORDER BY t.id DESC", pt).fetchall()
    conn.close()
    return render_template("admin.html", liderancas=liderancas, ranking=ranking, espontaneos=esp, trabalhos=trab,
        total_liderancas=total_liderancas, total_pendentes=total_pendentes, total_esp=total_esp, total_trab=total_trab,
        busca=busca, municipio=municipio, lideranca_id=lideranca_id)


@app.route("/admin/aprovar/<int:user_id>")
@login_required
@admin_required
def aprovar(user_id):
    conn=db(); conn.execute("UPDATE usuarios SET status='ativo' WHERE id=? AND perfil='lideranca'", (user_id,)); conn.commit(); conn.close()
    flash("Liderança aprovada.")
    return redirect(url_for("admin"))

@app.route("/admin/bloquear/<int:user_id>")
@login_required
@admin_required
def bloquear(user_id):
    conn=db(); conn.execute("UPDATE usuarios SET status='bloqueado' WHERE id=? AND perfil='lideranca'", (user_id,)); conn.commit(); conn.close()
    flash("Liderança bloqueada.")
    return redirect(url_for("admin"))


@app.route("/admin/apagar_lideranca/<int:user_id>")
@login_required
@admin_required
def apagar_lideranca(user_id):
    conn = db()
    user = conn.execute("SELECT perfil FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if user and user["perfil"] == "lideranca":
        conn.execute("DELETE FROM espontaneos WHERE lideranca_id=?", (user_id,))
        conn.execute("DELETE FROM trabalho WHERE lideranca_id=?", (user_id,))
        conn.execute("DELETE FROM usuarios WHERE id=? AND perfil='lideranca'", (user_id,))
        conn.commit()
        flash("Liderança apagada com todos os cadastros vinculados.")
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/permissao_trabalho/<int:user_id>/<acao>")
@login_required
@admin_required
def permissao_trabalho(user_id, acao):
    valor = 1 if acao == "liberar" else 0
    conn = db()
    conn.execute("UPDATE usuarios SET pode_trabalho=? WHERE id=? AND perfil='lideranca'", (valor, user_id))
    conn.commit(); conn.close()
    flash("Permissão de trabalho atualizada.")
    return redirect(url_for("admin"))

@app.route("/admin/editar_espontaneo/<int:item_id>", methods=["GET","POST"])
@login_required
@admin_required
def editar_espontaneo(item_id):
    conn = db()
    if request.method == "POST":
        nome = request.form.get("nome_completo","").strip()
        municipio = request.form.get("municipio","").strip()
        telefone = request.form.get("telefone","").strip()
        endereco = request.form.get("endereco_completo","").strip()
        conn.execute("""UPDATE espontaneos SET nome_completo=?, municipio=?, telefone=?, endereco_completo=?,
            nome_normalizado=?, telefone_normalizado=? WHERE id=?""",
            (nome, municipio, telefone, endereco, normalizar(nome), normalizar(telefone), item_id))
        conn.commit(); conn.close()
        flash("Cadastro espontâneo editado.")
        return redirect(url_for("admin"))
    item = conn.execute("SELECT e.*, u.nome lideranca_nome FROM espontaneos e JOIN usuarios u ON u.id=e.lideranca_id WHERE e.id=?", (item_id,)).fetchone()
    conn.close()
    return render_template("editar_espontaneo.html", item=item)

@app.route("/admin/editar_trabalho/<int:item_id>", methods=["GET","POST"])
@login_required
@admin_required
def editar_trabalho(item_id):
    conn = db()
    if request.method == "POST":
        nome = request.form.get("nome","").strip()
        municipio = request.form.get("municipio","").strip()
        colegio = request.form.get("colegio","").strip()
        endereco = request.form.get("endereco","").strip()
        telefone = request.form.get("telefone","").strip()
        zona = request.form.get("zona","").strip()
        secao = request.form.get("secao","").strip()
        titulo = request.form.get("numero_titulo","").strip()
        conn.execute("""UPDATE trabalho SET nome=?, municipio=?, colegio=?, endereco=?, telefone=?, zona=?, secao=?, numero_titulo=?,
            nome_normalizado=?, telefone_normalizado=?, titulo_normalizado=? WHERE id=?""",
            (nome, municipio, colegio, endereco, telefone, zona, secao, titulo, normalizar(nome), normalizar(telefone), normalizar(titulo), item_id))
        conn.commit(); conn.close()
        flash("Cadastro de trabalho editado.")
        return redirect(url_for("admin"))
    item = conn.execute("SELECT t.*, u.nome lideranca_nome FROM trabalho t JOIN usuarios u ON u.id=t.lideranca_id WHERE t.id=?", (item_id,)).fetchone()
    conn.close()
    return render_template("editar_trabalho.html", item=item)


@app.route("/admin/exportar/<tipo>")
@login_required
@admin_required
def exportar(tipo):
    conn=db(); out=io.StringIO(); w=csv.writer(out)
    if tipo == "espontaneos":
        w.writerow(["Lideranca","Nome completo","Municipio","Telefone","Endereco completo","Data"])
        rows=conn.execute("SELECT e.*,u.nome lideranca_nome FROM espontaneos e JOIN usuarios u ON u.id=e.lideranca_id ORDER BY e.id DESC").fetchall()
        for r in rows: w.writerow([r["lideranca_nome"],r["nome_completo"],r["municipio"],r["telefone"],r["endereco_completo"],r["created_at"]])
        filename="espontaneos.csv"
    else:
        w.writerow(["Lideranca","Nome","Municipio","Colegio","Endereco","Telefone","Zona","Secao","Numero titulo","Data"])
        rows=conn.execute("SELECT t.*,u.nome lideranca_nome FROM trabalho t JOIN usuarios u ON u.id=t.lideranca_id ORDER BY t.id DESC").fetchall()
        for r in rows: w.writerow([r["lideranca_nome"],r["nome"],r["municipio"],r["colegio"],r["endereco"],r["telefone"],r["zona"],r["secao"],r["numero_titulo"],r["created_at"]])
        filename="trabalho.csv"
    conn.close()
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition":f"attachment; filename={filename}"})

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
