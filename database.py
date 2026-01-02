import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração da URL do Banco de Dados (Supabase com porta 6543)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_connection():
    """Cria a conexão estável para Vercel usando o Pooler (Porta 6543)"""
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL não encontrada.")
        return None
    try:
        # Adicionamos sslmode e pgbouncer=true na conexão
        conn = psycopg2.connect(
            DATABASE_URL, 
            sslmode='require',
            connect_timeout=10
        )
        return conn
    except Exception as e:
        print(f"Erro de conexão no Supabase: {e}")
        return None

def init_db():
    """Inicializa as tabelas e garante o admin configurado"""
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cursor:
                # Criação das Tabelas (Estrutura idêntica à que você usa)
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
                
                # Garante que o usuário admin tenha a senha que você definiu
                admin_user = "utbdenis6752"
                admin_pass = "675201"
                cursor.execute("""
                    INSERT INTO users (username, password_hash) 
                    VALUES (%s, %s) 
                    ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, (admin_user, generate_password_hash(admin_pass)))
        print("✅ Banco de Dados sincronizado com Sucesso (Porta 6543)!")
    except Exception as e:
        print(f"Erro ao inicializar: {e}")
    finally:
        if conn: conn.close()

# ... (restante das suas funções get_produtos, add_produto, etc.)
