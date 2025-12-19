from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import datetime
import mercadopago

# Importa as funções de API e dados
from apimercadopago import gerar_link_pagamento
from database import (
    get_produtos, get_produto_por_id, is_valid_login,
    add_or_update_produto, delete_produto, init_db,
    add_cliente, get_clientes, get_cliente_por_id, update_cliente, delete_cliente,
    get_configuracoes, update_configuracao,
    get_produtos_em_oferta,
    get_vendas, get_venda_por_id, registrar_venda, atualizar_status_venda
)

# ---------------- CONFIGURAÇÃO INICIAL ----------------
app = Flask(__name__)
app.secret_key = 'chave_ultra_secreta_denis'

# Configuração de uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inicializa o banco de dados ao iniciar o app
init_db()

# --------------------------------------------------------

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_shop_config():
    """Carrega todas as configurações do banco de dados para os templates."""
    config = get_configuracoes()
    banner_pagamento = []
    if config and config.get('banner_pagamento'):
        banner_pagamento = [f.strip() for f in config['banner_pagamento'].split(',') if f.strip()]
    return config, banner_pagamento

# --------------------------------------------------------
# --- ROTAS DA LOJA (VIEW PÚBLICA) ---
# --------------------------------------------------------

@app.route("/")
def homepage():
    produtos = get_produtos()
    ofertas = get_produtos_em_oferta()
    config, banner_pagamento = load_shop_config()
    return render_template(
        "homepage.html", produtos=produtos, ofertas=ofertas, config=config, banner_pagamento=banner_pagamento
    )

@app.route("/pagina_info/<chave_config>")
def pagina_info(chave_config):
    config, banner_pagamento = load_shop_config()
    titulos = {
        'contato_email': 'Email de Suporte', 'contato_whatsapp': 'WhatsApp da Loja',
        'quem_somos': 'Quem Somos', 'politica_privacidade': 'Política de Privacidade',
        'politica_reembolso': 'Política de Reembolso', 'formas_pagamento': 'Formas de Pagamento',
        'entrega_frete': 'Entrega e Frete', 'trocas_devolucoes': 'Trocas e Devoluções',
        'garantia_seguranca': 'Garantia e Segurança', 'rastrear_pedido': 'Rastrear seu Pedido',
    }
    titulo = titulos.get(chave_config, 'Informação da Loja')
    conteudo = config.get(chave_config, 'Conteúdo não encontrado.')
    return render_template(
        "pagina_info.html", titulo=titulo, conteudo=conteudo, config=config, banner_pagamento=banner_pagamento
    )

@app.route("/cadastro_cliente", methods=['GET', 'POST'])
def cadastro_cliente():
    config, banner_pagamento = load_shop_config()
    if request.method == 'POST':
        nome_completo = request.form['nome_completo']
        whatsapp = request.form['whatsapp']
        email = request.form['email']
        if add_cliente(nome_completo, whatsapp, email):
            return render_template("cadastro_sucesso.html", nome=nome_completo, config=config, banner_pagamento=banner_pagamento)
        else:
            return render_template("cadastro_cliente.html", error="Este e-mail já está cadastrado.", config=config, banner_pagamento=banner_pagamento)
    return render_template("cadastro_cliente.html", config=config, banner_pagamento=banner_pagamento)

@app.route("/produto/<id_produto>")
def produto_detalhes(id_produto):
    produto = get_produto_por_id(id_produto)
    config, banner_pagamento = load_shop_config()
    if not produto:
        return redirect(url_for('homepage'))

    try:
        if produto.get('oferta_fim') and datetime.datetime.now().isoformat() > produto['oferta_fim']:
            produto['em_oferta'] = 0
    except Exception:
        pass

    imagens = [produto.get('img_path_1'), produto.get('img_path_2'), produto.get('img_path_3'), produto.get('img_path_4')]
    return render_template(
        "produto_detalhes.html", produto=produto, imagens=imagens, config=config, banner_pagamento=banner_pagamento
    )

@app.route("/comprar/<id_produto>")
def comprar_produto(id_produto):
    produto = get_produto_por_id(id_produto)
    if not produto:
        return redirect(url_for('compra_errada'))

    valor_venda = produto['preco']
    if produto.get('em_oferta') and produto.get('novo_preco'):
        valor_venda = produto['novo_preco']

    id_venda = registrar_venda(
        nome_cliente="Interessado", 
        email_cliente="n/a", 
        whatsapp_cliente="n/a",
        produto_nome=produto['nome'],
        quantidade=1,
        valor_total=valor_venda
    )

    link_iniciar_pagamento = gerar_link_pagamento(produto, id_venda)

    if link_iniciar_pagamento:
        return redirect(link_iniciar_pagamento)
    else:
        return redirect(url_for('compra_errada'))

# --- ROTA WEBHOOK: APROVAÇÃO AUTOMÁTICA ---
@app.route("/webhook", methods=['POST'])
def webhook():
    sdk = mercadopago.SDK("APP_USR-2222429353877099-112620-ccc34bc216b9dad3e14ec4618dbc5de3-1565971221")
    
    payment_id = request.args.get('data.id') or request.args.get('id')
    
    if payment_id:
        try:
            pagamento_info = sdk.payment().get(payment_id)
            
            if pagamento_info["status"] == 200:
                resposta = pagamento_info["response"]
                status_mp = resposta.get("status")
                id_venda_interna = resposta.get("external_reference")

                print(f"--- WEBHOOK RECEBIDO: Venda {id_venda_interna} Status {status_mp} ---")

                if status_mp == "approved" and id_venda_interna:
                    atualizar_status_venda(id_venda_interna, 'pago')
                    print(f"✅ SUCESSO: Venda {id_venda_interna} atualizada para PAGO!")
                
        except Exception as e:
            print(f"❌ Erro ao processar webhook: {e}")

    return jsonify({"status": "ok"}), 200

@app.route("/sucesso")
def compra_certa():
    config, banner_pagamento = load_shop_config()
    return render_template("compracerta.html", config=config, banner_pagamento=banner_pagamento)

@app.route("/erro")
def compra_errada():
    config, banner_pagamento = load_shop_config()
    return render_template("compraerrada.html", config=config, banner_pagamento=banner_pagamento)

# ------------------------------------------------------------------------------------------------------
# --- ROTAS DO PAINEL ADMINISTRATIVO ---
# ------------------------------------------------------------------------------------------------------

@app.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if is_valid_login(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Credenciais inválidas.'
    return render_template("admin_login.html", error=error)

@app.route("/admin/dashboard")
def admin_dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    produtos = get_produtos()
    clientes = get_clientes()
    return render_template("admin_dashboard.html", produtos=produtos, clientes=clientes)

@app.route("/admin/vendas")
def admin_vendas():
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    vendas_lista = get_vendas()
    return render_template("admin_vendas.html", vendas=vendas_lista)

@app.route("/admin/venda/<int:id_venda>")
def admin_detalhe_venda(id_venda):
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    venda = get_venda_por_id(id_venda)
    if not venda:
        flash("Pedido não encontrado.")
        return redirect(url_for('admin_vendas'))
    return render_template("admin_detalhe_venda.html", venda=venda)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# --- CORREÇÃO APLICADA AQUI: ROTA DE EXCLUSÃO AGORA ACEITA POST ---
@app.route("/admin/delete/<id_produto>", methods=['POST'])
def admin_delete(id_produto):
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # Chama a função do database.py para remover do banco
    delete_produto(id_produto)
    
    flash(f"Produto {id_produto} excluído com sucesso!")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/clientes")
def admin_clientes():
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    clientes = get_clientes()
    return render_template("admin_clientes.html", clientes=clientes)

@app.route("/admin/clientes/delete/<int:id_cliente>", methods=['POST'])
def admin_delete_cliente(id_cliente):
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    delete_cliente(id_cliente)
    return redirect(url_for('admin_clientes'))

@app.route("/admin/clientes/edit/<int:id_cliente>", methods=['GET', 'POST'])
def admin_editar_cliente(id_cliente):
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))
    cliente = get_cliente_por_id(id_cliente)
    if request.method == 'POST':
        update_cliente(id_cliente, request.form['nome_completo'], request.form['whatsapp'], request.form['email'])
        return redirect(url_for('admin_clientes'))
    return render_template("admin_editar_cliente.html", cliente=cliente)

@app.route("/admin/edit/<id_produto>", methods=['GET', 'POST'])
@app.route("/admin/add", methods=['GET', 'POST'])
def admin_edit(id_produto=None):
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))

    produto = get_produto_por_id(id_produto) if id_produto else None

    if request.method == 'POST':
        id_prod = request.form.get('id', id_produto)
        nome = request.form['nome']
        
        try:
            preco = float(request.form.get('preco', 0))
            novo_preco = request.form.get('novo_preco')
            novo_preco = float(novo_preco) if novo_preco else None
        except ValueError:
            flash("Erro nos valores de preço. Use apenas números e ponto.")
            return redirect(request.url)

        descricao = request.form['descricao']
        em_oferta = request.form.get('em_oferta') == 'on'
        oferta_fim = request.form.get('oferta_fim')

        img_paths = []
        for i in range(1, 5):
            file = request.files.get(f'imagem_{i}')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                img_paths.append(f'/static/uploads/{filename}')
            else:
                img_paths.append(produto[f'img_path_{i}'] if produto else None)

        video_file = request.files.get('video')
        video_path = produto['video_path'] if produto else None
        if video_file and allowed_file(video_file.filename):
            v_filename = secure_filename(video_file.filename)
            video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], v_filename))
            video_path = f'/static/uploads/{v_filename}'

        add_or_update_produto(id_prod, nome, preco, descricao, img_paths, video_path, em_oferta, novo_preco, oferta_fim)
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_editar.html", produto=produto)

@app.route("/admin/configuracoes", methods=['GET', 'POST'])
def admin_configuracoes():
    if 'logged_in' not in session:
        return redirect(url_for('admin_login'))

    config = get_configuracoes()
    if request.method == 'POST':
        keys = ['contato_email', 'contato_whatsapp', 'quem_somos', 'politica_privacidade',
                'politica_reembolso', 'formas_pagamento', 'entrega_frete', 'trocas_devolucoes',
                'garantia_seguranca', 'rastrear_pedido', 'banner_pagamento', 'header_color', 'footer_color']

        for key in keys:
            update_configuracao(key, request.form.get(key, ''))

        for file_key in ['logo_img', 'banner_img']:
            file = request.files.get(file_key)
            if file and allowed_file(file.filename):
                fname = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                update_configuracao(file_key, f'/static/uploads/{fname}')

        flash("Configurações salvas!")
        return redirect(url_for('admin_configuracoes'))

    return render_template("admin_configuracoes.html", config=config)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
