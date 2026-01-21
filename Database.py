import sqlite3
import os
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Nome do arquivo de banco de dados
DB_PATH = "loja.db"

def create_connection():
    """Cria conexão com o banco de dados local SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row 
        return conn
    except Exception as e:
        print(f"Erro de conexão ao banco local: {e}")
        return None

def init_db():
    """Inicializa as tabelas e cria o Admin"""
    conn = create_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        
        # 1. Tabela de Usuários (Admin)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        # 2. Tabela de Produtos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                categoria TEXT,
                preco REAL NOT NULL,
                descricao TEXT,
                img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
                video_path TEXT,
                em_oferta INTEGER DEFAULT 0,
                novo_preco REAL DEFAULT 0.0,
                oferta_fim TEXT,
                desconto_pix INTEGER DEFAULT 0,
                estoque INTEGER DEFAULT 0,
                frete_gratis_valor REAL DEFAULT 0.0,
                prazo_entrega TEXT,
                tempo_preparo TEXT
            )
        """)

        # 3. Tabela de Configurações (Onde ficam as CAPAS das categorias)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)

        # 4. Tabela de Vendas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_cliente TEXT,
                email_cliente TEXT,
                whatsapp_cliente TEXT,
                produto_nome TEXT,
                quantidade INTEGER,
                valor_total REAL,
                status TEXT DEFAULT 'pendente',
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Tabela de Clientes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                telefone TEXT,
                senha TEXT NOT NULL,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Admin Padrão
        admin_user = "utbdenis6752"
        admin_pass = "675201"
        pw_hash = generate_password_hash(admin_pass)
        
        cur.execute("SELECT * FROM users WHERE username = ?", (admin_user,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (admin_user, pw_hash))
        
        conn.commit()
        conn.close()
        print("✅ Banco de dados ATUALIZADO e pronto!")
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")

# --- FUNÇÕES DE CATEGORIAS PERSONALIZADAS (FOTOS REAIS) ---

def update_capa_categoria(nome_categoria, img_path):
    """Salva a imagem real para a categoria (Ex: capa_CELULARES)"""
    conn = create_connection()
    if not conn: return
    cur = conn.cursor()
    chave = f"capa_{nome_categoria.upper()}"
    cur.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, img_path))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT * FROM produtos ORDER BY id DESC")
    res = [dict(row) for row in cur.fetchall()]
    conn.close()
    return res

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor()
    agora = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    cur.execute("""
        SELECT * FROM produtos 
        WHERE em_oferta = 1 
        AND (oferta_fim IS NULL OR oferta_fim = '' OR oferta_fim > ?)
    """, (agora,))
    res = [dict(row) for row in cur.fetchall()]
    conn.close()
    return res

def get_produto_por_id(id_prod):
    conn = create_connection()
    if not conn: return None
    cur = conn.cursor()
    cur.execute("SELECT * FROM produtos WHERE id = ?", (str(id_prod),))
    res = cur.fetchone()
    conn.close()
    return dict(res) if res else None

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    cur = conn.cursor()
    id_prod = dados.get('id') or str(int(datetime.datetime.now().timestamp()))[-8:]
    def clean_f(val): return float(str(val).replace(',', '.')) if val else 0.0
    
    cur.execute("""
        INSERT OR REPLACE INTO produtos (
            id, nome, categoria, preco, descricao, img_path_1, img_path_2, 
            img_path_3, img_path_4, video_path, em_oferta, 
            novo_preco, oferta_fim, desconto_pix, estoque,
            frete_gratis_valor, prazo_entrega, tempo_preparo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_prod, dados.get('nome'), dados.get('categoria'), clean_f(dados.get('preco')),
        dados.get('descricao'), dados.get('img_path_1'), dados.get('img_path_2'),
        dados.get('img_path_3'), dados.get('img_path_4'), dados.get('video_path'),
        1 if dados.get('em_oferta') else 0, clean_f(dados.get('novo_preco')), 
        dados.get('oferta_fim'), int(dados.get('desconto_pix') or 0),
        int(dados.get('estoque') or 0), clean_f(dados.get('frete_gratis_valor')),
        dados.get('prazo_entrega'), dados.get('tempo_preparo')
    ))
    conn.commit()
    conn.close()
    return id_prod

def excluir_produto(id_prod):
    conn = create_connection()
    if not conn: return
    cur = conn.cursor()
    cur.execute("DELETE FROM produtos WHERE id = ?", (id_prod,))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE CLIENTES ---

def salvar_novo_cliente(dados):
    conn = create_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        senha_hash = generate_password_hash(dados['senha'])
        cur.execute('''
            INSERT INTO clientes (nome, cpf, email, telefone, senha)
            VALUES (?, ?, ?, ?, ?)
        ''', (dados['nome'], dados['cpf'], dados['email'], dados['telefone'], senha_hash))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao salvar cliente: {e}")
        return False
    finally:
        conn.close()

def verificar_login_cliente(email, senha):
    conn = create_connection()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nome, email, senha FROM clientes WHERE email = ?", (email,))
        cliente = cur.fetchone()
        if cliente and check_password_hash(cliente['senha'], senha):
            return dict(cliente)
        return None
    finally:
        conn.close()

def atualizar_senha_cliente(id_cliente, nova_senha):
    conn = create_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        senha_hash = generate_password_hash(nova_senha)
        cur.execute("UPDATE clientes SET senha = ? WHERE id = ?", (senha_hash, id_cliente))
        conn.commit()
        return True
    finally:
        conn.close()

def get_clientes():
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute('SELECT id, nome, email, cpf, telefone, data_cadastro FROM clientes ORDER BY data_cadastro DESC')
    res = [dict(row) for row in cur.fetchall()]
    conn.close()
    return res

# --- CONFIGURAÇÕES GERAIS ---

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    cur = conn.cursor()
    cur.execute("SELECT chave, valor FROM configuracoes")
    res = cur.fetchall()
    config = {row['chave']: row['valor'] for row in res}
    conn.close()
    return config

def update_configuracao(chave, valor):
    conn = create_connection()
    if not conn: return
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()

def registrar_venda(nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total):
    conn = create_connection()
    if not conn: return None
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO vendas (nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total, 'pendente'))
    venda_id = cur.lastrowid
    conn.commit()
    conn.close()
    return venda_id

def get_vendas():
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendas ORDER BY id DESC")
    res = [dict(row) for row in cur.fetchall()]
    conn.close()
    return res

def is_valid_login(user, pwd):
    conn = create_connection()
    if not conn: return None
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (user,))
    res = cur.fetchone()
    conn.close()
    if res and check_password_hash(res['password_hash'], pwd):
        return dict(res)
    return None
