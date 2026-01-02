import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client

# Configurações do Supabase
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Inicializa cliente Supabase para Storage (Imagens)
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

# --- FUNÇÃO NOVA: UPLOAD DE IMAGEM PARA O SUPABASE STORAGE ---
def upload_imagem_supabase(file):
    """Envia o arquivo para o Bucket 'produtos' e retorna a URL pública"""
    if not supabase_client or not file:
        return None
    
    try:
        # Gera um nome único para o arquivo não sobrescrever outros
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Lê o conteúdo do arquivo
        file.seek(0)
        file_content = file.read()
        
        # Envia para o bucket chamado 'produtos'
        # IMPORTANTE: Você deve criar esse bucket no painel do Supabase como 'Public'
        bucket_name = "produtos"
        supabase_client.storage.from_(bucket_name).upload(filename, file_content, {"content-type": file.content_type})
        
        # Retorna a URL pública do arquivo
        return supabase_client.storage.from_(bucket_name).get_public_url(filename)
    except Exception as e:
        print(f"Erro no upload Supabase: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cursor:
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vendas (
                        id SERIAL PRIMARY KEY, data TEXT, nome_cliente TEXT, email_cliente TEXT,
                        whatsapp_cliente TEXT, produto_nome TEXT, quantidade INTEGER,
                        valor_total FLOAT, status TEXT DEFAULT 'pendente'
                    )
                """)
                admin_user = "utbdenis6752"
                cursor.execute("SELECT * FROM users WHERE username=%s", (admin_user,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                                   (admin_user, generate_password_hash("675201")))
        print("✅ Banco e Tabelas prontos!")
    finally:
        conn.close()

# --- Mantenha as funções get_produtos, get_produto_por_id, registrar_venda etc. ---
# Elas já estão corretas no seu código original.

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    try:
        id_prod = dados.get('id') or str(int(datetime.datetime.now().timestamp()))[-8:]
        def to_f(v): return float(str(v).replace(',', '.')) if v else 0.0

        with conn:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO produtos (id, nome, preco, descricao, img_path_1, img_path_2, img_path_3, img_path_4,
                                        video_path, em_oferta, novo_preco, oferta_fim, desconto_pix, estoque,
                                        frete_gratis_valor, prazo_entrega, tempo_preparo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
                    img_path_1=COALESCE(EXCLUDED.img_path_1, produtos.img_path_1),
                    img_path_2=COALESCE(EXCLUDED.img_path_2, produtos.img_path_2),
                    img_path_3=COALESCE(EXCLUDED.img_path_3, produtos.img_path_3),
                    img_path_4=COALESCE(EXCLUDED.img_path_4, produtos.img_path_4),
                    video_path=COALESCE(EXCLUDED.video_path, produtos.video_path),
                    em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, estoque=EXCLUDED.estoque,
                    frete_gratis_valor=EXCLUDED.frete_gratis_valor, prazo_entrega=EXCLUDED.prazo_entrega
                """
                cursor.execute(sql, (
                    id_prod, dados.get('nome'), to_f(dados.get('preco')), dados.get('descricao'),
                    dados.get('img_path_1'), dados.get('img_path_2'), dados.get('img_path_3'), dados.get('img_path_4'),
                    dados.get('video_path'), 1 if dados.get('em_oferta') else 0, to_f(dados.get('novo_preco')),
                    dados.get('oferta_fim'), int(dados.get('desconto_pix', 0)), int(dados.get('estoque', 0)),
                    to_f(dados.get('frete_gratis_valor')), dados.get('prazo_entrega'), dados.get('tempo_preparo')
                ))
    finally:
        conn.close()

# (Mantenha o restante das funções get_vendas, get_configuracoes, is_valid_login iguaizinhas)
