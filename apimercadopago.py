import os
import mercadopago

# Busca o Token de Produção das variáveis de ambiente da Vercel (Segurança)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

def gerar_link_pagamento(produto, id_venda, valor_total):
    """
    Gera o link do Mercado Pago configurado para a produção na Vercel.
    O valor_total já inclui o frete calculado.
    """
    try:
        # Inicializa o SDK com o token da Vercel
        sdk = mercadopago.SDK(ACCESS_TOKEN)

        # O link oficial da sua loja na Vercel (Substituiu o Serveo)
        LINK_EXTERNO = "https://loja-mp-profissional.vercel.app"

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
