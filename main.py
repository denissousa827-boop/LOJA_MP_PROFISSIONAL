from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import datetime
import uuid

# MÓDULOS DO SEU PROJETO (mantidos)
from apimercadopago import gerar_link_pagamento
import melhorenvio
import database

app = Flask(__name__)
app.secret_key = 'chave_ultra_secreta_denis'

# ==============================
# CONFIGURAÇÕES GERAIS
# ==============================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}
database.init_db()

# ==============================
# FUNÇÕES AUXILIARES
# ==============================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_shop_config():
    config = database.get_configuracoes() or {}
    banner_str = config.get('banner_pagamento', '')
    banner = [b.strip() for b in banner_str.split(',') if b.strip()] if banner_str else []
    return config, banner


def fake_upload_cloud(file):
    """
    ⚠️ SIMULA upload em nuvem (Vercel-safe)
    Você pode trocar futuramente por S3, Cloudinary etc.
    """
    ext = secure_filename(file.filename).rsplit('.', 1)[1]
    unique_name = f"{uuid.uuid4()}.{ext}"
    return f"https://cdn.fakeuploads.com/{unique_name}"

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


@app.route("/checkout/<id_produto>")
def checkout(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))

    config, _ = load_shop_config()
    return render_template("checkout.html", produto=produto, config=config)

# ==============================
# LOGIN ADMIN
# ==============================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        if database.is_valid_login(user, pw):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Usuário ou senha inválidos")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# ==============================
# DASHBOARD
# ==============================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    vendas = database.get_vendas()
    produtos = database.get_produtos()
    config, _ = load_shop_config()
    return render_template("admin_dashboard.html", vendas=vendas, produtos=produtos, config=config)

# ==============================
# CONFIGURAÇÕES
# ==============================
@app.route("/admin/configuracoes", methods=["GET", "POST"])
def admin_configuracoes():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        campos = [
            "titulo_site", "contato_whatsapp", "contato_email",
            "header_color", "footer_color",
            "mercado_pago_token", "melhor_envio_token", "cep_origem"
        ]

        for campo in campos:
            valor = request.form.get(campo)
            if valor is not None:
                database.update_configuracao(campo, valor)

        flash("Configurações atualizadas")
        return redirect(url_for("admin_dashboard"))

    config, _ = load_shop_config()
    return render_template("admin_configuracoes.html", config=config)

# ==============================
# CRUD PRODUTOS (SEM FILESYSTEM)
# ==============================
@app.route("/admin/edit", methods=["GET", "POST"])
@app.route("/admin/edit/<id_produto>", methods=["GET", "POST"])
def admin_edit(id_produto=None):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        try:
            preco = float(request.form.get("preco", "0").replace(",", "."))
            novo_preco = float(request.form.get("novo_preco", "0").replace(",", "."))
            frete_gratis = float(request.form.get("frete_gratis_valor", "0").replace(",", "."))
        except ValueError:
            preco = novo_preco = frete_gratis = 0.0

        dados = {
            "id": id_produto or request.form.get("id"),
            "nome": request.form.get("nome"),
            "descricao": request.form.get("descricao"),
            "preco": preco,
            "novo_preco": novo_preco,
            "em_oferta": "em_oferta" in request.form,
            "oferta_fim": request.form.get("oferta_fim"),
            "estoque": int(request.form.get("estoque") or 0),
            "desconto_pix": int(request.form.get("desconto_pix") or 0),
            "frete_gratis_valor": frete_gratis,
            "prazo_entrega": request.form.get("prazo_entrega"),
            "tempo_preparo": request.form.get("tempo_preparo"),
        }

        # IMAGENS
        for i in range(1, 5):
            file = request.files.get(f"imagem_{i}")
            if file and allowed_file(file.filename):
                dados[f"img_path_{i}"] = fake_upload_cloud(file)

        # VÍDEO
        video = request.files.get("video")
        if video and allowed_file(video.filename):
            dados["video_path"] = fake_upload_cloud(video)

        database.add_or_update_produto(dados)
        flash("Produto salvo com sucesso")
        return redirect(url_for("admin_dashboard"))

    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

# ==============================
# DELETE
# ==============================
@app.route("/admin/delete/<id_produto>", methods=["POST"])
def admin_delete(id_produto):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    database.delete_produto(id_produto)
    flash("Produto excluído")
    return redirect(url_for("admin_dashboard"))

# ==============================
# APIs
# ==============================
@app.route("/calcular_frete", methods=["POST"])
def calcular_frete():
    dados = request.json
    produto = database.get_produto_por_id(dados.get("produto_id"))
    if not produto:
        return jsonify({"error": "Produto não encontrado"}), 404

    preco = float(produto["novo_preco"] if produto.get("em_oferta") else produto["preco"])
    limite = float(produto.get("frete_gratis_valor") or 0)

    if limite and preco >= limite:
        return jsonify([{
            "name": "Frete Grátis",
            "price": "0.00",
            "delivery_range": {"min": 5, "max": 15}
        }])

    return jsonify(melhorenvio.calcular_frete(dados.get("cep"), preco))


@app.route("/processar_pagamento", methods=["POST"])
def processar_pagamento():
    id_prod = request.form.get("id_produto")
    produto = database.get_produto_por_id(id_prod)
    if not produto:
        return redirect(url_for("homepage"))

    preco = float(produto["novo_preco"] if produto.get("em_oferta") else produto["preco"])
    frete = float(request.form.get("frete_valor") or 0)

    if request.form.get("metodo_pagamento") == "pix":
        desconto = int(produto.get("desconto_pix") or 0)
        preco *= (100 - desconto) / 100

    total = preco + frete

    venda_id = database.registrar_venda(
        nome_cliente=request.form.get("nome"),
        email_cliente=request.form.get("email"),
        whatsapp_cliente=request.form.get("whatsapp"),
        produto_nome=produto["nome"],
        quantidade=1,
        valor_total=total
    )

    link = gerar_link_pagamento(produto, venda_id, total)
    return redirect(link) if link else redirect(url_for("produto_detalhes", id_produto=id_prod))


# ==============================
# ENTRYPOINT VERCEL
# ==============================
app_instance = app
