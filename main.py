from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import datetime

# Importação dos seus módulos
from apimercadopago import gerar_link_pagamento
import melhorenvio
import database

app = Flask(__name__)
app.secret_key = 'chave_ultra_secreta_denis'

# Inicializa o banco (Sincroniza tabelas)
database.init_db()

# --- FUNÇÕES AUXILIARES ---
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_shop_config():
    config = database.get_configuracoes() or {}
    banner_str = config.get('banner_pagamento', '')
    banner = [f.strip() for f in banner_str.split(',') if f.strip()] if banner_str else []
    return config, banner

# --- ROTAS PÚBLICAS (LOJA) ---
@app.route("/")
def homepage():
    produtos = database.get_produtos()
    ofertas = database.get_produtos_em_oferta()
    config, banner_pagamento = load_shop_config()
    return render_template("homepage.html", produtos=produtos, ofertas=ofertas, config=config, banner_pagamento=banner_pagamento)

@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))
    config, banner_pagamento = load_shop_config()
    imagens = [produto.get(f'img_path_{i}') for i in range(1, 5) if produto.get(f'img_path_{i}')]
    return render_template("produto_detalhes.html", produto=produto, imagens=imagens, config=config, banner_pagamento=banner_pagamento)

@app.route("/checkout/<id_produto>")
def checkout(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))
    config, _ = load_shop_config()
    return render_template("checkout.html", produto=produto, config=config)

# --- SISTEMA DE LOGIN ---
@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if database.is_valid_login(user, pw):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Usuário ou senha inválidos.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# --- PAINEL E CONFIGURAÇÕES ---
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    vendas = database.get_vendas()
    produtos = database.get_produtos()
    config, _ = load_shop_config()
    return render_template("admin_dashboard.html", vendas=vendas, produtos=produtos, config=config)

@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        campos_texto = ['titulo_site', 'contato_whatsapp', 'contato_email', 'header_color', 'footer_color', 'mercado_pago_token', 'melhor_envio_token', 'cep_origem']
        for campo in campos_texto:
            valor = request.form.get(campo)
            if valor is not None:
                database.save_configuracoes({campo: valor})

        # LOGO: Agora envia para o Supabase Storage
        file = request.files.get('logo_img')
        if file and allowed_file(file.filename):
            public_url = database.upload_imagem_supabase(file)
            if public_url:
                database.save_configuracoes({'logo_img': public_url})

        flash("Configurações atualizadas!")
        return redirect(url_for('admin_dashboard'))

    config, _ = load_shop_config()
    return render_template("admin_configuracoes.html", config=config)

# --- GERENCIAMENTO DE PRODUTOS ---
@app.route("/admin/edit", methods=['GET', 'POST'])
@app.route("/admin/edit/<id_produto>", methods=['GET', 'POST'])
def admin_edit(id_produto=None):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        try:
            preco_raw = request.form.get('preco', '0').replace(',', '.')
            preco = float(preco_raw) if preco_raw else 0.0
            novo_preco_raw = request.form.get('novo_preco', '0').replace(',', '.')
            novo_preco = float(novo_preco_raw) if novo_preco_raw else 0.0
            frete_gratis_raw = request.form.get('frete_gratis_valor', '0').replace(',', '.')
            frete_gratis = float(frete_gratis_raw) if frete_gratis_raw else 0.0
        except ValueError:
            preco, novo_preco, frete_gratis = 0.0, 0.0, 0.0

        dados = {
            'id': id_produto or request.form.get('id'),
            'nome': request.form.get('nome'),
            'preco': preco,
            'descricao': request.form.get('descricao'),
            'em_oferta': 'em_oferta' in request.form,
            'novo_preco': novo_preco,
            'desconto_pix': int(request.form.get('desconto_pix') or 0),
            'estoque': int(request.form.get('estoque') or 0),
            'frete_gratis_valor': frete_gratis,
            'prazo_entrega': request.form.get('prazo_entrega'),
            'tempo_preparo': request.form.get('tempo_preparo')
        }

        # Upload das 4 imagens para o Supabase Storage
        for i in range(1, 5):
            file = request.files.get(f'imagem_{i}')
            if file and allowed_file(file.filename):
                url_nuvem = database.upload_imagem_supabase(file)
                if url_nuvem:
                    dados[f'img_path_{i}'] = url_nuvem

        # Upload de vídeo para o Supabase Storage
        video_file = request.files.get('video')
        if video_file and allowed_file(video_file.filename):
            video_url = database.upload_imagem_supabase(video_file)
            if video_url:
                dados['video_path'] = video_url

        database.add_or_update_produto(dados)
        flash("Produto salvo com sucesso!")
        return redirect(url_for('admin_dashboard'))

    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

# ... (Manter as APIs calcular_frete e processar_pagamento iguais)
@app.route("/calcular_frete", methods=['POST'])
def calcular_frete():
    dados = request.json
    if not dados: return jsonify({"error": "Dados inválidos"}), 400
    cep_dest = dados.get('cep')
    prod_id = dados.get('produto_id')
    produto = database.get_produto_por_id(prod_id)
    if not produto: return jsonify({"error": "Produto não encontrado"}), 404
    preco_base = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
    limite_frete = float(produto.get('frete_gratis_valor') or 0)
    if limite_frete > 0 and preco_base >= limite_frete:
        return jsonify([{"name": "Frete Grátis", "price": "0.00", "delivery_range": {"min": 5, "max": 15}, "custom": True}])
    opcoes = melhorenvio.calcular_frete(cep_dest, preco_base)
    return jsonify(opcoes)

@app.route("/processar_pagamento", methods=['POST'])
def processar_pagamento():
    id_prod = request.form.get('id_produto')
    produto = database.get_produto_por_id(id_prod)
    if not produto: return redirect(url_for('homepage'))
    try:
        frete = float(request.form.get('frete_valor') or 0)
        preco = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
        metodo = request.form.get('metodo_pagamento', 'cartao')
        if metodo == 'pix' and produto.get('desconto_pix'):
            preco = preco * ((100 - int(produto['desconto_pix'])) / 100)
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
        return redirect(link) if link else "Erro ao gerar link de pagamento."
    except Exception as e:
        return f"Erro interno: {e}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
