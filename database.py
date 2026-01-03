import os
import datetime
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client

# --- CONFIGURAÇÕES DO AMBIENTE ---
# Estas devem estar configuradas na Vercel
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Use a SERVICE_ROLE_KEY para o backend ter permissão de admin
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

# Inicializa o Cliente Supabase para Auth e Storage
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_connection():
    """Conecta ao Postgres para dados da loja (vendas/produtos)"""
    if not DATABASE_URL:
        return None
    try:
        # Corrige a URL para o psycopg2
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url, sslmode='require')
    except Exception as e:
        print(f"Erro de conexão DB: {e}")
        return None

# --- VALIDAÇÃO DE LOGIN (SUPABASE AUTH) ---

def is_valid_login(email, password):
    """
    Tenta logar o usuário usando o e-mail e senha no Supabase Auth.
    Isso valida o usuário denissousa827@gmail.com que você criou.
    """
    try:
        # Tenta a autenticação oficial
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user:
            # Retorna um dicionário simulando o objeto de usuário para o restante do seu código
            return {
                "id": auth_response.user.id,
                "email": auth_response.user.email
            }
    except Exception as e:
        print(f"Erro na autenticação Supabase: {e}")
    return None

# --- FUNÇÕES DE VENDAS ---

def get_vendas():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vendas ORDER BY id DESC")
            return cur.fetchall()
    finally:
        conn.close()

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

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY id DESC")
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
                    INSERT INTO produtos (id, nome, preco, descricao, em_oferta, novo_preco, estoque)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
                    em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, estoque=EXCLUDED.estoque
                """
                cursor.execute(sql, (
                    id_prod, dados.get('nome'), to_f(dados.get('preco')), dados.get('descricao'),
                    1 if dados.get('em_oferta') else 0, to_f(dados.get('novo_preco')), int(dados.get('estoque', 0))
                ))
    finally:
        conn.close()
