import os
import mercadopago
import database

def gerar_link_pagamento(produto, id_venda, valor_total):
    """
    Gera o link do Mercado Pago.
    Busca o token dinamicamente do banco de dados ou ambiente.
    """
    try:
        # 1. Tenta pegar o token que você salvou nas configurações da loja (Elite)
        configs = database.get_configuracoes()
        token_do_banco = configs.get('mercado_pago_token')
        
        # 2. Se não estiver no banco, tenta pegar da variável de ambiente (Vercel/Termux)
        ACCESS_TOKEN = token_do_banco if token_do_banco else os.getenv("ACCESS_TOKEN")

        if not ACCESS_TOKEN:
            print("ERRO: Access Token do Mercado Pago não encontrado!")
            return None

        # Inicializa o SDK
        sdk = mercadopago.SDK(ACCESS_TOKEN)

        # Define a URL base (Se estiver no Termux, o webhook não funcionará externamente 
        # a menos que use Ngrok, mas o link de pagamento funcionará normal)
        LINK_EXTERNO = configs.get('titulo_site', 'https://loja-mp-profissional.vercel.app')
        if not LINK_EXTERNO.startswith("http"):
            LINK_EXTERNO = "https://loja-mp-profissional.vercel.app"

        preference_data = {
            "items": [
                {
                    "id": str(produto.get('id', '000')),
                    "title": f"{produto.get('nome', 'Produto')} + Envio",
                    "quantity": 1,
                    "unit_price": float(valor_total), # Valor final calculado no main.py
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
            "auto_return": "approved",
            "payment_methods": {
                "installments": 12 # Permite até 12x
            }
        }

        # Cria a preferência de pagamento
        resultado = sdk.preference().create(preference_data)
        
        if "response" in resultado and "init_point" in resultado["response"]:
            # Retorna o link para o checkout Pro
            return resultado["response"]["init_point"]
        else:
            print("Erro detalhado do MP:", resultado)
            return None

    except Exception as e:
        print(f"Erro crítico no pagamento: {e}")
        return None
