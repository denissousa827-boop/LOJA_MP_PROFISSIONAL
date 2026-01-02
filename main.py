from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os

# Importação dos seus módulos (certifique-se que os arquivos existem no GitHub)
from apimercadopago import gerar_link_pagamento
import melhorenvio
import database

app = Flask(__name__)
app.secret_key = 'chave_ultra_secreta_denis'

# Inicializa o banco de dados e as tabelas no Supabase
database.init_db()

# --- FUNÇÕES AUXILIARES ---
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_shop_config():
    """Carrega as configurações da loja do banco de dados."""
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
    # Coleta imagens existentes (1 a 4)
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
        # Salva textos
        configs_para_salvar = {}
        campos = ['titulo_site', 'contato_whatsapp', 'contato_email', 'header_color', 'footer_color', 'mercado_pago_token', 'melhor_envio_token', 'cep_origem']
        for campo in campos:
            configs_para_salvar[campo] = request.form.get(campo)

        # Upload da Logo para Supabase
        logo_file = request.files.get('logo_img')
        if logo_file and allowed_file(logo_file.filename):
            url_logo = database.upload_imagem_supabase(logo_file)
            if url_logo:
                configs_para_salvar['logo_img'] = url_logo

        # Aqui você precisará criar uma função save_config no seu database.py que itere o dict
        for k, v in configs_para_salvar.items():
            # Simulando a gravação individual para manter compatibilidade com seu database.py
            conn = database.create_connection()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO configuracoes (chave, valor) VALUES (%s, %s) ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor", (k, v))
            conn.close()

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
        dados = {
            'id': id_produto or request.form.get('id'),
            'nome': request.form.get('nome'),
            'preco': request.form.get('preco'),
            'descricao': request.form.get('descricao'),
            'em_oferta': 'em_oferta' in request.form,
            'novo_preco': request.form.get('novo_preco'),
            'oferta_fim': request.form.get('oferta_fim'),
            'desconto_pix': request.form.get('desconto_pix'),
            'estoque': request.form.get('estoque'),
            'frete_gratis_valor': request.form.get('frete_gratis_valor'),
            'prazo_entrega': request.form.get('prazo_entrega'),
            'tempo_preparo': request.form.get('tempo_preparo')
        }

        # Upload das 4 imagens para o Supabase
        for i in range(1, 5):
            file = request.files.get(f'imagem_{i}')
            if file and allowed_file(file.filename):
                url_publica = database.upload_imagem_supabase(file)
                if url_publica:
                    dados[f'img_path_{i}'] = url_publica

        # Upload de vídeo para o Supabase
        video_file = request.files.get('video')
        if video_file and allowed_file(video_file.filename):
            url_video = database.upload_imagem_supabase(video_file)
            if url_video:
                dados['video_path'] = url_video

        database.add_or_update_produto(dados)
        flash("Produto salvo com sucesso!")
        return redirect(url_for('admin_dashboard'))

    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

# --- APIs E PROCESSAMENTO ---
@app.route("/calcular_frete", methods=['POST'])
def calcular_frete():
    dados = request.json
    cep_dest = dados.get('cep')
    prod_id = dados.get('produto_id')
    produto = database.get_produto_por_id(prod_id)
    preco_base = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
    opcoes = melhorenvio.calcular_frete(cep_dest, preco_base)
    return jsonify(opcoes)

@app.route("/processar_pagamento", methods=['POST'])
def processar_pagamento():
    id_prod = request.form.get('id_produto')
    produto = database.get_produto_por_id(id_prod)
    frete = float(request.form.get('frete_valor') or 0)
    preco = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
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
    return redirect(link) if link else "Erro no link de pagamento"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
