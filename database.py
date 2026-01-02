import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = os.getenv("DATABASE_URL")

def create_connection():
    try:
        # Configuração para Pooler do Supabase (Porta 6543)
        return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=15)
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn:
        return "Erro: Não foi possível conectar ao banco. Verifique a DATABASE_URL na Vercel."
    try:
        with conn:
            with conn.cursor() as cur:
                # Criar Tabelas
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT);")
                cur.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT);")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS produtos (
                        id TEXT PRIMARY KEY, nome TEXT, preco NUMERIC, descricao TEXT,
                        img_path_1 TEXT, img_path_2 TEXT, em_oferta BOOLEAN DEFAULT FALSE,
                        novo_preco NUMERIC, estoque INTEGER, criado_em TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                # Resetar/Criar Admin com a senha correta
                hash_senha = generate_password_hash("675201")
                cur.execute("""
                    INSERT INTO users (username, password_hash) VALUES (%s, %s)
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", hash_senha))
        return "Sucesso: Banco sincronizado e Admin utbdenis6752 configurado!"
    except Exception as e:
        return f"Erro no Banco: {str(e)}"
    finally:
        if conn: conn.close()

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

# Funções GET para evitar erro na Homepage
def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
            return cur.fetchall()
    finally: 
        if conn: conn.close()

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE em_oferta = TRUE")
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
