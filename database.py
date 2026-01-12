import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env localmente
load_dotenv()

# Configuração seguindo o padrão Vite/Supabase que definimos
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Correção automática para o protocolo do SQLAlchemy/Postgres
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    """Cria a conexão com o PostgreSQL do Supabase com SSL obrigatório"""
    if not DATABASE_URL:
        # Resolve o erro visualizado nos logs do Termux
        print("ERRO: DATABASE_URL não configurada.")
        return None
    try:
        # sslmode='require' permite a conexão externa com o Supabase
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Erro de conexão ao banco: {e}")
        return None

def init_db():
    """Inicializa as tabelas profissionais no Supabase e cria o Admin"""
    conn = create_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        
        # Tabela de Usuários/Admin
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        # Tabela de Produtos (Estrutura Completa)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                preco FLOAT NOT NULL,
                descricao TEXT,
                img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
                video_path TEXT,
                em_oferta INTEGER DEFAULT 0,
                novo_preco FLOAT,
                oferta_fim TEXT,
                estoque INTEGER DEFAULT 0
            )
        """)

        # Criar Admin Padrão
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
        print("✅ Supabase sincronizado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar tabelas: {e}")

# --- FUNÇÕES ORIGINAIS ADAPTADAS ---

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
            em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, estoque=EXCLUDED.estoque,
            img_path_1=EXCLUDED.img_path_1, img_path_2=EXCLUDED.img_path_2
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
        print(f"Erro ao salvar produto no Supabase: {e}")

def is_valid_login(user, pwd):
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
