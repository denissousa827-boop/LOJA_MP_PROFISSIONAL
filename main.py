from flask import Flask, render_template, request, redirect, url_for, session, flash
import database 
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_denis_7788")

# Inicializa o banco ao abrir o site
with app.app_context():
    try:
        database.init_db()
    except Exception as e:
        print(f"Erro ao iniciar banco: {e}")

@app.route("/")
def homepage():
    produtos = database.get_produtos()
    ofertas = database.get_produtos_em_oferta()
    config = database.get_configuracoes()
    return render_template("homepage.html", produtos=produtos, ofertas=ofertas, config=config)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        usuario_valido = database.is_valid_login(user, pw)
        if usuario_valido:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Usuário ou senha inválidos!", "danger")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html", produtos=database.get_produtos(), vendas=database.get_vendas())

@app.route("/setup_admin")
def setup_admin():
    """ROTA DE EMERGÊNCIA: Use para criar/resetar o admin"""
    resultado = database.forçar_criacao_admin("utbdenis6752", "675201")
    return f"<h1>{resultado}</h1><p>Tente logar agora em /admin/login</p>"

app_instance = app
