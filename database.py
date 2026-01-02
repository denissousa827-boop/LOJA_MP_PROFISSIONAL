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

# Correção da String de Conexão para Vercel
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

supabase_storage = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_storage = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_connection():
    try:
        # Configuração agressiva de timeout e SSL para Vercel não travar
        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require",
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        return conn
    except Exception as e:
        print(f"ERRO CRÍTICO CONEXÃO: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn:
        raise Exception("Não foi possível conectar ao Supabase. Verifique a DATABASE_URL na Vercel.")
    try:
        with conn:
            with conn.cursor() as cur:
                # Criar tabelas uma por uma
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT);")
                cur.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT);")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS produtos (
                        id TEXT PRIMARY KEY, nome TEXT, preco NUMERIC(10,2), descricao TEXT,
                        img_path_1 TEXT, img_path_2 TEXT, em_oferta BOOLEAN DEFAULT FALSE,
                        novo_preco NUMERIC(10,2), estoque INTEGER, criado_em TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                # Força a criação do admin
                hash_senha = generate_password_hash("675201")
                cur.execute("""
                    INSERT INTO users (username, password_hash) VALUES (%s, %s)
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", hash_senha))
        return "Banco de dados sincronizado com sucesso!"
    except Exception as e:
        return f"Erro ao criar tabelas: {str(e)}"
    finally:
        conn.close()

# Mantenha as outras funções (is_valid_login, get_produtos) sempre fechando a conexão
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
        if conn: conn.close()
    return None

# Funções GET básicas
def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
            return cur.fetchall()
    finally: 
        if conn: conn.close()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {r['chave']: r['valor'] for r in cur.fetchall()}
    finally: 
        if conn: conn.close()
