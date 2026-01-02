import os
import psycopg2
import uuid
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from werkzeug.utils import secure_filename

# CONFIGURAÇÕES
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

supabase_storage = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_storage = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "produtos"

def create_connection():
    try:
        # Adicionado sslmode e timeout para estabilidade na Vercel
        return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)
    except Exception as e:
        print(f"Erro conexão: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                # Criar tabelas
                cur.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT);")
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT);")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS produtos (
                        id TEXT PRIMARY KEY, nome TEXT, preco NUMERIC, descricao TEXT,
                        img_path_1 TEXT, img_path_2 TEXT, em_oferta BOOLEAN DEFAULT FALSE,
                        novo_preco NUMERIC, estoque INTEGER, desconto_pix INTEGER,
                        frete_gratis_valor NUMERIC, prazo_entrega TEXT, tempo_preparo TEXT, criado_em TIMESTAMP DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS vendas (
                        id SERIAL PRIMARY KEY, data TIMESTAMP DEFAULT NOW(), nome_cliente TEXT,
                        email_cliente TEXT, whatsapp_cliente TEXT, produto_nome TEXT,
                        quantidade INTEGER, valor_total NUMERIC, status TEXT DEFAULT 'pendente'
                    );
                """)
                
                # RESET DE SENHA ADMIN (Força a senha 675201)
                hash_senha = generate_password_hash("675201")
                cur.execute("""
                    INSERT INTO users (username, password_hash) VALUES (%s, %s)
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", hash_senha))
        print("✅ Banco pronto para Vercel!")
    finally:
        conn.close()

def is_valid_login(user, password):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (user,))
            u = cur.fetchone()
            if u and check_password_hash(u["password_hash"], password):
                return u
    finally:
        conn.close()
    return None

# Funções de consulta simplificadas para evitar erros de cursor
def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
            return cur.fetchall()
    finally: conn.close()

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE em_oferta = TRUE")
            return cur.fetchall()
    finally: conn.close()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {r['chave']: r['valor'] for r in cur.fetchall()}
    finally: conn.close()

# ... (Mantenha suas funções de upload_imagem e registrar_venda)
