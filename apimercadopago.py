import mercadopago

# Sua Chave de Token de Produção
ACCESS_TOKEN = "APP_USR-2222429353877099-112620-ccc34bc216b9dad3e14ec4618dbc5de3-1565971221"

def gerar_link_pagamento(produto):
    sdk = mercadopago.SDK(ACCESS_TOKEN)

    # Define o preço (oferta ou normal)
    if produto.get('em_oferta') and produto.get('novo_preco'):
        preco_final = float(produto['novo_preco'])
    else:
        preco_final = float(produto['preco'])

    preference_data = {
        "items": [
            {
                "id": str(produto['id']),
                "title": str(produto['nome']),
                "quantity": 1,
                "unit_price": preco_final,
                "currency_id": "BRL"
            }
        ],
        "back_urls": {
            "success": "http://192.168.0.102:5000/sucesso",
            "failure": "http://192.168.0.102:5000/erro",
            "pending": "http://192.168.0.102:5000/erro"
        }
        # auto_return removido para evitar erro 400 em HTTP local
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        return preference.get("init_point")
    except Exception as e:
        print(f"Erro ao conectar com Mercado Pago: {e}")
        return None
