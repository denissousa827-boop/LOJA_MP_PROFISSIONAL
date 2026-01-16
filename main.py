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

# --- CONFIGURAÇÃO DE AMBIENTE (TERMUX vs VERCEL) ---
IS_VERCEL = "VERCEL" in os.environ

if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp'
else:
    UPLOAD_FOLDER = 'static/uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}

if not IS_VERCEL:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inicializa o banco de dados
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

# --- SISTEMA DE LOGIN ADMINISTRATIVO ---
@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    message = request.args.get('message')
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if database.is_valid_login(user, pw):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('admin_login', message="Dados incorretos."))
    return render_template("admin_login.html", message=message)

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# --- SISTEMA DE ACESSO DO CLIENTE (LOGIN E LOGOUT) ---
@app.route("/cliente/login", methods=['GET', 'POST'])
def cliente_login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        # Chama a função que criamos no database.py
        cliente = database.verificar_login_cliente(email, senha)
        
        if cliente:
            # Armazena os dados na sessão (Padrão Profissional)
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
        # SALVA NO BANCO DE DADOS ATRAVÉS DO DATABASE.PY
        sucesso = database.salvar_novo_cliente(dados)
        
        if sucesso:
            flash("Conta criada com sucesso! Faça seu login.")
            return redirect(url_for('cliente_login'))
        else:
            flash("Erro ao criar conta. Verifique se o E-mail ou CPF já estão cadastrados.")
    
    return render_template("cadastro_cliente.html")

# --- ROTAS DE RECUPERAÇÃO DE SENHA ---
@app.route("/cliente/recuperar-senha", methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        
        cliente = database.verificar_dados_recuperacao(email, cpf)
        
        if cliente:
            # Se os dados estiverem certos, mandamos para a página de nova senha
            # Usamos a sessão temporária para autorizar a troca
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
        nova_senha = request.form.get('senha')
        confirmacao = request.form.get('confirmacao')
        
        if nova_senha == confirmacao:
            database.atualizar_senha_cliente(session['id_recuperacao'], nova_senha)
            session.pop('id_recuperacao', None)
            flash("Senha alterada com sucesso! Faça login.")
            return redirect(url_for('cliente_login'))
        else:
            flash("As senhas não coincidem.")
            
    config, _ = load_shop_config()
    return render_template("nova_senha.html", config=config)

# --- PAINEL ADMIN E CONFIGURAÇÕES ---
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    vendas = database.get_vendas()
    produtos = database.get_produtos()
    clientes = database.get_clientes() 
    config, _ = load_shop_config()
    
    return render_template("admin_dashboard.html", 
                           vendas=vendas, 
                           produtos=produtos, 
                           clientes=clientes, 
                           config=config)

@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        campos = ['titulo_site', 'contato_whatsapp', 'contato_email', 'header_color', 'footer_color', 'mercado_pago_token', 'melhor_envio_token', 'cep_origem']
        for campo in campos:
            valor = request.form.get(campo)
            if valor is not None: database.update_configuracao(campo, valor)
        
        file = request.files.get('logo_img')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            database.update_configuracao('logo_img', f'/{path}')
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
            def to_f(v): return float(str(v).replace(',', '.')) if v else 0.0
            dados = {
                'id': id_produto or request.form.get('id'),
                'nome': request.form.get('nome'),
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
            for i in range(1, 5):
                f = request.files.get(f'imagem_{i}')
                if f and allowed_file(f.filename):
                    fname = secure_filename(f.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    f.save(path)
                    dados[f'img_path_{i}'] = f'/{path}'
            database.add_or_update_produto(dados)
            flash("Produto salvo!")
            return redirect(url_for('admin_dashboard'))
        except Exception as e: flash(f"Erro: {e}")
    produto = database.get_produto_por_id(id_produto) if id_produto else None
    config, _ = load_shop_config()
    return render_template("admin_editar.html", produto=produto, config=config)

@app.route("/admin/delete/<id_produto>", methods=['POST'])
def admin_delete(id_produto):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    database.delete_produto(id_produto)
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
