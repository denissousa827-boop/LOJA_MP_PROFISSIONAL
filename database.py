import os
import psycopg2
import datetime
import uuid
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client

# --- CONFIGURAÇÕES DO AMBIENTE ---
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
# IMPORTANTE: Na Vercel, use a SERVICE_ROLE_KEY para ter permissão total no admin
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

# Inicializa o cliente Supabase (Auth e Storage)
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Erro ao inicializar Supabase: {e}")

def create_connection():
    """Cria a conexão com o banco de dados do Supabase"""
    if not DATABASE_URL:
        return None
    try:
        # Corrige o prefixo para o psycopg2
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url, sslmode='require')
    except Exception as e:
        print(f"Erro de conexão DB: {e}")
        return None

# --- NOVO SISTEMA DE LOGIN (SUPABASE AUTH) ---

def is_valid_login(email, password):
    """Valida o login usando o e-mail (denissousa827@gmail.com) e senha"""
    if not supabase:
        return None
    try:
        # Autentica direto no Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if auth_response.user:
            return {
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
    except Exception as e:
        print(f"Erro no login Auth: {e}")
    return None

# --- FUNÇÃO DE UPLOAD DE IMAGENS (MANTIDA) ---

def upload_imagem_supabase(file):
    """Envia a foto para o bucket 'produtos' no Supabase"""
    if not supabase or not file: return None
    try:
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file.seek(0)
        content = file.read()
        bucket = "produtos"
        supabase.storage.from_(bucket).upload(filename, content, {"content-type": file.content_type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        print(f"Erro upload: {e}")
        return None

# --- FUNÇÕES DE CONSULTA (PRODUTOS) ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY id DESC")
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

# --- REGISTRO E CONSULTA DE VENDAS ---

def registrar_venda(nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total):
    conn = create_connection()
    if not conn: return 0
    try:
        with conn:
            with conn.cursor() as cur:
                data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                cur.execute("""
                    INSERT INTO vendas (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total))
                res = cur.fetchone()
                return res[0] if res else 0
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

# --- ADICIONAR OU ATUALIZAR PRODUTO (COMPLETO) ---

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
