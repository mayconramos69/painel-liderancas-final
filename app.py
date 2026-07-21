import os
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, abort
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "troque-esta-chave")
database_url = os.getenv("DATABASE_URL", "")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "home"


def normalize_username(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]", "", (value or "").lower().strip())


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="leader")
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class DayWork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    owner = db.relationship("User", backref="day_work_records")
    name = db.Column(db.String(160), nullable=False)
    voter_title = db.Column(db.String(80), nullable=False)
    school = db.Column(db.String(180), nullable=False)
    zone = db.Column(db.String(40), nullable=False)
    section = db.Column(db.String(40), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    notes = db.Column(db.Text)
    photo = db.Column(db.LargeBinary)
    photo_type = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class LeaderRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    owner = db.relationship("User", backref="leader_records")
    name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    district = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(220), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    entity = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def create_admin():
    username = normalize_username(os.getenv("ADMIN_USERNAME", "mayconramos2026"))
    user = User.query.filter_by(username=username).first()
    password = os.getenv("ADMIN_PASSWORD", "265110")
    if not user:
        user = User(
            name=os.getenv("ADMIN_NAME", "Maycon Ramos"),
            username=username,
            phone=normalize_phone(os.getenv("ADMIN_PHONE", "22999999999")),
            city=os.getenv("ADMIN_CITY", "Saquarema"),
            password_hash=generate_password_hash(password),
            role="admin",
            status="approved",
        )
        db.session.add(user)
    else:
        user.role = "admin"
        user.status = "approved"
        user.password_hash = generate_password_hash(password)
    db.session.commit()


def audit(entity, record_id, action, details=""):
    db.session.add(AuditLog(
        admin_id=current_user.id if current_user.is_authenticated else None,
        entity=entity,
        record_id=str(record_id),
        action=action,
        details=details,
    ))
    db.session.commit()


with app.app_context():
    db.create_all()
    create_admin()


@app.route("/", methods=["GET", "POST"])
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    mode = request.args.get("mode", "login")
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            username = normalize_username(request.form.get("username"))
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if not user or not check_password_hash(user.password_hash, password):
                flash("Usuário ou senha incorretos.", "error")
            elif user.status == "pending":
                flash("Seu acesso ainda está aguardando aprovação.", "info")
            elif user.status == "blocked":
                flash("Este acesso está bloqueado.", "error")
            else:
                login_user(user, remember=True)
                return redirect(url_for("dashboard"))
            mode = "login"

        elif action == "register":
            name = request.form.get("name", "").strip()
            username = normalize_username(request.form.get("username"))
            phone = normalize_phone(request.form.get("phone"))
            city = request.form.get("city", "").strip()
            password = request.form.get("password", "")

            if not name or len(username) < 4 or len(phone) < 10 or not city or len(password) < 6:
                flash("Revise os dados. Usuário mínimo 4 caracteres e senha mínimo 6.", "error")
            elif User.query.filter(or_(User.username == username, User.phone == phone)).first():
                flash("Usuário ou telefone já cadastrado.", "error")
            else:
                db.session.add(User(
                    name=name,
                    username=username,
                    phone=phone,
                    city=city,
                    password_hash=generate_password_hash(password),
                    role="leader",
                    status="pending",
                ))
                db.session.commit()
                flash("Cadastro enviado. Aguarde a aprovação do administrador.", "success")
                return redirect(url_for("home", mode="login"))
            mode = "register"

    return render_template("home.html", mode=mode)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.status != "approved":
        logout_user()
        return redirect(url_for("home"))

    if current_user.role == "admin":
        day_work = DayWork.query.order_by(DayWork.created_at.desc()).all()
        leaders = LeaderRecord.query.order_by(LeaderRecord.created_at.desc()).all()
        users = User.query.filter_by(role="leader").order_by(User.created_at.desc()).all()
    else:
        day_work = DayWork.query.filter_by(owner_id=current_user.id).order_by(DayWork.created_at.desc()).all()
        leaders = LeaderRecord.query.filter_by(owner_id=current_user.id).order_by(LeaderRecord.created_at.desc()).all()
        users = []

    total = sum((x.amount or Decimal("0")) for x in day_work + leaders)
    return render_template(
        "dashboard.html",
        day_work=day_work,
        leaders=leaders,
        users=users,
        total=total,
        current_date=date.today().isoformat(),
    )


def _parse_report_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _money(value):
    amount = Decimal(value or 0)
    formatted = f"{amount:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _pdf_response(title, subtitle, headers, rows, total_value, filename, column_widths):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="Sistema Área de Estudos",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111111"),
        spaceAfter=5,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=7,
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontName="Helvetica", fontSize=6.7, leading=8, alignment=TA_LEFT
    )
    head_style = ParagraphStyle(
        "Head", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white
    )
    story = [
        Paragraph("ÁREA DE ESTUDOS", title_style),
        Paragraph(title, title_style),
        Paragraph(subtitle, subtitle_style),
        Spacer(1, 3 * mm),
    ]
    table_data = [[Paragraph(str(h), head_style) for h in headers]]
    for row in rows:
        table_data.append([Paragraph(str(value or "-"), cell_style) for value in row])
    if not rows:
        table_data.append([Paragraph("Nenhum cadastro encontrado para os filtros escolhidos.", cell_style)] + [""] * (len(headers) - 1))

    table = Table(table_data, colWidths=column_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#191919")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aaaaaa")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f3f3")]),
        ("SPAN", (0, 1 if not rows else -1), (-1, 1 if not rows else -1)) if not rows else ("LINEBELOW", (0, -1), (-1, -1), 0, colors.white),
    ]))
    story.append(table)
    story.append(Spacer(1, 5 * mm))
    summary = f"Total de registros: {len(rows)} &nbsp;&nbsp;&nbsp; Valor total: <b>{_money(total_value)}</b>"
    story.append(Paragraph(summary, ParagraphStyle("Summary", parent=styles["Normal"], fontSize=9, leading=12)))
    generated = datetime.now().strftime("%d/%m/%Y às %H:%M")
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Relatório gerado em {generated} pelo Sistema Área de Estudos.", subtitle_style))
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


def _report_filters(query, model):
    selected_date = _parse_report_date(request.args.get("date", ""))
    owner_id = request.args.get("owner_id", type=int)
    city = request.args.get("city", "").strip()
    if selected_date:
        query = query.filter(func.date(model.created_at) == selected_date)
    if owner_id:
        query = query.filter(model.owner_id == owner_id)
    if city:
        query = query.filter(model.city.ilike(f"%{city}%"))
    return query, selected_date, owner_id, city


def _report_subtitle(selected_date, owner_id, city):
    parts = []
    parts.append(f"Data: {selected_date.strftime('%d/%m/%Y')}" if selected_date else "Data: todos os dias")
    if owner_id:
        owner = db.session.get(User, owner_id)
        parts.append(f"Responsável: {owner.name if owner else 'Não encontrado'}")
    else:
        parts.append("Responsável: todos")
    parts.append(f"Cidade: {city}" if city else "Cidade: todas")
    return " | ".join(parts)


@app.get("/admin/reports/day-work.pdf")
@admin_required
def report_day_work_pdf():
    query, selected_date, owner_id, city = _report_filters(
        DayWork.query.order_by(DayWork.created_at.asc()), DayWork
    )
    records = query.all()
    rows = []
    for x in records:
        rows.append([
            x.created_at.strftime("%d/%m/%Y %H:%M") if x.created_at else "-",
            x.name,
            x.voter_title,
            x.school,
            f"{x.zone}/{x.section}",
            x.city,
            x.owner.name,
            _money(x.amount),
            x.notes or "-",
        ])
    total_value = sum((x.amount or Decimal("0")) for x in records)
    date_tag = selected_date.isoformat() if selected_date else "todos"
    return _pdf_response(
        "Relatório de Trabalho do Dia",
        _report_subtitle(selected_date, owner_id, city),
        ["Cadastro", "Nome", "Título", "Colégio", "Zona/Seção", "Cidade", "Responsável", "Valor", "Observações"],
        rows,
        total_value,
        f"trabalho-do-dia-{date_tag}.pdf",
        [22*mm, 32*mm, 25*mm, 35*mm, 20*mm, 25*mm, 30*mm, 20*mm, 55*mm],
    )


@app.get("/admin/reports/leaders.pdf")
@admin_required
def report_leaders_pdf():
    query, selected_date, owner_id, city = _report_filters(
        LeaderRecord.query.order_by(LeaderRecord.created_at.asc()), LeaderRecord
    )
    records = query.all()
    rows = []
    for x in records:
        rows.append([
            x.created_at.strftime("%d/%m/%Y %H:%M") if x.created_at else "-",
            x.name,
            x.phone,
            x.city,
            x.district,
            x.address,
            x.owner.name,
            _money(x.amount),
            x.notes or "-",
        ])
    total_value = sum((x.amount or Decimal("0")) for x in records)
    date_tag = selected_date.isoformat() if selected_date else "todos"
    return _pdf_response(
        "Relatório de Líderes",
        _report_subtitle(selected_date, owner_id, city),
        ["Cadastro", "Nome", "Telefone", "Cidade", "Bairro", "Endereço", "Responsável", "Valor", "Observações"],
        rows,
        total_value,
        f"lideres-{date_tag}.pdf",
        [22*mm, 30*mm, 24*mm, 23*mm, 24*mm, 42*mm, 29*mm, 20*mm, 50*mm],
    )


@app.post("/day-work/create")
@login_required
def create_day_work():
    if current_user.role != "leader":
        abort(403)
    try:
        amount = Decimal(request.form.get("amount", "0"))
    except InvalidOperation:
        amount = Decimal("0")
    photo_file = request.files.get("photo")
    photo = None
    photo_type = None
    if photo_file and photo_file.filename:
        if not (photo_file.mimetype or "").startswith("image/"):
            flash("O arquivo precisa ser uma imagem.", "error")
            return redirect(url_for("dashboard") + "#trabalho")
        photo = photo_file.read()
        photo_type = photo_file.mimetype

    record = DayWork(
        owner_id=current_user.id,
        name=request.form.get("name", "").strip(),
        voter_title=request.form.get("voter_title", "").strip(),
        school=request.form.get("school", "").strip(),
        zone=request.form.get("zone", "").strip(),
        section=request.form.get("section", "").strip(),
        city=request.form.get("city", "").strip(),
        amount=amount,
        notes=request.form.get("notes", "").strip() or None,
        photo=photo,
        photo_type=photo_type,
    )
    db.session.add(record)
    db.session.commit()
    flash("Cadastro salvo. Somente o administrador poderá alterar.", "success")
    return redirect(url_for("dashboard") + "#cadastros")


@app.post("/leaders/create")
@login_required
def create_leader_record():
    if current_user.role != "leader":
        abort(403)
    try:
        amount = Decimal(request.form.get("amount", "0"))
    except InvalidOperation:
        amount = Decimal("0")
    record = LeaderRecord(
        owner_id=current_user.id,
        name=request.form.get("name", "").strip(),
        phone=normalize_phone(request.form.get("phone")),
        city=request.form.get("city", "").strip(),
        district=request.form.get("district", "").strip(),
        address=request.form.get("address", "").strip(),
        amount=amount,
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(record)
    db.session.commit()
    flash("Líder salvo. Somente o administrador poderá alterar.", "success")
    return redirect(url_for("dashboard") + "#cadastros")


@app.route("/photo/<int:record_id>")
@login_required
def photo(record_id):
    record = db.session.get(DayWork, record_id)
    if not record or not record.photo:
        abort(404)
    if current_user.role != "admin" and record.owner_id != current_user.id:
        abort(403)
    return send_file(BytesIO(record.photo), mimetype=record.photo_type or "image/jpeg")


@app.post("/admin/access/<int:user_id>/update")
@admin_required
def update_access(user_id):
    user = db.session.get(User, user_id) or abort(404)
    username = normalize_username(request.form.get("username"))
    conflict = User.query.filter(User.id != user.id, or_(User.username == username, User.phone == normalize_phone(request.form.get("phone")))).first()
    if conflict:
        flash("Usuário ou telefone já está em uso.", "error")
        return redirect(url_for("dashboard") + "#acessos")
    user.name = request.form.get("name", "").strip()
    user.username = username
    user.phone = normalize_phone(request.form.get("phone"))
    user.city = request.form.get("city", "").strip()
    user.status = request.form.get("status", "pending")
    password = request.form.get("password", "")
    if password:
        user.password_hash = generate_password_hash(password)
    db.session.commit()
    audit("User", user.id, "updated")
    flash("Acesso atualizado.", "success")
    return redirect(url_for("dashboard") + "#acessos")


@app.post("/admin/access/<int:user_id>/delete")
@admin_required
def delete_access(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.day_work_records or user.leader_records:
        user.status = "blocked"
        db.session.commit()
        flash("O acesso foi bloqueado porque possui cadastros vinculados.", "info")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("Acesso excluído.", "success")
    audit("User", user_id, "deleted_or_blocked")
    return redirect(url_for("dashboard") + "#acessos")


@app.post("/admin/day-work/<int:record_id>/update")
@admin_required
def update_day_work(record_id):
    record = db.session.get(DayWork, record_id) or abort(404)
    record.name = request.form.get("name", "").strip()
    record.voter_title = request.form.get("voter_title", "").strip()
    record.school = request.form.get("school", "").strip()
    record.zone = request.form.get("zone", "").strip()
    record.section = request.form.get("section", "").strip()
    record.city = request.form.get("city", "").strip()
    record.amount = Decimal(request.form.get("amount", "0"))
    record.notes = request.form.get("notes", "").strip() or None
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        record.photo = photo_file.read()
        record.photo_type = photo_file.mimetype
    db.session.commit()
    audit("DayWork", record.id, "updated")
    flash("Cadastro atualizado.", "success")
    return redirect(url_for("dashboard") + "#cadastros")


@app.post("/admin/day-work/<int:record_id>/delete")
@admin_required
def delete_day_work(record_id):
    record = db.session.get(DayWork, record_id) or abort(404)
    db.session.delete(record)
    db.session.commit()
    audit("DayWork", record_id, "deleted")
    flash("Cadastro excluído.", "success")
    return redirect(url_for("dashboard") + "#cadastros")


@app.post("/admin/leader/<int:record_id>/update")
@admin_required
def update_leader(record_id):
    record = db.session.get(LeaderRecord, record_id) or abort(404)
    record.name = request.form.get("name", "").strip()
    record.phone = normalize_phone(request.form.get("phone"))
    record.city = request.form.get("city", "").strip()
    record.district = request.form.get("district", "").strip()
    record.address = request.form.get("address", "").strip()
    record.amount = Decimal(request.form.get("amount", "0"))
    record.notes = request.form.get("notes", "").strip() or None
    db.session.commit()
    audit("LeaderRecord", record.id, "updated")
    flash("Líder atualizado.", "success")
    return redirect(url_for("dashboard") + "#lideres-lista")


@app.post("/admin/leader/<int:record_id>/delete")
@admin_required
def delete_leader(record_id):
    record = db.session.get(LeaderRecord, record_id) or abort(404)
    db.session.delete(record)
    db.session.commit()
    audit("LeaderRecord", record_id, "deleted")
    flash("Líder excluído.", "success")
    return redirect(url_for("dashboard") + "#lideres-lista")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
