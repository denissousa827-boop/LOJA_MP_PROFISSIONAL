import mercadopago

# Seu Token de Produção
ACCESS_TOKEN = "APP_USR-2222429353877099-112620-ccc34bc216b9dad3e14ec4618dbc5de3-1565971221"

def gerar_link_pagamento(produto, id_venda):
    """
    Gera o link do Mercado Pago configurado com o túnel do Serveo.
    """
    try:
        sdk = mercadopago.SDK(ACCESS_TOKEN)

        # Define o preço (Normal ou Oferta)
        if produto.get('em_oferta') == 1 and produto.get('novo_preco'):
            preco_final = float(produto['novo_preco'])
        else:
            preco_final = float(produto['preco'])

        # SEU LINK DO SERVEO (Não mude enquanto o túnel estiver aberto)
        LINK_EXTERNO = "https://2899e90966eaaa2ce0f188b95ef0da2e.serveousercontent.com"

        preference_data = {
            "items": [
                {
                    "id": str(produto.get('id', '000')),
                    "title": str(produto.get('nome', 'Produto')),
                    "quantity": 1,
                    "unit_price": preco_final,
                    "currency_id": "BRL"
                }
            ],
            "external_reference": str(id_venda), # ID da venda para o webhook atualizar
            "back_urls": {
                "success": f"{LINK_EXTERNO}/sucesso",
                "failure": f"{LINK_EXTERNO}/erro",
                "pending": f"{LINK_EXTERNO}/erro"
            },
            "notification_url": f"{LINK_EXTERNO}/webhook", # Onde o MP avisa o pagamento
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
