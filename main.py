# main.py
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os

# Importa as funções de API e dados
from apimercadopago import gerar_link_pagamento
from database import (
    get_produtos, get_produto_por_id, is_valid_login,
    add_or_update_produto, delete_produto, init_db,
    # Funções de Clientes
    add_cliente, get_clientes, get_cliente_por_id, update_cliente, delete_cliente,
    # Funções de Configurações
    get_configuracoes, update_configuracao,
    # NOVO: Função para obter produtos em oferta
    get_produtos_em_oferta
)

# ---------------- CONFIGURAÇÃO INICIAL ----------------
app = Flask(__name__)
# Chave secreta para gerenciar sessões (MUITO IMPORTANTE!)
app.secret_key = 'chave_ultra_secreta_denis'

# Configuração de uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inicializa o DB (Cria tabelas de produtos, usuários, clientes e configuracoes)
init_db()
# --------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- FUNÇÃO HELPER: CARREGA CONFIGURAÇÕES PARA O RODAPÉ ---
def load_shop_config():
    config = get_configuracoes()
    banner_pagamento = []
    if config.get('banner_pagamento'):
        # Converte a string de caminhos em lista e remove espaços
        banner_pagamento = [f.strip() for f in config['banner_pagamento'].split(',') if f.strip()]
    return config, banner_pagamento
# --------------------------------------------------------


# --- ROTAS DA LOJA (VIEW PÚBLICA) ---

@app.route("/")
def homepage():
    produtos = get_produtos()
    ofertas = get_produtos_em_oferta() # <-- NOVO: Carrega produtos em oferta
    config, banner_pagamento = load_shop_config() # <-- Carrega a config

    return render_template(
        "homepage.html",
        produtos=produtos,
        ofertas=ofertas, # <-- NOVO: Passa as ofertas
        config=config, # Passa as configurações para o template
        banner_pagamento=banner_pagamento
    )

# Rota de Página de Informações (Mantida)
@app.route("/pagina_info/<chave_config>")
def pagina_info(chave_config):
    config, banner_pagamento = load_shop_config()

    # Mapeamento da chave para o título (apenas para exibição)
    titulos = {
        'contato_email': 'Email de Suporte',
        'contato_whatsapp': 'WhatsApp da Loja',
        'quem_somos': 'Quem Somos',
        'politica_privacidade': 'Política de Privacidade',
        'politica_reembolso': 'Política de Reembolso',
        'formas_pagamento': 'Formas de Pagamento',
        'entrega_frete': 'Entrega e Frete',
        'trocas_devolucoes': 'Trocas e Devoluções',
        'garantia_seguranca': 'Garantia e Segurança',
        'rastrear_pedido': 'Rastrear seu Pedido',
    }

    titulo = titulos.get(chave_config, 'Informação da Loja')
    conteudo = config.get(chave_config, 'Conteúdo não encontrado para esta chave.')

    return render_template(
        "pagina_info.html",
        titulo=titulo,
        conteudo=conteudo,
        config=config,
        banner_pagamento=banner_pagamento
    )


# Rota de Cadastro de Cliente (Mantida)
@app.route("/cadastro_cliente", methods=['GET', 'POST'])
def cadastro_cliente():
    config, banner_pagamento = load_shop_config()

    if request.method == 'POST':
        nome_completo = request.form['nome_completo']
        whatsapp = request.form['whatsapp']
        email = request.form['email']

        if add_cliente(nome_completo, whatsapp, email):
            return render_template(
                "cadastro_sucesso.html",
                nome=nome_completo,
                config=config,
                banner_pagamento=banner_pagamento
            )
        else:
            return render_template(
                "cadastro_cliente.html",
                error="Este e-mail já está cadastrado. Tente outro.",
                config=config,
                banner_pagamento=banner_pagamento
            )

    return render_template(
        "cadastro_cliente.html",
        config=config,
        banner_pagamento=banner_pagamento
    )


# Rota de Detalhes do Produto (Mantida)
@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = get_produto_por_id(id_produto)
    config, banner_pagamento = load_shop_config()

    if not produto:
        return redirect(url_for('homepage'))

    imagens = [
        produto['img_path_1'],
        produto['img_path_2'],
        produto['img_path_3'],
        produto['img_path_4']
    ]
    video = produto['video_path']

    return render_template(
        "produto_detalhes.html",
        produto=produto,
        imagens=imagens,
        video=video,
        config=config,
        banner_pagamento=banner_pagamento
    )


# Rota dinâmica para gerar e redirecionar para o pagamento (Mantida)
@app.route("/comprar/<id_produto>")
def comprar_produto(id_produto):
    produto = get_produto_por_id(id_produto)

    if not produto:
        return redirect(url_for('compra_errada'))
    
    # Determina o preço a ser cobrado (preço de oferta se estiver em oferta)
    preco_final = produto.get('novo_preco') if produto.get('em_oferta') else produto['preco']

    carrinho_data = {
        id_produto: {
            "nome": produto["nome"],
            "quantidade": 1,
            "preco": str(preco_final)
        }
    }
    total = preco_final

    ip_da_requisicao = request.host

    link_iniciar_pagamento = gerar_link_pagamento(carrinho_data, total, ip_da_requisicao)

    if "compraerrada" in link_iniciar_pagamento:
        return redirect(url_for('compra_errada'))

    return redirect(link_iniciar_pagamento)


@app.route("/compracerta")
def compra_certa():
    config, banner_pagamento = load_shop_config()
    return render_template(
        "compracerta.html",
        config=config,
        banner_pagamento=banner_pagamento
    )


@app.route("/compraerrada")
def compra_errada():
    config, banner_pagamento = load_shop_config()
    return render_template(
        "compraerrada.html",
        config=config,
        banner_pagamento=banner_pagamento
    )

# --- ROTAS DO PAINEL ADMINISTRATIVO ---

@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = is_valid_login(username, password)

        if user:
            session['logged_in'] = True
            session['username'] = user['username']
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template("admin_login.html", error="Usuário ou senha inválidos.")

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    produtos = get_produtos()
    return render_template("admin_dashboard.html", produtos=produtos)

@app.route("/admin/logout")
def admin_logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('homepage'))

# CORRIGIDO: Rota de Adicionar/Editar Produtos (Agora salva dados de oferta)
@app.route("/admin/edit/<id_produto>", methods=['GET', 'POST'])
@app.route("/admin/add", methods=['GET', 'POST'])
def admin_edit(id_produto=None):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    produto = None
    if id_produto:
        produto = get_produto_por_id(id_produto)

    if request.method == 'POST':
        # 1. Coleta os dados do formulário
        id = request.form.get('id', id_produto)
        nome = request.form['nome']
        preco = float(request.form['preco'])
        descricao = request.form['descricao']
        
        # NOVOS DADOS DE OFERTA:
        em_oferta = request.form.get('em_oferta') == 'on' # Checkbox
        novo_preco_str = request.form.get('novo_preco')
        novo_preco = float(novo_preco_str) if novo_preco_str else None
        oferta_fim = request.form.get('oferta_fim')

        img_paths = []
        video_path = None

        # 2. Processa os uploads de arquivos (Mantido)
        for i in range(1, 5): # 4 Imagens
            file_key = f'imagem_{i}'
            if file_key in request.files:
                file = request.files[file_key]
                if file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    db_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(db_path)
                    img_paths.append(db_path)
                elif produto and produto[f'img_path_{i}']:
                    img_paths.append(produto[f'img_path_{i}'])
                else:
                    img_paths.append(None)
            elif produto and produto[f'img_path_{i}']:
                 img_paths.append(produto[f'img_path_{i}'])
            else:
                 img_paths.append(None)

        # Processa o upload do vídeo (Mantido)
        if 'video' in request.files:
            file = request.files['video']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                db_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(db_path)
                video_path = db_path
            elif produto and produto['video_path']:
                 video_path = produto['video_path']
        elif produto and produto['video_path']:
             video_path = produto['video_path']

        # 3. Salva no Banco de Dados (Passando os novos parâmetros)
        add_or_update_produto(
            id, nome, preco, descricao, img_paths, video_path, 
            em_oferta, novo_preco, oferta_fim
        )
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_editar.html", produto=produto)


@app.route("/admin/delete/<id_produto>", methods=['POST'])
def admin_delete(id_produto):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    delete_produto(id_produto)
    return redirect(url_for('admin_dashboard'))


# ROTAS DE GESTÃO DE CLIENTES (Mantidas)
@app.route("/admin/clientes")
def admin_clientes():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    clientes = get_clientes()
    return render_template("admin_clientes.html", clientes=clientes)

@app.route("/admin/clientes/edit/<int:id_cliente>", methods=['GET', 'POST'])
def admin_editar_cliente(id_cliente):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    cliente = get_cliente_por_id(id_cliente)
    if not cliente:
        return redirect(url_for('admin_clientes'))

    if request.method == 'POST':
        nome_completo = request.form['nome_completo']
        whatsapp = request.form['whatsapp']
        email = request.form['email']

        update_cliente(id_cliente, nome_completo, whatsapp, email)
        return redirect(url_for('admin_clientes'))

    return render_template("admin_editar_cliente.html", cliente=cliente)

@app.route("/admin/clientes/delete/<int:id_cliente>", methods=['POST'])
def admin_delete_cliente(id_cliente):
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    delete_cliente(id_cliente)
    return redirect(url_for('admin_clientes'))


# ROTA: Configurações da Loja (Corrigida: Adiciona cores e banner_img)
@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    config = get_configuracoes()

    if request.method == 'POST':
        # Lista de todas as chaves de configuração a serem atualizadas
        keys_to_update = [
            'contato_email', 'contato_whatsapp', 'quem_somos',
            'politica_privacidade', 'politica_reembolso',
            'formas_pagamento', 'entrega_frete', 'trocas_devolucoes',
            'garantia_seguranca', 'rastrear_pedido', 'banner_pagamento',
            # NOVAS CHAVES:
            'header_color', 'footer_color', 'banner_img'
        ]

        for key in keys_to_update:
            valor = request.form.get(key, '')
            update_configuracao(key, valor)

        config = get_configuracoes() # Recarrega as configs atualizadas
        return render_template("admin_configuracoes.html", config=config, success="Configurações salvas com sucesso!")

    return render_template("admin_configuracoes.html", config=config)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
