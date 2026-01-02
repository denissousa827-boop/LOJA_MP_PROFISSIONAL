import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração da URL do Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL não definida!")
        return None
    try:
        # Adicionado sslmode obrigatório para Vercel
        return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)
    except Exception as e:
        print(f"Erro de conexão Supabase: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cursor:
                # 1. Tabela de Produtos com TODAS as colunas que o seu site usa
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
                # 2. Tabelas de Suporte
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
                # 3. Admin Padrão
                cursor.execute("""
                    INSERT INTO users (username, password_hash) 
                    VALUES (%s, %s) 
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", generate_password_hash("675201")))
        print("✅ Banco de Dados Inicializado com todas as colunas!")
    except Exception as e:
        print(f"Erro no init_db: {e}")
    finally:
        conn.close()

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Busca TODAS as colunas para não quebrar o HTML
            cur.execute("SELECT * FROM produtos ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return []
    finally:
        conn.close()

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
        conn.close()

def add_or_update_produto(dados):
    conn = create_connection()
    if not conn: return
    try:
        id_prod = str(dados.get('id')) if dados.get('id') else str(int(datetime.datetime.now().timestamp()))[-8:]
        def to_f(v):
            try: return float(str(v).replace(',', '.'))
            except: return 0.0

        with conn:
            with conn.cursor() as cursor:
                # SQL Completo com 17 colunas para bater com a estrutura da tabela
                sql = """
                    INSERT INTO produtos (
                        id, nome, preco, descricao, img_path_1, img_path_2, img_path_3, img_path_4,
                        video_path, em_oferta, novo_preco, oferta_fim, desconto_pix, estoque,
                        frete_gratis_valor, prazo_entrega, tempo_preparo
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    nome=EXCLUDED.nome, preco=EXCLUDED.preco, descricao=EXCLUDED.descricao,
                    img_path_1=EXCLUDED.img_path_1, img_path_2=EXCLUDED.img_path_2, 
                    img_path_3=EXCLUDED.img_path_3, img_path_4=EXCLUDED.img_path_4,
                    video_path=EXCLUDED.video_path, em_oferta=EXCLUDED.em_oferta, 
                    novo_preco=EXCLUDED.novo_preco, oferta_fim=EXCLUDED.oferta_fim,
                    desconto_pix=EXCLUDED.desconto_pix, estoque=EXCLUDED.estoque,
                    frete_gratis_valor=EXCLUDED.frete_gratis_valor, 
                    prazo_entrega=EXCLUDED.prazo_entrega, tempo_preparo=EXCLUDED.tempo_preparo
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

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {row['chave']: row['valor'] for row in cur.fetchall()}
    except:
        return {}
    finally:
        conn.close()

def save_configuracoes(config_dict):
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                for chave, valor in config_dict.items():
                    cur.execute("""
                        INSERT INTO configuracoes (chave, valor) VALUES (%s, %s)
                        ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
                    """, (chave, str(valor)))
    finally:
        conn.close()

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
        conn.close()
    return None

if __name__ == '__main__':
    init_db()
