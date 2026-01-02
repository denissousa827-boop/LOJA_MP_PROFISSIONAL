import os
import datetime
import psycopg2
import uuid
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from werkzeug.utils import secure_filename

# ==================================================
# CONFIGURAÇÃO AMBIENTE (SUPABASE + VERCEL)
# ==================================================
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Inicializa Cliente de Storage
supabase_storage = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_storage = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "produtos"

def create_connection():
    """Conexão otimizada para Vercel Serverless"""
    try:
        return psycopg2.connect(
            DATABASE_URL, 
            sslmode="require", 
            connect_timeout=10
        )
    except Exception as e:
        print(f"[DB ERROR] Erro de conexão: {e}")
        return None

# ==================================================
# FUNÇÃO PARA UPLOAD DE IMAGENS
# ==================================================
def upload_imagem_supabase(file):
    """Faz upload e retorna a URL pública da imagem"""
    if not file or not file.filename or not supabase_storage:
        return None

    try:
        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4()}.{ext}"
        
        # Lê o conteúdo do arquivo
        file.seek(0)
        content = file.read()

        # Upload para o Bucket
        supabase_storage.storage.from_(BUCKET_NAME).upload(
            path=unique_name,
            file=content,
            file_options={"content-type": file.content_type}
        )

        # Retorna URL Pública
        return supabase_storage.storage.from_(BUCKET_NAME).get_public_url(unique_name)
    except Exception as e:
        print(f"[STORAGE ERROR] Falha no upload: {e}")
        return None

# ==================================================
# MANUTENÇÃO DE DADOS (SELECT / INSERT)
# ==================================================
def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                # Sua estrutura de tabelas original
                cur.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    preco NUMERIC(10,2) NOT NULL,
                    descricao TEXT,
                    img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
                    video_path TEXT, em_oferta BOOLEAN DEFAULT FALSE,
                    novo_preco NUMERIC(10,2), oferta_fim TIMESTAMP,
                    desconto_pix INTEGER DEFAULT 0, estoque INTEGER DEFAULT 0,
                    frete_gratis_valor NUMERIC(10,2) DEFAULT 0,
                    prazo_entrega TEXT DEFAULT '5 a 15 dias úteis',
                    tempo_preparo TEXT DEFAULT '1 a 2 dias',
                    criado_em TIMESTAMP DEFAULT NOW()
                );
                """)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                );
                """)
                # Admin padrão
                cur.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s) ON CONFLICT (username) DO NOTHING
                """, ("utbdenis6752", generate_password_hash("675201")))
        print("✅ Banco sincronizado")
    finally:
        conn.close()

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO produtos (
                    id, nome, preco, descricao, img_path_1, img_path_2, 
                    em_oferta, novo_preco, estoque
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
                    img_path_1=COALESCE(EXCLUDED.img_path_1, produtos.img_path_1),
                    img_path_2=COALESCE(EXCLUDED.img_path_2, produtos.img_path_2),
                    em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, 
                    estoque=EXCLUDED.estoque
                """, (
                    dados['id'], dados['nome'], dados['preco'], dados['descricao'],
                    dados.get('img1'), dados.get('img2'), dados['em_oferta'],
                    dados['novo_preco'], dados['estoque']
                ))
    finally:
        conn.close()

def save_configuracoes(configs: dict):
    conn = create_connection()
    if not conn: return False
    try:
        with conn:
            with conn.cursor() as cur:
                for chave, valor in configs.items():
                    cur.execute("""
                    INSERT INTO configuracoes (chave, valor) VALUES (%s, %s)
                    ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
                    """, (chave, str(valor)))
        return True
    except: return False
    finally: conn.close()
