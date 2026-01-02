import os
import psycopg2
import uuid
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client

# 1. Configurações (A Vercel vai ler estas variáveis)
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Corrige o erro comum de protocolo da Vercel
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cliente para salvar fotos na nuvem (Storage)
supabase_storage = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_storage = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_connection():
    """Cria conexão com o banco usando SSL obrigatório para Supabase"""
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def init_db():
    """Garante que o seu usuário Admin exista com a senha correta"""
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                # Se o usuário não existir, cria com senha 675201
                # Usamos um método de hash compatível (pbkdf2)
                senha_cripto = generate_password_hash("675201", method='pbkdf2:sha256')
                cur.execute("""
                    INSERT INTO users (username, password_hash) 
                    VALUES (%s, %s) 
                    ON CONFLICT (username) DO NOTHING
                """, ("utbdenis6752", senha_cripto))
    finally:
        conn.close()

def upload_imagem_supabase(file):
    """Envia a imagem para o balde 'produtos' no Supabase"""
    if not supabase_storage or not file:
        return None
    try:
        # Gera nome único para o arquivo
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        file.seek(0)
        content = file.read()
        
        # Envia para o bucket
        bucket = "produtos"
        supabase_storage.storage.from_(bucket).upload(filename, content, {"content-type": file.content_type})
        
        # Retorna o link que todo mundo pode ver na internet
        return supabase_storage.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        print(f"Erro no upload: {e}")
        return None

def is_valid_login(user, password):
    """Verifica se o login e senha estão corretos"""
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (user,))
            usuario = cur.fetchone()
            # Compara a senha digitada com a criptografada do banco
            if usuario and check_password_hash(usuario['password_hash'], password):
                return usuario
    finally:
        conn.close()
    return None

# Funções extras para o painel funcionar
def get_produtos():
    conn = create_connection()
    if not conn: return []
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
        return cur.fetchall()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT chave, valor FROM configuracoes")
        return {r['chave']: r['valor'] for r in cur.fetchall()}
