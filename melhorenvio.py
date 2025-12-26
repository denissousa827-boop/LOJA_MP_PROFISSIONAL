import requests
import database

def calcular_frete(cep_destino, preco_produto):
    # Busca as configurações direto do banco de dados para ser dinâmico
    configs = database.get_configuracoes()
    
    token = configs.get('melhor_envio_token')
    cep_origem = configs.get('cep_origem', '04866220')

    if not token:
        print("Erro: Token do Melhor Envio não configurado no painel.")
        return []

    url = "https://www.melhorenvio.com.br/api/v2/me/shipment/calculate"
    
    # Limpeza de dados
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
            print(f"Erro API Melhor Envio: {response.status_code}")
            return []
    except Exception as e:
        print(f"Erro de Conexão Frete: {e}")
        return []
