from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
import datetime
from supabase import create_client
from dotenv import load_dotenv

# ===== CARREGA ENV =====
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "produtos")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== IMPORTS DO PROJETO =====
from apimercadopago import gerar_link_pagamento
import melhorenvio
import database

app = Flask(__name__)
app.secret_key = 'chave_ultra_secreta_denis'

# ===== CONFIG LOCAL (MANTIDO) =====
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

database.init_db()

# ===== FUNÇÕES =====
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_shop_config():
    config = database.get_configuracoes() or {}
    banner_str = config.get('banner_pagamento', '')
    banner = [f.strip() for f in banner_str.split(',') if f.strip()] if banner_str else []
    return config, banner


# ===== 🔥 UPLOAD SUPABASE =====
def upload_imagem_supabase(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    nome_arquivo = f"{uuid.uuid4()}.{ext}"

    caminho = f"produtos/{nome_arquivo}"

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        caminho,
        file.read(),
        {"content-type": file.content_type}
    )

    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(caminho)
    return public_url


# ================= ROTAS PÚBLICAS =================
@app.route("/")
def homepage():
    produtos = database.get_produtos()
    ofertas = database.get_produtos_em_oferta()
    config, banner_pagamento = load_shop_config()
    return render_template("homepage.html", produtos=produtos, ofertas=ofertas,
                           config=config, banner_pagamento=banner_pagamento)


@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))

    imagens = [produto.get(f'img_path_{i}') for i in range(1, 5) if produto.get(f'img_path_{i}')]
    config, banner_pagamento = load_shop_config()

    return render_template("produto_detalhes.html",
                           produto=produto,
                           imagens=imagens,
                           config=config,
                           banner_pagamento=banner_pagamento)


@app.route("/checkout/<id_produto>")
def checkout(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))

    config, _ = load_shop_config()
    return render_template("checkout.html", produto=produto, config=config)


# ================= LOGIN =================
@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if database.is_valid_login(request.form.get('username'),
                                   request.form.get('password')):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Usuário ou senha inválidos.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# ================= PAINEL =================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    vendas = database.get_vendas()
    produtos = database.get_produtos()
    config, _ = load_shop_config()

    return render_template("admin_dashboard.html",
                           vendas=vendas,
                           produtos=produtos,
                           config=config)


# ================= CONFIGURAÇÕES =================
@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        campos = ['titulo_site', 'contato_whatsapp', 'contato_email',
                  'header_color', 'footer_color',
                  'mercado_pago_token', 'melhor_envio_token', 'cep_origem']

        for campo in campos:
            if campo in request.form:
                database.update_configuracao(campo, request.form.get(campo))

        flash("Configurações atualizadas!")
        return redirect(url_for('admin_dashboard'))

    config, _ = load_shop_config()
    return render_template("admin_configuracoes.html", config=config)


# ================= 🔥 PRODUTOS COM SUPABASE =================
@app.route("/admin/edit", methods=['GET', 'POST'])
@app.route("/admin/edit/<id_produto>", methods=['GET', 'POST'])
def admin_edit(id_produto=None):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        try:
            preco = float(request.form.get('preco', '0').replace(',', '.'))
            novo_preco = float(request.form.get('novo_preco', '0').replace(',', '.'))
            frete_gratis = float(request.form.get('frete_gratis_valor', '0').replace(',', '.'))
        except ValueError:
            preco = novo_preco = frete_gratis = 0.0

        dados = {
            'id': id_produto or request.form.get('id'),
            'nome': request.form.get('nome'),
            'descricao': request.form.get('descricao'),
            'preco': preco,
            'novo_preco': novo_preco,
            'em_oferta': 'em_oferta' in request.form,
            'oferta_fim': request.form.get('oferta_fim'),
            'desconto_pix': int(request.form.get('desconto_pix') or 0),
            'estoque': int(request.form.get('estoque') or 0),
            'frete_gratis_valor': frete_gratis,
            'prazo_entrega': request.form.get('prazo_entrega'),
            'tempo_preparo': request.form.get('tempo_preparo')
        }

        # 🔥 IMAGENS
        for i in range(1, 5):
            file = request.files.get(f'imagem_{i}')
            if file and file.filename:
                dados[f'img_path_{i}'] = upload_imagem_supabase(file)

        # 🎥 VÍDEO
        video = request.files.get('video')
        if video and video.filename:
            dados['video_path'] = upload_imagem_supabase(video)

        database.add_or_update_produto(dados)
        flash("Produto salvo com sucesso!")
        return redirect(url_for('admin_dashboard'))

    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)


@app.route("/admin/delete/<id_produto>", methods=['POST'])
def admin_delete(id_produto):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    database.delete_produto(id_produto)
    flash("Produto excluído!")
    return redirect(url_for('admin_dashboard'))


# ================= FRETE =================
@app.route("/calcular_frete", methods=['POST'])
def calcular_frete():
    dados = request.json
    produto = database.get_produto_por_id(dados.get('produto_id'))

    preco = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])

    limite = float(produto.get('frete_gratis_valor') or 0)
    if limite > 0 and preco >= limite:
        return jsonify([{
            "name": "Frete Grátis",
            "price": "0.00",
            "delivery_range": {"min": 5, "max": 15}
        }])

    return jsonify(melhorenvio.calcular_frete(dados.get('cep'), preco))


# ================= PAGAMENTO =================
@app.route("/processar_pagamento", methods=['POST'])
def processar_pagamento():
    produto = database.get_produto_por_id(request.form.get('id_produto'))

    preco = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
    frete = float(request.form.get('frete_valor') or 0)

    if request.form.get('metodo_pagamento') == 'pix':
        desconto = int(produto.get('desconto_pix') or 0)
        preco = preco * (100 - desconto) / 100

    total = preco + frete

    id_venda = database.registrar_venda(
        nome_cliente=request.form.get('nome'),
        email_cliente=request.form.get('email'),
        whatsapp_cliente=request.form.get('whatsapp'),
        produto_nome=produto['nome'],
        quantidade=1,
        valor_total=total
    )

    link = gerar_link_pagamento(produto, id_venda, total)
    return redirect(link)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
