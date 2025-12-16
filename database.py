# database.py
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# 1. Configuração do Banco de Dados
DB_NAME = 'loja.db'

def create_connection():
    """Cria uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com a tabela de produtos, usuários, clientes e CONFIGURAÇÕES."""
    conn = create_connection()
    cursor = conn.cursor()

    # Tabela de Produtos (ATUALIZADA com campos de OFERTA)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            descricao TEXT,
            img_path_1 TEXT,
            img_path_2 TEXT,
            img_path_3 TEXT,
            img_path_4 TEXT,
            video_path TEXT,
            em_oferta INTEGER DEFAULT 0,
            novo_preco REAL,
            oferta_fim TEXT
        )
    """)

    # Tabela de Usuários Admin (Mantida)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # Tabela de Clientes para notificações e promoções (Mantida)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY,
            nome_completo TEXT NOT NULL,
            whatsapp TEXT,
            email TEXT UNIQUE NOT NULL
        )
    """)

    # Tabela de Configurações (Mantida)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # 2. Usuário Administrador Fixo
    admin_username = "utbdenis6752"
    admin_password = "675201"
    admin_hash = generate_password_hash(admin_password)

    cursor.execute("SELECT * FROM users WHERE username=?", (admin_username,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (admin_username, admin_hash))

    # Preenche a tabela de configurações com valores iniciais se estiver vazia
    config_keys = [
        ('contato_email', 'suporte@minhaloja.com.br'),
        ('contato_whatsapp', '(99) 99999-9999'),
        ('quem_somos', 'Nós somos a Minha Loja Oficial, focada em produtos de alta qualidade.'),
        ('politica_privacidade', 'Este é o texto completo da Política de Privacidade. Edite-o no Painel Admin!'),
        ('politica_reembolso', 'Este é o texto completo da Política de Reembolso. Edite-o no Painel Admin!'),
        ('formas_pagamento', 'Nossas formas de pagamento incluem Cartão, Pix e Boleto, todos processados via Mercado Pago.'),
        ('entrega_frete', 'O prazo de entrega varia de 5 a 15 dias úteis, dependendo da região.'),
        ('trocas_devolucoes', 'Você tem 7 dias para solicitar a troca ou devolução do produto.'),
        ('garantia_seguranca', 'Todos os produtos possuem 90 dias de garantia contra defeitos de fabricação.'),
        ('rastrear_pedido', 'Link ou instruções sobre como rastrear o pedido.'),
        ('banner_pagamento', 'assets/pix.png,assets/visa.png,assets/mastercard.png'),
        # NOVAS CHAVES PARA CORES E BANNER PRINCIPAL:
        ('header_color', '#181818'), # Cor escura para o topo
        ('footer_color', '#303030'), # Cor para o rodapé
        ('banner_img', 'https://via.placeholder.com/1200x300.png?text=Seu+Banner+Principal+AQUI')
    ]

    for chave, valor in config_keys:
        cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))

    conn.commit()
    conn.close()

# 3. Funções de Manipulação de Dados (CRUD Produtos e Usuários)

def get_produtos():
    conn = create_connection()
    produtos = conn.execute("SELECT * FROM produtos").fetchall()
    conn.close()
    return produtos

# NOVO: Função para pegar produtos em oferta
def get_produtos_em_oferta():
    """Retorna todos os produtos marcados como em oferta."""
    conn = create_connection()
    # Seleciona produtos onde 'em_oferta' é 1 (True)
    produtos = conn.execute('SELECT * FROM produtos WHERE em_oferta = 1').fetchall()
    conn.close()
    return produtos

def get_produto_por_id(id_produto):
    conn = create_connection()
    produto = conn.execute("SELECT * FROM produtos WHERE id=?", (id_produto,)).fetchone()
    conn.close()
    return produto

# CORRIGIDO: Agora aceita e salva os parâmetros de OFERTA
def add_or_update_produto(id, nome, preco, descricao, img_paths, video_path, em_oferta=0, novo_preco=None, oferta_fim=None):
    conn = create_connection()
    img_1, img_2, img_3, img_4 = img_paths + [None] * (4 - len(img_paths))
    cursor = conn.cursor()
    
    # Prepara os valores de oferta (garante que só salva se 'em_oferta' for True)
    oferta_status = 1 if em_oferta else 0
    preco_oferta = novo_preco if oferta_status == 1 and novo_preco else None
    fim_oferta = oferta_fim if oferta_status == 1 and oferta_fim else None
    
    cursor.execute("""
        UPDATE produtos SET nome=?, preco=?, descricao=?,
        img_path_1=?, img_path_2=?, img_path_3=?, img_path_4=?, video_path=?,
        em_oferta=?, novo_preco=?, oferta_fim=?
        WHERE id=?
    """, (nome, preco, descricao, img_1, img_2, img_3, img_4, video_path,
        oferta_status, preco_oferta, fim_oferta, id))
    
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO produtos (id, nome, preco, descricao, img_path_1, img_path_2, img_path_3, img_path_4, video_path, em_oferta, novo_preco, oferta_fim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id, nome, preco, descricao, img_1, img_2, img_3, img_4, video_path,
            oferta_status, preco_oferta, fim_oferta))
            
    conn.commit()
    conn.close()

def delete_produto(id_produto):
    conn = create_connection()
    conn.execute("DELETE FROM produtos WHERE id=?", (id_produto,))
    conn.commit()
    conn.close()

def get_user(username):
    conn = create_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return user

def is_valid_login(username, password):
    user = get_user(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

# Funções de Manipulação de Dados (CRUD Clientes) - MANTIDAS
def add_cliente(nome_completo, whatsapp, email):
    conn = create_connection()
    try:
        conn.execute("INSERT INTO clientes (nome_completo, whatsapp, email) VALUES (?, ?, ?)",
                        (nome_completo, whatsapp, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_clientes():
    conn = create_connection()
    clientes = conn.execute("SELECT * FROM clientes ORDER BY nome_completo").fetchall()
    conn.close()
    return clientes

def get_cliente_por_id(id_cliente):
    conn = create_connection()
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id_cliente,)).fetchone()
    conn.close()
    return cliente

def update_cliente(id_cliente, nome_completo, whatsapp, email):
    conn = create_connection()
    conn.execute("UPDATE clientes SET nome_completo=?, whatsapp=?, email=? WHERE id=? ",
                    (nome_completo, whatsapp, email, id_cliente))
    conn.commit()
    conn.close()

def delete_cliente(id_cliente):
    conn = create_connection()
    conn.execute("DELETE FROM clientes WHERE id=?", (id_cliente,))
    conn.commit()
    conn.close()

# Funções para Configurações - MANTIDAS
def get_configuracoes():
    """Retorna todas as configurações como um dicionário chave: valor."""
    conn = create_connection()
    config_list = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
    conn.close()

    config_dict = {item['chave']: item['valor'] for item in config_list}
    return config_dict

def update_configuracao(chave, valor):
    """Atualiza ou insere uma única configuração."""
    conn = create_connection()
    conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()

init_db()
