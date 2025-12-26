import mercadopago

# Seu Token de Produção
ACCESS_TOKEN = "APP_USR-2222429353877099-112620-ccc34bc216b9dad3e14ec4618dbc5de3-1565971221"

def gerar_link_pagamento(produto, id_venda, valor_total):
    """
    Gera o link do Mercado Pago configurado com o túnel do Serveo.
    Agora recebe 'valor_total' que já inclui o frete calculado no checkout.
    """
    try:
        sdk = mercadopago.SDK(ACCESS_TOKEN)

        # SEU LINK DO SERVEO
        LINK_EXTERNO = "https://2899e90966eaaa2ce0f188b95ef0da2e.serveousercontent.com"

        preference_data = {
            "items": [
                {
                    "id": str(produto.get('id', '000')),
                    "title": f"{produto.get('nome', 'Produto')} + Envio",
                    "quantity": 1,
                    "unit_price": float(valor_total), # Valor final com frete
                    "currency_id": "BRL"
                }
            ],
            "external_reference": str(id_venda), 
            "back_urls": {
                "success": f"{LINK_EXTERNO}/sucesso",
                "failure": f"{LINK_EXTERNO}/erro",
                "pending": f"{LINK_EXTERNO}/erro"
            },
            "notification_url": f"{LINK_EXTERNO}/webhook", 
            "auto_return": "approved"
        }

        resultado = sdk.preference().create(preference_data)
        
        if "response" in resultado and "init_point" in resultado["response"]:
            return resultado["response"]["init_point"]
        else:
            print("Erro detalhado do MP:", resultado)
            return None

    except Exception as e:
        print(f"Erro crítico no pagamento: {e}")
        return None
