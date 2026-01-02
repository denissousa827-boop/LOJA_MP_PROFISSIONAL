import os
import psycopg2
import datetime
import uuid
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client

# Configurações do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cliente Supabase para Storage
supabase_storage = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_storage = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_connection():
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

# --- FUNÇÃO DE UPLOAD ---
def upload_imagem_supabase(file):
    if not supabase_storage or not file: return None
    try:
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file.seek(0)
        content = file.read()
        bucket = "produtos"
        supabase_storage.storage.from_(bucket).upload(filename, content, {"content-type": file.content_type})
        return supabase_storage.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        print(f"Erro upload: {e}")
        return None

# --- INICIALIZAÇÃO ---
def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                senha_hash = generate_password_hash("675201", method='pbkdf2:sha256')
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING", ("utbdenis6752", senha_hash))
    finally:
        conn.close()

# --- FUNÇÕES QUE O MAIN.PY PRECISA ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY id DESC")
            return cur.fetchall()
    finally:
        conn.close()

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn: return []
    try:
        agora = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Seleciona produtos onde em_oferta é 1 e a data final é maior que agora
            cur.execute("SELECT * FROM produtos WHERE em_oferta = 1 AND (oferta_fim IS NULL OR oferta_fim > %s) ORDER BY id DESC", (agora,))
            return cur.fetchall()
    finally:
        conn.close()

def get_produto_por_id(id_produto):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id = %s", (str(id_produto),))
            return cur.fetchone()
    finally:
        conn.close()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {r['chave']: r['valor'] for r in cur.fetchall()}
    finally:
        conn.close()

def is_valid_login(user, password):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (user,))
            u = cur.fetchone()
            if u and check_password_hash(u['password_hash'], password):
                return u
    finally:
        conn.close()
    return None

def registrar_venda(nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total):
    conn = create_connection()
    if not conn: return 0
    try:
        with conn:
            with conn.cursor() as cur:
                data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                cur.execute("""INSERT INTO vendas (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total)
                               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                            (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total))
                return cur.fetchone()[0]
    finally:
        conn.close()

def get_vendas():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vendas ORDER BY id DESC")
            return cur.fetchall()
    finally:
        conn.close()

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
