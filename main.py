from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import datetime
import requests # Necessário para consultar o Mercado Pago

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
    banner_pagamento = config.get('banner_principal', '')
    return config, banner_pagamento

# Função para validar o pagamento no Mercado Pago
def consultar_status_mp(payment_id):
    config, _ = load_shop_config()
    token = config.get('mercado_pago_token')
    if not token: return None, None
    
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200: # Corrigido para status_code
            dados = response.json()
            return dados.get('status'), dados.get('external_reference')
    except:
        pass
    return None, None

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
            if query in p.get('nome', '').lower() or query in p.get('descricao', '').lower():
                produtos_encontrados.append(p)
    return render_template("pesquisa.html", produtos=produtos_encontrados, query=query, config=config, banner_pagamento=banner_pagamento)

@app.route("/categoria/<nome_categoria>")
def categoria(nome_categoria):
    config, banner_pagamento = load_shop_config()
    todos_produtos = database.get_produtos()
    cat_search = nome_categoria.lower()
    produtos_categoria = [p for p in todos_produtos if cat_search == str(p.get('categoria', '')).lower()]
    return render_template("pesquisa.html", produtos=produtos_categoria, query=nome_categoria, config=config, banner_pagamento=banner_pagamento)

@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto: return redirect(url_for('homepage'))
    config, banner_pagamento = load_shop_config()
    imagens = [produto.get(f'img_path_{i}') for i in range(1, 5) if produto.get(f'img_path_{i}')]
    return render_template("produto_detalhes.html", produto=produto, imagens=imagens, config=config, banner_pagamento=banner_pagamento)

@app.route("/checkout/<id_produto>")
def checkout(id_produto):
    produto = database.get_produto_por_id(id_produto)
    if not produto: return redirect(url_for('homepage'))
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

# --- SISTEMA DE CLIENTE (LOGIN/PEDIDOS) ---
@app.route("/cliente/login", methods=['GET', 'POST'])
def cliente_login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        cliente = database.verificar_login_cliente(email, senha)
        if cliente:
            session['cliente_id'] = cliente['id']
            session['cliente_nome'] = cliente['nome']
            session['cliente_email'] = cliente['email']
            flash(f"Bem-vindo de volta, {cliente['nome']}!")
            return redirect(url_for('homepage'))
        else:
            flash("E-mail ou senha incorretos.")
    return render_template("cliente_login.html")

@app.route("/meus-pedidos")
def meus_pedidos():
    if 'cliente_id' not in session:
        flash("Por favor, faça login para ver seus pedidos.")
        return redirect(url_for('cliente_login'))
    config, banner_pagamento = load_shop_config()
    todas_vendas = database.get_vendas()
    pedidos_cliente = [v for v in todas_vendas if v.get('email') == session.get('cliente_email')]
    return render_template("meus_pedidos.html", pedidos=pedidos_cliente, config=config, banner_pagamento=banner_pagamento)

@app.route("/cliente/logout")
def cliente_logout():
    session.pop('cliente_id', None)
    session.pop('cliente_nome', None)
    session.pop('cliente_email', None)
    flash("Você saiu da sua conta.")
    return redirect(url_for('homepage'))

@app.route("/cliente/cadastro", methods=['GET', 'POST'])
def cliente_cadastro_rota():
    if request.method == 'POST':
        dados = {'nome': request.form.get('nome'), 'cpf': request.form.get('cpf'), 'email': request.form.get('email'), 'telefone': request.form.get('telefone'), 'senha': request.form.get('senha')}
        if database.salvar_novo_cliente(dados):
            flash("Conta criada com sucesso! Faça seu login.")
            return redirect(url_for('cliente_login'))
        else:
            flash("Erro ao criar conta. Verifique os dados.")
    return render_template("cadastro_cliente.html")

@app.route("/cliente/recuperar-senha", methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        cliente = database.verificar_dados_recuperacao(request.form.get('email'), request.form.get('cpf'))
        if cliente:
            session['id_recuperacao'] = cliente['id']
            return redirect(url_for('nova_senha'))
        flash("Dados não encontrados.")
    config, _ = load_shop_config()
    return render_template("recuperar_senha.html", config=config)

@app.route("/cliente/nova-senha", methods=['GET', 'POST'])
def nova_senha():
    if not session.get('id_recuperacao'): return redirect(url_for('recuperar_senha'))
    if request.method == 'POST':
        if request.form.get('senha') == request.form.get('confirmacao'):
            database.atualizar_senha_cliente(session['id_recuperacao'], request.form.get('senha'))
            session.pop('id_recuperacao', None)
            flash("Senha alterada com sucesso!")
            return redirect(url_for('cliente_login'))
        flash("As senhas não coincidem.")
    config, _ = load_shop_config()
    return render_template("nova_senha.html", config=config)

# --- SISTEMA ADMINISTRATIVO ---
@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if database.is_valid_login(request.form.get('username'), request.form.get('password')):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Dados incorretos.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    vendas = database.get_vendas()
    produtos = database.get_produtos()
    clientes = database.get_clientes()
    config, _ = load_shop_config()
    return render_template("admin_dashboard.html", vendas=vendas, produtos=produtos, clientes=clientes, config=config)

@app.route("/admin/pedidos")
def admin_pedidos():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    pedidos = database.get_vendas()
    config, _ = load_shop_config()
    return render_template("admin_pedidos.html", pedidos=pedidos, config=config)

@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        campos = ['titulo_site', 'contato_whatsapp', 'contato_email', 'header_color', 'footer_color', 'mercado_pago_token', 'melhor_envio_token', 'cep_origem']
        for campo in campos:
            valor = request.form.get(campo)
            if valor is not None: database.update_configuracao(campo, valor)
        for file_key in ['logo_img', 'banner_principal']:
            file = request.files.get(file_key)
            if file and allowed_file(file.filename):
                filename = f"{int(datetime.datetime.now().timestamp())}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                database.update_configuracao(file_key, f'/static/uploads/{filename}')
        flash("Configurações atualizadas!")
        return redirect(url_for('admin_dashboard'))
    config, _ = load_shop_config()
    return render_template("admin_configuracoes.html", config=config)

@app.route('/admin/upload_capa_cat', methods=['POST'])
def admin_upload_capa_cat():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    categoria, file = request.form.get('categoria'), request.files.get('imagem_capa')
    if file and categoria:
        filename = secure_filename(f"capa_{categoria.lower()}.png")
        file.save(os.path.join(UPLOAD_FOLDER_CAT, filename))
        database.update_capa_categoria(categoria, f"uploads/categorias/{filename}")
        flash(f'Capa de {categoria} atualizada!')
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/edit", methods=['GET', 'POST'])
@app.route("/admin/edit/<id_produto>", methods=['GET', 'POST'])
def admin_edit(id_produto=None):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    if request.method == 'POST':
        def to_f(v): return float(str(v).replace(',', '.')) if v else 0.0
        dados = {'id': id_produto or request.form.get('id'), 'nome': request.form.get('nome'), 'categoria': request.form.get('categoria'), 'preco': to_f(request.form.get('preco')), 'descricao': request.form.get('descricao'), 'em_oferta': 'em_oferta' in request.form, 'novo_preco': to_f(request.form.get('novo_preco')), 'oferta_fim': request.form.get('oferta_fim'), 'desconto_pix': int(request.form.get('desconto_pix') or 0), 'estoque': int(request.form.get('estoque') or 0), 'frete_gratis_valor': to_f(request.form.get('frete_gratis_valor')), 'prazo_entrega': request.form.get('prazo_entrega'), 'tempo_preparo': request.form.get('tempo_preparo')}
        for i in range(1, 5):
            f = request.files.get(f'imagem_{i}')
            if f and allowed_file(f.filename):
                fname = secure_filename(f.filename)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                dados[f'img_path_{i}'] = f'/static/uploads/{fname}'
        database.add_or_update_produto(dados)
        flash("Produto salvo!")
        return redirect(url_for('admin_dashboard'))
    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

@app.route("/admin/delete/<id_produto>", methods=['POST'])
def admin_delete(id_produto):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    database.excluir_produto(id_produto)
    flash("Produto removido!")
    return redirect(url_for('admin_dashboard'))

# --- APIs E FRETE ---
@app.route("/calcular_frete", methods=['POST'])
def calcular_frete_rota():
    dados = request.json
    produto = database.get_produto_por_id(dados.get('produto_id'))
    if not produto: return jsonify({"error": "Produto não encontrado"}), 404
    config, _ = load_shop_config()
    opcoes = melhorenvio.calcular_frete(cep_destino=dados.get('cep'), preco_produto=float(produto['novo_preco'] if produto.get('em_oferta') else produto['preco']), token_melhor_envio=config.get('melhor_envio_token'), cep_origem_config=config.get('cep_origem'))
    return jsonify(opcoes)

@app.route("/processar_pagamento", methods=['POST'])
def processar_pagamento():
    produto = database.get_produto_por_id(request.form.get('id_produto'))
    if not produto: return redirect(url_for('homepage'))
    try:
        total = float(request.form.get('total_final') or (produto['novo_preco'] if produto.get('em_oferta') else produto['preco']))
        id_v = database.registrar_venda(request.form.get('nome'), request.form.get('email'), request.form.get('whatsapp'), produto['nome'], 1, total)
        link = gerar_link_pagamento(produto, id_v, total)
        return redirect(link) if link else "Erro no link"
    except Exception as e: return f"Erro: {e}"

# --- ROTA WEBHOOK MERCADO PAGO ATUALIZADA ---
@app.route('/webhook/mercadopago', methods=['POST', 'GET'])
def webhook_mercadopago():
    # Detecta se os dados vêm da URL (GET) ou do corpo da requisição (POST)
    data = request.args if request.method == 'GET' else (request.json if request.is_json else request.form)
    
    # Tenta obter o ID da venda (external_reference) e o Status
    id_venda = data.get('external_reference')
    status = data.get('status') or data.get('collection_status')

    # Se for uma notificação oficial de pagamento (POST)
    payment_id = data.get('data.id') or (data.get('data', {}).get('id') if isinstance(data, dict) else None)
    
    if payment_id:
        # Consulta a API para ter certeza do status real
        status_oficial, ref_oficial = consultar_status_mp(payment_id)
        if status_oficial:
            status = status_oficial
            id_venda = ref_oficial

    # Se o pagamento foi aprovado, atualiza o banco
    if id_venda and status == 'approved':
        database.atualizar_status_venda(id_venda, 'pago')
        print(f"✅ Venda {id_venda} aprovada via Webhook!")
        
    # Se o cliente estiver voltando do checkout pelo navegador
    if request.method == 'GET':
        return redirect(url_for('sucesso'))
        
    return "OK", 200

@app.route("/sucesso")
def sucesso():
    config, _ = load_shop_config()
    return render_template("sucesso.html", config=config)

@app.route('/adicionar_carrinho/<id_produto>', methods=['POST'])
def adicionar_carrinho(id_produto):
    quantidade = int(request.form.get('quantidade', 1))
    if 'carrinho' not in session: session['carrinho'] = {}
    carrinho = session['carrinho']
    carrinho[str(id_produto)] = carrinho.get(str(id_produto), 0) + quantidade
    session.modified = True
    if request.form.get('acao') == 'comprar': return redirect(url_for('checkout', id_produto=id_produto))
    flash("Adicionado ao carrinho!")
    return redirect(url_for('exibir_carrinho'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
