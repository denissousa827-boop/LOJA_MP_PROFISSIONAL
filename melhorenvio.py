import os
import requests

def calcular_frete(cep_destino, preco_produto, token_melhor_envio, cep_origem_config):
    """
    Calcula o frete usando a API do Melhor Envio com dados dinâmicos do Admin.
    """
    # Se não vier token do banco, tenta pegar do ambiente ou retorna erro
    token = token_melhor_envio
    cep_origem = "".join(filter(str.isdigit, str(cep_origem_config)))

    if not token or len(token) < 10:
        print("ERRO: Token do Melhor Envio não encontrado nas configurações do banco.")
        return []

    url = "https://www.melhorenvio.com.br/api/v2/me/shipment/calculate"
    cep_destino = "".join(filter(str.isdigit, str(cep_destino)))

    try:
        valor_seguro = float(preco_produto)
        if valor_seguro < 0.1: valor_seguro = 0.1
    except:
        valor_seguro = 10.0

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "LojaOnline (suporte@sualoja.com)"
    }

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
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            opcoes = response.json()
            validas = []
            for opt in opcoes:
                if "error" not in opt and "price" in opt:
                    validas.append({
                        "id": opt.get("id"),
                        "nome": opt.get("name"),
                        "empresa": opt.get("company", {}).get("name"),
                        "preco": float(opt.get("price")),
                        "prazo": opt.get("delivery_range", {}).get("max") or opt.get("delivery_time"),
                        "logo": opt.get("company", {}).get("picture")
                    })
            return sorted(validas, key=lambda x: x['preco'])
        else:
            return []
    except Exception as e:
        print(f"Erro Conexão Melhor Envio: {e}")
        return []
