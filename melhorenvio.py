import os
import requests

def calcular_frete(cep_destino, preco_produto):
    """
    Calcula o frete usando a API do Melhor Envio.
    Busca o Token e o CEP de origem das variáveis de ambiente da Vercel.
    """
    # Busca as configurações das variáveis de ambiente da Vercel
    token = os.getenv('MELHOR_ENVIO_TOKEN')
    
    # Se você não configurar o CEP_ORIGEM na Vercel, ele usará o seu padrão abaixo
    cep_origem = os.getenv('CEP_ORIGEM', '04866220')

    if not token:
        print("Erro: Token do Melhor Envio não encontrado nas variáveis da Vercel.")
        return []

    url = "https://www.melhorenvio.com.br/api/v2/me/shipment/calculate"
    
    # Limpeza de dados (garante que sejam apenas números)
    cep_destino = "".join(filter(str.isdigit, str(cep_destino)))
    cep_origem = "".join(filter(str.isdigit, str(cep_origem)))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Loja Profissional (contato@sualoja.com.br)"
    }

    # Payload padrão para 1 produto (caixa padrão)
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
                "insurance_value": float(preco_produto),
                "quantity": 1
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            opcoes = response.json()
            validas = []
            for opt in opcoes:
                # Filtra transportadoras com erro ou sem preço
                if "error" not in opt and "price" in opt:
                    validas.append({
                        "id": opt.get("id"),
                        "nome": opt.get("name"),
                        "empresa": opt.get("company", {}).get("name"),
                        "preco": float(opt.get("price")),
                        "prazo": opt.get("delivery_range", {}).get("max"),
                        "logo": opt.get("company", {}).get("picture")
                    })
            return validas
        else:
            print(f"Erro API Melhor Envio: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Erro de Conexão Frete: {e}")
        return []
