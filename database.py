# database.py
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 1. Configuração do Banco de Dados
DB_NAME = 'loja.db'

def create_connection():
    """Cria uma conexão com o banco de dados SQLite e configura o row_factory."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Acessa colunas por nome
    return conn

def init_db():
    """Inicializa o banco de dados e força a atualização da senha do admin."""
    conn = create_connection()
    cursor = conn.cursor()

    # Tabela de Produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            descricao TEXT,
            img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
            video_path TEXT, em_oferta INTEGER DEFAULT 0,
            novo_preco REAL, oferta_fim TEXT
        )
    """)

    # Tabela de Usuários Admin
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # Tabela de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            whatsapp TEXT,
            email TEXT UNIQUE NOT NULL,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de Configurações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # --- CORREÇÃO DE ACESSO AO ADMIN ---
    admin_username = "utbdenis6752"
    admin_password = "675201"
    admin_hash = generate_password_hash(admin_password)

    # Deleta o admin antigo e insere o novo com o hash correto para evitar erro de login
    cursor.execute("DELETE FROM users WHERE username=?", (admin_username,))
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (admin_username, admin_hash))

    # Preenche configurações iniciais
    config_keys = [
        ('contato_email', 'suporte@minhaloja.com.br'),
        ('contato_whatsapp', '(99) 99999-9999'),
        ('header_color', '#181818'),
        ('footer_color', '#303030')
    ]
    for chave, valor in config_keys:
        cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))

    conn.commit()
    conn.close()

# --- FUNÇÕES DE LOGIN ---

def get_user(username):
    conn = create_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return user

def is_valid_login(username, password):
    user = get_user(username)
    # Se o usuário existe, verificamos se a senha digitada bate com o hash no banco
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

# --- RESTANTE DAS FUNÇÕES (PRODUTOS, CLIENTES, CONFIG) ---

def get_produtos():
    conn = create_connection()
    produtos = conn.execute("SELECT * FROM produtos").fetchall()
    conn.close()
    return [dict(p) for p in produtos]

def get_produtos_em_oferta():
    conn = create_connection()
    sql = "SELECT * FROM produtos WHERE em_oferta = 1 AND (oferta_fim IS NULL OR oferta_fim > ?)"
    agora = datetime.datetime.now().isoformat()
    produtos = conn.execute(sql, (agora,)).fetchall()
    conn.close()
    return [dict(p) for p in produtos]

def get_produto_por_id(id_produto):
    conn = create_connection()
    produto = conn.execute("SELECT * FROM produtos WHERE id=?", (id_produto,)).fetchone()
    conn.close()
    return dict(produto) if produto else None

def add_or_update_produto(id, nome, preco, descricao, img_paths, video_path, em_oferta=0, novo_preco=None, oferta_fim=None):
    conn = create_connection()
    cursor = conn.cursor()
    if not id: id = str(int(datetime.datetime.now().timestamp()))[-8:]
    img_1, img_2, img_3, img_4 = img_paths + [None] * (4 - len(img_paths))
    oferta_status = 1 if em_oferta else 0
    data = (nome, preco, descricao, img_1, img_2, img_3, img_4, video_path, oferta_status, novo_preco, oferta_fim, id)
    
    if get_produto_por_id(id):
        sql = "UPDATE produtos SET nome=?, preco=?, descricao=?, img_path_1=?, img_path_2=?, img_path_3=?, img_path_4=?, video_path=?, em_oferta=?, novo_preco=?, oferta_fim=? WHERE id=?"
    else:
        sql = "INSERT INTO produtos (nome, preco, descricao, img_path_1, img_path_2, img_path_3, img_path_4, video_path, em_oferta, novo_preco, oferta_fim, id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    
    cursor.execute(sql, data)
    conn.commit()
    conn.close()

def delete_produto(id_produto):
    conn = create_connection()
    conn.execute("DELETE FROM produtos WHERE id=?", (id_produto,))
    conn.commit()
    conn.close()

def add_cliente(nome_completo, whatsapp, email):
    conn = create_connection()
    try:
        conn.execute("INSERT INTO clientes (nome_completo, whatsapp, email) VALUES (?, ?, ?)", (nome_completo, whatsapp, email))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def get_clientes():
    conn = create_connection()
    clientes = conn.execute("SELECT * FROM clientes ORDER BY data_cadastro DESC").fetchall()
    conn.close()
    return [dict(c) for c in clientes]

def get_cliente_por_id(id_cliente):
    conn = create_connection()
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id_cliente,)).fetchone()
    conn.close()
    return dict(cliente) if cliente else None

def update_cliente(id_cliente, nome_completo, whatsapp, email):
    conn = create_connection()
    conn.execute("UPDATE clientes SET nome_completo=?, whatsapp=?, email=? WHERE id=?", (nome_completo, whatsapp, email, id_cliente))
    conn.commit()
    conn.close()

def delete_cliente(id_cliente):
    conn = create_connection()
    conn.execute("DELETE FROM clientes WHERE id=?", (id_cliente,))
    conn.commit()
    conn.close()

def get_configuracoes():
    conn = create_connection()
    config_list = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
    conn.close()
    return {item['chave']: item['valor'] for item in config_list}

def update_configuracao(chave, valor):
    conn = create_connection()
    conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
