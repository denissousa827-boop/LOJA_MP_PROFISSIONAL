import mercadopago
from flask import request 


# SEU ACCESS TOKEN DO MERCADO PAGO (AGORA EM MODO PRODUÇÃO)
MP_ACCESS_TOKEN = "APP_USR-2222429353877099-112620-ccc34bc216b9dad3e14ec4618dbc5de3-1565971221" 


def gerar_link_pagamento(carrinho_data, total): 
    """
    Gera a preferência de pagamento no Mercado Pago. 
    Usa request.host_url para obter a URL correta do servidor.
    """
    
    # Define a SERVER_URL dinamicamente usando o domínio real do servidor (http:// ou https://)
    SERVER_URL = request.host_url.rstrip('/') 

    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

    items_mp = []
    for item_id, item_data in carrinho_data.items():
        items_mp.append({
            "id": item_id,
            "title": item_data['nome'],
            "quantity": item_data['quantidade'],
            "currency_id": "BRL",
            "unit_price": float(item_data['preco'])
        })

    payment_data = {
        "items": items_mp,
        # ROTAS DE RETORNO USANDO O SERVER_URL dinâmico e seguro
        "back_urls": {
            "success": f"{SERVER_URL}/compracerta",
            "failure": f"{SERVER_URL}/compraerrada",
            "pending": f"{SERVER_URL}/compraerrada"
        },
        # WEBHOOK (ESSENCIAL PARA PRODUÇÃO NO RENDER/HTTPS)
        "notification_url": f"{SERVER_URL}/notificacoes_mp"
    }

    result = sdk.preference().create(payment_data)

    if "response" in result and "init_point" in result["response"]:
        link_iniciar_pagamento = result["response"]["init_point"] 
    else:
        # Imprime o erro no console do Termux para inspeção
        print(f"ERRO CRÍTICO NA API do Mercado Pago: {result}")
        link_iniciar_pagamento = f"{SERVER_URL}/compraerrada"

    return link_iniciar_pagamento
