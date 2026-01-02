import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

# 1. AJUSTE DE CONEXÃO: Suporte a Pooler (Porta 6543)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    """Cria a conexão com SSL e Timeout aumentado para evitar quedas na Vercel"""
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL não configurada na Vercel.")
        return None
    try:
        # Aumentamos o connect_timeout para 10 e forçamos o SSL
        conn = psycopg2.connect(
            DATABASE_URL, 
            sslmode='require', 
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        return conn
    except Exception as e:
        print(f"Erro de conexão no Supabase: {e}")
        return None

def init_db():
    """Inicializa as tabelas e garante o admin"""
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
                        id SERIAL PRIMARY KEY,
                        data TEXT,
                        nome_cliente TEXT,
                        email_cliente TEXT,
                        whatsapp_cliente TEXT,
                        produto_nome TEXT,
                        quantidade INTEGER,
                        valor_total FLOAT,
                        status TEXT DEFAULT 'pendente'
                    )
                """)
                
                admin_user = "utbdenis6752"
                admin_pass = "675201"
                # Usamos ON CONFLICT para garantir que o admin sempre tenha a senha correta
                cursor.execute("""
                    INSERT INTO users (username, password_hash) 
                    VALUES (%s, %s) 
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, (admin_user, generate_password_hash(admin_pass)))
        print("✅ Tabelas sincronizadas com Supabase!")
    except Exception as e:
        print(f"Erro no init_db: {e}")
    finally:
        conn.close()

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]
    finally:
        if conn: conn.close()

def get_produto_por_id(id_produto):
    if not id_produto: return None
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id=%s", (str(id_produto),))
            res = cur.fetchone()
            return dict(res) if res else None
    finally:
        if conn: conn.close()

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn: return []
    try:
        agora = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE em_oferta = 1 AND (oferta_fim IS NULL OR oferta_fim > %s) ORDER BY id DESC", (agora,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        if conn: conn.close()

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
                    em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, estoque=EXCLUDED.estoque,
                    frete_gratis_valor=EXCLUDED.frete_gratis_valor, prazo_entrega=EXCLUDED.prazo_entrega,
                    img_path_1=COALESCE(EXCLUDED.img_path_1, produtos.img_path_1),
                    img_path_2=COALESCE(EXCLUDED.img_path_2, produtos.img_path_2),
                    img_path_3=COALESCE(EXCLUDED.img_path_3, produtos.img_path_3),
                    img_path_4=COALESCE(EXCLUDED.img_path_4, produtos.img_path_4)
                """
                cursor.execute(sql, (
                    id_prod, dados.get('nome'), to_f(dados.get('preco')), dados.get('descricao'),
                    dados.get('img_path_1'), dados.get('img_path_2'), dados.get('img_path_3'), dados.get('img_path_4'),
                    dados.get('video_path'), 1 if dados.get('em_oferta') else 0, to_f(dados.get('novo_preco')),
                    dados.get('oferta_fim'), int(dados.get('desconto_pix', 0)), int(dados.get('estoque', 0)),
                    to_f(dados.get('frete_gratis_valor')), dados.get('prazo_entrega'), dados.get('tempo_preparo')
                ))
    finally:
        if conn: conn.close()

# --- VENDAS E CONFIGS ---

def registrar_venda(nome, email, whats, prod, qtd, total):
    conn = create_connection()
    if not conn: return 0
    try:
        with conn:
            with conn.cursor() as cur:
                data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                cur.execute("""INSERT INTO vendas (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total)
                               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                            (data, nome, email, whats, prod, qtd, total))
                return cur.fetchone()[0]
    finally:
        if conn: conn.close()

def get_vendas():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vendas ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]
    finally:
        if conn: conn.close()

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {row['chave']: row['valor'] for row in cur.fetchall()}
    finally:
        if conn: conn.close()

# 2. ADICIONADA FUNÇÃO DE UPDATE (IMPORTANTE PARA O PAINEL FUNCIONAR)
def update_configuracao(chave, valor):
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO configuracoes (chave, valor) 
                    VALUES (%s, %s) 
                    ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
                """, (chave, str(valor)))
    finally:
        if conn: conn.close()

def is_valid_login(user, password):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (user,))
            u = cur.fetchone()
            if u and check_password_hash(u['password_hash'], password):
                return dict(u)
    finally:
        if conn: conn.close()
    return None

if __name__ == '__main__':
    init_db()
