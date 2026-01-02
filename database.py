import os
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# ==================================================
# CONFIGURAÇÃO DATABASE (SUPABASE + VERCEL)
# ==================================================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    """
    Conexão segura e compatível com Serverless (Vercel)
    """
    try:
        return psycopg2.connect(
            DATABASE_URL,
            sslmode="require",
            connect_timeout=5
        )
    except Exception as e:
        print(f"[DB ERROR] Falha ao conectar: {e}")
        return None

# ==================================================
# INIT DB (EXECUTAR APENAS UMA VEZ)
# ==================================================
def init_db():
    conn = create_connection()
    if not conn:
        return

    try:
        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    preco NUMERIC(10,2) NOT NULL,
                    descricao TEXT,
                    img_path_1 TEXT,
                    img_path_2 TEXT,
                    img_path_3 TEXT,
                    img_path_4 TEXT,
                    video_path TEXT,
                    em_oferta BOOLEAN DEFAULT FALSE,
                    novo_preco NUMERIC(10,2),
                    oferta_fim TIMESTAMP,
                    desconto_pix INTEGER DEFAULT 0,
                    estoque INTEGER DEFAULT 0,
                    frete_gratis_valor NUMERIC(10,2) DEFAULT 0,
                    prazo_entrega TEXT DEFAULT '5 a 15 dias úteis',
                    tempo_preparo TEXT DEFAULT '1 a 2 dias',
                    criado_em TIMESTAMP DEFAULT NOW()
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS vendas (
                    id SERIAL PRIMARY KEY,
                    data TIMESTAMP DEFAULT NOW(),
                    nome_cliente TEXT,
                    email_cliente TEXT,
                    whatsapp_cliente TEXT,
                    produto_nome TEXT,
                    quantidade INTEGER,
                    valor_total NUMERIC(10,2),
                    status TEXT DEFAULT 'pendente'
                );
                """)

                cur.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (username) DO NOTHING
                """, ("utbdenis6752", generate_password_hash("675201")))

        print("✅ Banco sincronizado com Supabase")

    except Exception as e:
        print(f"[INIT_DB ERROR] {e}")
    finally:
        conn.close()

# ==================================================
# PRODUTOS
# ==================================================
def get_produtos():
    conn = create_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
            return cur.fetchall()
    finally:
        conn.close()

def get_produto_por_id(id_produto):
    if not id_produto:
        return None

    conn = create_connection()
    if not conn:
        return None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id=%s", (str(id_produto),))
            return cur.fetchone()
    finally:
        conn.close()

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM produtos
                WHERE em_oferta = TRUE
                AND (oferta_fim IS NULL OR oferta_fim > NOW())
                ORDER BY criado_em DESC
            """)
            return cur.fetchall()
    finally:
        conn.close()

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn:
        return

    def to_decimal(v):
        try:
            return float(str(v).replace(",", "."))
        except:
            return 0

    produto_id = dados.get("id") or str(int(datetime.datetime.now().timestamp()))

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO produtos (
                    id, nome, preco, descricao,
                    img_path_1, img_path_2, img_path_3, img_path_4,
                    video_path, em_oferta, novo_preco, oferta_fim,
                    desconto_pix, estoque, frete_gratis_valor,
                    prazo_entrega, tempo_preparo
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome,
                    preco=EXCLUDED.preco,
                    descricao=EXCLUDED.descricao,
                    img_path_1=EXCLUDED.img_path_1,
                    img_path_2=EXCLUDED.img_path_2,
                    img_path_3=EXCLUDED.img_path_3,
                    img_path_4=EXCLUDED.img_path_4,
                    video_path=EXCLUDED.video_path,
                    em_oferta=EXCLUDED.em_oferta,
                    novo_preco=EXCLUDED.novo_preco,
                    oferta_fim=EXCLUDED.oferta_fim,
                    desconto_pix=EXCLUDED.desconto_pix,
                    estoque=EXCLUDED.estoque,
                    frete_gratis_valor=EXCLUDED.frete_gratis_valor,
                    prazo_entrega=EXCLUDED.prazo_entrega,
                    tempo_preparo=EXCLUDED.tempo_preparo
                """, (
                    produto_id,
                    dados.get("nome"),
                    to_decimal(dados.get("preco")),
                    dados.get("descricao"),
                    dados.get("img_path_1"),
                    dados.get("img_path_2"),
                    dados.get("img_path_3"),
                    dados.get("img_path_4"),
                    dados.get("video_path"),
                    bool(dados.get("em_oferta")),
                    to_decimal(dados.get("novo_preco")),
                    dados.get("oferta_fim"),
                    int(dados.get("desconto_pix", 0)),
                    int(dados.get("estoque", 0)),
                    to_decimal(dados.get("frete_gratis_valor")),
                    dados.get("prazo_entrega"),
                    dados.get("tempo_preparo")
                ))
    finally:
        conn.close()

# ==================================================
# VENDAS
# ==================================================
def registrar_venda(nome, email, whats, prod, qtd, total):
    conn = create_connection()
    if not conn:
        return 0

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO vendas (
                    nome_cliente, email_cliente, whatsapp_cliente,
                    produto_nome, quantidade, valor_total
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id
                """, (nome, email, whats, prod, qtd, total))
                return cur.fetchone()[0]
    finally:
        conn.close()

def get_vendas():
    conn = create_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vendas ORDER BY data DESC")
            return cur.fetchall()
    finally:
        conn.close()

# ==================================================
# CONFIGURAÇÕES & LOGIN
# ==================================================
def get_configuracoes():
    conn = create_connection()
    if not conn:
        return {}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM configuracoes")
            return {r["chave"]: r["valor"] for r in cur.fetchall()}
    finally:
        conn.close()

def is_valid_login(user, password):
    conn = create_connection()
    if not conn:
        return None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (user,))
            u = cur.fetchone()
            if u and check_password_hash(u["password_hash"], password):
                return u
    finally:
        conn.close()
    return None

if __name__ == "__main__":
    init_db()
