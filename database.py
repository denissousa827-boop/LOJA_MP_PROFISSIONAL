import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração da URL do Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    """Cria a conexão com o PostgreSQL do Supabase"""
    if not DATABASE_URL:
        print("ERRO: Variável DATABASE_URL não encontrada no sistema.")
        return None
    try:
        # sslmode='require' é obrigatório para conexões externas ao Supabase
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

def init_db():
    """Garante que o admin exista e as tabelas estejam prontas"""
    conn = create_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        # Garante o admin padrão com senha criptografada para o login funcionar
        admin_user = "utbdenis6752"
        admin_pass = "675201"
        pw_hash = generate_password_hash(admin_pass)
        
        cur.execute("""
            INSERT INTO users (username, password_hash) 
            VALUES (%s, %s) 
            ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
        """, (admin_user, pw_hash))
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Banco de dados sincronizado!")
    except Exception as e:
        print(f"Erro no init_db: {e}")

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM produtos ORDER BY id DESC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in res]

def get_produto_por_id(id_prod):
    conn = create_connection()
    if not conn: return None
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM produtos WHERE id = %s", (str(id_prod),))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return dict(res) if res else None

def get_produtos_em_oferta():
    """Resolve o erro AttributeError: 'get_produtos_em_oferta'"""
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    agora = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    cur.execute("""
        SELECT * FROM produtos 
        WHERE em_oferta = 1 
        AND (oferta_fim IS NULL OR oferta_fim = '' OR oferta_fim > %s)
    """, (agora,))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in res]

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        id_prod = dados.get('id') or str(int(datetime.datetime.now().timestamp()))[-8:]
        sql = """
            INSERT INTO produtos (id, nome, preco, descricao, img_path_1, img_path_2, 
                                img_path_3, img_path_4, video_path, em_oferta, 
                                novo_preco, oferta_fim, estoque)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
            em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, estoque=EXCLUDED.estoque
        """
        cur.execute(sql, (
            id_prod, dados.get('nome'), float(str(dados.get('preco')).replace(',', '.')),
            dados.get('descricao'), dados.get('img_path_1'), dados.get('img_path_2'),
            dados.get('img_path_3'), dados.get('img_path_4'), dados.get('video_path'),
            1 if dados.get('em_oferta') else 0, dados.get('novo_preco'), 
            dados.get('oferta_fim'), int(dados.get('estoque', 0))
        ))
        conn.commit()
        cur.close()
        conn.close()
        return id_prod
    except Exception as e:
        print(f"Erro ao salvar produto: {e}")

# --- FUNÇÕES DE VENDAS E CONFIGURAÇÕES ---

def get_vendas():
    """Resolve o erro AttributeError: 'get_vendas'"""
    conn = create_connection()
    if not conn: return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM vendas ORDER BY id DESC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in res]

def get_configuracoes():
    """Resolve o erro AttributeError: 'get_configuracoes'"""
    conn = create_connection()
    if not conn: return {}
    cur = conn.cursor()
    cur.execute("SELECT chave, valor FROM configuracoes")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0]: row[1] for row in res}

def is_valid_login(user, pwd):
    """Verifica o login comparando o hash da senha"""
    conn = create_connection()
    if not conn: return None
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE username = %s", (user,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    if res and check_password_hash(res['password_hash'], pwd):
        return dict(res)
    return None
