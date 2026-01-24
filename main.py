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

# --- CONFIGURAÇÃO DE AMBIENTE ---
IS_VERCEL = "VERCEL" in os.environ
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp'
    UPLOAD_FOLDER_CAT = '/tmp'
else:
    UPLOAD_FOLDER = 'static/uploads'
    UPLOAD_FOLDER_CAT = 'static/uploads/categorias'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}

# Criação das pastas de upload se não estiver no Vercel
if not IS_VERCEL:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER_CAT, exist_ok=True)

with app.app_context():
    database.init_db()

# --- FUNÇÕES AUXILIARES ---
def allowed_file(filename):
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

@app.route("/pesquisar")
def pesquisar():
    query = request.args.get('q', '')
    config, banner_pagamento = load_shop_config()
    todos_produtos = database.get_produtos()

    produtos_encontrados = []
    if query:
        query = query.lower()
        for p in todos_produtos:
            nome = p.get('nome', '').lower()
            descricao = p.get('descricao', '').lower()
            if query in nome or query in descricao:
                produtos_encontrados.append(p)

    return render_template("pesquisa.html", produtos=produtos_encontrados, query=query, config=config, banner_pagamento=banner_pagamento)

@app.route("/categoria/<nome_categoria>")
def categoria(nome_categoria):
    config, banner_pagamento = load_shop_config()
    todos_produtos = database.get_produtos()

    produtos_categoria = []
    cat_search = nome_categoria.lower()

    for p in todos_produtos:
        categoria_prod = str(p.get('categoria', '')).lower()
        descricao_prod = str(p.get('descricao', '')).lower()

        if cat_search == categoria_prod or cat_search in descricao_prod:
            produtos_categoria.append(p)

    return render_template("pesquisa.html", produtos=produtos_categoria, query=nome_categoria, config=config, banner_pagamento=banner_pagamento)

@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))
    config, banner_pagamento = load_shop_config()
    # MANTIDO: Lógica original das 4 imagens/vídeos
    imagens = [produto.get(f'img_path_{i}') for i in range(1, 5) if produto.get(f'img_path_{i}')]
    return render_template("produto_detalhes.html", produto=produto, imagens=imagens, config=config, banner_pagamento=banner_pagamento)

@app.route("/checkout/<id_produto>")
def checkout(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('homepage'))
    config, _ = load_shop_config()
    return render_template("checkout.html", produto=produto, config=config)

# --- SISTEMA DE CARRINHO ---

@app.route("/carrinho")
def exibir_carrinho():
    config, _ = load_shop_config()
    carrinho_sessao = session.get('carrinho', {})
    produtos_no_carrinho = []
    total_geral = 0

    for id_p, qtd in carrinho_sessao.items():
        p = database.get_produto_por_id(id_p)
        if p:
            preco = float(p['novo_preco'] if p.get('em_oferta') else p['preco'])
            subtotal = preco * qtd
            total_geral += subtotal
            p['quantidade_carrinho'] = qtd
            p['subtotal'] = subtotal
            produtos_no_carrinho.append(p)

    return render_template("carrinho.html", produtos=produtos_no_carrinho, total=total_geral, config=config)

@app.route('/remover_carrinho/<id_produto>')
def remover_carrinho(id_produto):
    carrinho = session.get('carrinho', {})
    id_p = str(id_produto)
    if id_p in carrinho:
        carrinho.pop(id_p)
        session.modified = True
    flash("Item removido do carrinho.")
    return redirect(url_for('exibir_carrinho'))

# --- SISTEMA DE LOGIN DO CLIENTE ---
@app.route("/cliente/login", methods=['GET', 'POST'])
def cliente_login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        cliente = database.verificar_login_cliente(email, senha)
        if cliente:
            session['cliente_id'] = cliente['id']
            session['cliente_nome'] = cliente['nome']
            flash(f"Bem-vindo de volta, {cliente['nome']}!")
            return redirect(url_for('homepage'))
        else:
            flash("E-mail ou senha incorretos.")
    return render_template("cliente_login.html")

@app.route("/cliente/logout")
def cliente_logout():
    session.pop('cliente_id', None)
    session.pop('cliente_nome', None)
    flash("Você saiu da sua conta.")
    return redirect(url_for('homepage'))

@app.route("/cliente/cadastro", methods=['GET', 'POST'])
def cliente_cadastro_rota():
    if request.method == 'POST':
        dados = {
            'nome': request.form.get('nome'),
            'cpf': request.form.get('cpf'),
            'email': request.form.get('email'),
            'telefone': request.form.get('telefone'),
            'senha': request.form.get('senha')
        }
        sucesso = database.salvar_novo_cliente(dados)
        if sucesso:
            flash("Conta criada com sucesso! Faça seu login.")
            return redirect(url_for('cliente_login'))
        else:
            flash("Erro ao criar conta. Verifique se o E-mail ou CPF já estão cadastrados.")
    return render_template("cadastro_cliente.html")

# --- RECUPERAÇÃO DE SENHA DO CLIENTE ---
@app.route("/cliente/recuperar-senha", methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        cliente = database.verificar_dados_recuperacao(email, cpf)
        if cliente:
            session['id_recuperacao'] = cliente['id']
            return redirect(url_for('nova_senha'))
        else:
            flash("Dados não encontrados. Verifique o E-mail e o CPF.")
    config, _ = load_shop_config()
    return render_template("recuperar_senha.html", config=config)

@app.route("/cliente/nova-senha", methods=['GET', 'POST'])
def nova_senha():
    if not session.get('id_recuperacao'):
        return redirect(url_for('recuperar_senha'))
    if request.method == 'POST':
        nova_s = request.form.get('senha')
        confirmacao = request.form.get('confirmacao')
        if nova_s == confirmacao:
            database.atualizar_senha_cliente(session['id_recuperacao'], nova_s)
            session.pop('id_recuperacao', None)
            flash("Senha alterada com sucesso! Faça login.")
            return redirect(url_for('cliente_login'))
        else:
            flash("As senhas não coincidem.")
    config, _ = load_shop_config()
    return render_template("nova_senha.html", config=config)

# --- SISTEMA ADMINISTRATIVO ---
@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if database.is_valid_login(user, pw):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Dados incorretos.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Sessão encerrada.")
    return redirect(url_for('admin_login'))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    vendas = database.get_vendas()
    produtos = database.get_produtos()
    clientes = database.get_clientes()
    config, _ = load_shop_config()
    return render_template("admin_dashboard.html", vendas=vendas, produtos=produtos, clientes=clientes, config=config)

@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        campos = ['titulo_site', 'contato_whatsapp', 'contato_email', 'header_color', 'footer_color', 'mercado_pago_token', 'melhor_envio_token', 'cep_origem']
        for campo in campos:
            valor = request.form.get(campo)
            if valor is not None: database.update_configuracao(campo, valor)

        for file_key in ['logo_img', 'banner_principal']:
            file = request.files.get(file_key)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{int(datetime.datetime.now().timestamp())}_{filename}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                database.update_configuracao(file_key, f'/static/uploads/{filename}')

        flash("Configurações atualizadas!")
        return redirect(url_for('admin_dashboard'))

    config, _ = load_shop_config()
    return render_template("admin_configuracoes.html", config=config)

@app.route('/admin/upload_capa_cat', methods=['POST'])
def admin_upload_capa_cat():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    categoria = request.form.get('categoria')
    file = request.files.get('imagem_capa')

    if file and categoria:
        filename = secure_filename(f"capa_{categoria.lower()}.png")
        save_path = os.path.join(UPLOAD_FOLDER_CAT, filename)
        file.save(save_path)
        db_path = f"uploads/categorias/{filename}"
        database.update_capa_categoria(categoria, db_path)
        flash(f'Capa de {categoria} atualizada com sucesso!', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route("/admin/edit", methods=['GET', 'POST'])
@app.route("/admin/edit/<id_produto>", methods=['GET', 'POST'])
def admin_edit(id_produto=None):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        try:
            def to_f(v): return float(str(v).replace(',', '.')) if v else 0.0
            dados = {
                'id': id_produto or request.form.get('id'),
                'nome': request.form.get('nome'),
                'categoria': request.form.get('categoria'),
                'preco': to_f(request.form.get('preco')),
                'descricao': request.form.get('descricao'),
                'em_oferta': 'em_oferta' in request.form,
                'novo_preco': to_f(request.form.get('novo_preco')),
                'oferta_fim': request.form.get('oferta_fim'),
                'desconto_pix': int(request.form.get('desconto_pix') or 0),
                'estoque': int(request.form.get('estoque') or 0),
                'frete_gratis_valor': to_f(request.form.get('frete_gratis_valor')),
                'prazo_entrega': request.form.get('prazo_entrega'),
                'tempo_preparo': request.form.get('tempo_preparo')
            }
            # MANTIDO: Lógica de upload das 4 imagens no admin
            for i in range(1, 5):
                f = request.files.get(f'imagem_{i}')
                if f and allowed_file(f.filename):
                    fname = secure_filename(f.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    f.save(path)
                    dados[f'img_path_{i}'] = f'/static/uploads/{fname}'
            database.add_or_update_produto(dados)
            flash("Produto salvo!")
            return redirect(url_for('admin_dashboard'))
        except Exception as e: flash(f"Erro: {e}")
    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

@app.route("/admin/delete/<id_produto>", methods=['POST'])
def admin_delete(id_produto):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    database.excluir_produto(id_produto)
    flash("Produto removido!")
    return redirect(url_for('admin_dashboard'))

# --- APIs E PAGAMENTO ---
@app.route("/calcular_frete", methods=['POST'])
def calcular_frete():
    dados = request.json
    produto = database.get_produto_por_id(dados.get('produto_id'))
    if not produto: return jsonify({"error": "Produto não encontrado"}), 404
    preco = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
    opcoes = melhorenvio.calcular_frete(dados.get('cep'), preco)
    return jsonify(opcoes)

@app.route("/processar_pagamento", methods=['POST'])
def processar_pagamento():
    id_p = request.form.get('id_produto')
    produto = database.get_produto_por_id(id_p)
    if not produto: return redirect(url_for('homepage'))
    try:
        frete = float(request.form.get('frete_valor') or 0)
        preco = float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco'])
        total = preco + frete
        id_v = database.registrar_venda(request.form.get('nome'), request.form.get('email'), request.form.get('whatsapp'), produto['nome'], 1, total)
        link = gerar_link_pagamento(produto, id_v, total)
        return redirect(link) if link else "Erro no link de pagamento"
    except Exception as e: return f"Erro: {e}"

@app.route("/sucesso")
def sucesso():
    config, _ = load_shop_config()
    return render_template("sucesso.html", config=config)

# --- CORREÇÃO: ROTA ADICIONAR AO CARRINHO ---
@app.route('/adicionar_carrinho/<id_produto>', methods=['POST'])
def adicionar_carrinho(id_produto):
    quantidade = int(request.form.get('quantidade', 1))
    acao = request.form.get('acao') # 'comprar' ou 'carrinho'

    if 'carrinho' not in session:
        session['carrinho'] = {}

    carrinho = session['carrinho']
    id_p = str(id_produto)

    if id_p in carrinho:
        carrinho[id_p] += quantidade
    else:
        carrinho[id_p] = quantidade

    session.modified = True

    if acao == 'comprar':
        return redirect(url_for('checkout', id_produto=id_produto))
    
    flash("Produto adicionado ao carrinho!")
    return redirect(url_for('exibir_carrinho'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
