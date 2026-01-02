import os
import psycopg2
import datetime
import uuid
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client

# Configurações vindas da Vercel
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Corrige o protocolo para o SQLAlchemy/Psycopg2
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cliente para salvar fotos na nuvem
supabase_storage = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_storage = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_connection():
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=15)
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

def upload_imagem_supabase(file):
    """Envia arquivo para o Bucket 'produtos' e retorna link público"""
    if not supabase_storage or not file:
        return None
    try:
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file.seek(0)
        content = file.read()
        
        # Envia para o bucket 'produtos' (Você deve criar ele no Supabase)
        supabase_storage.storage.from_("produtos").upload(filename, content, {"content-type": file.content_type})
        return supabase_storage.storage.from_("produtos").get_public_url(filename)
    except Exception as e:
        print(f"Erro no upload: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn: return "Erro de conexão"
    try:
        with conn:
            with conn.cursor() as cur:
                # Criação das tabelas profissionais
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS produtos (
                        id TEXT PRIMARY KEY, nome TEXT NOT NULL, preco FLOAT NOT NULL,
                        descricao TEXT, img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
                        video_path TEXT, em_oferta INTEGER DEFAULT 0, novo_preco FLOAT,
                        oferta_fim TEXT, desconto_pix INTEGER DEFAULT 0, estoque INTEGER DEFAULT 0,
                        frete_gratis_valor FLOAT DEFAULT 0.0, prazo_entrega TEXT, tempo_preparo TEXT
                    )
                """)
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)")
                cur.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)")
                cur.execute("CREATE TABLE IF NOT EXISTS vendas (id SERIAL PRIMARY KEY, data TEXT, nome_cliente TEXT, valor_total FLOAT)")
                
                # Garante seu acesso admin
                pw_hash = generate_password_hash("675201")
                cur.execute("""
                    INSERT INTO users (username, password_hash) VALUES (%s, %s)
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", pw_hash))
        return "✅ Tudo pronto! Banco sincronizado."
    finally:
        conn.close()

# --- Funções de consulta ---
def get_produtos():
    conn = create_connection()
    if not conn: return []
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM produtos ORDER BY id DESC")
        return cur.fetchall()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT chave, valor FROM configuracoes")
        return {r['chave']: r['valor'] for r in cur.fetchall()}

def is_valid_login(user, password):
    conn = create_connection()
    if not conn: return None
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM users WHERE username=%s", (user,))
        u = cur.fetchone()
        if u and check_password_hash(u['password_hash'], password):
            return u
    return None
