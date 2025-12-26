import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração do Banco de Dados
DB_NAME = 'loja.db'

def create_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = create_connection()
    cursor = conn.cursor()

    # Tabela de Produtos Atualizada com campos Profissionais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            descricao TEXT,
            img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
            video_path TEXT, 
            em_oferta INTEGER DEFAULT 0,
            novo_preco REAL, 
            oferta_fim TEXT,
            
            -- Novos Campos Estilo Mercado Livre
            desconto_pix INTEGER DEFAULT 0,
            estoque INTEGER DEFAULT 0,
            frete_gratis_valor REAL DEFAULT 0.0,
            prazo_entrega TEXT DEFAULT '5 a 15 dias úteis',
            tempo_preparo TEXT DEFAULT '1 a 2 dias'
        )
    """)

    # Tabelas Auxiliares
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)")

    # Tabela de Vendas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            nome_cliente TEXT,
            email_cliente TEXT,
            whatsapp_cliente TEXT,
            produto_nome TEXT,
            quantidade INTEGER,
            valor_total REAL,
            status TEXT DEFAULT 'pendente'
        )
    """)

    # Criar Admin Padrão
    admin_user = "utbdenis6752"
    admin_pass = "675201"
    cursor.execute("SELECT * FROM users WHERE username=?", (admin_user,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                       (admin_user, generate_password_hash(admin_pass)))

    conn.commit()
    # Executa a migração caso o banco já exista mas falte colunas
    migrar_banco(conn)
    conn.close()

def migrar_banco(conn):
    """ Adiciona novas colunas caso o banco já exista sem elas """
    cursor = conn.cursor()
    colunas_novas = [
        ('desconto_pix', 'INTEGER DEFAULT 0'),
        ('estoque', 'INTEGER DEFAULT 0'),
        ('frete_gratis_valor', 'REAL DEFAULT 0.0'),
        ('prazo_entrega', 'TEXT DEFAULT "7 e 12/jan"'),
        ('tempo_preparo', 'TEXT DEFAULT "1 a 2 dias"')
    ]
    
    for nome_col, tipo in colunas_novas:
        try:
            cursor.execute(f"ALTER TABLE produtos ADD COLUMN {nome_col} {tipo}")
        except sqlite3.OperationalError:
            pass # Coluna já existe
    conn.commit()

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    conn = create_connection()
    produtos = conn.execute("SELECT * FROM produtos ORDER BY rowid DESC").fetchall()
    conn.close()
    return [dict(p) for p in produtos]

def get_produto_por_id(id_produto):
    if not id_produto: return None
    conn = create_connection()
    produto = conn.execute("SELECT * FROM produtos WHERE id=?", (str(id_produto),)).fetchone()
    conn.close()
    return dict(produto) if produto else None

def get_produtos_em_oferta():
    conn = create_connection()
    agora = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    sql = "SELECT * FROM produtos WHERE em_oferta = 1 AND (oferta_fim IS NULL OR oferta_fim > ?) ORDER BY rowid DESC"
    produtos = conn.execute(sql, (agora,)).fetchall()
    conn.close()
    return [dict(p) for p in produtos]

def add_or_update_produto(dados):
    conn = create_connection()
    cursor = conn.cursor()

    id_prod = dados.get('id')
    if not id_prod:
        id_prod = str(int(datetime.datetime.now().timestamp()))[-8:]

    atual = get_produto_por_id(id_prod) or {}

    sql = """INSERT OR REPLACE INTO produtos
             (id, nome, preco, descricao, img_path_1, img_path_2, img_path_3, img_path_4,
              video_path, em_oferta, novo_preco, oferta_fim, 
              desconto_pix, estoque, frete_gratis_valor, prazo_entrega, tempo_preparo)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    try:
        preco = float(str(dados.get('preco', 0)).replace(',', '.'))
        novo_preco = float(str(dados.get('novo_preco', 0)).replace(',', '.')) if dados.get('novo_preco') else None
        frete_gratis = float(str(dados.get('frete_gratis_valor', 0)).replace(',', '.'))
    except:
        preco, novo_preco, frete_gratis = 0.0, None, 0.0

    cursor.execute(sql, (
        id_prod,
        dados.get('nome'),
        preco,
        dados.get('descricao'),
        dados.get('img_path_1') or atual.get('img_path_1'),
        dados.get('img_path_2') or atual.get('img_path_2'),
        dados.get('img_path_3') or atual.get('img_path_3'),
        dados.get('img_path_4') or atual.get('img_path_4'),
        dados.get('video_path') or atual.get('video_path'),
        1 if dados.get('em_oferta') else 0,
        novo_preco,
        dados.get('oferta_fim'),
        int(dados.get('desconto_pix', 0)),
        int(dados.get('estoque', 0)),
        frete_gratis,
        dados.get('prazo_entrega', '7 e 12/jan'),
        dados.get('tempo_preparo', '1 a 2 dias')
    ))
    conn.commit()
    conn.close()

def delete_produto(id_produto):
    conn = create_connection()
    conn.execute("DELETE FROM produtos WHERE id=?", (id_produto,))
    conn.commit()
    conn.close()

# --- VENDAS E CONFIGS ---

def registrar_venda(nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total):
    conn = create_connection()
    cursor = conn.cursor()
    data_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor.execute('''INSERT INTO vendas (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (data_atual, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total))
    id_venda = cursor.lastrowid
    conn.commit()
    conn.close()
    return id_venda

def get_vendas():
    conn = create_connection()
    vendas = conn.execute("SELECT * FROM vendas ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(v) for v in vendas]

def get_configuracoes():
    conn = create_connection()
    try:
        config_list = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
        config_dict = {item['chave']: item['valor'] for item in config_list}
    except:
        config_dict = {}
    conn.close()
    return config_dict

def update_configuracao(chave, valor):
    conn = create_connection()
    conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, str(valor)))
    conn.commit()
    conn.close()

def is_valid_login(username, password):
    conn = create_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

if __name__ == '__main__':
    init_db()
