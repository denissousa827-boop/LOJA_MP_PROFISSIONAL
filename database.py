import os
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# =============================
# DATABASE CONFIG
# =============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definida")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# =============================
# CONEXÃO SEGURA SERVERLESS
# =============================
def get_conn():
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5
    )

# =============================
# INIT DB (RODAR MANUALMENTE)
# =============================
def init_db():
    conn = get_conn()
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
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (username) DO NOTHING
                """, ("utbdenis6752", generate_password_hash("675201")))
    finally:
        conn.close()

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
        conn.close()

def get_produto_por_id(produto_id):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id=%s", (produto_id,))
            return cur.fetchone()
    finally:
        conn.close()

def salvar_produto(d):
    conn = get_conn()
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
    finally:
        conn.close()

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
        conn.close()
