from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import datetime
import uuid

# MÓDULOS DO SEU PROJETO
from apimercadopago import gerar_link_pagamento
import melhorenvio
import database 

app = Flask(__name__)
app.secret_key = 'chave_ultra_secreta_denis'

# ==============================
# CONFIGURAÇÕES GERAIS
# ==============================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}

# Inicializa o banco de dados e cria tabelas na primeira execução
with app.app_context():
    database.init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_shop_config():
    config = database.get_configuracoes() or {}
    banner_str = config.get('banner_pagamento', '')
    banner = [b.strip() for b in banner_str.split(',') if b.strip()] if banner_str else []
    return config, banner

# ==============================
# ROTAS PÚBLICAS
# ==============================
@app.route("/")
def homepage():
    produtos = database.get_produtos()
    ofertas = database.get_produtos_em_oferta()
    config, banner = load_shop_config()
    return render_template("homepage.html", produtos=produtos, ofertas=ofertas, config=config, banner_pagamento=banner)

@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))
    
    imagens = [produto.get(f'img_path_{i}') for i in range(1, 5) if produto.get(f'img_path_{i}')]
    config, banner = load_shop_config()
    return render_template("produto_detalhes.html", produto=produto, imagens=imagens, config=config, banner_pagamento=banner)

# ==============================
# ADMINISTRAÇÃO
# ==============================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        if database.is_valid_login(user, pw):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Usuário ou senha inválidos", "danger")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    vendas = database.get_vendas()
    produtos = database.get_produtos()
    config, _ = load_shop_config()
    return render_template("admin_dashboard.html", vendas=vendas, produtos=produtos, config=config)

@app.route("/admin/configuracoes", methods=["POST"])
def admin_configuracoes():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    campos = ["titulo_site", "contato_whatsapp", "contato_email", "header_color", "footer_color", "mercado_pago_token", "melhor_envio_token", "cep_origem"]
    configs_para_salvar = {c: request.form.get(c) for c in campos if request.form.get(c) is not None}
    database.save_configuracoes(configs_para_salvar)
    flash("Configurações atualizadas!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit", methods=["GET", "POST"])
@app.route("/admin/edit/<id_produto>", methods=["GET", "POST"])
def admin_edit(id_produto=None):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        try:
            def parse_float(val): return float(str(val).replace(",", ".")) if val else 0.0
            dados = {
                "id": id_produto or request.form.get("id") or str(int(datetime.datetime.now().timestamp())),
                "nome": request.form.get("nome"),
                "descricao": request.form.get("descricao"),
                "preco": parse_float(request.form.get("preco")),
                "novo_preco": parse_float(request.form.get("novo_preco")),
                "em_oferta": "em_oferta" in request.form,
                "estoque": int(request.form.get("estoque") or 0),
                "desconto_pix": int(request.form.get("desconto_pix") or 0),
                "frete_gratis_valor": parse_float(request.form.get("frete_gratis_valor")),
                "prazo_entrega": request.form.get("prazo_entrega"),
                "tempo_preparo": request.form.get("tempo_preparo"),
            }
            for i in range(1, 5):
                f = request.files.get(f"imagem_{i}")
                if f and f.filename != '' and allowed_file(f.filename):
                    url = database.upload_imagem_supabase(f)
                    if url: dados[f"img_path_{i}"] = url
            database.add_or_update_produto(dados)
            flash("Produto salvo!", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            flash(f"Erro: {e}", "danger")
    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

# ==============================
# PAGAMENTO E SETUP
# ==============================
@app.route("/processar_pagamento", methods=["POST"])
def processar_pagamento():
    id_prod = request.form.get("id_produto")
    produto = database.get_produto_por_id(id_prod)
    if not produto: return redirect(url_for("homepage"))
    preco = float(produto["novo_preco"] if produto.get("em_oferta") else produto["preco"])
    frete = float(request.form.get("frete_valor") or 0)
    total = preco + frete
    venda_id = database.registrar_venda(request.form.get("nome"), request.form.get("email"), request.form.get("whatsapp"), produto["nome"], 1, total)
    link = gerar_link_pagamento(produto, venda_id, total)
    return redirect(link) if link else redirect(url_for("produto_detalhes", id_produto=id_prod))

@app.route("/setup_admin")
def setup_admin():
    database.init_db()
    return "Comando de criação de tabelas e admin executado! Tente logar no painel agora."

app_instance = app
