# ==================================================
# INICIALIZAÇÃO DO BANCO (init_db)
# ==================================================
def init_db():
    conn = create_connection()
    if not conn: return
    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Cria as tabelas necessárias
                cur.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id TEXT PRIMARY KEY, nome TEXT NOT NULL, preco NUMERIC(10,2) NOT NULL,
                    descricao TEXT, img_path_1 TEXT, img_path_2 TEXT, img_path_3 TEXT, img_path_4 TEXT,
                    video_path TEXT, em_oferta BOOLEAN DEFAULT FALSE, novo_preco NUMERIC(10,2),
                    oferta_fim TIMESTAMP, desconto_pix INTEGER DEFAULT 0, estoque INTEGER DEFAULT 0,
                    frete_gratis_valor NUMERIC(10,2) DEFAULT 0, prazo_entrega TEXT, tempo_preparo TEXT, criado_em TIMESTAMP DEFAULT NOW()
                );
                """)
                cur.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT);")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS vendas (
                    id SERIAL PRIMARY KEY, data TIMESTAMP DEFAULT NOW(), nome_cliente TEXT,
                    email_cliente TEXT, whatsapp_cliente TEXT, produto_nome TEXT,
                    quantidade INTEGER, valor_total NUMERIC(10,2), status TEXT DEFAULT 'pendente'
                );
                """)
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT);")
                
                # 2. FORÇA A ATUALIZAÇÃO DO ADMIN (Garante que a senha seja 675201)
                senha_nova = generate_password_hash("675201")
                cur.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, ("utbdenis6752", senha_nova))
                
        print("✅ Banco sincronizado e senha do admin atualizada!")
    except Exception as e:
        print(f"[INIT DB ERROR] {e}")
    finally:
        conn.close()
