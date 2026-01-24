import os
import requests

def calcular_frete(cep_destino, preco_produto):
    """
    Calcula o frete usando a API do Melhor Envio.
    Configurado para ambiente local/servidor próprio (Sem Vercel/Supabase).
    """
    # 1. Configurações de Token e Origem
    # Tenta pegar do sistema, se não existir, usa o valor fixo (substitua o SEU_TOKEN_AQUI)
    token = os.getenv('MELHOR_ENVIO_TOKEN', 'SEU_TOKEN_REAL_AQUI')
    cep_origem = os.getenv('CEP_ORIGEM', '04866220') 

    if not token or token == 'SEU_TOKEN_REAL_AQUI':
        print("AVISO: Token do Melhor Envio não configurado corretamente.")
        return []

    # 2. Endereço da API (Produção)
    url = "https://www.melhorenvio.com.br/api/v2/me/shipment/calculate"
    
    # 3. Limpeza e Tratamento de Dados
    # Garante que o CEP tenha apenas números e o preço seja float
    cep_destino = "".join(filter(str.isdigit, str(cep_destino)))
    cep_origem = "".join(filter(str.isdigit, str(cep_origem)))

    try:
        # Garante que o valor do seguro não seja menor que o mínimo aceito pela API
        valor_seguro = float(preco_produto)
        if valor_seguro < 0.1:
            valor_seguro = 0.1
    except (ValueError, TypeError):
        valor_seguro = 10.0 # Valor padrão caso falhe

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "LojaLocal (contato@sualoja.com.br)"
    }

    # 4. Payload (Estrutura de dimensões para cálculo)
    payload = {
        "from": {"postal_code": cep_origem},
        "to": {"postal_code": cep_destino},
        "products": [
            {
                "id": "item_venda",
                "width": 11,
                "height": 11,
                "length": 16,
                "weight": 0.5,
                "insurance_value": valor_seguro,
                "quantity": 1
            }
        ]
    }

    try:
        # Timeout adicionado para evitar que o servidor trave se a API estiver lenta
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            opcoes = response.json()
            validas = []
            
            for opt in opcoes:
                # Verifica se a transportadora retornou preço e não tem erro
                if "error" not in opt and "price" in opt:
                    try:
                        # O segredo da soma correta está em converter para float aqui
                        preco_frete = float(opt.get("price"))
                        
                        validas.append({
                            "id": opt.get("id"),
                            "nome": opt.get("name"),
                            "empresa": opt.get("company", {}).get("name"),
                            "preco": preco_frete,
                            "prazo": opt.get("delivery_range", {}).get("max") or opt.get("delivery_time"),
                            "logo": opt.get("company", {}).get("picture")
                        })
                    except (ValueError, TypeError):
                        continue
            
            # Ordena do mais barato para o mais caro
            return sorted(validas, key=lambda x: x['preco'])
        
        else:
            print(f"Erro API Melhor Envio: {response.status_code} - {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"Erro de Conexão com Melhor Envio: {e}")
        return []
