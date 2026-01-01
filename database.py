import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração do Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    """Cria conexão segura com o Banco de Dados"""
    try:
        # Adicionado timeout e garantindo sslmode
        conn = psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=5)
        return conn
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

def init_db():
    """Inicializa as tabelas e o usuário admin"""
    conn = create_connection()
    if not conn:
        return
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
                    );
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY, 
                        username TEXT UNIQUE, 
                        password_hash TEXT
                    );
                    CREATE TABLE IF NOT EXISTS configuracoes (
                        chave TEXT PRIMARY KEY, 
                        valor TEXT
                    );
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
                    );
                """)
                
                # Usuário Admin Padrão
                admin_user = "utbdenis6752"
                admin_pass = "675201"
                cursor.execute("""
                    INSERT INTO users (username, password_hash) 
                    VALUES (%s, %s) 
                    ON CONFLICT (username) DO NOTHING
                """, (admin_user, generate_password_hash(admin_pass)))
    except Exception as e:
        print(f"Erro ao inicializar tabelas: {e}")
    finally:
        conn.close()

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM produtos ORDER BY id DESC")
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_produto_por_id(id_produto):
    if not id_produto: return None
    conn = create_connection()
    if not conn: return None
    try:
        with conn:
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
        # Sanitização de valores numéricos
        def to_float(val):
            try: return float(str(val).replace(',', '.')) if val else 0.0
            except: return 0.0

        id_prod = dados.get('id') or str(int(datetime.datetime.now().timestamp()))[-8:]
        
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
                    em_oferta=EXCLUDED.em_oferta, novo_preco=EXCLUDED.novo_preco, 
                    oferta_fim=EXCLUDED.oferta_fim, desconto_pix=EXCLUDED.desconto_pix, 
                    estoque=EXCLUDED.estoque, frete_gratis_valor=EXCLUDED.frete_gratis_valor,
                    prazo_entrega=EXCLUDED.prazo_entrega, tempo_preparo=EXCLUDED.tempo_preparo
                """
                cursor.execute(sql, (
                    id_prod, dados.get('nome'), to_float(dados.get('preco')),
                    dados.get('descricao'), dados.get('img_path_1'), dados.get('img_path_2'),
                    dados.get('img_path_3'), dados.get('img_path_4'), dados.get('video_path'),
                    1 if dados.get('em_oferta') else 0, to_float(dados.get('novo_preco')), dados.get('oferta_fim'),
                    int(dados.get('desconto_pix') or 0), int(dados.get('estoque') or 0),
                    to_float(dados.get('frete_gratis_valor')),
                    dados.get('prazo_entrega'), dados.get('tempo_preparo')
                ))
    except Exception as e:
        print(f"Erro ao salvar produto: {e}")
    finally:
        conn.close()

# --- FUNÇÕES DE VENDAS E CONFIG ---

def registrar_venda(nome, email, whats, prod, qtd, total):
    conn = create_connection()
    if not conn: return int(datetime.datetime.now().timestamp())
    try:
        with conn:
            with conn.cursor() as cur:
                data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                cur.execute("""
                    INSERT INTO vendas (data, nome_cliente, email_cliente, whatsapp_cliente, produto_nome, quantidade, valor_total) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (data, nome, email, whats, prod, qtd, total))
                return cur.fetchone()[0]
    except Exception as e:
        print(f"Erro ao registrar venda: {e}")
        return int(datetime.datetime.now().timestamp())
    finally:
        conn.close()

def get_configuracoes():
    configs = {'melhor_envio_token': os.getenv('MELHOR_ENVIO_TOKEN'), 'cep_origem': os.getenv('CEP_ORIGEM', '04866220')}
    conn = create_connection()
    if not conn: return configs
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT chave, valor FROM configuracoes")
                for row in cur.fetchall():
                    configs[row['chave']] = row['valor']
    finally:
        conn.close()
    return configs

def is_valid_login(user, pwd):
    conn = create_connection()
    if not conn: return None
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE username=%s", (user,))
                res = cur.fetchone()
                if res and check_password_hash(res['password_hash'], pwd):
                    return dict(res)
    finally:
        conn.close()
    return None
