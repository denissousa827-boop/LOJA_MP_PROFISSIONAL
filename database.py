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
    if not DATABASE_URL:
        return None
    try:
        # Conexão direta simplificada para evitar erros de timeout na Vercel
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cursor:
                # Criar tabelas básicas
                cursor.execute("""
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
                        desconto_pix INTEGER DEFAULT 0,
                        estoque INTEGER DEFAULT 0,
                        frete_gratis_valor FLOAT DEFAULT 0.0,
                        prazo_entrega TEXT DEFAULT '5 a 15 dias úteis',
                        tempo_preparo TEXT DEFAULT '1 a 2 dias'
                    )
                """)
                cursor.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)")
                
                # Criar admin padrão
                cursor.execute("""
                    INSERT INTO users (username, password_hash) 
                    VALUES (%s, %s) 
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", generate_password_hash("675201")))
    except Exception as e:
        print(f"Erro no init_db: {e}")
    finally:
        conn.close()

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]
    except:
        return []
    finally:
        conn.close()

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    try:
        # Se não tiver ID, gera um baseado no timestamp
        id_prod = str(dados.get('id')) if dados.get('id') else str(int(datetime.datetime.now().timestamp()))[-8:]
        
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO produtos (id, nome, preco, descricao, img_path_1, em_oferta, novo_preco, estoque)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
                    img_path_1=EXCLUDED.img_path_1, em_oferta=EXCLUDED.em_oferta, 
                    novo_preco=EXCLUDED.novo_preco, estoque=EXCLUDED.estoque
                """, (
                    id_prod, 
                    dados.get('nome'), 
                    float(str(dados.get('preco', 0)).replace(',', '.')),
                    dados.get('descricao'),
                    dados.get('img_path_1'),
                    1 if dados.get('em_oferta') else 0,
                    float(str(dados.get('novo_preco', 0)).replace(',', '.')),
                    int(dados.get('estoque', 0))
                ))
    except Exception as e:
        print(f"Erro ao salvar produto: {e}")
    finally:
        conn.close()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {row['chave']: row['valor'] for row in cur.fetchall()}
    except:
        return {}
    finally:
        conn.close()

def save_configuracoes(config_dict):
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                for chave, valor in config_dict.items():
                    cur.execute("""
                        INSERT INTO configuracoes (chave, valor) VALUES (%s, %s)
                        ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
                    """, (chave, str(valor)))
    finally:
        conn.close()

def is_valid_login(user, password):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (user,))
            u = cur.fetchone()
            if u and check_password_hash(u['password_hash'], password):
                return dict(u)
    except:
        return None
    finally:
        conn.close()
    return None
