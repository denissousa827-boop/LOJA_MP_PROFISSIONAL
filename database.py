import os
from supabase import create_client, Client

# Configurações do Supabase via Variáveis de Ambiente
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use a Service Role para acesso Admin
supabase: Client = create_client(url, key)

# --- FUNÇÕES DE CONFIGURAÇÃO ---

def get_configuracoes():
    """Busca todas as chaves e valores da tabela configuracoes e transforma em dicionário."""
    try:
        response = supabase.table('configuracoes').select("*").execute()
        # Transforma [{chave: 'cor', valor: '#000'}, ...] em {'cor': '#000'}
        return {item['chave']: item['valor'] for item in response.data}
    except Exception as e:
        print(f"Erro ao buscar configurações: {e}")
        return {}

def update_configuracao(chave, valor):
    """Atualiza ou insere uma configuração (UPSERT)."""
    try:
        supabase.table('configuracoes').upsert({'chave': chave, 'valor': valor}).execute()
        return True
    except Exception as e:
        print(f"Erro ao salvar {chave}: {e}")
        return False

# --- FUNÇÕES DE PRODUTOS ---

def get_produtos():
    """Retorna todos os produtos do catálogo."""
    response = supabase.table('produtos').select("*").order('criado_em', desc=True).execute()
    return response.data

def get_produto_por_id(id_produto):
    """Busca um produto específico pelo ID."""
    response = supabase.table('produtos').select("*").eq('id', id_produto).maybe_single().execute()
    return response.data

def add_or_update_produto(dados):
    """Adiciona ou atualiza um produto no Supabase."""
    return supabase.table('produtos').upsert(dados).execute()

# --- AUTENTICAÇÃO ---

def is_valid_login(email, password):
    """
    Valida o login usando o Supabase Auth.
    Se o login for bem-sucedido, retorna os dados do usuário.
    """
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return {"email": res.user.email, "id": res.user.id}
    except Exception as e:
        print(f"Erro na autenticação: {e}")
    return None

# --- STORAGE (UPLOAD DE IMAGENS) ---

def upload_imagem_supabase(file):
    """Faz o upload da imagem para o bucket 'produtos' e retorna a URL pública."""
    try:
        file_path = f"uploads/{file.filename}"
        # Lê o conteúdo do arquivo
        file_content = file.read()
        
        # Upload para o bucket 'produtos'
        supabase.storage.from_('produtos').upload(file_path, file_content, {"content-type": "image/jpeg"})
        
        # Gera a URL pública
        url_res = supabase.storage.from_('produtos').get_public_url(file_path)
        return url_res
    except Exception as e:
        print(f"Erro no upload: {e}")
        return None
