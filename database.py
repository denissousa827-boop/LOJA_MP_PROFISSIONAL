import os
import psycopg2
import uuid
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from werkzeug.utils import secure_filename

# ==================================================
# CONFIGURAÇÃO AMBIENTE
# ==================================================
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
        # Configuração vital para Vercel + Supabase
        return psycopg2.connect(
            DATABASE_URL, 
            sslmode="require", 
            connect_timeout=10
        )
    except Exception as e:
        print(f"[DB ERROR] Erro conexão: {e}")
        return None

# ==================================================
# INICIALIZAÇÃO E LOGIN
# ==================================================
def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT);")
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT);")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS produtos (
                        id TEXT PRIMARY KEY, nome TEXT, preco NUMERIC, descricao TEXT,
                        img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
                        video_path TEXT, em_oferta BOOLEAN DEFAULT FALSE,
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
                
                # Garante que o Admin utbdenis6752 tenha a senha 675201
                hash_senha = generate_password_hash("675201")
                cur.execute("""
                    INSERT INTO users (username, password_hash) VALUES (%s, %s)
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", hash_senha))
        print("✅ Banco pronto e Admin atualizado!")
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

# ==================================================
# CONSULTAS (GET)
# ==================================================
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
            cur.execute("SELECT * FROM produtos WHERE em_oferta = TRUE ORDER BY criado_em DESC")
            return cur.fetchall()
    finally: conn.close()

def get_produto_por_id(id_prod):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id = %s", (id_prod,))
            return cur.fetchone()
    finally: conn.close()

def get_vendas():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vendas ORDER BY data DESC")
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

# ==================================================
# AÇÕES (INSERT/UPDATE/UPLOAD)
# ==================================================
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
    finally: conn.close()

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO produtos (
                    id, nome, preco, descricao, img_path_1, img_path_2, 
                    em_oferta, novo_preco, estoque, desconto_pix, frete_gratis_valor, prazo_entrega, tempo_preparo
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
                    img_path_1=COALESCE(EXCLUDED.img_path_1, produtos.img_path_1),
                    img_path_2=COALESCE(EXCLUDED.img_path_2, produtos.img_path_2),
                    em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, 
                    estoque=EXCLUDED.estoque, desconto_pix=EXCLUDED.desconto_pix,
                    frete_gratis_valor=EXCLUDED.frete_gratis_valor, prazo_entrega=EXCLUDED.prazo_entrega,
                    tempo_preparo=EXCLUDED.tempo_preparo
                """, (
                    dados['id'], dados['nome'], dados['preco'], dados['descricao'],
                    dados.get('img_path_1'), dados.get('img_path_2'), dados['em_oferta'],
                    dados['novo_preco'], dados['estoque'], dados.get('desconto_pix', 0),
                    dados.get('frete_gratis_valor', 0), dados.get('prazo_entrega'), dados.get('tempo_preparo')
                ))
    finally: conn.close()

def registrar_venda(nome, email, whats, prod, qtd, total):
    conn = create_connection()
    if not conn: return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO vendas (nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """, (nome, email, whats, prod, qtd, total))
                return cur.fetchone()[0]
    finally: conn.close()

def upload_imagem_supabase(file):
    if not file or not file.filename or not supabase_storage:
        return None
    try:
        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4()}.{ext}"
        file.seek(0)
        content = file.read()
        supabase_storage.storage.from_(BUCKET_NAME).upload(
            path=unique_name, file=content, file_options={"content-type": file.content_type}
        )
        return supabase_storage.storage.from_(BUCKET_NAME).get_public_url(unique_name)
    except Exception as e:
        print(f"[STORAGE ERROR] {e}")
        return None
