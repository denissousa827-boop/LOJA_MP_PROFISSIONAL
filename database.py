import os
import datetime
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# =============================
# CONFIGURAÇÃO DATABASE
# =============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL não configurada")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Pool seguro para Vercel
POOL = SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    dsn=DATABASE_URL,
    sslmode="require",
    connect_timeout=10
)

def get_conn():
    return POOL.getconn()

def release_conn(conn):
    POOL.putconn(conn)

# =============================
# INIT DB (EXECUTE APENAS 1 VEZ)
# =============================
def init_db():
    conn = get_conn()
    try:
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

            conn.commit()
            print("✅ Banco inicializado corretamente")
    finally:
        release_conn(conn)

# =============================
# PRODUTOS
# =============================
def get_produtos():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
            return cur.fetchall()
    finally:
        release_conn(conn)

def get_produto_por_id(produto_id):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id=%s", (produto_id,))
            return cur.fetchone()
    finally:
        release_conn(conn)

def salvar_produto(d):
    conn = get_conn()
    try:
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
                d.get("id") or str(int(datetime.datetime.now().timestamp())),
                d["nome"],
                d["preco"],
                d.get("descricao"),
                d.get("img_path_1"),
                d.get("img_path_2"),
                d.get("img_path_3"),
                d.get("img_path_4"),
                d.get("video_path"),
                d.get("em_oferta", False),
                d.get("novo_preco"),
                d.get("oferta_fim"),
                d.get("desconto_pix", 0),
                d.get("estoque", 0),
                d.get("frete_gratis_valor", 0),
                d.get("prazo_entrega"),
                d.get("tempo_preparo")
            ))
            conn.commit()
    finally:
        release_conn(conn)

# =============================
# CONFIGURAÇÕES
# =============================
def get_configuracoes():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM configuracoes")
            return {r["chave"]: r["valor"] for r in cur.fetchall()}
    finally:
        release_conn(conn)

def salvar_configuracoes(cfg):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for k, v in cfg.items():
                cur.execute("""
                INSERT INTO configuracoes (chave, valor)
                VALUES (%s,%s)
                ON CONFLICT (chave) DO UPDATE SET valor=EXCLUDED.valor
                """, (k, str(v)))
            conn.commit()
    finally:
        release_conn(conn)

# =============================
# LOGIN
# =============================
def validar_login(usuario, senha):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (usuario,))
            u = cur.fetchone()
            if u and check_password_hash(u["password_hash"], senha):
                return u
            return None
    finally:
        release_conn(conn)
