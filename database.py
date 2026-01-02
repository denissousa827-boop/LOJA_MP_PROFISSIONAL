# ==================================================
# CONSULTAS (Essenciais para o main.py)
# ==================================================
def get_produtos():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos ORDER BY criado_em DESC")
            return cur.fetchall()
    finally: conn.close()

def get_produtos_em_oferta():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE em_oferta = TRUE ORDER BY criado_em DESC")
            return cur.fetchall()
    finally: conn.close()

def get_vendas():
    conn = create_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vendas ORDER BY data DESC")
            return cur.fetchall()
    finally: conn.close()

def is_valid_login(user, password):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (user,))
            u = cur.fetchone()
            if u and check_password_hash(u["password_hash"], password):
                return u
    finally: conn.close()
    return None

def get_configuracoes():
    conn = create_connection()
    if not conn: return {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor FROM configuracoes")
            return {r['chave']: r['valor'] for r in cur.fetchall()}
    finally: conn.close()

def get_produto_por_id(id_prod):
    conn = create_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id = %s", (id_prod,))
            return cur.fetchone()
    finally: conn.close()
